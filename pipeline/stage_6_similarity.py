"""Stage 6 — Pairwise similarity, HDBSCAN clustering, canonical SVG selection."""

import json
import logging
import os
import shutil
import uuid

import numpy as np

from pipeline.config import (
    ARTIFACTS_DIR,
    CLUSTERS_DIR,
    EMBEDDINGS_DIR,
    HDBSCAN_MIN_CLUSTER_SIZES,
    MANIFESTS_DIR,
    SIMILARITY_DIR,
    SIMILARITY_EMBEDDING_WEIGHT,
    SIMILARITY_TAG_WEIGHT,
    SIMILARITY_TOP_N,
    SVGS_DIR,
)
from pipeline.models import MotifCluster, SimilarityEdge
from pipeline.provenance import create_provenance, load_manifest, save_manifest

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def jaccard_similarity(a: list[str], b: list[str]) -> float:
    """Jaccard similarity between two string lists treated as sets."""
    set_a, set_b = set(a), set(b)
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def combined_score(
    tag_score: float, embed_score: float, tag_w: float, embed_w: float,
) -> float:
    """Weighted blend of tag-based and embedding-based similarity."""
    return tag_score * tag_w + embed_score * embed_w


def find_medoid(embeddings: np.ndarray, centroid: np.ndarray) -> int:
    """Return index of the embedding closest (L2) to *centroid*."""
    diffs = embeddings - centroid
    dists = np.linalg.norm(diffs, axis=1)
    return int(np.argmin(dists))


# ---------------------------------------------------------------------------
# Main run
# ---------------------------------------------------------------------------

def run(artifacts_dir: str = ARTIFACTS_DIR) -> None:
    """Compute pairwise similarity, cluster with HDBSCAN, select canonical SVGs."""
    import hdbscan
    from sklearn.metrics import silhouette_score
    from sklearn.metrics.pairwise import cosine_similarity

    manifest_path = os.path.join(MANIFESTS_DIR, "stage_6_similarity.json")
    manifest = load_manifest(manifest_path)

    os.makedirs(SIMILARITY_DIR, exist_ok=True)
    os.makedirs(CLUSTERS_DIR, exist_ok=True)

    # ---- Load embeddings ----
    npz_path = os.path.join(EMBEDDINGS_DIR, "clip_embeddings.npz")
    index_path = os.path.join(EMBEDDINGS_DIR, "index.json")
    if not os.path.exists(npz_path) or not os.path.exists(index_path):
        logger.warning("Embeddings not found; run stage 5 first.")
        return

    embeddings = np.load(npz_path)["embeddings"]
    with open(index_path) as f:
        index_records = json.load(f)

    n = len(index_records)
    if n == 0:
        logger.info("No embeddings to process.")
        return

    segment_ids = [r["segment_id"] for r in index_records]
    artifact_ids = [r["artifact_id"] for r in index_records]

    # ---- Load segment metadata for SVG paths ----
    segments_dir = os.path.join(artifacts_dir, "segments")
    seg_meta: dict[str, dict] = {}
    if os.path.isdir(segments_dir):
        for art_dir_name in os.listdir(segments_dir):
            seg_dir = os.path.join(segments_dir, art_dir_name)
            if not os.path.isdir(seg_dir):
                continue
            for seg_fname in os.listdir(seg_dir):
                if not seg_fname.endswith(".json"):
                    continue
                with open(os.path.join(seg_dir, seg_fname)) as f:
                    sd = json.load(f)
                seg_meta[sd["id"]] = sd

    # ---- Load artifact tags ----
    artifact_tags: dict[str, list[str]] = {}
    if os.path.isdir(artifacts_dir):
        for fname in os.listdir(artifacts_dir):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(artifacts_dir, fname)
            if not os.path.isfile(fpath):
                continue
            with open(fpath) as f:
                data = json.load(f)
            art = data.get("artifact", {})
            artifact_tags[art.get("id", "")] = art.get("motif_tags", [])

    # Build per-segment tag list via its artifact
    seg_tags: dict[str, list[str]] = {}
    for seg_id, art_id in zip(segment_ids, artifact_ids):
        seg_tags[seg_id] = artifact_tags.get(art_id, [])

    # ---- Pairwise similarity ----
    logger.info("Computing pairwise cosine similarity for %d segments.", n)
    cos_sim = cosine_similarity(embeddings)

    all_edges: list[SimilarityEdge] = []
    per_segment_edges: dict[str, list[dict]] = {sid: [] for sid in segment_ids}

    for i in range(n):
        scores: list[tuple[int, float]] = []
        for j in range(n):
            if i == j:
                continue
            tag_sim = jaccard_similarity(seg_tags[segment_ids[i]], seg_tags[segment_ids[j]])
            embed_sim = float(cos_sim[i, j])
            combo = combined_score(tag_sim, embed_sim, SIMILARITY_TAG_WEIGHT, SIMILARITY_EMBEDDING_WEIGHT)
            scores.append((j, combo))
        scores.sort(key=lambda t: t[1], reverse=True)
        top = scores[:SIMILARITY_TOP_N]
        for j, sc in top:
            edge = SimilarityEdge(
                segment_a_id=segment_ids[i],
                segment_b_id=segment_ids[j],
                score=round(sc, 6),
                method="cosine+jaccard",
            )
            all_edges.append(edge)
            per_segment_edges[segment_ids[i]].append(edge.to_dict())

    # Save per-segment similarity
    for sid, edges in per_segment_edges.items():
        out_path = os.path.join(SIMILARITY_DIR, f"{sid}.json")
        with open(out_path, "w") as f:
            json.dump(edges, f, indent=2)
    logger.info("Saved similarity edges for %d segments.", n)

    # ---- HDBSCAN clustering ----
    logger.info("Running HDBSCAN with candidate min_cluster_sizes=%s", HDBSCAN_MIN_CLUSTER_SIZES)
    best_labels = None
    best_score = -1.0
    best_mcs = None

    for mcs in HDBSCAN_MIN_CLUSTER_SIZES:
        if mcs > n:
            continue
        clusterer = hdbscan.HDBSCAN(min_cluster_size=mcs, metric="euclidean")
        labels = clusterer.fit_predict(embeddings)
        n_clusters = len(set(labels) - {-1})
        if n_clusters < 2:
            continue
        mask = labels >= 0
        if mask.sum() < 2:
            continue
        try:
            sc = silhouette_score(embeddings[mask], labels[mask])
        except ValueError:
            continue
        logger.info("  min_cluster_size=%d  clusters=%d  silhouette=%.4f", mcs, n_clusters, sc)
        if sc > best_score:
            best_score = sc
            best_labels = labels
            best_mcs = mcs

    if best_labels is None:
        logger.warning("No valid clustering found.")
        save_manifest(manifest_path, {"status": "no_clusters", "edge_count": len(all_edges)})
        return

    logger.info("Best clustering: min_cluster_size=%d, silhouette=%.4f", best_mcs, best_score)

    # ---- Build clusters ----
    canonical_svg_dir = os.path.join(SVGS_DIR, "canonical")
    os.makedirs(canonical_svg_dir, exist_ok=True)

    cluster_ids_set = sorted(set(best_labels) - {-1})
    clusters: list[MotifCluster] = []

    for cid in cluster_ids_set:
        member_mask = best_labels == cid
        member_indices = np.where(member_mask)[0]
        member_seg_ids = [segment_ids[i] for i in member_indices]

        cluster_embeddings = embeddings[member_mask]
        centroid = cluster_embeddings.mean(axis=0)
        medoid_local = find_medoid(cluster_embeddings, centroid)
        medoid_global = member_indices[medoid_local]
        medoid_seg_id = segment_ids[medoid_global]

        # Copy medoid SVG as canonical
        canonical_svg_path = ""
        medoid_meta = seg_meta.get(medoid_seg_id, {})
        src_svg = medoid_meta.get("svg_path", "")
        if src_svg and os.path.exists(src_svg):
            dest = os.path.join(canonical_svg_dir, f"cluster_{cid}.svg")
            shutil.copy2(src_svg, dest)
            canonical_svg_path = dest

        # Auto-label from most common tags
        tag_counts: dict[str, int] = {}
        for sid in member_seg_ids:
            for t in seg_tags.get(sid, []):
                tag_counts[t] = tag_counts.get(t, 0) + 1
        top_tags = sorted(tag_counts, key=tag_counts.get, reverse=True)[:3]
        label = "+".join(top_tags) if top_tags else f"cluster_{cid}"

        prov = create_provenance(
            source_id=f"hdbscan:mcs{best_mcs}:c{cid}",
            source_url="local",
            raw_data=b"",
            license="derived",
            transformation="hdbscan_clustering",
        )
        cluster = MotifCluster(
            id=f"cluster_{cid}",
            label=label,
            member_count=len(member_seg_ids),
            centroid_embedding=centroid.tolist(),
            canonical_svg_path=canonical_svg_path,
            member_segment_ids=member_seg_ids,
            provenance=prov,
        )
        clusters.append(cluster)

        cluster_path = os.path.join(CLUSTERS_DIR, f"cluster_{cid}.json")
        with open(cluster_path, "w") as f:
            json.dump(cluster.to_dict(), f, indent=2)

    manifest["cluster_count"] = len(clusters)
    manifest["edge_count"] = len(all_edges)
    manifest["best_min_cluster_size"] = best_mcs
    manifest["silhouette_score"] = round(best_score, 4)
    save_manifest(manifest_path, manifest)

    logger.info("Stage 6 complete: %d clusters, %d edges.", len(clusters), len(all_edges))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()

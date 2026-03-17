"""Stage 7 — Static export for the web front-end."""

import json
import logging
import os
import shutil

from pipeline.config import (
    ARTIFACTS_DIR,
    CLUSTERS_DIR,
    EXPORT_DIR,
    EXPORT_SIZE_BUDGET_MB,
    MANIFESTS_DIR,
    SIMILARITY_DIR,
    SIMILARITY_EXPORT_TOP_N,
    SITES_DIR,
    SVGS_DIR,
)
from pipeline.provenance import load_manifest, save_manifest

logger = logging.getLogger(__name__)


def build_site_summary(
    site: dict, artifacts: list[dict], cluster_ids: list[str],
) -> dict:
    """Build a lightweight summary dict for a single site.

    Parameters
    ----------
    site : dict
        Site record (must contain at least ``id``, ``name``, ``region``,
        ``latitude``, ``longitude``).
    artifacts : list[dict]
        Artifacts belonging to this site.
    cluster_ids : list[str]
        Cluster ids associated with the site's artifacts.

    Returns
    -------
    dict
        Summary with keys: id, name, region, latitude, longitude,
        artifact_count, motif_tags, cluster_ids.
    """
    all_tags: set[str] = set()
    for art in artifacts:
        for t in art.get("motif_tags", []):
            all_tags.add(t)

    return {
        "id": site.get("id"),
        "name": site.get("name"),
        "region": site.get("region"),
        "latitude": site.get("latitude"),
        "longitude": site.get("longitude"),
        "artifact_count": len(artifacts),
        "motif_tags": sorted(all_tags),
        "cluster_ids": sorted(set(cluster_ids)),
    }


def _dir_size_mb(path: str) -> float:
    """Return total size of directory in megabytes."""
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path):
        for fn in filenames:
            total += os.path.getsize(os.path.join(dirpath, fn))
    return total / (1024 * 1024)


def run() -> None:
    """Export sites, artifacts, clusters, SVGs, and similarity for the web layer."""
    manifest_path = os.path.join(MANIFESTS_DIR, "stage_7_export.json")
    manifest = load_manifest(manifest_path)

    os.makedirs(EXPORT_DIR, exist_ok=True)

    # ---- Load sites ----
    sites: list[dict] = []
    if os.path.isdir(SITES_DIR):
        for fname in sorted(os.listdir(SITES_DIR)):
            if not fname.endswith(".json"):
                continue
            with open(os.path.join(SITES_DIR, fname)) as f:
                sites.append(json.load(f))
    site_by_id = {s["id"]: s for s in sites}

    # ---- Load artifacts grouped by site ----
    artifacts_by_site: dict[str, list[dict]] = {}
    all_artifacts: list[dict] = []
    if os.path.isdir(ARTIFACTS_DIR):
        for fname in sorted(os.listdir(ARTIFACTS_DIR)):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(ARTIFACTS_DIR, fname)
            if not os.path.isfile(fpath):
                continue
            with open(fpath) as f:
                data = json.load(f)
            art = data.get("artifact", data)
            all_artifacts.append(art)
            sid = art.get("site_id", "unknown")
            artifacts_by_site.setdefault(sid, []).append(art)

    # ---- Load clusters ----
    clusters: list[dict] = []
    cluster_members: dict[str, list[str]] = {}  # cluster_id -> segment_ids
    if os.path.isdir(CLUSTERS_DIR):
        for fname in sorted(os.listdir(CLUSTERS_DIR)):
            if not fname.endswith(".json"):
                continue
            with open(os.path.join(CLUSTERS_DIR, fname)) as f:
                cl = json.load(f)
            clusters.append(cl)
            cluster_members[cl["id"]] = cl.get("member_segment_ids", [])

    # Map segment_id -> artifact_id (from embeddings index)
    from pipeline.config import EMBEDDINGS_DIR

    seg_to_art: dict[str, str] = {}
    index_path = os.path.join(EMBEDDINGS_DIR, "index.json")
    if os.path.exists(index_path):
        with open(index_path) as f:
            for rec in json.load(f):
                seg_to_art[rec["segment_id"]] = rec["artifact_id"]

    # Map artifact_id -> site_id
    art_to_site: dict[str, str] = {}
    for art in all_artifacts:
        art_to_site[art.get("id", "")] = art.get("site_id", "")

    # ---- Export sites.json ----
    site_summaries: list[dict] = []
    for site in sites:
        sid = site["id"]
        arts = artifacts_by_site.get(sid, [])
        # Determine clusters relevant to this site
        site_cluster_ids: list[str] = []
        for cid, seg_ids in cluster_members.items():
            for seg_id in seg_ids:
                art_id = seg_to_art.get(seg_id, "")
                if art_to_site.get(art_id) == sid:
                    site_cluster_ids.append(cid)
                    break
        summary = build_site_summary(site, arts, site_cluster_ids)
        site_summaries.append(summary)

    sites_export_path = os.path.join(EXPORT_DIR, "sites.json")
    with open(sites_export_path, "w") as f:
        json.dump(site_summaries, f, indent=2)
    logger.info("Exported %d sites.", len(site_summaries))

    # ---- Export artifacts per site ----
    artifacts_export_dir = os.path.join(EXPORT_DIR, "artifacts")
    os.makedirs(artifacts_export_dir, exist_ok=True)
    for sid, arts in artifacts_by_site.items():
        out = os.path.join(artifacts_export_dir, f"{sid}.json")
        with open(out, "w") as f:
            json.dump(arts, f, indent=2)

    # ---- Export clusters.json ----
    clusters_export_path = os.path.join(EXPORT_DIR, "clusters.json")
    with open(clusters_export_path, "w") as f:
        json.dump(clusters, f, indent=2)
    logger.info("Exported %d clusters.", len(clusters))

    # ---- Copy SVGs ----
    svgs_export_dir = os.path.join(EXPORT_DIR, "svgs")
    for subdir in ("segments", "canonical"):
        src = os.path.join(SVGS_DIR, subdir)
        dst = os.path.join(svgs_export_dir, subdir)
        if os.path.isdir(src):
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

    # ---- Export similarity (capped) ----
    sim_export_dir = os.path.join(EXPORT_DIR, "similarity")
    os.makedirs(sim_export_dir, exist_ok=True)
    if os.path.isdir(SIMILARITY_DIR):
        for fname in sorted(os.listdir(SIMILARITY_DIR)):
            if not fname.endswith(".json"):
                continue
            with open(os.path.join(SIMILARITY_DIR, fname)) as f:
                edges = json.load(f)
            capped = edges[:SIMILARITY_EXPORT_TOP_N]
            with open(os.path.join(sim_export_dir, fname), "w") as f:
                json.dump(capped, f, indent=2)

    # ---- Export provenance per site ----
    prov_export_dir = os.path.join(EXPORT_DIR, "provenance")
    os.makedirs(prov_export_dir, exist_ok=True)
    for sid, arts in artifacts_by_site.items():
        prov_records = []
        for art in arts:
            for p in art.get("provenance", []):
                prov_records.append(p)
        out = os.path.join(prov_export_dir, f"{sid}.json")
        with open(out, "w") as f:
            json.dump(prov_records, f, indent=2)

    # ---- Size check ----
    total_mb = _dir_size_mb(EXPORT_DIR)
    over_budget = total_mb > EXPORT_SIZE_BUDGET_MB
    if over_budget:
        logger.warning(
            "Export size %.1f MB exceeds budget of %d MB!",
            total_mb, EXPORT_SIZE_BUDGET_MB,
        )
    else:
        logger.info("Export size: %.1f MB (budget: %d MB)", total_mb, EXPORT_SIZE_BUDGET_MB)

    manifest["site_count"] = len(site_summaries)
    manifest["artifact_count"] = len(all_artifacts)
    manifest["cluster_count"] = len(clusters)
    manifest["export_size_mb"] = round(total_mb, 2)
    manifest["over_budget"] = over_budget
    save_manifest(manifest_path, manifest)

    logger.info("Stage 7 export complete.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()

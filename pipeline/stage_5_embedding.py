"""Stage 5 — CLIP embeddings and motif text tagging."""

import json
import logging
import os
import re
import uuid

import numpy as np

from pipeline.config import ARTIFACTS_DIR, CLIP_MODEL, EMBEDDINGS_DIR, MANIFESTS_DIR
from pipeline.models import Embedding
from pipeline.provenance import create_provenance, load_manifest, save_manifest

logger = logging.getLogger(__name__)

# Regex patterns for motif classification from textual metadata.
# Expanded vocabulary to match museum API descriptions, AAT tag terms,
# medium/technique strings, and culture fields — not just narrow art-history terms.
MOTIF_PATTERNS: dict[str, re.Pattern] = {
    # Geometric motifs
    "spiral": re.compile(r"\bspiral\b", re.IGNORECASE),
    "meander": re.compile(r"\bmeander\b", re.IGNORECASE),
    "cross": re.compile(r"\bcross(?:es)?\b", re.IGNORECASE),
    "chevron": re.compile(r"\bchevron\b", re.IGNORECASE),
    "wave": re.compile(r"\bwave\b", re.IGNORECASE),
    "guilloche": re.compile(r"\bguilloche\b", re.IGNORECASE),
    "rosette": re.compile(r"\brosette\b", re.IGNORECASE),
    "palmette": re.compile(r"\bpalmette\b", re.IGNORECASE),
    "zigzag": re.compile(r"\bzig-?zag\b", re.IGNORECASE),
    "concentric_circles": re.compile(r"\bconcentric\s+circle", re.IGNORECASE),
    "hatching": re.compile(r"\bhatch(?:ing|ed)\b", re.IGNORECASE),
    "geometric": re.compile(r"\bgeometric\b", re.IGNORECASE),
    "floral": re.compile(r"\bfloral\b", re.IGNORECASE),
    "figural": re.compile(r"\bfigur(?:al|ative|e)\b", re.IGNORECASE),
    "animal": re.compile(r"\banimal\b", re.IGNORECASE),
    "anthropomorphic": re.compile(r"\banthropomorphic\b", re.IGNORECASE),
    # Broader decorative vocabulary (common in museum descriptions)
    "relief": re.compile(r"\brelief\b", re.IGNORECASE),
    "engraved": re.compile(r"\bengrav(?:ed|ing)\b", re.IGNORECASE),
    "painted": re.compile(r"\bpaint(?:ed|ing)\b", re.IGNORECASE),
    "carved": re.compile(r"\bcarv(?:ed|ing)\b", re.IGNORECASE),
    "mosaic": re.compile(r"\bmosaic\b", re.IGNORECASE),
    "enamel": re.compile(r"\benamel\b", re.IGNORECASE),
    "inlaid": re.compile(r"\binla(?:id|y)\b", re.IGNORECASE),
    "gilded": re.compile(r"\bgild(?:ed|ing)\b", re.IGNORECASE),
    # Ceramic technique terms (Met 'medium' field)
    "red_figure": re.compile(r"\bred[- ]figure\b", re.IGNORECASE),
    "black_figure": re.compile(r"\bblack[- ]figure\b", re.IGNORECASE),
    "cloisonne": re.compile(r"\bcloisonn[eé]\b", re.IGNORECASE),
    "terracotta": re.compile(r"\bterracotta\b", re.IGNORECASE),
    # Figurative subject terms (common in Met API tags)
    "griffin": re.compile(r"\bgriffin\b", re.IGNORECASE),
    "lion": re.compile(r"\blion\b", re.IGNORECASE),
    "horse": re.compile(r"\bhorse\b", re.IGNORECASE),
    "bird": re.compile(r"\bbird\b", re.IGNORECASE),
    "serpent": re.compile(r"\bserpent\b|\bsnake\b", re.IGNORECASE),
    "sphinx": re.compile(r"\bsphinx\b", re.IGNORECASE),
    "chariot": re.compile(r"\bchariot\b", re.IGNORECASE),
}


def extract_motif_tags(text: str) -> list[str]:
    """Extract motif tags from free text by matching against known patterns.

    Returns a sorted list of unique tag names.
    """
    tags: set[str] = set()
    for tag_name, pattern in MOTIF_PATTERNS.items():
        if pattern.search(text):
            tags.add(tag_name)
    return sorted(tags)


def compute_clip_embeddings(image_paths: list[str]) -> np.ndarray | None:
    """Compute CLIP image embeddings for a batch of images.

    Parameters
    ----------
    image_paths : list[str]
        Paths to image files.

    Returns
    -------
    np.ndarray | None
        Array of shape (N, D) with L2-normalised embeddings, or None on failure.
    """
    try:
        import torch
        from PIL import Image
        from transformers import CLIPModel, CLIPProcessor
    except ImportError as exc:
        logger.error("Missing dependency for CLIP: %s", exc)
        return None

    processor = CLIPProcessor.from_pretrained(CLIP_MODEL)
    model = CLIPModel.from_pretrained(CLIP_MODEL)
    model.set_to_inference_mode = lambda: None  # no-op
    model.requires_grad_(False)

    images = []
    for p in image_paths:
        try:
            images.append(Image.open(p).convert("RGB"))
        except Exception as exc:
            logger.warning("Cannot open %s: %s", p, exc)
            return None

    if not images:
        return None

    inputs = processor(images=images, return_tensors="pt", padding=True)
    with torch.no_grad():
        feats = model.get_image_features(**inputs)

    # L2 normalise
    feats = feats / feats.norm(dim=-1, keepdim=True)
    return feats.cpu().numpy()


def run(artifacts_dir: str = ARTIFACTS_DIR) -> None:
    """Tag artifacts via text, embed segments via CLIP, save .npz + index.json."""
    manifest_path = os.path.join(MANIFESTS_DIR, "stage_5_embedding.json")
    manifest = load_manifest(manifest_path)

    os.makedirs(EMBEDDINGS_DIR, exist_ok=True)

    # --- Text tagging pass ---
    if os.path.isdir(artifacts_dir):
        for fname in sorted(os.listdir(artifacts_dir)):
            if not fname.endswith(".json"):
                continue
            art_path = os.path.join(artifacts_dir, fname)
            with open(art_path) as f:
                data = json.load(f)

            artifact = data.get("artifact", {})
            # Build a comprehensive text blob from all available fields —
            # name, description, type, materials, and techniques — so tag
            # extraction has the widest possible surface to match against.
            text_parts = [
                artifact.get("name", ""),
                artifact.get("description", ""),
                artifact.get("type", ""),
            ]
            text_parts.extend(artifact.get("materials", []))
            text_parts.extend(artifact.get("techniques", []))
            text_blob = " ".join(filter(None, text_parts))
            tags = extract_motif_tags(text_blob)
            if tags and tags != artifact.get("motif_tags"):
                artifact["motif_tags"] = tags
                data["artifact"] = artifact
                with open(art_path, "w") as f:
                    json.dump(data, f, indent=2)

    # --- CLIP embedding pass ---
    segments_dir = os.path.join(artifacts_dir, "segments")
    if not os.path.isdir(segments_dir):
        logger.info("No segments directory found; skipping CLIP embedding.")
        return

    all_segment_ids: list[str] = []
    all_image_paths: list[str] = []
    all_artifact_ids: list[str] = []

    for art_dir_name in sorted(os.listdir(segments_dir)):
        seg_dir = os.path.join(segments_dir, art_dir_name)
        if not os.path.isdir(seg_dir):
            continue
        for seg_fname in sorted(os.listdir(seg_dir)):
            if not seg_fname.endswith(".json"):
                continue
            seg_path = os.path.join(seg_dir, seg_fname)
            with open(seg_path) as f:
                seg_data = json.load(f)
            crop_path = seg_data.get("cropped_image_path", "")
            if crop_path and os.path.exists(crop_path):
                all_segment_ids.append(seg_data["id"])
                all_image_paths.append(crop_path)
                all_artifact_ids.append(seg_data.get("artifact_id", ""))

    if not all_image_paths:
        logger.info("No segment images found for embedding.")
        return

    # Batch embed
    BATCH_SIZE = 32
    all_embeddings: list[np.ndarray] = []

    for start in range(0, len(all_image_paths), BATCH_SIZE):
        batch_paths = all_image_paths[start : start + BATCH_SIZE]
        emb = compute_clip_embeddings(batch_paths)
        if emb is not None:
            all_embeddings.append(emb)
        else:
            logger.warning("Embedding batch failed at offset %d", start)

    if not all_embeddings:
        logger.warning("No embeddings produced.")
        return

    embeddings_matrix = np.concatenate(all_embeddings, axis=0)

    # Save .npz
    npz_path = os.path.join(EMBEDDINGS_DIR, "clip_embeddings.npz")
    np.savez_compressed(npz_path, embeddings=embeddings_matrix)
    logger.info("Saved %d embeddings to %s", len(embeddings_matrix), npz_path)

    # Save index.json
    index_records: list[dict] = []
    for i, (seg_id, art_id) in enumerate(zip(all_segment_ids, all_artifact_ids)):
        prov = create_provenance(
            source_id=f"clip:{seg_id}",
            source_url="local",
            raw_data=b"",
            license="derived",
            transformation="clip_embedding",
        )
        emb_obj = Embedding(
            id=str(uuid.uuid4()),
            segment_id=seg_id,
            artifact_id=art_id,
            model=CLIP_MODEL,
            vector=embeddings_matrix[i].tolist(),
            embedding_type="clip_image",
            provenance=prov,
        )
        index_records.append(emb_obj.to_dict())

    index_path = os.path.join(EMBEDDINGS_DIR, "index.json")
    with open(index_path, "w") as f:
        json.dump(index_records, f, indent=2)

    manifest["embedding_count"] = len(index_records)
    manifest["npz_path"] = npz_path
    manifest["index_path"] = index_path
    save_manifest(manifest_path, manifest)

    logger.info("Stage 5 complete: %d embeddings indexed", len(index_records))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()

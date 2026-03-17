"""Stage 4 — CLIPSeg-based motif extraction and SVG tracing."""

import json
import logging
import os
import subprocess
import uuid

import cv2
import numpy as np

from pipeline.config import (
    ARTIFACTS_DIR,
    CLIPSEG_MODEL,
    CLIPSEG_PROMPTS,
    SEGMENT_MAX_AREA_RATIO,
    SEGMENT_MAX_ASPECT_RATIO,
    SEGMENT_MIN_AREA_RATIO,
    SEGMENT_MIN_COMPLEXITY,
    SVG_MAX_PATHS,
    SVG_MIN_PATHS,
    SVGS_DIR,
)
from pipeline.models import MotifSegment
from pipeline.provenance import create_provenance

logger = logging.getLogger(__name__)

_clipseg_model = None
_clipseg_processor = None


def _load_clipseg():
    """Lazy-load CLIPSeg model and processor (cached after first call)."""
    global _clipseg_model, _clipseg_processor
    if _clipseg_model is None:
        from transformers import CLIPSegForImageSegmentation, CLIPSegProcessor

        _clipseg_processor = CLIPSegProcessor.from_pretrained(CLIPSEG_MODEL)
        _clipseg_model = CLIPSegForImageSegmentation.from_pretrained(CLIPSEG_MODEL)
        logger.info("Loaded CLIPSeg model: %s", CLIPSEG_MODEL)
    return _clipseg_model, _clipseg_processor


def generate_masks(image, prompts: list[str]) -> np.ndarray:
    """Run CLIPSeg for each prompt, max across prompts, Otsu threshold.

    Parameters
    ----------
    image : PIL.Image
        The input image.
    prompts : list[str]
        Text prompts to segment against.

    Returns
    -------
    np.ndarray
        Binary mask (uint8, 0/255).
    """
    import torch

    model, processor = _load_clipseg()

    all_logits = []
    for prompt in prompts:
        inputs = processor(text=[prompt], images=[image], return_tensors="pt", padding=True)
        with torch.no_grad():
            outputs = model(**inputs)
        logits = torch.sigmoid(outputs.logits).squeeze().cpu().numpy()
        # Resize logits to match image size
        h, w = image.size[1], image.size[0]
        logits_resized = cv2.resize(logits, (w, h), interpolation=cv2.INTER_LINEAR)
        all_logits.append(logits_resized)

    # Max across prompts
    combined = np.max(np.stack(all_logits, axis=0), axis=0)

    # Normalize to 0-255 for Otsu
    combined_u8 = (combined * 255).astype(np.uint8)
    _, binary = cv2.threshold(combined_u8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return binary


def filter_segments(stats: np.ndarray, image_area: int) -> list[int]:
    """Filter connected-component stats by area ratio and aspect ratio.

    Parameters
    ----------
    stats : np.ndarray
        Output of cv2.connectedComponentsWithStats — shape (N, 5).
        Columns: x, y, w, h, area.  Row 0 is the background.
    image_area : int
        Total pixel count of the source image.

    Returns
    -------
    list[int]
        Indices (into *stats*) of components that pass all filters.
    """
    kept: list[int] = []
    for i in range(1, len(stats)):  # skip background at index 0
        x, y, w, h, area = stats[i]
        ratio = area / image_area
        if ratio < SEGMENT_MIN_AREA_RATIO or ratio > SEGMENT_MAX_AREA_RATIO:
            continue
        aspect = max(w, h) / max(min(w, h), 1)
        if aspect > SEGMENT_MAX_ASPECT_RATIO:
            continue
        kept.append(i)
    return kept


def count_svg_paths(svg_content: str) -> int:
    """Count ``<path`` occurrences in SVG content."""
    return svg_content.lower().count("<path")


def trace_to_svg(input_path: str, output_path: str) -> bool:
    """Convert a raster image to SVG via vtracer subprocess.

    Returns True on success, False otherwise.
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        subprocess.run(
            ["vtracer", "--input", input_path, "--output", output_path],
            check=True,
            capture_output=True,
            timeout=30,
        )
        return True
    except Exception as exc:
        logger.warning("vtracer failed for %s: %s", input_path, exc)
        return False


def segment_image(
    image,
    artifact_id: str,
    image_id: str,
) -> list[MotifSegment]:
    """Full segmentation pipeline for one image.

    Steps: generate masks -> connected components -> filter -> crop -> trace SVG -> quality gate.
    """
    binary = generate_masks(image, CLIPSEG_PROMPTS)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary)
    image_area = binary.shape[0] * binary.shape[1]

    kept_indices = filter_segments(stats, image_area)
    img_np = np.array(image.convert("RGB"))

    segments: list[MotifSegment] = []

    for idx in kept_indices:
        x, y, w, h, area = stats[idx]
        mask_component = (labels == idx).astype(np.uint8) * 255

        # Crop image and mask
        cropped_img = img_np[y : y + h, x : x + w]
        cropped_mask = mask_component[y : y + h, x : x + w]

        # Apply mask — set non-motif pixels to white
        result = cropped_img.copy()
        result[cropped_mask == 0] = 255

        # Contour complexity (perimeter)
        contours, _ = cv2.findContours(cropped_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        complexity = sum(cv2.arcLength(c, True) for c in contours)
        if complexity < SEGMENT_MIN_COMPLEXITY:
            continue

        segment_id = str(uuid.uuid4())
        crop_dir = os.path.join(ARTIFACTS_DIR, "segments", artifact_id)
        os.makedirs(crop_dir, exist_ok=True)
        crop_path = os.path.join(crop_dir, f"{segment_id}.png")
        cv2.imwrite(crop_path, cv2.cvtColor(result, cv2.COLOR_RGB2BGR))

        # Trace to SVG
        svg_path = os.path.join(SVGS_DIR, artifact_id, f"{segment_id}.svg")
        svg_ok = trace_to_svg(crop_path, svg_path)

        # Quality gate on SVG path count
        final_svg_path = None
        if svg_ok and os.path.exists(svg_path):
            with open(svg_path) as f:
                svg_content = f.read()
            n_paths = count_svg_paths(svg_content)
            if SVG_MIN_PATHS <= n_paths <= SVG_MAX_PATHS:
                final_svg_path = svg_path
            else:
                logger.debug("SVG rejected (%d paths): %s", n_paths, svg_path)

        prov = create_provenance(
            source_id=f"clipseg:{image_id}",
            source_url="local",
            raw_data=b"",
            license="derived",
            transformation="clipseg_segment",
        )

        seg = MotifSegment(
            id=segment_id,
            artifact_image_id=image_id,
            artifact_id=artifact_id,
            mask_index=idx,
            bbox=[int(x), int(y), int(w), int(h)],
            area_ratio=area / image_area,
            contour_complexity=complexity,
            cropped_image_path=crop_path,
            svg_path=final_svg_path,
            provenance=prov,
        )
        segments.append(seg)

    return segments


def run(artifacts_dir: str = ARTIFACTS_DIR) -> None:
    """Iterate artifacts, segment their images, save MotifSegment JSONs."""
    from PIL import Image

    if not os.path.isdir(artifacts_dir):
        logger.warning("Artifacts directory does not exist: %s", artifacts_dir)
        return

    segments_dir = os.path.join(artifacts_dir, "segments")
    os.makedirs(segments_dir, exist_ok=True)

    total = 0

    for fname in sorted(os.listdir(artifacts_dir)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(artifacts_dir, fname)
        with open(path) as f:
            data = json.load(f)

        artifact = data.get("artifact", {})
        artifact_id = artifact.get("id", "")
        images = data.get("images", [])

        for img_info in images:
            local_path = img_info.get("local_path", "")
            if not local_path or not os.path.exists(local_path):
                continue
            image_id = img_info.get("id", "")

            try:
                image = Image.open(local_path).convert("RGB")
            except Exception as exc:
                logger.warning("Cannot open image %s: %s", local_path, exc)
                continue

            segs = segment_image(image, artifact_id, image_id)

            # Save each segment as JSON
            out_dir = os.path.join(segments_dir, artifact_id)
            os.makedirs(out_dir, exist_ok=True)
            for seg in segs:
                seg_path = os.path.join(out_dir, f"{seg.id}.json")
                with open(seg_path, "w") as f:
                    json.dump(seg.to_dict(), f, indent=2)

            total += len(segs)
            logger.info("Segmented %s/%s: %d motifs", artifact_id, image_id, len(segs))

    logger.info("Stage 4 complete: %d total segments", total)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()

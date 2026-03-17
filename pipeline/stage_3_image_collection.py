"""Stage 3 — Image collection: download artifact images with checkpointing."""

import json
import logging
import os
import urllib.request

from pipeline.config import ARTIFACTS_DIR, IMAGES_DIR, MANIFESTS_DIR, PIPELINE_MODE
from pipeline.provenance import load_manifest, save_manifest

logger = logging.getLogger(__name__)


def download_image(url: str, output_path: str) -> bool:
    """Download a single image from *url* to *output_path*.

    Returns True on success, False on any error.
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        urllib.request.urlretrieve(url, output_path)
        logger.debug("Downloaded %s -> %s", url, output_path)
        return True
    except Exception as exc:
        logger.warning("Failed to download %s: %s", url, exc)
        return False


def run(artifacts_dir: str = ARTIFACTS_DIR) -> None:
    """Iterate artifact JSON files, download images, update local_path, save manifest."""
    manifest_path = os.path.join(MANIFESTS_DIR, "stage_3_image_collection.json")
    manifest = load_manifest(manifest_path)
    completed: set[str] = set(manifest.get("completed_images", []))

    if not os.path.isdir(artifacts_dir):
        logger.warning("Artifacts directory does not exist: %s", artifacts_dir)
        return

    for fname in sorted(os.listdir(artifacts_dir)):
        if not fname.endswith(".json"):
            continue
        artifact_path = os.path.join(artifacts_dir, fname)
        with open(artifact_path) as f:
            data = json.load(f)

        images = data.get("images", [])
        changed = False

        for img in images:
            image_id = img.get("id", "")
            if image_id in completed:
                continue

            url = img.get("source_image_url", "")
            if not url:
                continue

            if PIPELINE_MODE == "dev":
                ext = os.path.splitext(url.split("?")[0])[-1] or ".jpg"
                local_path = os.path.join(IMAGES_DIR, f"{image_id}{ext}")
                ok = download_image(url, local_path)
                if ok:
                    img["local_path"] = local_path
                    changed = True
                    completed.add(image_id)
            else:
                # Production mode placeholder — streaming / cloud storage
                logger.info("Production download not yet implemented for %s", image_id)
                continue

        if changed:
            with open(artifact_path, "w") as f:
                json.dump(data, f, indent=2)

        # Checkpoint after each artifact
        manifest["completed_images"] = sorted(completed)
        save_manifest(manifest_path, manifest)

    logger.info("Stage 3 complete: %d images downloaded", len(completed))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()

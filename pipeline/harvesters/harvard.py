"""Harvard Art Museums API harvester."""

import json
import logging
import uuid

from pipeline.config import HARVARD_API_BASE, HARVARD_API_KEY
from pipeline.api_client import CachedAPIClient
from pipeline.models import Artifact, ArtifactImage, ProvenanceRecord

logger = logging.getLogger(__name__)


def parse_harvard_object(
    raw: dict, prov: ProvenanceRecord, site_id: str, region: str
) -> tuple[Artifact, list[ArtifactImage]]:
    """Parse a Harvard Art Museums API object into Artifact + images."""
    obj_id = raw.get("id", 0)
    artifact_id = f"harv_{obj_id}"

    # Parse medium with comma split
    medium = raw.get("medium", "") or ""
    materials = [m.strip() for m in medium.split(",") if m.strip()]

    date_start = raw.get("datebegin")
    date_end = raw.get("dateend")

    artifact = Artifact(
        id=artifact_id,
        name=raw.get("title", ""),
        description=raw.get("description", "") or "",
        type=raw.get("classification", "artifact"),
        site_id=site_id,
        region=region,
        period=raw.get("period", None) or None,
        date_range_start=int(date_start) if date_start is not None else None,
        date_range_end=int(date_end) if date_end is not None else None,
        materials=materials,
        techniques=[],
        motif_tags=[],
        provenance=[prov],
    )

    images: list[ArtifactImage] = []
    primary_url = raw.get("primaryimageurl", "")
    if primary_url:
        img_id = f"img_{uuid.uuid4().hex[:12]}"
        images.append(
            ArtifactImage(
                id=img_id,
                artifact_id=artifact_id,
                source_image_url=primary_url,
                local_path="",
                provenance=prov,
            )
        )
    for img in raw.get("images", []):
        url = img.get("baseimageurl", "")
        if url and url != primary_url:
            img_id = f"img_{uuid.uuid4().hex[:12]}"
            images.append(
                ArtifactImage(
                    id=img_id,
                    artifact_id=artifact_id,
                    source_image_url=url,
                    local_path="",
                    provenance=prov,
                )
            )

    return artifact, images


def search_harvard(culture: str, client: CachedAPIClient) -> list[dict]:
    """Search Harvard Art Museums by culture, return list of object records."""
    url = f"{HARVARD_API_BASE}/object"
    params = {
        "apikey": HARVARD_API_KEY,
        "culture": culture,
        "hasimage": 1,
        "size": 100,
    }
    raw = client.get(url, params=params)
    if raw is None:
        return []
    data = json.loads(raw)
    return data.get("records", [])

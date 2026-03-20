"""Metropolitan Museum of Art API harvester."""

import json
import logging
import uuid

from pipeline.config import MET_MUSEUM_API_BASE
from pipeline.api_client import CachedAPIClient
from pipeline.models import Artifact, ArtifactImage, ProvenanceRecord

logger = logging.getLogger(__name__)


def parse_medium(medium: str) -> tuple[list[str], list[str]]:
    """Split medium string like 'Terracotta; red-figure' into (materials, techniques).

    Parts before semicolon are materials, after are techniques.
    """
    if not medium:
        return [], []
    parts = [p.strip() for p in medium.split(";")]
    materials = [parts[0]] if parts else []
    techniques = parts[1:] if len(parts) > 1 else []
    return materials, techniques


def parse_met_object(
    raw: dict, prov: ProvenanceRecord, site_id: str, region: str
) -> tuple[Artifact, list[ArtifactImage]]:
    """Parse a Met Museum API object response into Artifact + images."""
    oid = raw.get("objectID", 0)
    artifact_id = f"met_{oid}"

    materials, techniques = parse_medium(raw.get("medium", ""))

    date_start = raw.get("objectBeginDate")
    date_end = raw.get("objectEndDate")

    # Build a rich description from all available text fields.
    # The API returns structured tags (AAT vocabulary), culture, medium, and
    # objectName — combine them so downstream motif-tag extraction has
    # something meaningful to match against.
    desc_parts = [raw.get("objectName", "")]
    if raw.get("culture"):
        desc_parts.append(raw["culture"])
    if raw.get("medium"):
        desc_parts.append(raw["medium"])
    tag_terms = [t.get("term", "") for t in (raw.get("tags") or []) if t.get("term")]
    if tag_terms:
        desc_parts.append("; ".join(tag_terms))
    description = " | ".join(p for p in desc_parts if p)

    artifact = Artifact(
        id=artifact_id,
        name=raw.get("title", ""),
        description=description,
        type=raw.get("classification", "artifact"),
        site_id=site_id,
        region=region,
        period=raw.get("period", None) or None,
        date_range_start=int(date_start) if date_start is not None else None,
        date_range_end=int(date_end) if date_end is not None else None,
        materials=materials,
        techniques=techniques,
        motif_tags=[],
        provenance=[prov],
    )

    images: list[ArtifactImage] = []
    primary_url = raw.get("primaryImage", "")
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
    for url in raw.get("additionalImages", []):
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


def search_met(query: str, client: CachedAPIClient) -> list[int]:
    """Search Met Museum API, return list of objectIDs."""
    url = f"{MET_MUSEUM_API_BASE}/search"
    raw = client.get(url, params={"q": query, "hasImages": "true"})
    if raw is None:
        return []
    data = json.loads(raw)
    return data.get("objectIDs", []) or []


def fetch_met_object(oid: int, client: CachedAPIClient) -> dict | None:
    """Fetch a single Met Museum object by ID."""
    url = f"{MET_MUSEUM_API_BASE}/objects/{oid}"
    raw = client.get(url)
    if raw is None:
        return None
    return json.loads(raw)

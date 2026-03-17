"""Wikidata SPARQL harvester for ancient artifacts."""

import json
import logging
import uuid

import requests

from pipeline.config import (
    WIKIDATA_SPARQL_ENDPOINT,
    WIKIDATA_USER_AGENT,
    WIKIDATA_QUERY_TIMEOUT,
)
from pipeline.models import Artifact, ArtifactImage
from pipeline.provenance import create_provenance

logger = logging.getLogger(__name__)


def build_artifact_query(site_qid: str) -> str:
    """Build SPARQL query for artifacts discovered at a site (P189)."""
    return f"""
SELECT DISTINCT ?item ?itemLabel ?itemDescription ?material ?materialLabel
       ?image ?inception
WHERE {{
  ?item wdt:P189 wd:{site_qid} .
  OPTIONAL {{ ?item wdt:P186 ?material . }}
  OPTIONAL {{ ?item wdt:P18 ?image . }}
  OPTIONAL {{ ?item wdt:P571 ?inception . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}}
LIMIT 500
"""


def parse_inception_year(s: str | None) -> int | None:
    """Parse Wikidata inception datetime to year integer.

    Examples: "-0500-01-01T00:00:00Z" -> -500, "0100-01-01T00:00:00Z" -> 100
    """
    if not s:
        return None
    try:
        date_part = s.split("T")[0]
        if date_part.startswith("-"):
            return -int(date_part[1:].split("-")[0])
        return int(date_part.split("-")[0])
    except (ValueError, IndexError):
        return None


def parse_wikidata_artifact(
    binding: dict, site_id: str, region: str
) -> tuple[Artifact, list[ArtifactImage]]:
    """Parse a single SPARQL result binding into Artifact + images."""
    uri = binding["item"]["value"]
    qid = uri.rsplit("/", 1)[-1]
    artifact_id = f"wd_{qid}"

    name = binding.get("itemLabel", {}).get("value", qid)
    description = binding.get("itemDescription", {}).get("value", "")

    materials = []
    mat_label = binding.get("materialLabel", {}).get("value")
    if mat_label:
        materials = [mat_label]

    inception_year = parse_inception_year(
        binding.get("inception", {}).get("value")
    )

    raw_bytes = json.dumps(binding).encode()
    prov = create_provenance(
        source_id="wikidata",
        source_url=uri,
        raw_data=raw_bytes,
        license="CC0-1.0",
        transformation="sparql_binding_parse",
    )

    artifact = Artifact(
        id=artifact_id,
        name=name,
        description=description,
        type="artifact",
        site_id=site_id,
        region=region,
        period=None,
        date_range_start=inception_year,
        date_range_end=inception_year,
        materials=materials,
        techniques=[],
        motif_tags=[],
        provenance=[prov],
    )

    images: list[ArtifactImage] = []
    image_url = binding.get("image", {}).get("value")
    if image_url:
        img_id = f"img_{uuid.uuid4().hex[:12]}"
        img_prov = create_provenance(
            source_id="wikidata",
            source_url=image_url,
            raw_data=image_url.encode(),
            license="CC0-1.0",
            transformation="image_ref",
        )
        images.append(
            ArtifactImage(
                id=img_id,
                artifact_id=artifact_id,
                source_image_url=image_url,
                local_path="",
                provenance=img_prov,
            )
        )

    return artifact, images


def query_artifacts_for_site(site_qid: str) -> list[dict]:
    """Execute SPARQL query and return bindings list."""
    query = build_artifact_query(site_qid)
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": WIKIDATA_USER_AGENT,
    }
    try:
        resp = requests.get(
            WIKIDATA_SPARQL_ENDPOINT,
            params={"query": query},
            headers=headers,
            timeout=WIKIDATA_QUERY_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", {}).get("bindings", [])
    except requests.RequestException as e:
        logger.warning("Wikidata SPARQL query failed for %s: %s", site_qid, e)
        return []

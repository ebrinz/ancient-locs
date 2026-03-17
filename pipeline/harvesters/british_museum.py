"""British Museum SPARQL harvester using CIDOC-CRM ontology."""

import json
import logging
import uuid

import requests

from pipeline.config import BM_SPARQL_ENDPOINT
from pipeline.models import Artifact, ArtifactImage
from pipeline.provenance import create_provenance

logger = logging.getLogger(__name__)


def build_bm_query(lat: float, lng: float, radius_km: float) -> str:
    """Build SPARQL query for BM objects found near coordinates using CIDOC-CRM."""
    return f"""
PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>
PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bmo: <http://collection.britishmuseum.org/id/ontology/>

SELECT DISTINCT ?object ?label ?description ?material ?materialLabel ?image
WHERE {{
  ?object a crm:E22_Man-Made_Object .
  ?object crm:P16i_was_used_for ?production .
  ?production crm:P7_took_place_at ?place .
  ?place geo:lat ?lat .
  ?place geo:long ?long .
  FILTER(
    ABS(?lat - {lat}) < {radius_km / 111.0} &&
    ABS(?long - {lng}) < {radius_km / 111.0}
  )
  OPTIONAL {{ ?object rdfs:label ?label . }}
  OPTIONAL {{ ?object crm:P3_has_note ?description . }}
  OPTIONAL {{
    ?object crm:P45_consists_of ?material .
    ?material rdfs:label ?materialLabel .
  }}
  OPTIONAL {{ ?object bmo:PX_has_main_representation ?image . }}
}}
LIMIT 500
"""


def parse_bm_result(
    binding: dict, site_id: str, region: str
) -> tuple[Artifact, list[ArtifactImage]]:
    """Parse a BM SPARQL binding into Artifact + images."""
    uri = binding["object"]["value"]
    # Extract ID from URI like http://collection.britishmuseum.org/id/object/XXX
    bm_id = uri.rsplit("/", 1)[-1]
    artifact_id = f"bm_{bm_id}"

    name = binding.get("label", {}).get("value", bm_id)
    description = binding.get("description", {}).get("value", "")

    materials = []
    mat_label = binding.get("materialLabel", {}).get("value")
    if mat_label:
        materials = [mat_label]

    raw_bytes = json.dumps(binding).encode()
    prov = create_provenance(
        source_id="british_museum",
        source_url=uri,
        raw_data=raw_bytes,
        license="CC-BY-NC-SA-4.0",
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
        date_range_start=None,
        date_range_end=None,
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
            source_id="british_museum",
            source_url=image_url,
            raw_data=image_url.encode(),
            license="CC-BY-NC-SA-4.0",
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


def query_bm_artifacts(lat: float, lng: float, radius_km: float) -> list[dict]:
    """Execute BM SPARQL query, return bindings list. Fails gracefully."""
    query = build_bm_query(lat, lng, radius_km)
    headers = {"Accept": "application/sparql-results+json"}
    try:
        resp = requests.get(
            BM_SPARQL_ENDPOINT,
            params={"query": query},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", {}).get("bindings", [])
    except requests.RequestException as e:
        logger.warning("British Museum SPARQL query failed: %s", e)
        return []

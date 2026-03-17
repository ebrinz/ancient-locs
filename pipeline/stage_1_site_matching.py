"""Stage 1: Site matching with Wikidata SPARQL and fuzzy name scoring."""

import json
import os
import time

import Levenshtein
from SPARQLWrapper import SPARQLWrapper, JSON

from pipeline.config import (
    RAW_PLACES,
    SITES_DIR,
    MANIFESTS_DIR,
    WIKIDATA_SPARQL_ENDPOINT,
    WIKIDATA_USER_AGENT,
    WIKIDATA_QUERY_TIMEOUT,
    SITE_MATCH_RADIUS_KM,
    SITE_NAME_FUZZY_THRESHOLD,
    PIPELINE_MODE,
    DEV_MAX_SITES,
)
from pipeline.models import Site
from pipeline.provenance import load_manifest, save_manifest


def load_raw_sites(path: str) -> list[Site]:
    """Load places.json and return a list of Site objects."""
    with open(path) as f:
        raw_list = json.load(f)
    return [Site.from_raw(raw) for raw in raw_list]


def save_site(site: Site, output_dir: str) -> str:
    """Save a Site as JSON to output_dir/{id}.json. Returns the file path."""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{site.id}.json")
    with open(path, "w") as f:
        json.dump(site.to_dict(), f, indent=2)
    return path


def build_wikidata_query(lat: float, lng: float, radius_km: float) -> str:
    """Build a SPARQL query for nearby archaeological sites."""
    return f"""SELECT ?item ?itemLabel ?pleiades WHERE {{
  SERVICE wikibase:around {{
    ?item wdt:P625 ?loc .
    bd:serviceParam wikibase:center "Point({lng} {lat})"^^geo:wktLiteral .
    bd:serviceParam wikibase:radius "{radius_km}" .
  }}
  ?item wdt:P31/wdt:P279* wd:Q839954 .
  OPTIONAL {{ ?item wdt:P1584 ?pleiades . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}}"""


def score_match(site_name: str | None, candidate_name: str | None) -> float:
    """Score a candidate name against a site name.

    Returns 1.0 for exact match (case-insensitive), a fuzzy score between
    0.0 and 1.0 based on Levenshtein distance if within the configured
    threshold, or 0.0 otherwise.
    """
    if site_name is None or candidate_name is None:
        return 0.0

    site_lower = site_name.lower().strip()
    cand_lower = candidate_name.lower().strip()

    if site_lower == cand_lower:
        return 1.0

    distance = Levenshtein.distance(site_lower, cand_lower)
    if distance <= SITE_NAME_FUZZY_THRESHOLD:
        return max(0.0, 1.0 - distance / max(len(site_lower), len(cand_lower), 1))

    return 0.0


def query_wikidata(lat: float, lng: float, radius_km: float) -> list[dict]:
    """Execute a SPARQL query against Wikidata and return candidate sites.

    Returns a list of dicts with keys: qid, label, pleiades.
    """
    sparql = SPARQLWrapper(WIKIDATA_SPARQL_ENDPOINT)
    sparql.setQuery(build_wikidata_query(lat, lng, radius_km))
    sparql.setReturnFormat(JSON)
    sparql.setTimeout(WIKIDATA_QUERY_TIMEOUT)
    sparql.addCustomHttpHeader("User-Agent", WIKIDATA_USER_AGENT)

    results = sparql.query().convert()

    candidates = []
    for binding in results["results"]["bindings"]:
        qid = binding["item"]["value"].rsplit("/", 1)[-1]
        label = binding.get("itemLabel", {}).get("value")
        pleiades = binding.get("pleiades", {}).get("value")
        candidates.append({"qid": qid, "label": label, "pleiades": pleiades})

    return candidates


def match_site(site: Site) -> Site:
    """Query Wikidata for candidates near the site, score them, and pick the best match."""
    candidates = query_wikidata(site.latitude, site.longitude, SITE_MATCH_RADIUS_KM)

    best_score = 0.0
    best_candidate = None

    for candidate in candidates:
        score = score_match(site.name, candidate.get("label"))
        if score > best_score:
            best_score = score
            best_candidate = candidate

    if best_candidate and best_score > 0.0:
        site.external_ids["wikidata"] = best_candidate["qid"]
        if best_candidate.get("pleiades"):
            site.external_ids["pleiades"] = best_candidate["pleiades"]

    return site


def run(input_path: str | None = None, output_dir: str | None = None) -> None:
    """Main runner for Stage 1.

    Features manifest-based idempotency, 1-second rate limiting between
    Wikidata queries, and dev-mode batch limiting.
    """
    input_path = input_path or RAW_PLACES
    output_dir = output_dir or SITES_DIR

    manifest_path = os.path.join(MANIFESTS_DIR, "stage_1.json")
    manifest = load_manifest(manifest_path)
    processed_ids: set[str] = set(manifest.get("processed", []))

    sites = load_raw_sites(input_path)

    if PIPELINE_MODE == "dev":
        sites = sites[:DEV_MAX_SITES]

    for i, site in enumerate(sites):
        if site.id in processed_ids:
            continue

        site = match_site(site)
        save_site(site, output_dir)

        processed_ids.add(site.id)
        manifest["processed"] = list(processed_ids)
        save_manifest(manifest_path, manifest)

        # Rate limit: 1 second between Wikidata queries
        if i < len(sites) - 1:
            time.sleep(1)

    print(f"Stage 1 complete: {len(processed_ids)} sites processed.")

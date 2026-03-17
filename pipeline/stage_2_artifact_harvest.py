"""Stage 2 — Artifact harvesting from 5 sources with deduplication."""

import json
import logging
import os
from datetime import datetime, timezone

from pipeline.api_client import CachedAPIClient
from pipeline.config import (
    ARTIFACTS_DIR,
    BM_RATE_LIMIT,
    DEV_MAX_ARTIFACTS_PER_SITE,
    HARVARD_API_KEY,
    MANIFESTS_DIR,
    MET_MUSEUM_RATE_LIMIT,
    PIPELINE_MODE,
    RAW_DIR,
    SITE_MATCH_RADIUS_KM,
    SITES_DIR,
)
from pipeline.dedup import deduplicate_artifacts
from pipeline.harvesters.british_museum import parse_bm_result, query_bm_artifacts
from pipeline.harvesters.harvard import parse_harvard_object, search_harvard
from pipeline.harvesters.met import fetch_met_object, parse_met_object, search_met
from pipeline.harvesters.wikidata import parse_wikidata_artifact, query_artifacts_for_site
from pipeline.harvesters.wikimedia_commons import (
    COMMONS_CATEGORIES,
    parse_commons_file,
    search_commons_category,
)
from pipeline.models import Artifact, ArtifactImage, Site
from pipeline.provenance import load_manifest, save_manifest

logger = logging.getLogger(__name__)


def load_enriched_sites(sites_dir: str) -> list[Site]:
    """Load Site objects from JSON files in the sites directory."""
    sites: list[Site] = []
    if not os.path.isdir(sites_dir):
        logger.warning("Sites directory does not exist: %s", sites_dir)
        return sites
    for fname in sorted(os.listdir(sites_dir)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(sites_dir, fname)
        with open(path) as f:
            data = json.load(f)
        site = Site(**data)
        sites.append(site)
    return sites


def save_artifact(artifact: Artifact, images: list[ArtifactImage], output_dir: str) -> None:
    """Save an artifact and its images as a single JSON file."""
    os.makedirs(output_dir, exist_ok=True)
    payload = {
        "artifact": artifact.to_dict(),
        "images": [img.to_dict() for img in images],
    }
    path = os.path.join(output_dir, f"{artifact.id}.json")
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)


def harvest_site(
    site: Site,
    met_client: CachedAPIClient,
    harvard_client: CachedAPIClient,
    commons_client: CachedAPIClient,
) -> list[tuple[Artifact, list[ArtifactImage]]]:
    """Query all 5 sources for artifacts related to a site, deduplicate, return results."""
    all_artifacts: list[Artifact] = []
    all_images: dict[str, list[ArtifactImage]] = {}

    def _collect(art: Artifact, imgs: list[ArtifactImage]) -> None:
        all_artifacts.append(art)
        all_images[art.id] = imgs

    # 1) Wikidata
    wikidata_qid = (site.external_ids or {}).get("wikidata")
    if wikidata_qid:
        bindings = query_artifacts_for_site(wikidata_qid)
        for binding in bindings:
            art, imgs = parse_wikidata_artifact(binding, site.id, site.region)
            _collect(art, imgs)
        logger.info("Wikidata: %d artifacts for %s", len(bindings), site.name)

    # 2) Met Museum
    if site.name:
        met_ids = search_met(site.name, met_client)
        for oid in met_ids[:50]:
            raw = fetch_met_object(oid, met_client)
            if raw is None:
                continue
            prov = met_client.create_provenance(
                source_url=f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}",
                raw_data=json.dumps(raw).encode(),
                license="CC0-1.0",
                transformation="met_api_parse",
            )
            art, imgs = parse_met_object(raw, prov, site.id, site.region)
            _collect(art, imgs)
        logger.info("Met Museum: %d object IDs for %s", len(met_ids), site.name)

    # 3) Harvard Art Museums
    if site.region:
        records = search_harvard(site.region, harvard_client)
        for rec in records:
            prov = harvard_client.create_provenance(
                source_url=f"https://api.harvardartmuseums.org/object/{rec.get('id', 0)}",
                raw_data=json.dumps(rec).encode(),
                license="fair-use",
                transformation="harvard_api_parse",
            )
            art, imgs = parse_harvard_object(rec, prov, site.id, site.region)
            _collect(art, imgs)
        logger.info("Harvard: %d records for %s", len(records), site.name)

    # 4) British Museum
    bindings = query_bm_artifacts(site.latitude, site.longitude, SITE_MATCH_RADIUS_KM)
    for binding in bindings:
        art, imgs = parse_bm_result(binding, site.id, site.region)
        _collect(art, imgs)
    logger.info("British Museum: %d bindings for %s", len(bindings), site.name)

    # 5) Wikimedia Commons (site-specific search using site name)
    if site.name:
        pages = search_commons_category(site.name, commons_client)
        for page in pages:
            art, imgs = parse_commons_file(page, site.id, site.region)
            _collect(art, imgs)
        logger.info("Wikimedia Commons: %d pages for %s", len(pages), site.name)

    # Deduplicate
    deduped = deduplicate_artifacts(all_artifacts)

    # Cap in dev mode
    if PIPELINE_MODE == "dev":
        deduped = deduped[:DEV_MAX_ARTIFACTS_PER_SITE]

    # Pair back with images
    results = []
    for art in deduped:
        imgs = all_images.get(art.id, [])
        results.append((art, imgs))

    return results


def run(sites_dir: str = SITES_DIR, output_dir: str = ARTIFACTS_DIR) -> None:
    """Main Stage 2 runner: harvest artifacts for all enriched sites."""
    manifest_path = os.path.join(MANIFESTS_DIR, "stage_2_artifact_harvest.json")
    manifest = load_manifest(manifest_path)

    sites = load_enriched_sites(sites_dir)
    logger.info("Loaded %d enriched sites", len(sites))

    cache_dir = os.path.join(RAW_DIR, "api_cache")
    met_client = CachedAPIClient("met_museum", cache_dir, rate_limit=MET_MUSEUM_RATE_LIMIT)
    harvard_client = CachedAPIClient("harvard", cache_dir, rate_limit=1.0)
    commons_client = CachedAPIClient("wikimedia_commons", cache_dir, rate_limit=1.0)

    total_artifacts = 0

    # Harvest per-site artifacts
    for site in sites:
        if site.id in manifest.get("completed_sites", {}):
            logger.info("Skipping already-harvested site %s", site.name)
            continue

        results = harvest_site(site, met_client, harvard_client, commons_client)
        for art, imgs in results:
            save_artifact(art, imgs, output_dir)
            total_artifacts += 1

        manifest.setdefault("completed_sites", {})[site.id] = {
            "name": site.name,
            "artifact_count": len(results),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        save_manifest(manifest_path, manifest)

    # Harvest Wikimedia Commons categories independently
    if "commons_categories" not in manifest.get("completed_sources", {}):
        commons_count = 0
        for category in COMMONS_CATEGORIES:
            pages = search_commons_category(category, commons_client)
            for page in pages:
                art, imgs = parse_commons_file(page, site_id="commons", region="global")
                save_artifact(art, imgs, output_dir)
                commons_count += 1
        total_artifacts += commons_count
        manifest.setdefault("completed_sources", {})["commons_categories"] = {
            "category_count": len(COMMONS_CATEGORIES),
            "artifact_count": commons_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        save_manifest(manifest_path, manifest)
        logger.info("Wikimedia Commons categories: %d artifacts", commons_count)

    logger.info("Stage 2 complete: %d total artifacts saved", total_artifacts)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()

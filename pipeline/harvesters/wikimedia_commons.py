"""Wikimedia Commons category harvester via MediaWiki API."""

import json
import logging
import uuid

from pipeline.config import WIKIMEDIA_API_BASE, WIKIMEDIA_USER_AGENT
from pipeline.api_client import CachedAPIClient
from pipeline.models import Artifact, ArtifactImage
from pipeline.provenance import create_provenance

logger = logging.getLogger(__name__)

COMMONS_CATEGORIES = [
    "Ancient art",
    "Petroglyphs",
    "Cave paintings",
    "Archaeological artifacts",
    "Ancient pottery",
    "Relief sculptures",
    "Ancient mosaics",
]


def parse_commons_file(
    page: dict, site_id: str, region: str
) -> tuple[Artifact, list[ArtifactImage]]:
    """Parse a MediaWiki API page result into Artifact + images."""
    pageid = page.get("pageid", 0)
    artifact_id = f"wmc_{pageid}"
    title = page.get("title", "").replace("File:", "")

    # Extract imageinfo
    imageinfo = page.get("imageinfo", [{}])[0] if page.get("imageinfo") else {}
    image_url = imageinfo.get("url", "")

    # Extract extmetadata for description and license
    extmeta = imageinfo.get("extmetadata", {})
    description = extmeta.get("ImageDescription", {}).get("value", "")
    license_name = extmeta.get("LicenseShortName", {}).get("value", "unknown")

    raw_bytes = json.dumps(page).encode()
    prov = create_provenance(
        source_id="wikimedia_commons",
        source_url=f"https://commons.wikimedia.org/wiki/File:{title}",
        raw_data=raw_bytes,
        license=license_name,
        transformation="mediawiki_parse",
    )

    artifact = Artifact(
        id=artifact_id,
        name=title,
        description=description,
        type="image",
        site_id=site_id,
        region=region,
        period=None,
        date_range_start=None,
        date_range_end=None,
        materials=[],
        techniques=[],
        motif_tags=[],
        provenance=[prov],
    )

    images: list[ArtifactImage] = []
    if image_url:
        img_id = f"img_{uuid.uuid4().hex[:12]}"
        img_prov = create_provenance(
            source_id="wikimedia_commons",
            source_url=image_url,
            raw_data=image_url.encode(),
            license=license_name,
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


def search_commons_category(
    category: str, client: CachedAPIClient
) -> list[dict]:
    """Query Wikimedia Commons for files in a category via MediaWiki API."""
    params = {
        "action": "query",
        "format": "json",
        "generator": "categorymembers",
        "gcmtitle": f"Category:{category}",
        "gcmtype": "file",
        "gcmlimit": 50,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
    }
    headers = {"User-Agent": WIKIMEDIA_USER_AGENT}
    raw = client.get(WIKIMEDIA_API_BASE, params=params, headers=headers)
    if raw is None:
        return []
    data = json.loads(raw)
    pages = data.get("query", {}).get("pages", {})
    return list(pages.values())

"""Tests for all 5 harvester parsers and query builders."""

import pytest

from pipeline.models import ProvenanceRecord
from pipeline.harvesters.wikidata import (
    build_artifact_query,
    parse_inception_year,
    parse_wikidata_artifact,
)
from pipeline.harvesters.met import parse_medium, parse_met_object
from pipeline.harvesters.british_museum import build_bm_query, parse_bm_result
from pipeline.harvesters.harvard import parse_harvard_object
from pipeline.harvesters.wikimedia_commons import (
    COMMONS_CATEGORIES,
    parse_commons_file,
)


def _prov(source: str) -> ProvenanceRecord:
    """Helper to create a test ProvenanceRecord."""
    return ProvenanceRecord(
        source_id=source,
        source_url=f"https://example.com/{source}",
        fetch_date="2026-01-01T00:00:00+00:00",
        license="CC0-1.0",
        raw_response_hash="abc123",
        transformation="test",
    )


# ─── Wikidata ────────────────────────────────────────────────────────────────


class TestWikidata:
    def test_build_query_contains_site_qid(self):
        query = build_artifact_query("Q12345")
        assert "Q12345" in query
        assert "P189" in query
        assert "LIMIT 500" in query

    def test_parse_inception_year_negative(self):
        assert parse_inception_year("-0500-01-01T00:00:00Z") == -500

    def test_parse_inception_year_positive(self):
        assert parse_inception_year("0100-01-01T00:00:00Z") == 100

    def test_parse_inception_year_none(self):
        assert parse_inception_year(None) is None

    def test_parse_inception_year_invalid(self):
        assert parse_inception_year("not-a-date") is None

    def test_parse_wikidata_artifact(self):
        binding = {
            "item": {"value": "http://www.wikidata.org/entity/Q999"},
            "itemLabel": {"value": "Gold Mask"},
            "itemDescription": {"value": "A golden funerary mask"},
            "materialLabel": {"value": "gold"},
            "image": {"value": "https://commons.wikimedia.org/img/mask.jpg"},
            "inception": {"value": "-0500-01-01T00:00:00Z"},
        }
        artifact, images = parse_wikidata_artifact(binding, "site_1", "Mediterranean")
        assert artifact.id == "wd_Q999"
        assert artifact.name == "Gold Mask"
        assert artifact.materials == ["gold"]
        assert artifact.date_range_start == -500
        assert artifact.site_id == "site_1"
        assert artifact.region == "Mediterranean"
        assert len(images) == 1
        assert images[0].artifact_id == "wd_Q999"
        assert images[0].id.startswith("img_")

    def test_parse_wikidata_artifact_no_image(self):
        binding = {
            "item": {"value": "http://www.wikidata.org/entity/Q888"},
            "itemLabel": {"value": "Bronze Ring"},
        }
        artifact, images = parse_wikidata_artifact(binding, "site_2", "Levant")
        assert artifact.id == "wd_Q888"
        assert len(images) == 0


# ─── Met Museum ──────────────────────────────────────────────────────────────


class TestMet:
    def test_parse_medium_with_technique(self):
        materials, techniques = parse_medium("Terracotta; red-figure")
        assert materials == ["Terracotta"]
        assert techniques == ["red-figure"]

    def test_parse_medium_empty(self):
        materials, techniques = parse_medium("")
        assert materials == []
        assert techniques == []

    def test_parse_medium_no_technique(self):
        materials, techniques = parse_medium("Bronze")
        assert materials == ["Bronze"]
        assert techniques == []

    def test_parse_met_object(self):
        raw = {
            "objectID": 42,
            "title": "Amphora",
            "objectName": "Vessel",
            "classification": "Ceramics",
            "medium": "Terracotta; black-figure",
            "period": "Archaic",
            "objectBeginDate": -600,
            "objectEndDate": -500,
            "primaryImage": "https://met.org/img/amphora.jpg",
            "additionalImages": ["https://met.org/img/amphora_2.jpg"],
        }
        prov = _prov("met")
        artifact, images = parse_met_object(raw, prov, "site_3", "Greece")
        assert artifact.id == "met_42"
        assert artifact.name == "Amphora"
        assert artifact.materials == ["Terracotta"]
        assert artifact.techniques == ["black-figure"]
        assert artifact.date_range_start == -600
        assert artifact.period == "Archaic"
        assert len(images) == 2


# ─── British Museum ──────────────────────────────────────────────────────────


class TestBritishMuseum:
    def test_build_bm_query_contains_coords(self):
        query = build_bm_query(51.5, -0.1, 5.0)
        assert "51.5" in query
        assert "-0.1" in query
        assert "geo:lat" in query
        assert "CIDOC" in query.lower() or "crm" in query.lower()

    def test_parse_bm_result(self):
        binding = {
            "object": {
                "value": "http://collection.britishmuseum.org/id/object/GAA7890"
            },
            "label": {"value": "Stone Axe"},
            "description": {"value": "Neolithic polished axe"},
            "materialLabel": {"value": "flint"},
            "image": {"value": "https://bm.org/img/axe.jpg"},
        }
        artifact, images = parse_bm_result(binding, "site_4", "Britain")
        assert artifact.id == "bm_GAA7890"
        assert artifact.name == "Stone Axe"
        assert artifact.materials == ["flint"]
        assert len(images) == 1

    def test_parse_bm_result_no_image(self):
        binding = {
            "object": {
                "value": "http://collection.britishmuseum.org/id/object/XYZ123"
            },
        }
        artifact, images = parse_bm_result(binding, "site_5", "Egypt")
        assert artifact.id == "bm_XYZ123"
        assert len(images) == 0


# ─── Harvard ─────────────────────────────────────────────────────────────────


class TestHarvard:
    def test_parse_harvard_object(self):
        raw = {
            "id": 55,
            "title": "Kylix",
            "description": "Drinking cup with painted motif",
            "classification": "Vessels",
            "medium": "Ceramic, pigment, slip",
            "period": "Classical",
            "datebegin": -450,
            "dateend": -400,
            "primaryimageurl": "https://harvard.edu/img/kylix.jpg",
            "images": [
                {"baseimageurl": "https://harvard.edu/img/kylix_alt.jpg"},
            ],
        }
        prov = _prov("harvard")
        artifact, images = parse_harvard_object(raw, prov, "site_6", "Greece")
        assert artifact.id == "harv_55"
        assert artifact.name == "Kylix"
        assert artifact.materials == ["Ceramic", "pigment", "slip"]
        assert artifact.date_range_start == -450
        assert len(images) == 2

    def test_parse_harvard_object_no_images(self):
        raw = {"id": 99, "title": "Fragment", "medium": ""}
        prov = _prov("harvard")
        artifact, images = parse_harvard_object(raw, prov, "site_7", "Levant")
        assert artifact.id == "harv_99"
        assert artifact.materials == []
        assert len(images) == 0


# ─── Wikimedia Commons ───────────────────────────────────────────────────────


class TestWikimediaCommons:
    def test_commons_categories_list(self):
        assert len(COMMONS_CATEGORIES) == 7
        assert "Petroglyphs" in COMMONS_CATEGORIES

    def test_parse_commons_file(self):
        page = {
            "pageid": 12345,
            "title": "File:Ancient_vase.jpg",
            "imageinfo": [
                {
                    "url": "https://upload.wikimedia.org/ancient_vase.jpg",
                    "extmetadata": {
                        "ImageDescription": {"value": "An ancient Greek vase"},
                        "LicenseShortName": {"value": "CC BY-SA 4.0"},
                    },
                }
            ],
        }
        artifact, images = parse_commons_file(page, "site_8", "Greece")
        assert artifact.id == "wmc_12345"
        assert artifact.name == "Ancient_vase.jpg"
        assert artifact.description == "An ancient Greek vase"
        assert len(images) == 1
        assert images[0].source_image_url == "https://upload.wikimedia.org/ancient_vase.jpg"

    def test_parse_commons_file_no_imageinfo(self):
        page = {"pageid": 99999, "title": "File:Missing.jpg"}
        artifact, images = parse_commons_file(page, "site_9", "Unknown")
        assert artifact.id == "wmc_99999"
        assert len(images) == 0

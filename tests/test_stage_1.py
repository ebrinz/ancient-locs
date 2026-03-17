"""Tests for Stage 1: site matching."""

import json
import os
import tempfile

from pipeline.models import Site
from pipeline.stage_1_site_matching import (
    load_raw_sites,
    save_site,
    build_wikidata_query,
    score_match,
)


SAMPLE_RAW_SITES = [
    {
        "id": "100",
        "name": "Abdera",
        "other_names": None,
        "modern_names": None,
        "region": "Aegean",
        "section": None,
        "latitude": "40.93 N",
        "longitude": "24.97 E",
        "status": "Accurate location",
        "info": None,
        "sources": None,
    },
    {
        "id": "200",
        "name": "Olympia",
        "other_names": None,
        "modern_names": None,
        "region": "Peloponnesos",
        "section": None,
        "latitude": "37.64 N",
        "longitude": "21.63 E",
        "status": "Accurate location",
        "info": None,
        "sources": None,
    },
]


class TestLoadRawSites:
    def test_returns_site_objects(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(SAMPLE_RAW_SITES, f)
            f.flush()
            path = f.name

        try:
            sites = load_raw_sites(path)
            assert len(sites) == 2
            assert isinstance(sites[0], Site)
            assert sites[0].id == "100"
            assert sites[0].name == "Abdera"
            assert sites[0].latitude == 40.93
            assert sites[1].id == "200"
            assert sites[1].name == "Olympia"
        finally:
            os.unlink(path)


class TestSaveSite:
    def test_saves_json_file(self):
        site = Site(
            id="100",
            name="Abdera",
            other_names=None,
            modern_names=None,
            region="Aegean",
            section=None,
            latitude=40.93,
            longitude=24.97,
            status="Accurate location",
            info=None,
            sources=None,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = save_site(site, tmpdir)
            assert path == os.path.join(tmpdir, "100.json")
            assert os.path.exists(path)

            with open(path) as f:
                data = json.load(f)
            assert data["id"] == "100"
            assert data["name"] == "Abdera"
            assert data["external_ids"]["wikidata"] is None


class TestBuildWikidataQuery:
    def test_query_contains_coordinates_and_radius(self):
        query = build_wikidata_query(40.93, 24.97, 5.0)
        assert "Point(24.97 40.93)" in query
        assert '"5.0"' in query
        assert "wdt:P625" in query
        assert "wdt:P31/wdt:P279*" in query
        assert "wd:Q839954" in query
        assert "wdt:P1584" in query


class TestScoreMatch:
    def test_exact_match(self):
        assert score_match("Abdera", "Abdera") == 1.0

    def test_exact_match_case_insensitive(self):
        assert score_match("Abdera", "abdera") == 1.0

    def test_close_match(self):
        score = score_match("Abdera", "Abderra")
        assert 0.0 < score < 1.0

    def test_none_site_name(self):
        assert score_match(None, "Abdera") == 0.0

    def test_none_candidate_name(self):
        assert score_match("Abdera", None) == 0.0

    def test_no_match(self):
        assert score_match("Abdera", "Completely Different Name") == 0.0

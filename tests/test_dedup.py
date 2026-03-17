"""Tests for pipeline.dedup module."""

from pipeline.dedup import deduplicate_artifacts, _is_dup, _priority
from pipeline.models import Artifact, ProvenanceRecord


def _make_prov(source_id: str) -> ProvenanceRecord:
    return ProvenanceRecord(
        source_id=source_id,
        source_url="http://example.com",
        fetch_date="2026-01-01T00:00:00Z",
        license="CC0",
        raw_response_hash="abc123",
        transformation="test",
    )


def _make_artifact(name: str, source_id: str, site_id: str = "site_1",
                   date_start: int | None = -500, date_end: int | None = -300) -> Artifact:
    return Artifact(
        id=f"{source_id}_{name.replace(' ', '_')}",
        name=name,
        description="",
        type="artifact",
        site_id=site_id,
        region="Mesopotamia",
        period=None,
        date_range_start=date_start,
        date_range_end=date_end,
        materials=[],
        techniques=[],
        motif_tags=[],
        provenance=[_make_prov(source_id)],
    )


class TestExactNameMerge:
    """Artifacts with same name, site, and overlapping dates should merge."""

    def test_exact_duplicates_merge(self):
        a = _make_artifact("Golden Bowl", "wikidata")
        b = _make_artifact("Golden Bowl", "met_museum")
        result = deduplicate_artifacts([a, b])

        assert len(result) == 1
        # Provenance from both sources should be combined
        source_ids = {p.source_id for p in result[0].provenance}
        assert source_ids == {"wikidata", "met_museum"}

    def test_exact_duplicates_three_sources(self):
        a = _make_artifact("Stone Tablet", "wikidata")
        b = _make_artifact("Stone Tablet", "harvard")
        c = _make_artifact("Stone Tablet", "british_museum")
        result = deduplicate_artifacts([a, b, c])

        assert len(result) == 1
        assert len(result[0].provenance) == 3


class TestDifferentNamesNoMerge:
    """Artifacts with very different names should not merge."""

    def test_different_names_kept_separate(self):
        a = _make_artifact("Golden Bowl", "wikidata")
        b = _make_artifact("Bronze Sword", "met_museum")
        result = deduplicate_artifacts([a, b])

        assert len(result) == 2

    def test_different_sites_kept_separate(self):
        a = _make_artifact("Golden Bowl", "wikidata", site_id="site_1")
        b = _make_artifact("Golden Bowl", "met_museum", site_id="site_2")
        result = deduplicate_artifacts([a, b])

        assert len(result) == 2


class TestWikidataPriorityWins:
    """When merging, the wikidata artifact (highest priority) should be kept."""

    def test_wikidata_wins_over_met(self):
        wd = _make_artifact("Ancient Vase", "wikidata")
        met = _make_artifact("Ancient Vase", "met_museum")
        result = deduplicate_artifacts([met, wd])

        assert len(result) == 1
        # The kept artifact should be the wikidata one (highest priority)
        assert result[0].id == wd.id

    def test_priority_ordering(self):
        assert _priority(_make_artifact("x", "wikidata")) == 5
        assert _priority(_make_artifact("x", "met_museum")) == 4
        assert _priority(_make_artifact("x", "harvard")) == 3
        assert _priority(_make_artifact("x", "british_museum")) == 2
        assert _priority(_make_artifact("x", "wikimedia_commons")) == 1

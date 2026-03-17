import pytest
from pipeline.models import (
    ProvenanceRecord, Site, Artifact, ArtifactImage,
    MotifSegment, Embedding, MotifCluster, SimilarityEdge,
    parse_coordinate,
)


def test_parse_coordinate_north():
    assert parse_coordinate("40.93360567 N") == pytest.approx(40.93360567)


def test_parse_coordinate_south():
    assert parse_coordinate("19.69291001 S") == pytest.approx(-19.69291001)


def test_parse_coordinate_west():
    assert parse_coordinate("98.84606407 W") == pytest.approx(-98.84606407)


def test_parse_coordinate_none():
    assert parse_coordinate(None) == 0.0


def test_site_from_raw():
    raw = {
        "id": "23374", "name": "Abdera", "other_names": None,
        "modern_names": None, "region": "Aegean", "section": None,
        "latitude": "40.93360567 N", "longitude": "24.97302984 E",
        "status": "Accurate location", "info": None, "sources": None,
    }
    site = Site.from_raw(raw)
    assert site.latitude == pytest.approx(40.93360567)
    assert site.longitude == pytest.approx(24.97302984)
    assert site.external_ids == {"wikidata": None, "pleiades": None}


def test_site_from_raw_null_name():
    raw = {
        "id": "999", "name": None, "other_names": None,
        "modern_names": None, "region": "Europe", "section": None,
        "latitude": "50.0 N", "longitude": "10.0 E",
        "status": "Accurate location", "info": None, "sources": None,
    }
    site = Site.from_raw(raw)
    assert site.name is None
    assert site.latitude == pytest.approx(50.0)


def test_provenance_to_dict():
    pr = ProvenanceRecord(
        source_id="wikidata", source_url="https://example.com",
        fetch_date="2026-03-16T00:00:00Z", license="CC0",
        raw_response_hash="abc123", transformation="none",
    )
    d = pr.to_dict()
    assert d["source_id"] == "wikidata"


def test_artifact_to_dict():
    a = Artifact(
        id="art_1", name="Spiral Bowl", description="A bowl",
        type="pottery", site_id="1", region="Aegean",
        period="Late Bronze Age", date_range_start=-1500,
        date_range_end=-1200, materials=["clay"],
        techniques=["wheel-thrown"], motif_tags=["spiral"],
        provenance=[],
    )
    d = a.to_dict()
    assert d["motif_tags"] == ["spiral"]


def test_motif_segment_to_dict():
    ms = MotifSegment(
        id="seg_1", artifact_image_id="img_1", artifact_id="art_1",
        mask_index=0, bbox=[10, 20, 50, 50], area_ratio=0.15,
        contour_complexity=25.0, cropped_image_path="",
        svg_path="data/svgs/seg_1.svg",
        provenance=ProvenanceRecord(
            source_id="clipseg", source_url="", fetch_date="",
            license="", raw_response_hash="", transformation="clipseg_v1",
        ),
    )
    d = ms.to_dict()
    assert d["bbox"] == [10, 20, 50, 50]
    assert d["provenance"]["transformation"] == "clipseg_v1"


def test_motif_cluster_to_dict():
    mc = MotifCluster(
        id="cluster_1", label="spiral", member_count=42,
        centroid_embedding=[0.1, 0.2],
        canonical_svg_path="data/svgs/canonical/cluster_1.svg",
        member_segment_ids=["seg_1", "seg_2"],
        provenance=ProvenanceRecord(
            source_id="hdbscan", source_url="", fetch_date="",
            license="", raw_response_hash="",
            transformation="hdbscan_min_cluster_size_15",
        ),
    )
    d = mc.to_dict()
    assert d["label"] == "spiral"
    assert d["member_count"] == 42


def test_similarity_edge_to_dict():
    e = SimilarityEdge(
        segment_a_id="seg_1", segment_b_id="seg_2",
        score=0.87, method="clip_cosine",
    )
    d = e.to_dict()
    assert d["score"] == 0.87

from pipeline.stage_7_export import build_site_summary

def test_build_site_summary():
    site = {"id": "1", "name": "Abdera", "region": "Aegean", "latitude": 40.93, "longitude": 24.97}
    arts = [
        {"id": "a1", "site_id": "1", "motif_tags": ["spiral"]},
        {"id": "a2", "site_id": "1", "motif_tags": ["wave", "spiral"]},
    ]
    s = build_site_summary(site, arts, ["cluster_0"])
    assert s["artifact_count"] == 2
    assert "spiral" in s["motif_tags"]
    assert "cluster_0" in s["cluster_ids"]

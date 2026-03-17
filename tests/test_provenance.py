import os
import tempfile
from pipeline.provenance import (
    compute_hash, create_provenance,
    save_raw_response, load_manifest, save_manifest,
)


def test_compute_hash_deterministic():
    data = b"hello world"
    assert compute_hash(data) == compute_hash(data)
    assert len(compute_hash(data)) == 64


def test_create_provenance():
    pr = create_provenance(
        source_id="met_museum",
        source_url="https://example.com/api/1",
        raw_data=b'{"objectID": 1}',
        license="CC0",
    )
    assert pr.source_id == "met_museum"
    assert pr.raw_response_hash == compute_hash(b'{"objectID": 1}')
    assert pr.fetch_date


def test_save_raw_response():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = save_raw_response(b'{"test": 1}', "met_museum", tmpdir)
        assert os.path.exists(path)
        with open(path, "rb") as f:
            assert f.read() == b'{"test": 1}'


def test_manifest_roundtrip():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "manifest.json")
        save_manifest(path, {"processed": ["s1", "s2"]})
        loaded = load_manifest(path)
        assert loaded["processed"] == ["s1", "s2"]


def test_load_manifest_missing():
    assert load_manifest("/nonexistent/manifest.json") == {}

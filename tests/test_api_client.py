import os
import tempfile
from pipeline.api_client import CachedAPIClient


def test_cache_save_and_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = CachedAPIClient("test", tmpdir, rate_limit=0)
        data = b'{"test": true}'
        path = client.save_to_cache(data)
        assert os.path.exists(path)
        assert client.load_from_cache(path) == data


def test_cache_creates_provenance():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = CachedAPIClient("met_museum", tmpdir, rate_limit=0)
        pr = client.create_provenance("https://example.com", b'{"id":1}', "CC0")
        assert pr.source_id == "met_museum"
        assert len(pr.raw_response_hash) == 64

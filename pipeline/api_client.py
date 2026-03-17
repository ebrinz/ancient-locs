import os
import time
import logging
import requests
from pipeline.provenance import compute_hash, create_provenance
from pipeline.models import ProvenanceRecord

logger = logging.getLogger(__name__)


class CachedAPIClient:
    def __init__(self, source_id: str, cache_dir: str, rate_limit: float = 1.0):
        self.source_id = source_id
        self.cache_dir = cache_dir
        self.rate_limit = rate_limit
        self._last_request = 0.0

    def _wait(self):
        elapsed = time.time() - self._last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last_request = time.time()

    def get(self, url: str, params: dict | None = None,
            headers: dict | None = None) -> bytes | None:
        cache_key = compute_hash((url + str(params)).encode())
        cache_path = os.path.join(self.cache_dir, self.source_id, cache_key + ".json")
        if os.path.exists(cache_path):
            return self.load_from_cache(cache_path)
        self._wait()
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            resp.raise_for_status()
            self.save_to_cache(resp.content, cache_path)
            return resp.content
        except requests.RequestException as e:
            logger.warning(f"Request failed for {url}: {e}")
            return None

    def save_to_cache(self, data: bytes, path: str | None = None) -> str:
        if path is None:
            path = os.path.join(self.cache_dir, self.source_id, compute_hash(data) + ".json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return path

    def load_from_cache(self, path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()

    def create_provenance(self, source_url: str, raw_data: bytes,
                          license: str, transformation: str = "none") -> ProvenanceRecord:
        return create_provenance(self.source_id, source_url, raw_data, license, transformation)

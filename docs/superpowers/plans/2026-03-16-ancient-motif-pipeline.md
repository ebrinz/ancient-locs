# Ancient Art Motif Encyclopedia — Pipeline Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python pipeline that harvests ancient artifact images from 5 public APIs, segments motif regions with CLIPSeg, embeds segments with CLIP, clusters to discover motif types, generates canonical SVGs, and exports static data for a Next.js map app.

**Architecture:** 8-stage Python pipeline (scrape → site matching → artifact harvesting → image collection → segmentation → embedding → similarity/clustering → export). Dev mode saves all images for QA; production mode streams and discards. Static JSON/SVG/NPZ output consumed by a separate Next.js frontend.

**Tech Stack:** Python 3.11+, requests, SPARQLWrapper, numpy, transformers (CLIP, CLIPSeg), hdbscan, vtracer, opencv-python, Levenshtein, pytest.

**Spec:** `docs/superpowers/specs/2026-03-16-ancient-motif-encyclopedia-design.md`

---

## File Structure

```
pipeline/
  __init__.py
  models.py              # All dataclasses: ProvenanceRecord, Site, Artifact, ArtifactImage, MotifSegment, Embedding, MotifCluster, SimilarityEdge
  provenance.py           # hash, create_provenance, save_raw_response, manifest I/O
  config.py               # Paths, API config, PIPELINE_MODE, thresholds
  api_client.py           # CachedAPIClient with rate limiting
  dedup.py                # Multi-signal artifact deduplication
  harvesters/
    __init__.py
    wikidata.py            # Wikidata SPARQL harvester
    met.py                 # Met Museum REST API harvester
    british_museum.py      # BM SPARQL harvester
    harvard.py             # Harvard Art Museums REST harvester
    wikimedia_commons.py   # MediaWiki API harvester
  stage_1_site_matching.py
  stage_2_artifact_harvest.py
  stage_3_image_collection.py
  stage_4_segmentation.py  # CLIPSeg + vtracer
  stage_5_embedding.py     # CLIP + text tagging
  stage_6_similarity.py    # Cosine sim + HDBSCAN clustering + canonical SVGs
  stage_7_export.py
  run.py                   # Orchestrator
  requirements.txt

tests/
  __init__.py
  test_models.py
  test_provenance.py
  test_api_client.py
  test_dedup.py
  test_stage_1.py
  test_harvesters.py
  test_stage_4.py
  test_stage_5.py
  test_stage_6.py
  test_stage_7.py

pyproject.toml
```

---

## Chunk 1: Project Scaffolding & Core Infrastructure

### Task 1: Reorganize repo, create package config

**Files:**
- Move: `scrape.py` → `pipeline/scrape.py`
- Move: `places.json` → `data/raw/places.json`
- Modify: `.gitignore`
- Create: `pyproject.toml`
- Create: `pipeline/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p pipeline/harvesters data/raw data/sites data/artifacts data/images data/segments data/svgs data/embeddings data/similarity data/clusters data/manifests data/raw/wikidata data/raw/met_museum data/raw/british_museum data/raw/harvard data/raw/wikimedia_commons tests
```

- [ ] **Step 2: Move existing files**

```bash
git mv scrape.py pipeline/scrape.py
git mv places.json data/raw/places.json
```

- [ ] **Step 3: Create package files**

```python
# pipeline/__init__.py
```

```python
# tests/__init__.py
```

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "ancient-locs-pipeline"
version = "0.1.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 4: Update .gitignore**

Append to `.gitignore`:
```
# Pipeline data outputs
data/sites/
data/artifacts/
data/images/
data/segments/
data/svgs/
data/embeddings/
data/similarity/
data/clusters/
data/manifests/
data/raw/wikidata/
data/raw/met_museum/
data/raw/british_museum/
data/raw/harvard/
data/raw/wikimedia_commons/
!data/raw/places.json

# Next.js
web/node_modules/
web/.next/
web/out/
web/public/data/
```

- [ ] **Step 5: Update scrape.py path**

In `pipeline/scrape.py`, change `OUTPUT_FILE = 'places.json'` to:
```python
import os
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'places.json')
```

- [ ] **Step 6: Install in dev mode and commit**

```bash
pip install -e .
git add -A && git commit -m "chore: reorganize repo, add pyproject.toml"
```

---

### Task 2: Data models

**Files:**
- Create: `pipeline/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_models.py
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
        centroid_embedding=[0.1, 0.2], canonical_svg_path="data/svgs/canonical/cluster_1.svg",
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
```

- [ ] **Step 2: Run tests to verify failure**

```bash
python -m pytest tests/test_models.py -v
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement models**

```python
# pipeline/models.py
from dataclasses import dataclass, field, asdict
from typing import Optional


def parse_coordinate(value: str | None) -> float:
    if value is None:
        return 0.0
    parts = value.strip().split()
    num = float(parts[0])
    if len(parts) > 1 and parts[1] in ("S", "W"):
        num = -num
    return num


@dataclass
class ProvenanceRecord:
    source_id: str
    source_url: str
    fetch_date: str
    license: str
    raw_response_hash: str
    transformation: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Site:
    id: str
    name: Optional[str]
    other_names: Optional[str]
    modern_names: Optional[str]
    region: str
    section: Optional[str]
    latitude: float
    longitude: float
    status: str
    info: Optional[str]
    sources: Optional[str]
    external_ids: dict = field(default_factory=lambda: {"wikidata": None, "pleiades": None})

    @classmethod
    def from_raw(cls, raw: dict) -> "Site":
        return cls(
            id=raw["id"],
            name=raw.get("name"),
            other_names=raw.get("other_names"),
            modern_names=raw.get("modern_names"),
            region=raw.get("region", ""),
            section=raw.get("section"),
            latitude=parse_coordinate(raw.get("latitude", "0 N")),
            longitude=parse_coordinate(raw.get("longitude", "0 E")),
            status=raw.get("status", ""),
            info=raw.get("info"),
            sources=raw.get("sources"),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Artifact:
    id: str
    name: str
    description: str
    type: str
    site_id: Optional[str]
    region: Optional[str]
    period: Optional[str]
    date_range_start: Optional[int]
    date_range_end: Optional[int]
    materials: list[str]
    techniques: list[str]
    motif_tags: list[str]
    provenance: list[ProvenanceRecord]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ArtifactImage:
    id: str
    artifact_id: str
    source_image_url: str
    local_path: str
    provenance: ProvenanceRecord

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MotifSegment:
    id: str
    artifact_image_id: str
    artifact_id: str
    mask_index: int
    bbox: list[int]
    area_ratio: float
    contour_complexity: float
    cropped_image_path: str
    svg_path: Optional[str]
    provenance: ProvenanceRecord

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Embedding:
    id: str
    segment_id: str
    artifact_id: str
    model: str
    vector: list[float]
    embedding_type: str
    provenance: ProvenanceRecord

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MotifCluster:
    id: str
    label: Optional[str]
    member_count: int
    centroid_embedding: list[float]
    canonical_svg_path: str
    member_segment_ids: list[str]
    provenance: ProvenanceRecord

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SimilarityEdge:
    segment_a_id: str
    segment_b_id: str
    score: float
    method: str

    def to_dict(self) -> dict:
        return asdict(self)
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_models.py -v
```
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/models.py tests/test_models.py
git commit -m "feat: add data models with MotifSegment, MotifCluster, and provenance"
```

---

### Task 3: Provenance utilities

**Files:**
- Create: `pipeline/provenance.py`
- Create: `tests/test_provenance.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_provenance.py
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
```

- [ ] **Step 2: Run tests to verify failure**

```bash
python -m pytest tests/test_provenance.py -v
```

- [ ] **Step 3: Implement provenance**

```python
# pipeline/provenance.py
import hashlib
import json
import os
from datetime import datetime, timezone
from pipeline.models import ProvenanceRecord


def compute_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def create_provenance(
    source_id: str, source_url: str, raw_data: bytes,
    license: str, transformation: str = "none",
) -> ProvenanceRecord:
    return ProvenanceRecord(
        source_id=source_id, source_url=source_url,
        fetch_date=datetime.now(timezone.utc).isoformat(),
        license=license, raw_response_hash=compute_hash(raw_data),
        transformation=transformation,
    )


def save_raw_response(data: bytes, source_id: str, raw_dir: str) -> str:
    source_dir = os.path.join(raw_dir, source_id)
    os.makedirs(source_dir, exist_ok=True)
    path = os.path.join(source_dir, compute_hash(data) + ".json")
    with open(path, "wb") as f:
        f.write(data)
    return path


def save_manifest(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_manifest(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_provenance.py -v
```

- [ ] **Step 5: Commit**

```bash
git add pipeline/provenance.py tests/test_provenance.py
git commit -m "feat: add provenance utilities"
```

---

### Task 4: Config and API client

**Files:**
- Create: `pipeline/config.py`
- Create: `pipeline/api_client.py`
- Create: `tests/test_api_client.py`
- Create: `pipeline/requirements.txt`

- [ ] **Step 1: Create config**

```python
# pipeline/config.py
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
SITES_DIR = os.path.join(DATA_DIR, "sites")
ARTIFACTS_DIR = os.path.join(DATA_DIR, "artifacts")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
SEGMENTS_DIR = os.path.join(DATA_DIR, "segments")
SVGS_DIR = os.path.join(DATA_DIR, "svgs")
EMBEDDINGS_DIR = os.path.join(DATA_DIR, "embeddings")
SIMILARITY_DIR = os.path.join(DATA_DIR, "similarity")
CLUSTERS_DIR = os.path.join(DATA_DIR, "clusters")
MANIFESTS_DIR = os.path.join(DATA_DIR, "manifests")
EXPORT_DIR = os.path.join(PROJECT_ROOT, "web", "public", "data")
RAW_PLACES = os.path.join(RAW_DIR, "places.json")

# Pipeline mode: "dev" saves everything, "production" saves only embeddings+SVGs+metadata
PIPELINE_MODE = os.environ.get("PIPELINE_MODE", "dev")

# API config
WIKIDATA_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
WIKIDATA_USER_AGENT = "AncientLocsBot/1.0 (https://github.com/ebrinz/ancient-locs)"
WIKIDATA_QUERY_TIMEOUT = 60

MET_MUSEUM_API_BASE = "https://collectionapi.metmuseum.org/public/collection/v1"
MET_MUSEUM_RATE_LIMIT = 1.0

BM_SPARQL_ENDPOINT = "https://collection.britishmuseum.org/sparql"
BM_RATE_LIMIT = 2.0

HARVARD_API_BASE = "https://api.harvardartmuseums.org"
HARVARD_API_KEY = os.environ.get("HARVARD_API_KEY", "")
HARVARD_DAILY_LIMIT = 2500

WIKIMEDIA_API_BASE = "https://commons.wikimedia.org/w/api.php"
WIKIMEDIA_USER_AGENT = WIKIDATA_USER_AGENT

# Site matching
SITE_MATCH_RADIUS_KM = 5.0
SITE_NAME_FUZZY_THRESHOLD = 3

# CLIPSeg
CLIPSEG_PROMPTS = [
    "decorative motif", "carved pattern", "painted design",
    "geometric decoration", "engraved symbol",
]
SEGMENT_MIN_AREA_RATIO = 0.03
SEGMENT_MAX_AREA_RATIO = 0.40
SEGMENT_MIN_COMPLEXITY = 10.0
SEGMENT_MAX_ASPECT_RATIO = 5.0

# CLIP
CLIP_MODEL = "openai/clip-vit-base-patch32"
CLIPSEG_MODEL = "CIDAS/clipseg-rd64-refined"

# SVG quality gate
SVG_MIN_PATHS = 5
SVG_MAX_PATHS = 5000

# Similarity
SIMILARITY_TOP_N = 20
SIMILARITY_EMBEDDING_WEIGHT = 0.7
SIMILARITY_TAG_WEIGHT = 0.3

# Clustering
HDBSCAN_MIN_CLUSTER_SIZES = [5, 15, 30, 50]

# Export
EXPORT_SIZE_BUDGET_MB = 50
SIMILARITY_EXPORT_TOP_N = 10

# Dev mode batch limits
DEV_MAX_SITES = 100
DEV_MAX_ARTIFACTS_PER_SITE = 10
```

- [ ] **Step 2: Write failing test for API client**

```python
# tests/test_api_client.py
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
```

- [ ] **Step 3: Run tests to verify failure**

```bash
python -m pytest tests/test_api_client.py -v
```

- [ ] **Step 4: Implement API client**

```python
# pipeline/api_client.py
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
```

- [ ] **Step 5: Create requirements.txt**

```
# pipeline/requirements.txt
requests>=2.31
SPARQLWrapper>=2.0
numpy>=1.24
Levenshtein>=0.21
transformers>=4.36
torch>=2.1
Pillow>=10.0
opencv-python>=4.8
vtracer>=0.6
hdbscan>=0.8
scikit-learn>=1.3
pytest>=7.0
```

- [ ] **Step 6: Run tests and commit**

```bash
python -m pytest tests/test_api_client.py -v
git add pipeline/config.py pipeline/api_client.py pipeline/requirements.txt tests/test_api_client.py
git commit -m "feat: add config, cached API client, and requirements"
```

---

## Chunk 2: Stages 1-2 — Site Matching & Artifact Harvesting

### Task 5: Stage 1 — Site matching

**Files:**
- Create: `pipeline/stage_1_site_matching.py`
- Create: `tests/test_stage_1.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_stage_1.py
import json
import os
import tempfile
import pytest
from pipeline.stage_1_site_matching import (
    load_raw_sites, save_site, build_wikidata_query, score_match,
)


def test_load_raw_sites():
    raw = [
        {"id": "1", "name": "Abdera", "other_names": None, "modern_names": None,
         "region": "Aegean", "section": None, "latitude": "40.9 N",
         "longitude": "24.9 E", "status": "Accurate location", "info": None, "sources": None},
        {"id": "2", "name": None, "other_names": None, "modern_names": None,
         "region": "Europe", "section": None, "latitude": "50.0 S",
         "longitude": "10.0 W", "status": "Imprecise", "info": None, "sources": None},
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "places.json")
        with open(path, "w") as f:
            json.dump(raw, f)
        sites = load_raw_sites(path)
        assert len(sites) == 2
        assert sites[0].latitude == pytest.approx(40.9)
        assert sites[1].latitude == pytest.approx(-50.0)
        assert sites[1].name is None


def test_save_site():
    from pipeline.models import Site
    site = Site(id="1", name="Test", other_names=None, modern_names=None,
                region="Aegean", section=None, latitude=40.0, longitude=24.0,
                status="Accurate", info=None, sources=None,
                external_ids={"wikidata": "Q123", "pleiades": None})
    with tempfile.TemporaryDirectory() as tmpdir:
        save_site(site, tmpdir)
        with open(os.path.join(tmpdir, "1.json")) as f:
            loaded = json.load(f)
        assert loaded["external_ids"]["wikidata"] == "Q123"


def test_build_wikidata_query():
    q = build_wikidata_query(40.9, 24.9, 5.0)
    assert "40.9" in q
    assert "24.9" in q
    assert "wdt:P625" in q


def test_score_match_exact():
    assert score_match("Abdera", "Abdera") == 1.0


def test_score_match_close():
    assert score_match("Abdera", "Abderra") > 0.5


def test_score_match_none_name():
    assert score_match(None, "Anything") == 0.0


def test_score_match_no_match():
    assert score_match("Abdera", "Completely Different") == 0.0
```

- [ ] **Step 2: Run tests to verify failure**

```bash
python -m pytest tests/test_stage_1.py -v
```

- [ ] **Step 3: Implement Stage 1**

```python
# pipeline/stage_1_site_matching.py
"""Stage 1: Match sites to Wikidata/Pleiades external IDs."""
import json
import os
import time
import logging

import Levenshtein
from SPARQLWrapper import SPARQLWrapper, JSON

from pipeline.models import Site
from pipeline.provenance import load_manifest, save_manifest
from pipeline.config import (
    RAW_PLACES, SITES_DIR, MANIFESTS_DIR,
    WIKIDATA_SPARQL_ENDPOINT, WIKIDATA_USER_AGENT, WIKIDATA_QUERY_TIMEOUT,
    SITE_MATCH_RADIUS_KM, SITE_NAME_FUZZY_THRESHOLD,
    PIPELINE_MODE, DEV_MAX_SITES,
)

logger = logging.getLogger(__name__)


def load_raw_sites(path: str) -> list[Site]:
    with open(path) as f:
        return [Site.from_raw(r) for r in json.load(f)]


def save_site(site: Site, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{site.id}.json")
    with open(path, "w") as f:
        json.dump(site.to_dict(), f, indent=2)
    return path


def build_wikidata_query(lat: float, lng: float, radius_km: float = 5.0) -> str:
    return f"""
    SELECT ?item ?itemLabel ?pleiades WHERE {{
      SERVICE wikibase:around {{
        ?item wdt:P625 ?location .
        bd:serviceParam wikibase:center "Point({lng} {lat})"^^geo:wktLiteral .
        bd:serviceParam wikibase:radius "{radius_km}" .
      }}
      ?item wdt:P31/wdt:P279* wd:Q839954 .
      OPTIONAL {{ ?item wdt:P1584 ?pleiades . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
    }}
    """


def score_match(site_name: str | None, candidate_name: str) -> float:
    if site_name is None:
        return 0.0
    if site_name.lower() == candidate_name.lower():
        return 1.0
    dist = Levenshtein.distance(site_name.lower(), candidate_name.lower())
    if dist <= SITE_NAME_FUZZY_THRESHOLD:
        return 1.0 - (dist / (SITE_NAME_FUZZY_THRESHOLD + 1))
    return 0.0


def query_wikidata(lat: float, lng: float, radius_km: float = 5.0) -> list[dict]:
    sparql = SPARQLWrapper(WIKIDATA_SPARQL_ENDPOINT)
    sparql.addCustomHttpHeader("User-Agent", WIKIDATA_USER_AGENT)
    sparql.setTimeout(WIKIDATA_QUERY_TIMEOUT)
    sparql.setQuery(build_wikidata_query(lat, lng, radius_km))
    sparql.setReturnFormat(JSON)
    try:
        results = sparql.query().convert()
        return [
            {
                "qid": r["item"]["value"].split("/")[-1],
                "label": r["itemLabel"]["value"],
                "pleiades": r.get("pleiades", {}).get("value"),
            }
            for r in results["results"]["bindings"]
        ]
    except Exception as e:
        logger.warning(f"Wikidata query failed for ({lat}, {lng}): {e}")
        return []


def match_site(site: Site) -> Site:
    candidates = query_wikidata(site.latitude, site.longitude, SITE_MATCH_RADIUS_KM)
    best_score, best = 0.0, None
    for c in candidates:
        s = score_match(site.name, c["label"])
        if s > best_score:
            best_score, best = s, c
    if site.name is None and candidates:
        best = candidates[0]
    if best:
        site.external_ids["wikidata"] = best["qid"]
        if best.get("pleiades"):
            site.external_ids["pleiades"] = best["pleiades"]
    return site


def run(input_path: str = RAW_PLACES, output_dir: str = SITES_DIR):
    manifest_path = os.path.join(MANIFESTS_DIR, "stage_1.json")
    manifest = load_manifest(manifest_path)
    processed = set(manifest.get("processed", []))

    sites = load_raw_sites(input_path)
    if PIPELINE_MODE == "dev":
        sites = sites[:DEV_MAX_SITES]
    logger.info(f"Loaded {len(sites)} sites, {len(processed)} already processed")

    matched = 0
    for i, site in enumerate(sites):
        if site.id in processed:
            continue
        site = match_site(site)
        save_site(site, output_dir)
        processed.add(site.id)
        if site.external_ids.get("wikidata"):
            matched += 1
        if (i + 1) % 100 == 0:
            logger.info(f"Processed {i + 1}/{len(sites)}, matched {matched}")
            save_manifest(manifest_path, {"processed": list(processed)})
        time.sleep(1)

    save_manifest(manifest_path, {"processed": list(processed)})
    logger.info(f"Stage 1 complete: {matched}/{len(sites)} matched")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_stage_1.py -v
```

- [ ] **Step 5: Commit**

```bash
git add pipeline/stage_1_site_matching.py tests/test_stage_1.py
git commit -m "feat(stage1): site matching with Wikidata SPARQL and fuzzy name scoring"
```

---

### Task 6: Harvesters (all 5 sources)

**Files:**
- Create: `pipeline/harvesters/__init__.py`
- Create: `pipeline/harvesters/wikidata.py`
- Create: `pipeline/harvesters/met.py`
- Create: `pipeline/harvesters/british_museum.py`
- Create: `pipeline/harvesters/harvard.py`
- Create: `pipeline/harvesters/wikimedia_commons.py`
- Create: `tests/test_harvesters.py`

- [ ] **Step 1: Write failing tests for all parsers**

```python
# tests/test_harvesters.py
import pytest
from pipeline.models import ProvenanceRecord
from pipeline.harvesters.wikidata import build_artifact_query, parse_wikidata_artifact
from pipeline.harvesters.met import parse_met_object, parse_medium
from pipeline.harvesters.british_museum import build_bm_query, parse_bm_result
from pipeline.harvesters.harvard import parse_harvard_object
from pipeline.harvesters.wikimedia_commons import parse_commons_file


def _prov(source="test"):
    return ProvenanceRecord(source_id=source, source_url="", fetch_date="",
                            license="CC0", raw_response_hash="", transformation="none")


# --- Wikidata ---
def test_wd_query_has_p189():
    q = build_artifact_query("Q12345")
    assert "Q12345" in q and "P189" in q


def test_wd_parse():
    binding = {
        "item": {"value": "http://www.wikidata.org/entity/Q999"},
        "itemLabel": {"value": "Spiral amphora"},
        "materialLabel": {"value": "ceramic"},
        "image": {"value": "https://commons.wikimedia.org/img.jpg"},
        "inception": {"value": "-0500-01-01T00:00:00Z"},
    }
    art, imgs = parse_wikidata_artifact(binding, site_id="1", region="Aegean")
    assert art.id == "wd_Q999"
    assert art.materials == ["ceramic"]
    assert len(imgs) == 1


# --- Met ---
def test_met_parse_medium():
    mats, techs = parse_medium("Terracotta; red-figure")
    assert mats == ["Terracotta"]
    assert techs == ["red-figure"]


def test_met_parse_object():
    raw = {
        "objectID": 248908, "title": "Kylix", "objectName": "Kylix",
        "medium": "Terracotta; red-figure", "classification": "Vases",
        "culture": "Greek", "period": "Classical",
        "objectBeginDate": -450, "objectEndDate": -440,
        "primaryImage": "https://images.metmuseum.org/ex.jpg",
        "additionalImages": [], "artistDisplayName": "",
        "department": "Greek and Roman Art", "excavation": "",
        "isPublicDomain": True,
    }
    art, imgs = parse_met_object(raw, _prov("met_museum"), "1", "Aegean")
    assert art.name == "Kylix"
    assert art.date_range_start == -450
    assert len(imgs) == 1


# --- British Museum ---
def test_bm_query():
    q = build_bm_query(51.5, -0.1, 5.0)
    assert "51.5" in q


def test_bm_parse():
    binding = {
        "object": {"value": "http://collection.britishmuseum.org/id/object/123"},
        "label": {"value": "Painted vessel"},
        "image": {"value": "https://example.com/img.jpg"},
        "material": {"value": "ceramic"},
    }
    art, imgs = parse_bm_result(binding, site_id="1", region="Levant")
    assert art.id == "bm_123"
    assert len(imgs) == 1


# --- Harvard ---
def test_harvard_parse():
    raw = {
        "id": 54321, "title": "Bowl with spirals",
        "classification": "Vessels", "medium": "Terracotta, painted",
        "culture": "Greek", "dated": "5th century BCE",
        "datebegin": -500, "dateend": -400,
        "images": [{"baseimageurl": "https://nrs.harvard.edu/ex.jpg"}],
    }
    art, imgs = parse_harvard_object(raw, _prov("harvard"), "1", "Aegean")
    assert art.id == "harv_54321"
    assert art.date_range_start == -500
    assert len(imgs) == 1


# --- Wikimedia Commons ---
def test_commons_parse():
    page = {
        "pageid": 99999, "title": "File:Cave painting spiral.jpg",
        "imageinfo": [{
            "url": "https://upload.wikimedia.org/wikipedia/commons/a/ab/Cave.jpg",
            "extmetadata": {
                "LicenseShortName": {"value": "CC BY-SA 4.0"},
                "ImageDescription": {"value": "Neolithic cave painting with spiral motif"},
            },
        }],
    }
    art, imgs = parse_commons_file(page, site_id="1", region="Europe")
    assert art.id == "wmc_99999"
    assert "cave painting" in art.description.lower()
    assert len(imgs) == 1
```

- [ ] **Step 2: Run tests to verify failure**

```bash
python -m pytest tests/test_harvesters.py -v
```

- [ ] **Step 3: Implement all 5 harvesters**

```python
# pipeline/harvesters/__init__.py
```

```python
# pipeline/harvesters/wikidata.py
"""Wikidata SPARQL artifact harvester."""
import logging
import uuid
from SPARQLWrapper import SPARQLWrapper, JSON
from pipeline.models import Artifact, ArtifactImage
from pipeline.provenance import create_provenance
from pipeline.config import WIKIDATA_SPARQL_ENDPOINT, WIKIDATA_USER_AGENT, WIKIDATA_QUERY_TIMEOUT

logger = logging.getLogger(__name__)


def build_artifact_query(site_qid: str) -> str:
    return f"""
    SELECT ?item ?itemLabel ?materialLabel ?image ?inception WHERE {{
      ?item wdt:P189 wd:{site_qid} .
      OPTIONAL {{ ?item wdt:P186 ?material . }}
      OPTIONAL {{ ?item wdt:P18 ?image . }}
      OPTIONAL {{ ?item wdt:P571 ?inception . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
    }} LIMIT 500
    """


def parse_inception_year(s: str | None) -> int | None:
    if not s:
        return None
    try:
        return -int(s[1:5]) if s.startswith("-") else int(s[:4])
    except (ValueError, IndexError):
        return None


def parse_wikidata_artifact(binding: dict, site_id: str | None,
                            region: str | None) -> tuple[Artifact, list[ArtifactImage]]:
    qid = binding["item"]["value"].split("/")[-1]
    aid = f"wd_{qid}"
    label = binding.get("itemLabel", {}).get("value", "")
    material = binding.get("materialLabel", {}).get("value", "")
    year = parse_inception_year(binding.get("inception", {}).get("value"))
    prov = create_provenance("wikidata", binding["item"]["value"],
                             str(binding).encode(), "CC0")
    art = Artifact(id=aid, name=label, description=label, type="", site_id=site_id,
                   region=region, period=None, date_range_start=year, date_range_end=year,
                   materials=[material] if material else [], techniques=[], motif_tags=[],
                   provenance=[prov])
    imgs = []
    img_url = binding.get("image", {}).get("value")
    if img_url:
        imgs.append(ArtifactImage(id=f"img_{uuid.uuid4().hex[:12]}", artifact_id=aid,
                                  source_image_url=img_url, local_path="", provenance=prov))
    return art, imgs


def query_artifacts_for_site(site_qid: str) -> list[dict]:
    sparql = SPARQLWrapper(WIKIDATA_SPARQL_ENDPOINT)
    sparql.addCustomHttpHeader("User-Agent", WIKIDATA_USER_AGENT)
    sparql.setTimeout(WIKIDATA_QUERY_TIMEOUT)
    sparql.setQuery(build_artifact_query(site_qid))
    sparql.setReturnFormat(JSON)
    try:
        return sparql.query().convert()["results"]["bindings"]
    except Exception as e:
        logger.warning(f"Wikidata artifact query failed for {site_qid}: {e}")
        return []
```

```python
# pipeline/harvesters/met.py
"""Metropolitan Museum of Art API harvester."""
import json
import logging
import uuid
from pipeline.api_client import CachedAPIClient
from pipeline.models import Artifact, ArtifactImage, ProvenanceRecord
from pipeline.config import MET_MUSEUM_API_BASE

logger = logging.getLogger(__name__)


def parse_medium(medium: str) -> tuple[list[str], list[str]]:
    if not medium:
        return [], []
    parts = [p.strip() for p in medium.split(";")]
    return ([parts[0]] if parts else []), parts[1:]


def parse_met_object(raw: dict, prov: ProvenanceRecord,
                     site_id: str | None, region: str | None
                     ) -> tuple[Artifact, list[ArtifactImage]]:
    materials, techniques = parse_medium(raw.get("medium", ""))
    aid = f"met_{raw['objectID']}"
    art = Artifact(
        id=aid, name=raw.get("title", ""),
        description=f"{raw.get('objectName', '')}. {raw.get('culture', '')}. {raw.get('department', '')}",
        type=raw.get("classification", ""), site_id=site_id, region=region,
        period=raw.get("period") or None,
        date_range_start=raw.get("objectBeginDate"), date_range_end=raw.get("objectEndDate"),
        materials=materials, techniques=techniques, motif_tags=[], provenance=[prov],
    )
    urls = ([raw["primaryImage"]] if raw.get("primaryImage") else []) + raw.get("additionalImages", [])
    imgs = [ArtifactImage(id=f"img_{uuid.uuid4().hex[:12]}", artifact_id=aid,
                          source_image_url=u, local_path="", provenance=prov) for u in urls]
    return art, imgs


def search_met(query: str, client: CachedAPIClient) -> list[int]:
    data = client.get(f"{MET_MUSEUM_API_BASE}/search", params={"q": query, "hasImages": "true"})
    if data is None:
        return []
    return json.loads(data).get("objectIDs", []) or []


def fetch_met_object(oid: int, client: CachedAPIClient) -> dict | None:
    data = client.get(f"{MET_MUSEUM_API_BASE}/objects/{oid}")
    return json.loads(data) if data else None
```

```python
# pipeline/harvesters/british_museum.py
"""British Museum Linked Open Data SPARQL harvester."""
import logging
import uuid
from SPARQLWrapper import SPARQLWrapper, JSON
from pipeline.models import Artifact, ArtifactImage
from pipeline.provenance import create_provenance
from pipeline.config import BM_SPARQL_ENDPOINT

logger = logging.getLogger(__name__)


def build_bm_query(lat: float, lng: float, radius_km: float = 5.0) -> str:
    deg = radius_km / 111.0
    return f"""
    PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>
    SELECT ?object ?label ?image ?material WHERE {{
      ?object rdfs:label ?label .
      OPTIONAL {{ ?object crm:P45_consists_of/rdfs:label ?material . }}
      OPTIONAL {{ ?object crm:P138i_has_representation ?image . }}
      ?object crm:P16i_was_used_for/crm:P7_took_place_at ?place .
      ?place geo:lat ?lat ; geo:long ?lng .
      FILTER(ABS(?lat - {lat}) < {deg} && ABS(?lng - {lng}) < {deg})
    }} LIMIT 100
    """


def parse_bm_result(binding: dict, site_id: str | None,
                    region: str | None) -> tuple[Artifact, list[ArtifactImage]]:
    obj_id = binding["object"]["value"].split("/")[-1]
    aid = f"bm_{obj_id}"
    prov = create_provenance("british_museum", binding["object"]["value"],
                             str(binding).encode(), "CC-BY-NC-SA-4.0")
    art = Artifact(id=aid, name=binding.get("label", {}).get("value", ""),
                   description="", type="", site_id=site_id, region=region,
                   period=None, date_range_start=None, date_range_end=None,
                   materials=[binding["material"]["value"]] if binding.get("material") else [],
                   techniques=[], motif_tags=[], provenance=[prov])
    imgs = []
    if binding.get("image", {}).get("value"):
        imgs.append(ArtifactImage(id=f"img_{uuid.uuid4().hex[:12]}", artifact_id=aid,
                                  source_image_url=binding["image"]["value"],
                                  local_path="", provenance=prov))
    return art, imgs


def query_bm_artifacts(lat: float, lng: float, radius_km: float = 5.0) -> list[dict]:
    sparql = SPARQLWrapper(BM_SPARQL_ENDPOINT)
    sparql.setQuery(build_bm_query(lat, lng, radius_km))
    sparql.setReturnFormat(JSON)
    try:
        return sparql.query().convert()["results"]["bindings"]
    except Exception as e:
        logger.warning(f"BM SPARQL failed for ({lat}, {lng}): {e} — skipping")
        return []
```

```python
# pipeline/harvesters/harvard.py
"""Harvard Art Museums API harvester."""
import json
import logging
import uuid
from pipeline.api_client import CachedAPIClient
from pipeline.models import Artifact, ArtifactImage, ProvenanceRecord
from pipeline.config import HARVARD_API_BASE, HARVARD_API_KEY

logger = logging.getLogger(__name__)


def parse_harvard_object(raw: dict, prov: ProvenanceRecord,
                         site_id: str | None, region: str | None
                         ) -> tuple[Artifact, list[ArtifactImage]]:
    aid = f"harv_{raw['id']}"
    medium = raw.get("medium", "")
    parts = [p.strip() for p in medium.split(",")]
    materials = [parts[0]] if parts and parts[0] else []
    techniques = parts[1:] if len(parts) > 1 else []
    art = Artifact(
        id=aid, name=raw.get("title", ""),
        description=f"{raw.get('classification', '')}. {raw.get('culture', '')}",
        type=raw.get("classification", ""), site_id=site_id, region=region,
        period=raw.get("dated") or None,
        date_range_start=raw.get("datebegin"), date_range_end=raw.get("dateend"),
        materials=materials, techniques=techniques, motif_tags=[], provenance=[prov],
    )
    imgs = [ArtifactImage(id=f"img_{uuid.uuid4().hex[:12]}", artifact_id=aid,
                          source_image_url=img["baseimageurl"], local_path="", provenance=prov)
            for img in raw.get("images", []) if img.get("baseimageurl")]
    return art, imgs


def search_harvard(culture: str, client: CachedAPIClient) -> list[dict]:
    if not HARVARD_API_KEY:
        logger.warning("No HARVARD_API_KEY set, skipping")
        return []
    data = client.get(f"{HARVARD_API_BASE}/object",
                      params={"apikey": HARVARD_API_KEY, "culture": culture,
                              "hasimage": 1, "size": 50})
    if data is None:
        return []
    return json.loads(data).get("records", [])
```

```python
# pipeline/harvesters/wikimedia_commons.py
"""Wikimedia Commons MediaWiki API harvester."""
import json
import logging
import uuid
from pipeline.api_client import CachedAPIClient
from pipeline.models import Artifact, ArtifactImage
from pipeline.provenance import create_provenance
from pipeline.config import WIKIMEDIA_API_BASE, WIKIMEDIA_USER_AGENT

logger = logging.getLogger(__name__)

COMMONS_CATEGORIES = [
    "Ancient art", "Petroglyphs", "Cave paintings",
    "Archaeological artifacts", "Ancient pottery",
    "Relief sculptures", "Ancient mosaics",
]


def parse_commons_file(page: dict, site_id: str | None,
                       region: str | None) -> tuple[Artifact, list[ArtifactImage]]:
    pid = page["pageid"]
    aid = f"wmc_{pid}"
    title = page.get("title", "").replace("File:", "")
    imageinfo = page.get("imageinfo", [{}])[0]
    extmeta = imageinfo.get("extmetadata", {})
    desc = extmeta.get("ImageDescription", {}).get("value", "")
    license_str = extmeta.get("LicenseShortName", {}).get("value", "unknown")
    img_url = imageinfo.get("url", "")

    prov = create_provenance("wikimedia_commons",
                             f"https://commons.wikimedia.org/wiki/File:{title}",
                             json.dumps(page).encode(), license_str)
    art = Artifact(id=aid, name=title, description=desc, type="",
                   site_id=site_id, region=region, period=None,
                   date_range_start=None, date_range_end=None,
                   materials=[], techniques=[], motif_tags=[], provenance=[prov])
    imgs = []
    if img_url:
        imgs.append(ArtifactImage(id=f"img_{uuid.uuid4().hex[:12]}", artifact_id=aid,
                                  source_image_url=img_url, local_path="", provenance=prov))
    return art, imgs


def search_commons_category(category: str, client: CachedAPIClient) -> list[dict]:
    params = {
        "action": "query", "format": "json",
        "generator": "categorymembers", "gcmtitle": f"Category:{category}",
        "gcmtype": "file", "gcmlimit": 50,
        "prop": "imageinfo", "iiprop": "url|extmetadata",
    }
    data = client.get(WIKIMEDIA_API_BASE, params=params,
                      headers={"User-Agent": WIKIMEDIA_USER_AGENT})
    if data is None:
        return []
    result = json.loads(data)
    pages = result.get("query", {}).get("pages", {})
    return list(pages.values())
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_harvesters.py -v
```

- [ ] **Step 5: Commit**

```bash
git add pipeline/harvesters/ tests/test_harvesters.py
git commit -m "feat(stage2): all 5 harvesters — Wikidata, Met, BM, Harvard, Wikimedia Commons"
```

---

### Task 7: Deduplication + Stage 2 runner

**Files:**
- Create: `pipeline/dedup.py`
- Create: `pipeline/stage_2_artifact_harvest.py`
- Create: `tests/test_dedup.py`

- [ ] **Step 1: Write failing dedup tests**

```python
# tests/test_dedup.py
from pipeline.dedup import deduplicate_artifacts
from pipeline.models import Artifact, ProvenanceRecord


def _art(id, name, site_id, start, source):
    return Artifact(id=id, name=name, description="", type="pottery",
                    site_id=site_id, region="Aegean", period=None,
                    date_range_start=start, date_range_end=start,
                    materials=["clay"], techniques=[], motif_tags=[],
                    provenance=[ProvenanceRecord(source_id=source, source_url="",
                                fetch_date="", license="CC0", raw_response_hash="",
                                transformation="none")])


def test_dedup_exact_name():
    a1 = _art("met_1", "Spiral Bowl", "s1", -500, "met_museum")
    a2 = _art("wd_Q1", "Spiral Bowl", "s1", -500, "wikidata")
    result = deduplicate_artifacts([a1, a2])
    assert len(result) == 1
    assert len(result[0].provenance) == 2


def test_dedup_different_no_merge():
    a1 = _art("met_1", "Spiral Bowl", "s1", -500, "met_museum")
    a2 = _art("met_2", "Wave Pitcher", "s1", -300, "met_museum")
    result = deduplicate_artifacts([a1, a2])
    assert len(result) == 2


def test_dedup_wikidata_priority():
    a1 = _art("met_1", "Spiral Bowl", "s1", -500, "met_museum")
    a2 = _art("wd_Q1", "Spiral Bowll", "s1", -500, "wikidata")
    result = deduplicate_artifacts([a1, a2])
    assert len(result) == 1
    assert result[0].id == "wd_Q1"
```

- [ ] **Step 2: Run tests, verify failure**

```bash
python -m pytest tests/test_dedup.py -v
```

- [ ] **Step 3: Implement dedup**

```python
# pipeline/dedup.py
"""Multi-signal artifact deduplication."""
import Levenshtein
from pipeline.models import Artifact
from pipeline.config import SITE_NAME_FUZZY_THRESHOLD

SOURCE_PRIORITY = {"wikidata": 5, "met_museum": 4, "harvard": 3,
                    "british_museum": 2, "wikimedia_commons": 1}


def _dates_overlap(a: Artifact, b: Artifact) -> bool:
    if a.date_range_start is None or b.date_range_start is None:
        return True
    a_end = a.date_range_end or a.date_range_start
    b_end = b.date_range_end or b.date_range_start
    return a.date_range_start <= b_end and b.date_range_start <= a_end


def _is_dup(a: Artifact, b: Artifact) -> bool:
    if a.site_id != b.site_id:
        return False
    if not _dates_overlap(a, b):
        return False
    return Levenshtein.distance(a.name.lower(), b.name.lower()) <= SITE_NAME_FUZZY_THRESHOLD


def _priority(a: Artifact) -> int:
    return max((SOURCE_PRIORITY.get(p.source_id, 0) for p in a.provenance), default=0)


def deduplicate_artifacts(artifacts: list[Artifact]) -> list[Artifact]:
    if not artifacts:
        return []
    sorted_arts = sorted(artifacts, key=_priority, reverse=True)
    merged: list[Artifact] = []
    for art in sorted_arts:
        dup = next((e for e in merged if _is_dup(e, art)), None)
        if dup:
            dup.provenance.extend(art.provenance)
        else:
            merged.append(art)
    return merged
```

- [ ] **Step 4: Implement Stage 2 runner**

```python
# pipeline/stage_2_artifact_harvest.py
"""Stage 2: Harvest artifacts from 5 API sources."""
import json
import os
import logging
from pipeline.models import Site, Artifact, ArtifactImage
from pipeline.api_client import CachedAPIClient
from pipeline.dedup import deduplicate_artifacts
from pipeline.harvesters.wikidata import query_artifacts_for_site, parse_wikidata_artifact
from pipeline.harvesters.met import search_met, fetch_met_object, parse_met_object
from pipeline.harvesters.british_museum import query_bm_artifacts, parse_bm_result
from pipeline.harvesters.harvard import search_harvard, parse_harvard_object
from pipeline.harvesters.wikimedia_commons import search_commons_category, parse_commons_file, COMMONS_CATEGORIES
from pipeline.provenance import load_manifest, save_manifest
from pipeline.config import (
    SITES_DIR, ARTIFACTS_DIR, RAW_DIR, MANIFESTS_DIR,
    MET_MUSEUM_API_BASE, MET_MUSEUM_RATE_LIMIT, BM_RATE_LIMIT,
    HARVARD_API_KEY, PIPELINE_MODE, DEV_MAX_ARTIFACTS_PER_SITE,
)

logger = logging.getLogger(__name__)


def load_enriched_sites(sites_dir: str) -> list[Site]:
    sites = []
    for fn in os.listdir(sites_dir):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(sites_dir, fn)) as f:
            d = json.load(f)
        ext = d.pop("external_ids", {})
        site = Site(**d)
        site.external_ids = ext
        sites.append(site)
    return sites


def save_artifact(artifact: Artifact, images: list[ArtifactImage], output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    data = artifact.to_dict()
    data["images"] = [img.to_dict() for img in images]
    with open(os.path.join(output_dir, f"{artifact.id}.json"), "w") as f:
        json.dump(data, f, indent=2)


def harvest_site(site: Site, met_client: CachedAPIClient,
                 harvard_client: CachedAPIClient,
                 commons_client: CachedAPIClient) -> list[tuple[Artifact, list[ArtifactImage]]]:
    all_results: list[tuple[Artifact, list[ArtifactImage]]] = []
    qid = site.external_ids.get("wikidata")

    # Wikidata
    if qid:
        for b in query_artifacts_for_site(qid):
            all_results.append(parse_wikidata_artifact(b, site.id, site.region))

    # Met Museum
    if site.name:
        for oid in search_met(site.name, met_client)[:20]:
            raw = fetch_met_object(oid, met_client)
            if raw:
                prov = met_client.create_provenance(
                    f"{MET_MUSEUM_API_BASE}/objects/{oid}",
                    json.dumps(raw).encode(),
                    "CC0" if raw.get("isPublicDomain") else "Restricted")
                all_results.append(parse_met_object(raw, prov, site.id, site.region))

    # British Museum (graceful skip)
    bm_bindings = query_bm_artifacts(site.latitude, site.longitude)
    for b in bm_bindings:
        all_results.append(parse_bm_result(b, site.id, site.region))

    # Harvard
    if HARVARD_API_KEY and site.region:
        culture = site.region.split(":")[0].strip()
        for raw in search_harvard(culture, harvard_client):
            prov = harvard_client.create_provenance(
                f"https://api.harvardartmuseums.org/object/{raw['id']}",
                json.dumps(raw).encode(), "Restricted")
            all_results.append(parse_harvard_object(raw, prov, site.id, site.region))

    # Deduplicate
    arts = [a for a, _ in all_results]
    imgs_by_id = {a.id: i for a, i in all_results}
    deduped = deduplicate_artifacts(arts)

    cap = DEV_MAX_ARTIFACTS_PER_SITE if PIPELINE_MODE == "dev" else len(deduped)
    return [(a, imgs_by_id.get(a.id, [])) for a in deduped[:cap]]


def run(sites_dir: str = SITES_DIR, output_dir: str = ARTIFACTS_DIR):
    manifest_path = os.path.join(MANIFESTS_DIR, "stage_2.json")
    manifest = load_manifest(manifest_path)
    processed = set(manifest.get("processed_sites", []))

    sites = load_enriched_sites(sites_dir)
    matched = [s for s in sites if s.external_ids.get("wikidata")]
    logger.info(f"{len(matched)} sites with external IDs, {len(processed)} done")

    met_client = CachedAPIClient("met_museum", RAW_DIR, MET_MUSEUM_RATE_LIMIT)
    harvard_client = CachedAPIClient("harvard", RAW_DIR, 1.5)
    commons_client = CachedAPIClient("wikimedia_commons", RAW_DIR, 0.5)

    # Also harvest from Wikimedia Commons categories (not site-specific)
    for cat in COMMONS_CATEGORIES:
        for page in search_commons_category(cat, commons_client):
            art, imgs = parse_commons_file(page, site_id=None, region=None)
            save_artifact(art, imgs, output_dir)

    total = 0
    for i, site in enumerate(matched):
        if site.id in processed:
            continue
        results = harvest_site(site, met_client, harvard_client, commons_client)
        for art, imgs in results:
            save_artifact(art, imgs, output_dir)
            total += 1
        processed.add(site.id)
        if (i + 1) % 50 == 0:
            logger.info(f"Processed {i+1}/{len(matched)}, {total} artifacts")
            save_manifest(manifest_path, {"processed_sites": list(processed)})

    save_manifest(manifest_path, {"processed_sites": list(processed)})
    logger.info(f"Stage 2 complete: {total} artifacts")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
```

- [ ] **Step 5: Run tests and commit**

```bash
python -m pytest tests/test_dedup.py -v
git add pipeline/dedup.py pipeline/stage_2_artifact_harvest.py tests/test_dedup.py
git commit -m "feat(stage2): artifact harvesting with 5 sources, dedup, and runner"
```

---

## Chunk 3: Stages 3-5 — Images, Segmentation, Embedding

### Task 8: Stage 3 — Image collection

**Files:**
- Create: `pipeline/stage_3_image_collection.py`

- [ ] **Step 1: Implement image downloader with checkpointing**

```python
# pipeline/stage_3_image_collection.py
"""Stage 3: Download artifact images with checkpointing."""
import json
import os
import logging
import requests
from pipeline.provenance import load_manifest, save_manifest, compute_hash
from pipeline.config import ARTIFACTS_DIR, IMAGES_DIR, MANIFESTS_DIR, PIPELINE_MODE

logger = logging.getLogger(__name__)


def download_image(url: str, output_path: str) -> bool:
    try:
        resp = requests.get(url, timeout=30, stream=True)
        resp.raise_for_status()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        return True
    except Exception as e:
        logger.warning(f"Download failed {url}: {e}")
        return False


def run(artifacts_dir: str = ARTIFACTS_DIR):
    manifest_path = os.path.join(MANIFESTS_DIR, "stage_3_downloads.json")
    manifest = load_manifest(manifest_path)
    processed = set(manifest.get("processed_images", []))

    for fn in os.listdir(artifacts_dir):
        if not fn.endswith(".json"):
            continue
        filepath = os.path.join(artifacts_dir, fn)
        with open(filepath) as f:
            data = json.load(f)

        updated = False
        for img in data.get("images", []):
            if img["id"] in processed:
                continue
            ext = os.path.splitext(img["source_image_url"].split("?")[0])[1] or ".jpg"
            local_path = os.path.join(IMAGES_DIR, data["id"], f"{img['id']}{ext}")

            if PIPELINE_MODE == "dev":
                if download_image(img["source_image_url"], local_path):
                    img["local_path"] = local_path
                    updated = True
            # In production mode, images are downloaded on-demand during streaming
            # (Stages 3-5 fused). This stage just records what needs downloading.
            processed.add(img["id"])

        if updated:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)

    save_manifest(manifest_path, {"processed_images": list(processed)})
    logger.info(f"Stage 3 complete: {len(processed)} images processed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
```

- [ ] **Step 2: Commit**

```bash
git add pipeline/stage_3_image_collection.py
git commit -m "feat(stage3): image download with checkpointing and dev/prod mode"
```

---

### Task 9: Stage 4 — CLIPSeg segmentation

**Files:**
- Create: `pipeline/stage_4_segmentation.py`
- Create: `tests/test_stage_4.py`

- [ ] **Step 1: Write failing tests for segment filtering**

```python
# tests/test_stage_4.py
import numpy as np
import pytest
from pipeline.stage_4_segmentation import filter_segments, count_svg_paths


def test_filter_segments_keeps_good():
    stats = np.array([
        # label, x, y, w, h, area
        [0, 0, 0, 100, 100, 10000],  # background
        [1, 10, 10, 30, 30, 600],     # good segment (~6% of 10000)
    ], dtype=np.int32)
    image_area = 10000
    kept = filter_segments(stats, image_area)
    assert 1 in kept


def test_filter_segments_rejects_too_small():
    stats = np.array([
        [0, 0, 0, 100, 100, 10000],
        [1, 10, 10, 5, 5, 10],  # 0.1% — too small
    ], dtype=np.int32)
    kept = filter_segments(stats, 10000)
    assert 1 not in kept


def test_filter_segments_rejects_too_large():
    stats = np.array([
        [0, 0, 0, 100, 100, 10000],
        [1, 0, 0, 100, 100, 5000],  # 50% — too large
    ], dtype=np.int32)
    kept = filter_segments(stats, 10000)
    assert 1 not in kept


def test_count_svg_paths():
    svg = '<svg><path d="M0 0"/><path d="M1 1"/></svg>'
    assert count_svg_paths(svg) == 2
```

- [ ] **Step 2: Run tests to verify failure**

```bash
python -m pytest tests/test_stage_4.py -v
```

- [ ] **Step 3: Implement CLIPSeg segmentation stage**

```python
# pipeline/stage_4_segmentation.py
"""Stage 4: CLIPSeg motif segmentation + SVG tracing."""
import json
import os
import uuid
import logging
import subprocess

import cv2
import numpy as np

from pipeline.models import MotifSegment
from pipeline.provenance import create_provenance, load_manifest, save_manifest
from pipeline.config import (
    ARTIFACTS_DIR, IMAGES_DIR, SEGMENTS_DIR, SVGS_DIR, MANIFESTS_DIR,
    CLIPSEG_PROMPTS, CLIPSEG_MODEL, PIPELINE_MODE,
    SEGMENT_MIN_AREA_RATIO, SEGMENT_MAX_AREA_RATIO,
    SEGMENT_MIN_COMPLEXITY, SEGMENT_MAX_ASPECT_RATIO,
    SVG_MIN_PATHS, SVG_MAX_PATHS,
)

logger = logging.getLogger(__name__)

_clipseg_model = None
_clipseg_processor = None


def _load_clipseg():
    global _clipseg_model, _clipseg_processor
    if _clipseg_model is None:
        from transformers import CLIPSegProcessor, CLIPSegForImageSegmentation
        _clipseg_processor = CLIPSegProcessor.from_pretrained(CLIPSEG_MODEL)
        _clipseg_model = CLIPSegForImageSegmentation.from_pretrained(CLIPSEG_MODEL)
    return _clipseg_model, _clipseg_processor


def generate_masks(image: np.ndarray, prompts: list[str]) -> np.ndarray:
    """Run CLIPSeg, return binary mask (union of all prompts, Otsu threshold)."""
    from PIL import Image
    import torch

    model, processor = _load_clipseg()
    pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

    inputs = processor(text=prompts, images=[pil_img] * len(prompts),
                       return_tensors="pt", padding=True)
    with torch.no_grad():
        outputs = model(**inputs)

    # Max activation across prompts
    logits = outputs.logits  # (num_prompts, H, W)
    max_logits = logits.max(dim=0).values.numpy()

    # Resize to original image size
    h, w = image.shape[:2]
    resized = cv2.resize(max_logits, (w, h))

    # Otsu threshold
    normalized = ((resized - resized.min()) / (resized.max() - resized.min() + 1e-8) * 255).astype(np.uint8)
    _, binary = cv2.threshold(normalized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def filter_segments(stats: np.ndarray, image_area: int) -> list[int]:
    """Return list of label indices that pass filtering."""
    kept = []
    for i in range(1, len(stats)):  # skip background (label 0)
        area = stats[i, cv2.CC_STAT_AREA]
        w = stats[i, cv2.CC_STAT_WIDTH]
        h = stats[i, cv2.CC_STAT_HEIGHT]
        ratio = area / image_area
        if ratio < SEGMENT_MIN_AREA_RATIO or ratio > SEGMENT_MAX_AREA_RATIO:
            continue
        aspect = max(w, h) / (min(w, h) + 1e-8)
        if aspect > SEGMENT_MAX_ASPECT_RATIO:
            continue
        kept.append(i)
    return kept


def count_svg_paths(svg_content: str) -> int:
    return svg_content.count("<path")


def trace_to_svg(input_path: str, output_path: str) -> bool:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    try:
        subprocess.run(["vtracer", "--input", input_path, "--output", output_path,
                         "--colormode", "binary", "--filter_speckle", "4"],
                       check=True, capture_output=True, timeout=60)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.warning(f"vtracer failed for {input_path}: {e}")
        return False


def segment_image(image: np.ndarray, artifact_id: str,
                  image_id: str) -> list[MotifSegment]:
    """Segment an image and return MotifSegment records."""
    binary_mask = generate_masks(image, CLIPSEG_PROMPTS)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary_mask)
    image_area = image.shape[0] * image.shape[1]
    kept = filter_segments(stats, image_area)

    segments = []
    for idx, label_idx in enumerate(kept):
        x = int(stats[label_idx, cv2.CC_STAT_LEFT])
        y = int(stats[label_idx, cv2.CC_STAT_TOP])
        w = int(stats[label_idx, cv2.CC_STAT_WIDTH])
        h = int(stats[label_idx, cv2.CC_STAT_HEIGHT])
        area = int(stats[label_idx, cv2.CC_STAT_AREA])

        # Crop segment using mask
        mask_region = (labels == label_idx).astype(np.uint8) * 255
        cropped = cv2.bitwise_and(image, image, mask=mask_region)
        cropped = cropped[y:y+h, x:x+w]

        seg_id = f"seg_{uuid.uuid4().hex[:12]}"

        # Compute contour complexity
        contours, _ = cv2.findContours(mask_region[y:y+h, x:x+w],
                                        cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        perimeter = sum(cv2.arcLength(c, True) for c in contours)
        complexity = (perimeter ** 2) / (area + 1e-8)

        if complexity < SEGMENT_MIN_COMPLEXITY:
            continue

        # Save cropped image (dev mode)
        cropped_path = ""
        if PIPELINE_MODE == "dev":
            cropped_path = os.path.join(SEGMENTS_DIR, artifact_id, f"{seg_id}.png")
            os.makedirs(os.path.dirname(cropped_path), exist_ok=True)
            cv2.imwrite(cropped_path, cropped)

        # Trace to SVG
        svg_path = os.path.join(SVGS_DIR, "segments", artifact_id, f"{seg_id}.svg")
        tmp_path = svg_path.replace(".svg", ".png")
        os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
        cv2.imwrite(tmp_path, cropped)
        svg_ok = trace_to_svg(tmp_path, svg_path)

        # Quality gate
        final_svg = None
        if svg_ok:
            with open(svg_path) as f:
                path_count = count_svg_paths(f.read())
            if SVG_MIN_PATHS <= path_count <= SVG_MAX_PATHS:
                final_svg = svg_path
            else:
                os.remove(svg_path)

        # Clean up tmp
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

        prov = create_provenance("clipseg", "", b"", "", f"clipseg_v1_mask_{label_idx}")

        segments.append(MotifSegment(
            id=seg_id, artifact_image_id=image_id, artifact_id=artifact_id,
            mask_index=idx, bbox=[x, y, w, h], area_ratio=area / image_area,
            contour_complexity=complexity, cropped_image_path=cropped_path,
            svg_path=final_svg, provenance=prov,
        ))

    return segments


def run(artifacts_dir: str = ARTIFACTS_DIR):
    manifest_path = os.path.join(MANIFESTS_DIR, "stage_4.json")
    manifest = load_manifest(manifest_path)
    processed = set(manifest.get("processed_images", []))
    all_segments: list[dict] = []

    for fn in os.listdir(artifacts_dir):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(artifacts_dir, fn)) as f:
            data = json.load(f)

        for img_data in data.get("images", []):
            if img_data["id"] in processed:
                continue
            local_path = img_data.get("local_path", "")
            if not local_path or not os.path.exists(local_path):
                continue

            image = cv2.imread(local_path)
            if image is None:
                continue

            segments = segment_image(image, data["id"], img_data["id"])
            for seg in segments:
                seg_path = os.path.join(ARTIFACTS_DIR, "segments", f"{seg.id}.json")
                os.makedirs(os.path.dirname(seg_path), exist_ok=True)
                with open(seg_path, "w") as f:
                    json.dump(seg.to_dict(), f, indent=2)

            processed.add(img_data["id"])

    save_manifest(manifest_path, {"processed_images": list(processed)})
    logger.info(f"Stage 4 complete: {len(processed)} images segmented")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_stage_4.py -v
```

- [ ] **Step 5: Commit**

```bash
git add pipeline/stage_4_segmentation.py tests/test_stage_4.py
git commit -m "feat(stage4): CLIPSeg motif segmentation with Otsu thresholding and SVG tracing"
```

---

### Task 10: Stage 5 — CLIP embedding + text tagging

**Files:**
- Create: `pipeline/stage_5_embedding.py`
- Create: `tests/test_stage_5.py`

- [ ] **Step 1: Write failing test for text motif extraction**

```python
# tests/test_stage_5.py
import pytest
from pipeline.stage_5_embedding import extract_motif_tags


def test_extract_spiral_wave():
    tags = extract_motif_tags("A bowl with spiral patterns and wave motifs")
    assert "spiral" in tags
    assert "wave" in tags


def test_extract_multiple():
    tags = extract_motif_tags("Cross-hatched with concentric circles and meander border")
    assert "cross" in tags
    assert "hatching" in tags
    assert "concentric_circles" in tags
    assert "meander" in tags


def test_extract_none():
    tags = extract_motif_tags("A plain undecorated vessel")
    assert tags == []


def test_extract_case_insensitive():
    tags = extract_motif_tags("SPIRALS and Rosettes")
    assert "spiral" in tags
    assert "rosette" in tags
```

- [ ] **Step 2: Run tests, verify failure**

```bash
python -m pytest tests/test_stage_5.py -v
```

- [ ] **Step 3: Implement Stage 5**

```python
# pipeline/stage_5_embedding.py
"""Stage 5: CLIP embeddings on motif segments + text motif tagging."""
import json
import os
import re
import logging

import numpy as np

from pipeline.provenance import create_provenance, load_manifest, save_manifest
from pipeline.config import ARTIFACTS_DIR, EMBEDDINGS_DIR, MANIFESTS_DIR, CLIP_MODEL

logger = logging.getLogger(__name__)

MOTIF_PATTERNS = {
    "spiral": r"\bspirals?\b", "meander": r"\bmeanders?\b",
    "cross": r"\bcross(?:es|ed)?\b", "chevron": r"\bchevrons?\b",
    "wave": r"\bwav(?:e|es|y)\b", "guilloche": r"\bguilloch(?:e|es)\b",
    "rosette": r"\brosettes?\b", "palmette": r"\bpalmettes?\b",
    "zigzag": r"\bzig-?zags?\b", "concentric_circles": r"\bconcentric\s+circles?\b",
    "hatching": r"\bhatch(?:ed|ing)\b", "geometric": r"\bgeometric\b",
    "floral": r"\bfloral\b", "figural": r"\bfigur(?:al|ative|ed)\b",
    "animal": r"\b(?:animal|zoomorphic)\b",
    "anthropomorphic": r"\banthropomorphic\b",
}


def extract_motif_tags(text: str) -> list[str]:
    if not text:
        return []
    lower = text.lower()
    return sorted(tag for tag, pat in MOTIF_PATTERNS.items() if re.search(pat, lower))


def compute_clip_embeddings(image_paths: list[str]) -> np.ndarray | None:
    if not image_paths:
        return None
    try:
        from transformers import CLIPProcessor, CLIPModel
        from PIL import Image

        model = CLIPModel.from_pretrained(CLIP_MODEL)
        processor = CLIPProcessor.from_pretrained(CLIP_MODEL)

        images = []
        for p in image_paths:
            try:
                images.append(Image.open(p).convert("RGB"))
            except Exception:
                images.append(None)

        valid = [(i, img) for i, img in enumerate(images) if img is not None]
        if not valid:
            return None

        indices, imgs = zip(*valid)
        inputs = processor(images=list(imgs), return_tensors="pt", padding=True)
        outputs = model.get_image_features(**inputs)
        embeds = outputs.detach().numpy()
        embeds = embeds / (np.linalg.norm(embeds, axis=1, keepdims=True) + 1e-8)

        # Place into full array with zeros for failed images
        full = np.zeros((len(image_paths), embeds.shape[1]))
        for i, idx in enumerate(indices):
            full[idx] = embeds[i]
        return full
    except ImportError:
        logger.error("transformers/torch not installed, skipping CLIP")
        return None


def run(artifacts_dir: str = ARTIFACTS_DIR):
    manifest_path = os.path.join(MANIFESTS_DIR, "stage_5.json")
    manifest = load_manifest(manifest_path)
    processed = set(manifest.get("processed", []))

    # Text tagging on artifacts
    for fn in os.listdir(artifacts_dir):
        if not fn.endswith(".json"):
            continue
        fp = os.path.join(artifacts_dir, fn)
        with open(fp) as f:
            data = json.load(f)
        art_id = data["id"]
        if art_id in processed:
            continue
        tags = extract_motif_tags(f"{data.get('name', '')} {data.get('description', '')}")
        data["motif_tags"] = tags
        with open(fp, "w") as f:
            json.dump(data, f, indent=2)
        processed.add(art_id)

    # CLIP embeddings on segments
    seg_dir = os.path.join(ARTIFACTS_DIR, "segments")
    if os.path.exists(seg_dir):
        seg_ids, seg_paths = [], []
        for fn in os.listdir(seg_dir):
            if not fn.endswith(".json"):
                continue
            with open(os.path.join(seg_dir, fn)) as f:
                seg = json.load(f)
            cropped = seg.get("cropped_image_path", "")
            svg = seg.get("svg_path", "")
            img_path = cropped if cropped and os.path.exists(cropped) else None
            if img_path and seg["id"] not in processed:
                seg_ids.append(seg["id"])
                seg_paths.append(img_path)

        if seg_paths:
            embeddings = compute_clip_embeddings(seg_paths)
            if embeddings is not None:
                os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
                np.savez_compressed(
                    os.path.join(EMBEDDINGS_DIR, "clip_embeddings.npz"),
                    embeddings=embeddings)
                with open(os.path.join(EMBEDDINGS_DIR, "index.json"), "w") as f:
                    json.dump({sid: i for i, sid in enumerate(seg_ids)}, f, indent=2)

    save_manifest(manifest_path, {"processed": list(processed)})
    logger.info(f"Stage 5 complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_stage_5.py -v
```

- [ ] **Step 5: Commit**

```bash
git add pipeline/stage_5_embedding.py tests/test_stage_5.py
git commit -m "feat(stage5): CLIP segment embeddings and text motif tagging"
```

---

## Chunk 4: Stages 6-7 — Similarity, Clustering, Export

### Task 11: Stage 6 — Similarity + HDBSCAN clustering

**Files:**
- Create: `pipeline/stage_6_similarity.py`
- Create: `tests/test_stage_6.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_stage_6.py
import pytest
import numpy as np
from pipeline.stage_6_similarity import jaccard_similarity, combined_score, find_medoid


def test_jaccard_identical():
    assert jaccard_similarity(["spiral", "wave"], ["spiral", "wave"]) == 1.0


def test_jaccard_partial():
    assert jaccard_similarity(["spiral", "wave"], ["spiral", "cross"]) == pytest.approx(1/3)


def test_jaccard_empty():
    assert jaccard_similarity([], []) == 0.0


def test_combined_score():
    s = combined_score(tag_score=0.5, embed_score=0.8, tag_w=0.3, embed_w=0.7)
    assert s == pytest.approx(0.5 * 0.3 + 0.8 * 0.7)


def test_find_medoid():
    embeddings = np.array([[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]])
    centroid = np.array([0.95, 0.05])
    idx = find_medoid(embeddings, centroid)
    assert idx == 1  # closest to centroid
```

- [ ] **Step 2: Run tests, verify failure**

```bash
python -m pytest tests/test_stage_6.py -v
```

- [ ] **Step 3: Implement Stage 6**

```python
# pipeline/stage_6_similarity.py
"""Stage 6: Pairwise similarity + HDBSCAN clustering + canonical SVGs."""
import json
import os
import shutil
import logging
from collections import Counter

import numpy as np
import hdbscan

from pipeline.models import MotifCluster
from pipeline.provenance import create_provenance, load_manifest, save_manifest
from pipeline.config import (
    ARTIFACTS_DIR, EMBEDDINGS_DIR, SIMILARITY_DIR, CLUSTERS_DIR, SVGS_DIR,
    MANIFESTS_DIR, SIMILARITY_TOP_N,
    SIMILARITY_EMBEDDING_WEIGHT, SIMILARITY_TAG_WEIGHT,
    HDBSCAN_MIN_CLUSTER_SIZES,
)

logger = logging.getLogger(__name__)


def jaccard_similarity(a: list[str], b: list[str]) -> float:
    if not a and not b:
        return 0.0
    sa, sb = set(a), set(b)
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


def combined_score(tag_score: float, embed_score: float,
                   tag_w: float = SIMILARITY_TAG_WEIGHT,
                   embed_w: float = SIMILARITY_EMBEDDING_WEIGHT) -> float:
    return tag_score * tag_w + embed_score * embed_w


def find_medoid(embeddings: np.ndarray, centroid: np.ndarray) -> int:
    dists = np.linalg.norm(embeddings - centroid, axis=1)
    return int(np.argmin(dists))


def run():
    # Load embeddings
    npz_path = os.path.join(EMBEDDINGS_DIR, "clip_embeddings.npz")
    index_path = os.path.join(EMBEDDINGS_DIR, "index.json")
    if not os.path.exists(npz_path) or not os.path.exists(index_path):
        logger.warning("No embeddings found, skipping Stage 6")
        return

    embeddings = np.load(npz_path)["embeddings"]
    with open(index_path) as f:
        embed_index = json.load(f)  # seg_id -> array index

    seg_ids = list(embed_index.keys())
    logger.info(f"Loaded {len(seg_ids)} segment embeddings")

    # Load segment metadata for tag lookup
    seg_dir = os.path.join(ARTIFACTS_DIR, "segments")
    seg_artifact_map = {}  # seg_id -> artifact_id
    if os.path.exists(seg_dir):
        for fn in os.listdir(seg_dir):
            if fn.endswith(".json"):
                with open(os.path.join(seg_dir, fn)) as f:
                    seg = json.load(f)
                seg_artifact_map[seg["id"]] = seg.get("artifact_id", "")

    # Load artifact tags
    art_tags: dict[str, list[str]] = {}
    for fn in os.listdir(ARTIFACTS_DIR):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(ARTIFACTS_DIR, fn)) as f:
            art = json.load(f)
        art_tags[art["id"]] = art.get("motif_tags", [])

    # --- Similarity ---
    os.makedirs(SIMILARITY_DIR, exist_ok=True)
    for i, sid_a in enumerate(seg_ids):
        a_vec = embeddings[embed_index[sid_a]]
        a_art = seg_artifact_map.get(sid_a, "")
        a_tags = art_tags.get(a_art, [])
        edges = []
        for j, sid_b in enumerate(seg_ids):
            if i == j:
                continue
            b_vec = embeddings[embed_index[sid_b]]
            b_art = seg_artifact_map.get(sid_b, "")
            b_tags = art_tags.get(b_art, [])
            embed_sim = float(np.dot(a_vec, b_vec))
            tag_sim = jaccard_similarity(a_tags, b_tags)
            score = combined_score(tag_sim, embed_sim)
            if score > 0:
                edges.append({"segment_b_id": sid_b, "score": round(score, 4), "method": "combined"})
        edges.sort(key=lambda e: e["score"], reverse=True)
        with open(os.path.join(SIMILARITY_DIR, f"{sid_a}.json"), "w") as f:
            json.dump({"segment_id": sid_a, "similar": edges[:SIMILARITY_TOP_N]}, f, indent=2)
        if (i + 1) % 500 == 0:
            logger.info(f"Similarity: {i+1}/{len(seg_ids)}")

    # --- Clustering ---
    os.makedirs(CLUSTERS_DIR, exist_ok=True)
    best_labels, best_score, best_mcs = None, -1, 15
    for mcs in HDBSCAN_MIN_CLUSTER_SIZES:
        clusterer = hdbscan.HDBSCAN(min_cluster_size=mcs, metric="cosine")
        labels = clusterer.fit_predict(embeddings)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        if n_clusters < 2:
            continue
        from sklearn.metrics import silhouette_score
        try:
            score = silhouette_score(embeddings, labels, metric="cosine")
        except ValueError:
            continue
        logger.info(f"HDBSCAN min_cluster_size={mcs}: {n_clusters} clusters, silhouette={score:.3f}")
        if score > best_score:
            best_score, best_labels, best_mcs = score, labels, mcs

    if best_labels is None:
        logger.warning("No valid clustering found")
        return

    logger.info(f"Best clustering: min_cluster_size={best_mcs}, silhouette={best_score:.3f}")

    # Build clusters
    cluster_members: dict[int, list[str]] = {}
    for i, label in enumerate(best_labels):
        if label == -1:
            continue
        cluster_members.setdefault(label, []).append(seg_ids[i])

    for label, members in cluster_members.items():
        cluster_id = f"cluster_{label}"
        member_indices = [embed_index[sid] for sid in members]
        member_embeddings = embeddings[member_indices]
        centroid = member_embeddings.mean(axis=0)

        # Medoid canonical SVG
        medoid_idx = find_medoid(member_embeddings, centroid)
        medoid_seg_id = members[medoid_idx]
        medoid_svg_src = os.path.join(SVGS_DIR, "segments")
        canonical_svg_path = os.path.join(SVGS_DIR, "canonical", f"{cluster_id}.svg")

        # Find the medoid's SVG
        found_svg = False
        for root, dirs, files in os.walk(medoid_svg_src):
            for fn in files:
                if fn.startswith(medoid_seg_id) and fn.endswith(".svg"):
                    os.makedirs(os.path.dirname(canonical_svg_path), exist_ok=True)
                    shutil.copy2(os.path.join(root, fn), canonical_svg_path)
                    found_svg = True
                    break
            if found_svg:
                break

        # Auto-label from most common tags
        all_tags: list[str] = []
        for sid in members:
            art_id = seg_artifact_map.get(sid, "")
            all_tags.extend(art_tags.get(art_id, []))
        tag_counts = Counter(all_tags)
        label_str = tag_counts.most_common(1)[0][0] if tag_counts else None

        prov = create_provenance("hdbscan", "", str(best_mcs).encode(), "",
                                 f"hdbscan_min_cluster_size_{best_mcs}")

        cluster = MotifCluster(
            id=cluster_id, label=label_str, member_count=len(members),
            centroid_embedding=centroid.tolist(),
            canonical_svg_path=canonical_svg_path if found_svg else "",
            member_segment_ids=members, provenance=prov,
        )
        with open(os.path.join(CLUSTERS_DIR, f"{cluster_id}.json"), "w") as f:
            json.dump(cluster.to_dict(), f, indent=2)

    logger.info(f"Stage 6 complete: {len(cluster_members)} clusters")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_stage_6.py -v
```

- [ ] **Step 5: Commit**

```bash
git add pipeline/stage_6_similarity.py tests/test_stage_6.py
git commit -m "feat(stage6): pairwise similarity, HDBSCAN clustering, medoid canonical SVGs"
```

---

### Task 12: Stage 7 — Export

**Files:**
- Create: `pipeline/stage_7_export.py`
- Create: `tests/test_stage_7.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_stage_7.py
from pipeline.stage_7_export import build_site_summary


def test_build_site_summary():
    site = {"id": "1", "name": "Abdera", "region": "Aegean",
            "latitude": 40.93, "longitude": 24.97}
    arts = [
        {"id": "a1", "site_id": "1", "motif_tags": ["spiral"]},
        {"id": "a2", "site_id": "1", "motif_tags": ["wave", "spiral"]},
    ]
    s = build_site_summary(site, arts, ["cluster_0"])
    assert s["artifact_count"] == 2
    assert "spiral" in s["motif_tags"]
    assert "cluster_0" in s["cluster_ids"]
```

- [ ] **Step 2: Run test, verify failure**

```bash
python -m pytest tests/test_stage_7.py -v
```

- [ ] **Step 3: Implement Stage 7**

```python
# pipeline/stage_7_export.py
"""Stage 7: Export pipeline data for Next.js static consumption."""
import json
import os
import shutil
import logging
from pipeline.config import (
    SITES_DIR, ARTIFACTS_DIR, SVGS_DIR, SIMILARITY_DIR, CLUSTERS_DIR,
    EXPORT_DIR, EXPORT_SIZE_BUDGET_MB, SIMILARITY_EXPORT_TOP_N,
)

logger = logging.getLogger(__name__)


def build_site_summary(site: dict, artifacts: list[dict],
                       cluster_ids: list[str]) -> dict:
    tags = set()
    for a in artifacts:
        tags.update(a.get("motif_tags", []))
    return {
        "id": site["id"], "name": site.get("name"),
        "region": site.get("region"),
        "latitude": site.get("latitude"), "longitude": site.get("longitude"),
        "artifact_count": len(artifacts),
        "motif_tags": sorted(tags),
        "cluster_ids": cluster_ids,
    }


def run():
    os.makedirs(EXPORT_DIR, exist_ok=True)

    # Load sites
    sites = {}
    for fn in os.listdir(SITES_DIR):
        if fn.endswith(".json"):
            with open(os.path.join(SITES_DIR, fn)) as f:
                s = json.load(f)
                sites[s["id"]] = s

    # Load artifacts grouped by site
    arts_by_site: dict[str, list[dict]] = {}
    for fn in os.listdir(ARTIFACTS_DIR):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(ARTIFACTS_DIR, fn)) as f:
            art = json.load(f)
        sid = art.get("site_id") or "unlinked"
        arts_by_site.setdefault(sid, []).append(art)

    # Load clusters
    clusters = []
    cluster_site_map: dict[str, set] = {}  # site_id -> cluster_ids
    if os.path.exists(CLUSTERS_DIR):
        for fn in os.listdir(CLUSTERS_DIR):
            if fn.endswith(".json"):
                with open(os.path.join(CLUSTERS_DIR, fn)) as f:
                    c = json.load(f)
                clusters.append(c)

    # Export sites.json
    summaries = []
    for sid, site in sites.items():
        arts = arts_by_site.get(sid, [])
        if arts:
            cids = list(cluster_site_map.get(sid, []))
            summaries.append(build_site_summary(site, arts, cids))
    with open(os.path.join(EXPORT_DIR, "sites.json"), "w") as f:
        json.dump(summaries, f)

    # Export artifacts per site
    arts_dir = os.path.join(EXPORT_DIR, "artifacts")
    os.makedirs(arts_dir, exist_ok=True)
    for sid, arts in arts_by_site.items():
        with open(os.path.join(arts_dir, f"{sid}.json"), "w") as f:
            json.dump(arts, f)

    # Export clusters
    with open(os.path.join(EXPORT_DIR, "clusters.json"), "w") as f:
        json.dump(clusters, f)

    # Export SVGs
    for subdir in ["segments", "canonical"]:
        src = os.path.join(SVGS_DIR, subdir)
        dst = os.path.join(EXPORT_DIR, "svgs", subdir)
        if os.path.exists(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)

    # Export similarity (capped)
    sim_out = os.path.join(EXPORT_DIR, "similarity")
    os.makedirs(sim_out, exist_ok=True)
    if os.path.exists(SIMILARITY_DIR):
        for fn in os.listdir(SIMILARITY_DIR):
            if fn.endswith(".json"):
                with open(os.path.join(SIMILARITY_DIR, fn)) as f:
                    sim = json.load(f)
                sim["similar"] = sim["similar"][:SIMILARITY_EXPORT_TOP_N]
                with open(os.path.join(sim_out, fn), "w") as f:
                    json.dump(sim, f)

    # Export provenance per site
    prov_out = os.path.join(EXPORT_DIR, "provenance")
    os.makedirs(prov_out, exist_ok=True)
    for sid, arts in arts_by_site.items():
        provs = []
        for a in arts:
            provs.extend(a.get("provenance", []))
        with open(os.path.join(prov_out, f"{sid}.json"), "w") as f:
            json.dump(provs, f)

    # Size check
    total = sum(os.path.getsize(os.path.join(dp, fn))
                for dp, _, fns in os.walk(EXPORT_DIR) for fn in fns)
    mb = total / (1024 * 1024)
    logger.info(f"Export size: {mb:.1f} MB (budget: {EXPORT_SIZE_BUDGET_MB} MB)")
    if mb > EXPORT_SIZE_BUDGET_MB:
        logger.warning("Export exceeds budget!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_stage_7.py -v
```

- [ ] **Step 5: Commit**

```bash
git add pipeline/stage_7_export.py tests/test_stage_7.py
git commit -m "feat(stage7): static export with chunked similarity, clusters, and size budget"
```

---

## Chunk 5: Pipeline Runner & Integration

### Task 13: Pipeline orchestrator

**Files:**
- Create: `pipeline/run.py`

- [ ] **Step 1: Implement runner**

```python
# pipeline/run.py
"""Run pipeline stages selectively."""
import argparse
import importlib
import logging
import sys

logger = logging.getLogger("pipeline")

STAGES = {
    1: ("Site Matching", "pipeline.stage_1_site_matching"),
    2: ("Artifact Harvesting", "pipeline.stage_2_artifact_harvest"),
    3: ("Image Collection", "pipeline.stage_3_image_collection"),
    4: ("Motif Segmentation", "pipeline.stage_4_segmentation"),
    5: ("Motif Embedding", "pipeline.stage_5_embedding"),
    6: ("Similarity + Clustering", "pipeline.stage_6_similarity"),
    7: ("Export", "pipeline.stage_7_export"),
}


def main():
    parser = argparse.ArgumentParser(description="Ancient Motif Pipeline")
    parser.add_argument("--stages", nargs="+", type=int,
                        default=list(STAGES.keys()))
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    for n in args.stages:
        if n not in STAGES:
            logger.error(f"Unknown stage: {n}")
            sys.exit(1)
        name, mod = STAGES[n]
        logger.info(f"=== Stage {n}: {name} ===")
        importlib.import_module(mod).run()
        logger.info(f"=== Stage {n} complete ===\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add pipeline/run.py
git commit -m "feat: pipeline orchestrator for selective stage execution"
```

---

### Task 14: Run full test suite

- [ ] **Step 1: Run all tests**

```bash
python -m pytest tests/ -v
```
Expected: all PASS

- [ ] **Step 2: Fix any failures and commit fixes**

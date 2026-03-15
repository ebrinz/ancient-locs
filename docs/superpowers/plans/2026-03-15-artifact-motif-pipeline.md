# Artifact Motif Influence Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python data enrichment pipeline that links archaeological sites to artifact records, images, motif embeddings, and similarity scores, then exports static data for a Next.js map app on GitHub Pages.

**Architecture:** Six-stage Python pipeline (site matching → artifact harvesting → image collection → motif tagging → similarity → export) producing static JSON/SVG/NPZ files. Next.js static app consumes exported data via MapLibre GL map with SVG motif markers.

**Tech Stack:** Python 3.11+, requests, SPARQLWrapper, numpy, transformers (CLIP), vtracer, rembg, opencv-python, Levenshtein. Next.js 14, MapLibre GL JS, TypeScript.

**Spec:** `docs/superpowers/specs/2026-03-15-artifact-motif-pipeline-design.md`

---

## Chunk 1: Project Scaffolding & Core Infrastructure

### Task 1: Reorganize repo and update gitignore

**Files:**
- Move: `scrape.py` → `pipeline/scrape.py`
- Move: `places.json` → `data/raw/places.json`
- Modify: `.gitignore`
- Modify: `README.md`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p pipeline data/raw data/sites data/artifacts data/images data/svgs data/embeddings data/similarity data/manifests data/raw/wikidata data/raw/met_museum data/raw/british_museum data/raw/harvard
```

- [ ] **Step 2: Move existing files**

```bash
git mv scrape.py pipeline/scrape.py
git mv places.json data/raw/places.json
```

- [ ] **Step 3: Update .gitignore**

Add to `.gitignore`:
```
# Pipeline data outputs (too large for repo)
data/sites/
data/artifacts/
data/images/
data/svgs/
data/embeddings/
data/similarity/
data/manifests/
data/raw/wikidata/
data/raw/met_museum/
data/raw/british_museum/
data/raw/harvard/

# Keep data/raw/places.json tracked
!data/raw/places.json

# Next.js
web/node_modules/
web/.next/
web/out/
web/public/data/
```

- [ ] **Step 4: Update scrape.py OUTPUT_FILE path**

In `pipeline/scrape.py`, change:
```python
OUTPUT_FILE = 'places.json'
```
to:
```python
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'places.json')
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: reorganize repo — move scrape.py to pipeline/, places.json to data/raw/"
```

---

### Task 2: Data models and provenance utilities

**Files:**
- Create: `pipeline/models.py`
- Create: `pipeline/provenance.py`
- Create: `pipeline/config.py`
- Test: `tests/test_models.py`
- Test: `tests/test_provenance.py`

- [ ] **Step 1: Write failing test for models**

```python
# tests/test_models.py
import pytest
from pipeline.models import ProvenanceRecord, Site, Artifact, ArtifactImage, Embedding, SimilarityEdge


def test_provenance_record_to_dict():
    pr = ProvenanceRecord(
        source_id="wikidata",
        source_url="https://query.wikidata.org/sparql?query=...",
        fetch_date="2026-03-15T10:00:00Z",
        license="CC0",
        raw_response_hash="abc123",
        transformation="none",
    )
    d = pr.to_dict()
    assert d["source_id"] == "wikidata"
    assert d["license"] == "CC0"


def test_site_from_raw_places_record():
    raw = {
        "id": "23374",
        "name": "Abdera",
        "other_names": None,
        "modern_names": None,
        "region": "Aegean",
        "section": None,
        "latitude": "40.93360567 N",
        "longitude": "24.97302984 E",
        "status": "Accurate location",
        "info": None,
        "sources": None,
    }
    site = Site.from_raw(raw)
    assert site.latitude == pytest.approx(40.93360567)
    assert site.longitude == pytest.approx(24.97302984)
    assert site.id == "23374"


def test_site_from_raw_south_west():
    raw = {
        "id": "1",
        "name": "Test",
        "other_names": None,
        "modern_names": None,
        "region": "Latin America : Settlements",
        "section": None,
        "latitude": "19.69291001 S",
        "longitude": "98.84606407 W",
        "status": "Accurate location",
        "info": None,
        "sources": None,
    }
    site = Site.from_raw(raw)
    assert site.latitude == pytest.approx(-19.69291001)
    assert site.longitude == pytest.approx(-98.84606407)


def test_site_from_raw_null_name():
    raw = {
        "id": "999",
        "name": None,
        "other_names": None,
        "modern_names": None,
        "region": "Europe",
        "section": None,
        "latitude": "50.0 N",
        "longitude": "10.0 E",
        "status": "Accurate location",
        "info": None,
        "sources": None,
    }
    site = Site.from_raw(raw)
    assert site.name is None
    assert site.latitude == pytest.approx(50.0)


def test_artifact_to_dict_roundtrip():
    a = Artifact(
        id="art_1",
        name="Spiral Bowl",
        description="A bowl with spiral motifs",
        type="pottery",
        site_id="23374",
        region="Aegean",
        period="Late Bronze Age",
        date_range_start=-1500,
        date_range_end=-1200,
        materials=["clay"],
        techniques=["wheel-thrown"],
        motif_tags=["spiral"],
        provenance=[],
    )
    d = a.to_dict()
    assert d["name"] == "Spiral Bowl"
    assert d["motif_tags"] == ["spiral"]
    assert d["site_id"] == "23374"


def test_similarity_edge_to_dict():
    e = SimilarityEdge(
        artifact_a_id="art_1",
        artifact_b_id="art_2",
        score=0.87,
        method="clip_cosine",
    )
    d = e.to_dict()
    assert d["score"] == 0.87
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/crashy/Development/ancient-locs && python -m pytest tests/test_models.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'pipeline'`

- [ ] **Step 3: Implement models**

```python
# pipeline/__init__.py
# (empty, makes pipeline a package)
```

```python
# pipeline/models.py
from dataclasses import dataclass, field, asdict
from typing import Optional


def parse_coordinate(value: str) -> float:
    """Parse '40.93360567 N' into 40.93360567, negating for S/W."""
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
    svg_path: Optional[str]
    provenance: ProvenanceRecord

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Embedding:
    id: str
    artifact_id: str
    model: str
    vector: list[float]
    embedding_type: str  # "image" or "text"
    provenance: ProvenanceRecord

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SimilarityEdge:
    artifact_a_id: str
    artifact_b_id: str
    score: float
    method: str

    def to_dict(self) -> dict:
        return asdict(self)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_models.py -v
```
Expected: all PASS

- [ ] **Step 5: Write failing test for provenance utilities**

```python
# tests/test_provenance.py
import json
import os
import tempfile
from pipeline.provenance import (
    compute_hash,
    create_provenance,
    save_raw_response,
    load_manifest,
    save_manifest,
)


def test_compute_hash():
    h = compute_hash(b'{"test": true}')
    assert len(h) == 64  # SHA256 hex


def test_compute_hash_deterministic():
    data = b"hello world"
    assert compute_hash(data) == compute_hash(data)


def test_create_provenance():
    pr = create_provenance(
        source_id="met_museum",
        source_url="https://collectionapi.metmuseum.org/public/collection/v1/objects/1",
        raw_data=b'{"objectID": 1}',
        license="CC0",
        transformation="none",
    )
    assert pr.source_id == "met_museum"
    assert pr.raw_response_hash == compute_hash(b'{"objectID": 1}')
    assert pr.fetch_date  # not empty


def test_save_raw_response():
    with tempfile.TemporaryDirectory() as tmpdir:
        data = b'{"objectID": 1}'
        path = save_raw_response(data, "met_museum", tmpdir)
        assert os.path.exists(path)
        with open(path, "rb") as f:
            assert f.read() == data


def test_manifest_roundtrip():
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = os.path.join(tmpdir, "manifest.json")
        save_manifest(manifest_path, {"processed": ["site_1", "site_2"]})
        loaded = load_manifest(manifest_path)
        assert loaded["processed"] == ["site_1", "site_2"]


def test_load_manifest_missing_file():
    loaded = load_manifest("/nonexistent/path/manifest.json")
    assert loaded == {}
```

- [ ] **Step 6: Run tests to verify they fail**

```bash
python -m pytest tests/test_provenance.py -v
```
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 7: Implement provenance utilities**

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
    source_id: str,
    source_url: str,
    raw_data: bytes,
    license: str,
    transformation: str = "none",
) -> ProvenanceRecord:
    return ProvenanceRecord(
        source_id=source_id,
        source_url=source_url,
        fetch_date=datetime.now(timezone.utc).isoformat(),
        license=license,
        raw_response_hash=compute_hash(raw_data),
        transformation=transformation,
    )


def save_raw_response(data: bytes, source_id: str, raw_dir: str) -> str:
    source_dir = os.path.join(raw_dir, source_id)
    os.makedirs(source_dir, exist_ok=True)
    filename = compute_hash(data) + ".json"
    path = os.path.join(source_dir, filename)
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
    with open(path, "r") as f:
        return json.load(f)
```

- [ ] **Step 8: Run tests to verify they pass**

```bash
python -m pytest tests/test_provenance.py -v
```
Expected: all PASS

- [ ] **Step 9: Create config**

```python
# pipeline/config.py
import os

# Paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
SITES_DIR = os.path.join(DATA_DIR, "sites")
ARTIFACTS_DIR = os.path.join(DATA_DIR, "artifacts")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
SVGS_DIR = os.path.join(DATA_DIR, "svgs")
EMBEDDINGS_DIR = os.path.join(DATA_DIR, "embeddings")
SIMILARITY_DIR = os.path.join(DATA_DIR, "similarity")
MANIFESTS_DIR = os.path.join(DATA_DIR, "manifests")
EXPORT_DIR = os.path.join(PROJECT_ROOT, "web", "public", "data")

# Raw source subdirectories
RAW_PLACES = os.path.join(RAW_DIR, "places.json")

# API Configuration
WIKIDATA_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
WIKIDATA_USER_AGENT = "AncientLocsBot/1.0 (https://github.com/ebrinz/ancient-locs)"
WIKIDATA_QUERY_TIMEOUT = 60

MET_MUSEUM_API_BASE = "https://collectionapi.metmuseum.org/public/collection/v1"
MET_MUSEUM_RATE_LIMIT = 1.0  # seconds between requests

BM_SPARQL_ENDPOINT = "https://collection.britishmuseum.org/sparql"
BM_RATE_LIMIT = 2.0  # seconds between requests

HARVARD_API_BASE = "https://api.harvardartmuseums.org"
HARVARD_API_KEY = os.environ.get("HARVARD_API_KEY", "")
HARVARD_DAILY_LIMIT = 2500

# Site matching
SITE_MATCH_RADIUS_KM = 5.0
SITE_NAME_FUZZY_THRESHOLD = 3  # max Levenshtein distance

# Similarity
SIMILARITY_TOP_N = 20
SIMILARITY_TAG_WEIGHT = 0.4
SIMILARITY_EMBEDDING_WEIGHT = 0.6

# CLIP
CLIP_MODEL = "openai/clip-vit-base-patch32"

# SVG quality gate
SVG_MIN_PATHS = 5
SVG_MAX_PATHS = 5000

# Export
EXPORT_SIZE_BUDGET_MB = 50
SIMILARITY_EXPORT_TOP_N = 10  # reduced for export
```

- [ ] **Step 10: Create requirements.txt**

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
rembg>=2.0
vtracer>=0.6
pytest>=7.0
```

- [ ] **Step 11: Commit**

```bash
git add pipeline/ tests/ -A
git commit -m "feat: add data models, provenance utilities, and config"
```

---

## Chunk 2: Stage 1 — Site Matching

### Task 3: Coordinate parsing and site loading

**Files:**
- Create: `pipeline/stage_1_site_matching.py`
- Test: `tests/test_stage_1.py`

- [ ] **Step 1: Write failing test for loading all sites from raw data**

```python
# tests/test_stage_1.py
import json
import os
import tempfile
import pytest
from pipeline.models import Site
from pipeline.stage_1_site_matching import load_raw_sites, save_site


def test_load_raw_sites():
    raw_data = [
        {
            "id": "1",
            "name": "Abdera",
            "other_names": None,
            "modern_names": None,
            "region": "Aegean",
            "section": None,
            "latitude": "40.93360567 N",
            "longitude": "24.97302984 E",
            "status": "Accurate location",
            "info": None,
            "sources": None,
        },
        {
            "id": "2",
            "name": None,
            "other_names": None,
            "modern_names": None,
            "region": "Europe",
            "section": None,
            "latitude": "50.0 S",
            "longitude": "10.0 W",
            "status": "Imprecise",
            "info": None,
            "sources": None,
        },
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "places.json")
        with open(path, "w") as f:
            json.dump(raw_data, f)
        sites = load_raw_sites(path)
        assert len(sites) == 2
        assert sites[0].latitude == pytest.approx(40.93360567)
        assert sites[1].latitude == pytest.approx(-50.0)
        assert sites[1].longitude == pytest.approx(-10.0)
        assert sites[1].name is None


def test_save_site():
    site = Site(
        id="1", name="Test", other_names=None, modern_names=None,
        region="Aegean", section=None, latitude=40.0, longitude=24.0,
        status="Accurate location", info=None, sources=None,
        external_ids={"wikidata": "Q12345", "pleiades": None},
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        save_site(site, tmpdir)
        path = os.path.join(tmpdir, "1.json")
        assert os.path.exists(path)
        with open(path) as f:
            loaded = json.load(f)
        assert loaded["external_ids"]["wikidata"] == "Q12345"
```

- [ ] **Step 2: Run test to verify failure**

```bash
python -m pytest tests/test_stage_1.py::test_load_raw_sites tests/test_stage_1.py::test_save_site -v
```
Expected: FAIL

- [ ] **Step 3: Implement site loading and saving**

```python
# pipeline/stage_1_site_matching.py
"""Stage 1: Match sites to external IDs (Wikidata, Pleiades)."""
import json
import os
import time
import logging

from pipeline.models import Site, parse_coordinate
from pipeline.provenance import load_manifest, save_manifest
from pipeline.config import (
    RAW_PLACES, SITES_DIR, MANIFESTS_DIR,
    WIKIDATA_SPARQL_ENDPOINT, WIKIDATA_USER_AGENT, WIKIDATA_QUERY_TIMEOUT,
    SITE_MATCH_RADIUS_KM, SITE_NAME_FUZZY_THRESHOLD,
)

logger = logging.getLogger(__name__)


def load_raw_sites(path: str) -> list[Site]:
    with open(path) as f:
        raw_data = json.load(f)
    return [Site.from_raw(record) for record in raw_data]


def save_site(site: Site, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{site.id}.json")
    with open(path, "w") as f:
        json.dump(site.to_dict(), f, indent=2)
    return path
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_stage_1.py::test_load_raw_sites tests/test_stage_1.py::test_save_site -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/stage_1_site_matching.py tests/test_stage_1.py
git commit -m "feat(stage1): site loading and saving from raw places.json"
```

---

### Task 4: Wikidata SPARQL matching

**Files:**
- Modify: `pipeline/stage_1_site_matching.py`
- Test: `tests/test_stage_1.py` (add tests)

- [ ] **Step 1: Write failing test for Wikidata query builder**

```python
# Add to tests/test_stage_1.py
from pipeline.stage_1_site_matching import build_wikidata_query


def test_build_wikidata_query():
    query = build_wikidata_query(40.93, 24.97, radius_km=5.0)
    assert "40.93" in query
    assert "24.97" in query
    assert "wdt:P31" in query  # instance-of
    assert "wdt:P625" in query  # coordinate location
```

- [ ] **Step 2: Run test to verify failure**

```bash
python -m pytest tests/test_stage_1.py::test_build_wikidata_query -v
```

- [ ] **Step 3: Implement query builder**

Add to `pipeline/stage_1_site_matching.py`:

```python
def build_wikidata_query(lat: float, lng: float, radius_km: float = 5.0) -> str:
    return f"""
    SELECT ?item ?itemLabel ?pleiades WHERE {{
      SERVICE wikibase:around {{
        ?item wdt:P625 ?location .
        bd:serviceParam wikibase:center "Point({lng} {lat})"^^geo:wktLiteral .
        bd:serviceParam wikibase:radius "{radius_km}" .
      }}
      ?item wdt:P31/wdt:P279* wd:Q839954 .  # archaeological site or subclass
      OPTIONAL {{ ?item wdt:P1584 ?pleiades . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
    }}
    """
```

- [ ] **Step 4: Run test to verify pass**

```bash
python -m pytest tests/test_stage_1.py::test_build_wikidata_query -v
```

- [ ] **Step 5: Write failing test for match scoring**

```python
# Add to tests/test_stage_1.py
from pipeline.stage_1_site_matching import score_match


def test_score_match_exact_name():
    score = score_match("Abdera", "Abdera")
    assert score == 1.0


def test_score_match_close_name():
    score = score_match("Abdera", "Abdера")  # close match
    assert score > 0.5


def test_score_match_no_match():
    score = score_match("Abdera", "Completely Different Place")
    assert score == 0.0
```

- [ ] **Step 6: Implement match scoring**

Add to `pipeline/stage_1_site_matching.py`:

```python
import Levenshtein


def score_match(site_name: str | None, candidate_name: str) -> float:
    if site_name is None:
        return 0.0
    if site_name.lower() == candidate_name.lower():
        return 1.0
    distance = Levenshtein.distance(site_name.lower(), candidate_name.lower())
    if distance <= SITE_NAME_FUZZY_THRESHOLD:
        return 1.0 - (distance / (SITE_NAME_FUZZY_THRESHOLD + 1))
    return 0.0
```

- [ ] **Step 7: Run all Stage 1 tests**

```bash
python -m pytest tests/test_stage_1.py -v
```
Expected: all PASS

- [ ] **Step 8: Implement query_wikidata function (network call, not unit tested)**

Add to `pipeline/stage_1_site_matching.py`:

```python
from SPARQLWrapper import SPARQLWrapper, JSON


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
    best_score = 0.0
    best_match = None
    for candidate in candidates:
        s = score_match(site.name, candidate["label"])
        if s > best_score:
            best_score = s
            best_match = candidate
    # For null-name sites, take closest result if any
    if site.name is None and candidates:
        best_match = candidates[0]
    if best_match:
        site.external_ids["wikidata"] = best_match["qid"]
        if best_match.get("pleiades"):
            site.external_ids["pleiades"] = best_match["pleiades"]
    return site
```

- [ ] **Step 9: Implement main runner**

Add to `pipeline/stage_1_site_matching.py`:

```python
def run(input_path: str = RAW_PLACES, output_dir: str = SITES_DIR):
    manifest_path = os.path.join(MANIFESTS_DIR, "stage_1.json")
    manifest = load_manifest(manifest_path)
    processed = set(manifest.get("processed", []))

    sites = load_raw_sites(input_path)
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
        time.sleep(1)  # rate limit

    save_manifest(manifest_path, {"processed": list(processed)})
    logger.info(f"Stage 1 complete: {matched}/{len(sites)} sites matched")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
```

- [ ] **Step 10: Commit**

```bash
git add pipeline/stage_1_site_matching.py tests/test_stage_1.py
git commit -m "feat(stage1): Wikidata SPARQL matching with fuzzy name scoring"
```

---

## Chunk 3: Stage 2 — Artifact Harvesting

### Task 5: API client base and caching

**Files:**
- Create: `pipeline/api_client.py`
- Test: `tests/test_api_client.py`

- [ ] **Step 1: Write failing test for cached API client**

```python
# tests/test_api_client.py
import json
import os
import tempfile
from pipeline.api_client import CachedAPIClient


def test_cached_client_saves_response():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = CachedAPIClient(source_id="test", cache_dir=tmpdir, rate_limit=0)
        # Simulate a cached response
        data = b'{"test": true}'
        path = client.save_to_cache(data)
        assert os.path.exists(path)
        loaded = client.load_from_cache(path)
        assert loaded == data


def test_cached_client_creates_provenance():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = CachedAPIClient(source_id="met_museum", cache_dir=tmpdir, rate_limit=0)
        data = b'{"objectID": 1}'
        pr = client.create_provenance(
            source_url="https://example.com/api/1",
            raw_data=data,
            license="CC0",
        )
        assert pr.source_id == "met_museum"
        assert len(pr.raw_response_hash) == 64
```

- [ ] **Step 2: Run test to verify failure**

```bash
python -m pytest tests/test_api_client.py -v
```

- [ ] **Step 3: Implement CachedAPIClient**

```python
# pipeline/api_client.py
"""Base API client with caching and rate limiting."""
import os
import time
import requests
import logging

from pipeline.provenance import compute_hash, create_provenance, save_raw_response
from pipeline.models import ProvenanceRecord

logger = logging.getLogger(__name__)


class CachedAPIClient:
    def __init__(self, source_id: str, cache_dir: str, rate_limit: float = 1.0):
        self.source_id = source_id
        self.cache_dir = cache_dir
        self.rate_limit = rate_limit
        self._last_request_time = 0.0

    def _wait_for_rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last_request_time = time.time()

    def get(self, url: str, params: dict | None = None, headers: dict | None = None) -> bytes | None:
        cache_key = compute_hash((url + str(params)).encode())
        cache_path = os.path.join(self.cache_dir, self.source_id, cache_key + ".json")
        if os.path.exists(cache_path):
            return self.load_from_cache(cache_path)
        self._wait_for_rate_limit()
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.content
            self.save_to_cache(data, cache_path)
            return data
        except requests.RequestException as e:
            logger.warning(f"Request failed for {url}: {e}")
            return None

    def save_to_cache(self, data: bytes, path: str | None = None) -> str:
        if path is None:
            cache_key = compute_hash(data)
            path = os.path.join(self.cache_dir, self.source_id, cache_key + ".json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return path

    def load_from_cache(self, path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()

    def create_provenance(self, source_url: str, raw_data: bytes, license: str, transformation: str = "none") -> ProvenanceRecord:
        return create_provenance(
            source_id=self.source_id,
            source_url=source_url,
            raw_data=raw_data,
            license=license,
            transformation=transformation,
        )
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_api_client.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/api_client.py tests/test_api_client.py
git commit -m "feat: add cached API client with rate limiting and provenance"
```

---

### Task 6: Met Museum harvester

**Files:**
- Create: `pipeline/harvesters/met.py`
- Create: `pipeline/harvesters/__init__.py`
- Test: `tests/test_harvester_met.py`

- [ ] **Step 1: Write failing test for Met response parsing**

```python
# tests/test_harvester_met.py
from pipeline.harvesters.met import parse_met_object
from pipeline.models import ProvenanceRecord


def test_parse_met_object_pottery():
    raw = {
        "objectID": 248908,
        "title": "Terracotta kylix (drinking cup)",
        "objectName": "Kylix",
        "medium": "Terracotta; red-figure",
        "classification": "Vases",
        "culture": "Greek, Attic",
        "period": "Classical",
        "objectBeginDate": -450,
        "objectEndDate": -440,
        "primaryImage": "https://images.metmuseum.org/example.jpg",
        "additionalImages": [],
        "artistDisplayName": "",
        "department": "Greek and Roman Art",
        "excavation": "Excavated at Agrigento",
        "isPublicDomain": True,
    }
    prov = ProvenanceRecord(
        source_id="met_museum",
        source_url="https://collectionapi.metmuseum.org/public/collection/v1/objects/248908",
        fetch_date="2026-03-15T00:00:00Z",
        license="CC0",
        raw_response_hash="abc",
        transformation="none",
    )
    artifact, images = parse_met_object(raw, prov, site_id="123", region="Aegean")
    assert artifact.name == "Terracotta kylix (drinking cup)"
    assert artifact.type == "Vases"
    assert artifact.date_range_start == -450
    assert artifact.materials == ["Terracotta"]
    assert artifact.techniques == ["red-figure"]
    assert len(images) == 1
    assert images[0].source_image_url == "https://images.metmuseum.org/example.jpg"


def test_parse_met_object_no_image():
    raw = {
        "objectID": 1,
        "title": "Fragment",
        "objectName": "Fragment",
        "medium": "Clay",
        "classification": "Ceramics",
        "culture": "Egyptian",
        "period": "",
        "objectBeginDate": -2000,
        "objectEndDate": -1500,
        "primaryImage": "",
        "additionalImages": [],
        "artistDisplayName": "",
        "department": "Egyptian Art",
        "excavation": "",
        "isPublicDomain": False,
    }
    prov = ProvenanceRecord(
        source_id="met_museum", source_url="", fetch_date="", license="CC0",
        raw_response_hash="", transformation="none",
    )
    artifact, images = parse_met_object(raw, prov, site_id=None, region="Egypt")
    assert artifact.site_id is None
    assert artifact.region == "Egypt"
    assert len(images) == 0
```

- [ ] **Step 2: Run test to verify failure**

```bash
python -m pytest tests/test_harvester_met.py -v
```

- [ ] **Step 3: Implement Met parser**

```python
# pipeline/harvesters/__init__.py
# (empty)
```

```python
# pipeline/harvesters/met.py
"""Metropolitan Museum of Art API harvester."""
import json
import logging
import uuid

from pipeline.api_client import CachedAPIClient
from pipeline.models import Artifact, ArtifactImage, ProvenanceRecord
from pipeline.config import MET_MUSEUM_API_BASE, MET_MUSEUM_RATE_LIMIT, RAW_DIR

logger = logging.getLogger(__name__)


def parse_medium(medium: str) -> tuple[list[str], list[str]]:
    """Split medium string like 'Terracotta; red-figure' into materials and techniques."""
    if not medium:
        return [], []
    parts = [p.strip() for p in medium.split(";")]
    materials = [parts[0]] if parts else []
    techniques = parts[1:] if len(parts) > 1 else []
    return materials, techniques


def parse_met_object(
    raw: dict,
    provenance: ProvenanceRecord,
    site_id: str | None,
    region: str | None,
) -> tuple[Artifact, list[ArtifactImage]]:
    materials, techniques = parse_medium(raw.get("medium", ""))
    artifact_id = f"met_{raw['objectID']}"

    artifact = Artifact(
        id=artifact_id,
        name=raw.get("title", ""),
        description=f"{raw.get('objectName', '')}. {raw.get('culture', '')}. {raw.get('department', '')}".strip(),
        type=raw.get("classification", ""),
        site_id=site_id,
        region=region,
        period=raw.get("period") or None,
        date_range_start=raw.get("objectBeginDate"),
        date_range_end=raw.get("objectEndDate"),
        materials=materials,
        techniques=techniques,
        motif_tags=[],
        provenance=[provenance],
    )

    images = []
    all_image_urls = []
    if raw.get("primaryImage"):
        all_image_urls.append(raw["primaryImage"])
    all_image_urls.extend(raw.get("additionalImages", []))

    for url in all_image_urls:
        images.append(ArtifactImage(
            id=f"img_{uuid.uuid4().hex[:12]}",
            artifact_id=artifact_id,
            source_image_url=url,
            local_path="",
            svg_path=None,
            provenance=provenance,
        ))

    return artifact, images


def search_met(query: str, client: CachedAPIClient) -> list[int]:
    """Search Met API, return list of object IDs."""
    url = f"{MET_MUSEUM_API_BASE}/search"
    data = client.get(url, params={"q": query, "hasImages": "true", "medium": "Ceramics"})
    if data is None:
        return []
    result = json.loads(data)
    return result.get("objectIDs", []) or []


def fetch_met_object(object_id: int, client: CachedAPIClient) -> dict | None:
    url = f"{MET_MUSEUM_API_BASE}/objects/{object_id}"
    data = client.get(url)
    if data is None:
        return None
    return json.loads(data)
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_harvester_met.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/harvesters/ tests/test_harvester_met.py
git commit -m "feat(stage2): Met Museum API harvester with response parsing"
```

---

### Task 7: Wikidata artifact harvester

**Files:**
- Create: `pipeline/harvesters/wikidata.py`
- Test: `tests/test_harvester_wikidata.py`

- [ ] **Step 1: Write failing test for Wikidata artifact query builder**

```python
# tests/test_harvester_wikidata.py
from pipeline.harvesters.wikidata import build_artifact_query, parse_wikidata_artifact


def test_build_artifact_query():
    query = build_artifact_query("Q12345")
    assert "Q12345" in query
    assert "P189" in query  # location of discovery


def test_parse_wikidata_artifact():
    binding = {
        "item": {"value": "http://www.wikidata.org/entity/Q999"},
        "itemLabel": {"value": "Spiral-decorated amphora"},
        "materialLabel": {"value": "ceramic"},
        "image": {"value": "https://commons.wikimedia.org/wiki/Special:FilePath/example.jpg"},
        "inception": {"value": "-0500-01-01T00:00:00Z"},
    }
    artifact, images = parse_wikidata_artifact(binding, site_id="1", region="Aegean")
    assert artifact.id == "wd_Q999"
    assert artifact.name == "Spiral-decorated amphora"
    assert artifact.materials == ["ceramic"]
    assert len(images) == 1
```

- [ ] **Step 2: Run test to verify failure**

```bash
python -m pytest tests/test_harvester_wikidata.py -v
```

- [ ] **Step 3: Implement Wikidata harvester**

```python
# pipeline/harvesters/wikidata.py
"""Wikidata SPARQL artifact harvester."""
import logging
import uuid
from datetime import datetime, timezone

from SPARQLWrapper import SPARQLWrapper, JSON

from pipeline.models import Artifact, ArtifactImage, ProvenanceRecord
from pipeline.provenance import compute_hash, create_provenance
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
    }}
    LIMIT 500
    """


def parse_inception_year(inception_str: str | None) -> int | None:
    if not inception_str:
        return None
    try:
        # Format: "-0500-01-01T00:00:00Z" or "0500-01-01T00:00:00Z"
        if inception_str.startswith("-"):
            return -int(inception_str[1:5])
        return int(inception_str[:4])
    except (ValueError, IndexError):
        return None


def parse_wikidata_artifact(
    binding: dict,
    site_id: str | None,
    region: str | None,
) -> tuple[Artifact, list[ArtifactImage]]:
    qid = binding["item"]["value"].split("/")[-1]
    artifact_id = f"wd_{qid}"
    label = binding.get("itemLabel", {}).get("value", "")
    material = binding.get("materialLabel", {}).get("value", "")
    inception = binding.get("inception", {}).get("value")
    year = parse_inception_year(inception)

    prov = create_provenance(
        source_id="wikidata",
        source_url=binding["item"]["value"],
        raw_data=str(binding).encode(),
        license="CC0",
    )

    artifact = Artifact(
        id=artifact_id,
        name=label,
        description=label,
        type="",
        site_id=site_id,
        region=region,
        period=None,
        date_range_start=year,
        date_range_end=year,
        materials=[material] if material else [],
        techniques=[],
        motif_tags=[],
        provenance=[prov],
    )

    images = []
    image_url = binding.get("image", {}).get("value")
    if image_url:
        images.append(ArtifactImage(
            id=f"img_{uuid.uuid4().hex[:12]}",
            artifact_id=artifact_id,
            source_image_url=image_url,
            local_path="",
            svg_path=None,
            provenance=prov,
        ))

    return artifact, images


def query_artifacts_for_site(site_qid: str) -> list[dict]:
    sparql = SPARQLWrapper(WIKIDATA_SPARQL_ENDPOINT)
    sparql.addCustomHttpHeader("User-Agent", WIKIDATA_USER_AGENT)
    sparql.setTimeout(WIKIDATA_QUERY_TIMEOUT)
    sparql.setQuery(build_artifact_query(site_qid))
    sparql.setReturnFormat(JSON)
    try:
        results = sparql.query().convert()
        return results["results"]["bindings"]
    except Exception as e:
        logger.warning(f"Wikidata artifact query failed for {site_qid}: {e}")
        return []
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_harvester_wikidata.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/harvesters/wikidata.py tests/test_harvester_wikidata.py
git commit -m "feat(stage2): Wikidata SPARQL artifact harvester"
```

---

### Task 8: Deduplication and Stage 2 runner

**Files:**
- Create: `pipeline/dedup.py`
- Modify: `pipeline/stage_2_artifact_harvest.py`
- Test: `tests/test_dedup.py`

- [ ] **Step 1: Write failing test for deduplication**

```python
# tests/test_dedup.py
from pipeline.dedup import deduplicate_artifacts
from pipeline.models import Artifact, ProvenanceRecord


def _make_artifact(id, name, site_id, start, prov_source):
    return Artifact(
        id=id, name=name, description="", type="pottery",
        site_id=site_id, region="Aegean", period=None,
        date_range_start=start, date_range_end=start,
        materials=["clay"], techniques=[], motif_tags=[],
        provenance=[ProvenanceRecord(
            source_id=prov_source, source_url="", fetch_date="",
            license="CC0", raw_response_hash="", transformation="none",
        )],
    )


def test_dedup_exact_name_same_site():
    a1 = _make_artifact("met_1", "Spiral Bowl", "site_1", -500, "met_museum")
    a2 = _make_artifact("wd_Q1", "Spiral Bowl", "site_1", -500, "wikidata")
    result = deduplicate_artifacts([a1, a2])
    assert len(result) == 1
    assert len(result[0].provenance) == 2  # both provenance records kept


def test_dedup_different_names_no_merge():
    a1 = _make_artifact("met_1", "Spiral Bowl", "site_1", -500, "met_museum")
    a2 = _make_artifact("met_2", "Wave Pitcher", "site_1", -300, "met_museum")
    result = deduplicate_artifacts([a1, a2])
    assert len(result) == 2


def test_dedup_wikidata_priority():
    a1 = _make_artifact("met_1", "Spiral Bowl", "site_1", -500, "met_museum")
    a2 = _make_artifact("wd_Q1", "Spiral Bowll", "site_1", -500, "wikidata")  # close name
    result = deduplicate_artifacts([a1, a2])
    assert len(result) == 1
    assert result[0].id == "wd_Q1"  # wikidata wins as primary
```

- [ ] **Step 2: Run test to verify failure**

```bash
python -m pytest tests/test_dedup.py -v
```

- [ ] **Step 3: Implement deduplication**

```python
# pipeline/dedup.py
"""Multi-signal artifact deduplication."""
import Levenshtein
from pipeline.models import Artifact
from pipeline.config import SITE_NAME_FUZZY_THRESHOLD

# Source priority: higher = preferred as primary record
SOURCE_PRIORITY = {
    "wikidata": 4,
    "met_museum": 3,
    "harvard": 2,
    "british_museum": 1,
}


def _date_ranges_overlap(a: Artifact, b: Artifact) -> bool:
    if a.date_range_start is None or b.date_range_start is None:
        return True  # can't disprove overlap
    a_start = a.date_range_start
    a_end = a.date_range_end or a.date_range_start
    b_start = b.date_range_start
    b_end = b.date_range_end or b.date_range_start
    return a_start <= b_end and b_start <= a_end


def _is_duplicate(a: Artifact, b: Artifact) -> bool:
    if a.site_id != b.site_id:
        return False
    if not _date_ranges_overlap(a, b):
        return False
    name_dist = Levenshtein.distance(a.name.lower(), b.name.lower())
    return name_dist <= SITE_NAME_FUZZY_THRESHOLD


def _source_priority(artifact: Artifact) -> int:
    if not artifact.provenance:
        return 0
    return max(SOURCE_PRIORITY.get(p.source_id, 0) for p in artifact.provenance)


def deduplicate_artifacts(artifacts: list[Artifact]) -> list[Artifact]:
    if not artifacts:
        return []
    # Sort by source priority descending so higher-priority records come first
    sorted_arts = sorted(artifacts, key=_source_priority, reverse=True)
    merged: list[Artifact] = []

    for art in sorted_arts:
        found_dup = False
        for existing in merged:
            if _is_duplicate(existing, art):
                # Merge provenance from duplicate into existing
                existing.provenance.extend(art.provenance)
                found_dup = True
                break
        if not found_dup:
            merged.append(art)

    return merged
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_dedup.py -v
```
Expected: PASS

- [ ] **Step 5: Implement Stage 2 runner**

```python
# pipeline/stage_2_artifact_harvest.py
"""Stage 2: Harvest artifacts from multiple API sources."""
import json
import os
import logging

from pipeline.models import Site, Artifact, ArtifactImage
from pipeline.api_client import CachedAPIClient
from pipeline.dedup import deduplicate_artifacts
from pipeline.harvesters.met import search_met, fetch_met_object, parse_met_object
from pipeline.harvesters.wikidata import query_artifacts_for_site, parse_wikidata_artifact
from pipeline.provenance import load_manifest, save_manifest
from pipeline.config import (
    SITES_DIR, ARTIFACTS_DIR, RAW_DIR, MANIFESTS_DIR,
    MET_MUSEUM_RATE_LIMIT, MET_MUSEUM_API_BASE,
)

logger = logging.getLogger(__name__)


def load_enriched_sites(sites_dir: str) -> list[Site]:
    sites = []
    for filename in os.listdir(sites_dir):
        if not filename.endswith(".json"):
            continue
        with open(os.path.join(sites_dir, filename)) as f:
            data = json.load(f)
        site = Site(**{k: v for k, v in data.items() if k != "external_ids"})
        site.external_ids = data.get("external_ids", {})
        sites.append(site)
    return sites


def save_artifact(artifact: Artifact, images: list[ArtifactImage], output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{artifact.id}.json")
    data = artifact.to_dict()
    data["images"] = [img.to_dict() for img in images]
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def harvest_site(site: Site, met_client: CachedAPIClient) -> list[tuple[Artifact, list[ArtifactImage]]]:
    all_artifacts = []

    # Wikidata
    qid = site.external_ids.get("wikidata")
    if qid:
        bindings = query_artifacts_for_site(qid)
        for b in bindings:
            art, imgs = parse_wikidata_artifact(b, site_id=site.id, region=site.region)
            all_artifacts.append((art, imgs))

    # Met Museum
    search_terms = [site.name] if site.name else []
    if site.other_names:
        search_terms.append(site.other_names)
    for term in search_terms[:1]:  # limit searches
        object_ids = search_met(term, met_client)
        for oid in object_ids[:20]:  # cap per search
            raw = fetch_met_object(oid, met_client)
            if raw and raw.get("classification") in ("Vases", "Ceramics", "Pottery", "Terracottas"):
                prov = met_client.create_provenance(
                    source_url=f"{MET_MUSEUM_API_BASE}/objects/{oid}",
                    raw_data=json.dumps(raw).encode(),
                    license="CC0" if raw.get("isPublicDomain") else "Restricted",
                )
                art, imgs = parse_met_object(raw, prov, site_id=site.id, region=site.region)
                all_artifacts.append((art, imgs))

    # Deduplicate
    artifacts_only = [a for a, _ in all_artifacts]
    images_by_id = {a.id: imgs for a, imgs in all_artifacts}
    deduped = deduplicate_artifacts(artifacts_only)

    result = []
    for art in deduped:
        imgs = images_by_id.get(art.id, [])
        result.append((art, imgs))

    return result


def run(sites_dir: str = SITES_DIR, output_dir: str = ARTIFACTS_DIR):
    manifest_path = os.path.join(MANIFESTS_DIR, "stage_2.json")
    manifest = load_manifest(manifest_path)
    processed = set(manifest.get("processed_sites", []))

    sites = load_enriched_sites(sites_dir)
    matched_sites = [s for s in sites if s.external_ids.get("wikidata")]
    logger.info(f"Found {len(matched_sites)} sites with external IDs, {len(processed)} already processed")

    met_client = CachedAPIClient("met_museum", RAW_DIR, MET_MUSEUM_RATE_LIMIT)
    total_artifacts = 0

    for i, site in enumerate(matched_sites):
        if site.id in processed:
            continue
        results = harvest_site(site, met_client)
        for art, imgs in results:
            save_artifact(art, imgs, output_dir)
            total_artifacts += 1
        processed.add(site.id)
        if (i + 1) % 50 == 0:
            logger.info(f"Processed {i + 1}/{len(matched_sites)} sites, {total_artifacts} artifacts")
            save_manifest(manifest_path, {"processed_sites": list(processed)})

    save_manifest(manifest_path, {"processed_sites": list(processed)})
    logger.info(f"Stage 2 complete: {total_artifacts} artifacts harvested")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
```

- [ ] **Step 6: Commit**

```bash
git add pipeline/dedup.py pipeline/stage_2_artifact_harvest.py tests/test_dedup.py
git commit -m "feat(stage2): artifact harvesting with deduplication and Stage 2 runner"
```

---

## Chunk 4: Stages 3-4 — Images and Motif Tagging

### Task 9: Image downloader with checkpointing

**Files:**
- Create: `pipeline/stage_3_image_collection.py`
- Test: `tests/test_stage_3.py`

- [ ] **Step 1: Write failing test for image classification heuristic**

```python
# tests/test_stage_3.py
import numpy as np
from pipeline.stage_3_image_collection import is_likely_line_drawing


def test_line_drawing_low_variance():
    # Simulated grayscale image with very low color variance (like a line drawing)
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[20:30, :] = 255  # white lines
    assert is_likely_line_drawing(img) is True


def test_photo_high_variance():
    # Simulated photo with lots of color variety
    rng = np.random.RandomState(42)
    img = rng.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    assert is_likely_line_drawing(img) is False
```

- [ ] **Step 2: Run test to verify failure**

```bash
python -m pytest tests/test_stage_3.py -v
```

- [ ] **Step 3: Implement image utilities and downloader**

```python
# pipeline/stage_3_image_collection.py
"""Stage 3: Download artifact images, preprocess, trace to SVG."""
import json
import os
import hashlib
import logging
import subprocess

import cv2
import numpy as np
import requests

from pipeline.provenance import load_manifest, save_manifest, compute_hash
from pipeline.config import (
    ARTIFACTS_DIR, IMAGES_DIR, SVGS_DIR, MANIFESTS_DIR,
    SVG_MIN_PATHS, SVG_MAX_PATHS,
)

logger = logging.getLogger(__name__)


def is_likely_line_drawing(img: np.ndarray) -> bool:
    """Heuristic: line drawings have low color variance."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    variance = np.var(gray)
    unique_ratio = len(np.unique(gray)) / 256.0
    return variance < 2000 and unique_ratio < 0.3


def preprocess_photo(img: np.ndarray) -> np.ndarray:
    """Remove background, then convert photo to high-contrast binary for tracing."""
    from rembg import remove
    from PIL import Image

    # Background removal via rembg
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    pil_img = remove(pil_img)
    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGBA2GRAY)

    # Edge detection and dilation
    edges = cv2.Canny(img, 50, 150)
    kernel = np.ones((2, 2), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=1)
    return edges


def download_image(url: str, output_path: str) -> bool:
    """Download image, return True on success."""
    try:
        resp = requests.get(url, timeout=30, stream=True)
        resp.raise_for_status()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        return True
    except Exception as e:
        logger.warning(f"Download failed for {url}: {e}")
        return False


def trace_to_svg(input_path: str, output_path: str) -> bool:
    """Run vtracer to convert image to SVG."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    try:
        subprocess.run(
            ["vtracer", "--input", input_path, "--output", output_path,
             "--colormode", "binary", "--filter_speckle", "4"],
            check=True, capture_output=True, timeout=60,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.warning(f"vtracer failed for {input_path}: {e}")
        return False


def count_svg_paths(svg_path: str) -> int:
    """Count <path> elements in SVG."""
    with open(svg_path) as f:
        content = f.read()
    return content.count("<path")


def process_image(image_url: str, artifact_id: str, image_id: str) -> dict:
    """Download, preprocess, and trace one image. Returns status dict."""
    img_ext = os.path.splitext(image_url.split("?")[0])[1] or ".jpg"
    img_path = os.path.join(IMAGES_DIR, artifact_id, f"{image_id}{img_ext}")
    svg_path = os.path.join(SVGS_DIR, artifact_id, f"{image_id}.svg")

    result = {"image_id": image_id, "downloaded": False, "svg_path": None, "quality": "unknown"}

    if not download_image(image_url, img_path):
        return result
    result["downloaded"] = True
    result["local_path"] = img_path

    # Load and preprocess
    img = cv2.imread(img_path)
    if img is None:
        return result

    if not is_likely_line_drawing(img):
        processed = preprocess_photo(img)
        processed_path = img_path.replace(img_ext, f"_processed.png")
        cv2.imwrite(processed_path, processed)
        trace_input = processed_path
    else:
        trace_input = img_path

    if trace_to_svg(trace_input, svg_path):
        path_count = count_svg_paths(svg_path)
        if path_count < SVG_MIN_PATHS:
            result["quality"] = "too_simple"
        elif path_count > SVG_MAX_PATHS:
            result["quality"] = "too_noisy"
        else:
            result["quality"] = "good"
            result["svg_path"] = svg_path

    return result


def run(artifacts_dir: str = ARTIFACTS_DIR):
    manifest_path = os.path.join(MANIFESTS_DIR, "stage_3_downloads.json")
    manifest = load_manifest(manifest_path)
    processed = set(manifest.get("processed_images", []))

    for filename in os.listdir(artifacts_dir):
        if not filename.endswith(".json"):
            continue
        with open(os.path.join(artifacts_dir, filename)) as f:
            data = json.load(f)

        images = data.get("images", [])
        for img_data in images:
            img_id = img_data["id"]
            if img_id in processed:
                continue
            result = process_image(
                img_data["source_image_url"],
                data["id"],
                img_id,
            )
            if result["downloaded"]:
                img_data["local_path"] = result.get("local_path", "")
                img_data["svg_path"] = result.get("svg_path")
            processed.add(img_id)

        # Update artifact file with local paths
        with open(os.path.join(artifacts_dir, filename), "w") as f:
            json.dump(data, f, indent=2)

        save_manifest(manifest_path, {"processed_images": list(processed)})

    logger.info(f"Stage 3 complete: {len(processed)} images processed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_stage_3.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/stage_3_image_collection.py tests/test_stage_3.py
git commit -m "feat(stage3): image download, preprocessing, and SVG tracing with quality gate"
```

---

### Task 10: Motif tagging (text + CLIP)

**Files:**
- Create: `pipeline/stage_4_motif_tagging.py`
- Test: `tests/test_stage_4.py`

- [ ] **Step 1: Write failing test for text motif extraction**

```python
# tests/test_stage_4.py
from pipeline.stage_4_motif_tagging import extract_motif_tags


def test_extract_spiral():
    tags = extract_motif_tags("A bowl decorated with spiral patterns and wave motifs")
    assert "spiral" in tags
    assert "wave" in tags


def test_extract_multiple():
    tags = extract_motif_tags("Cross-hatched design with concentric circles and meander border")
    assert "cross" in tags
    assert "hatching" in tags
    assert "concentric_circles" in tags
    assert "meander" in tags


def test_extract_none():
    tags = extract_motif_tags("A plain undecorated vessel")
    assert tags == []


def test_extract_case_insensitive():
    tags = extract_motif_tags("Decorated with SPIRALS and Rosettes")
    assert "spiral" in tags
    assert "rosette" in tags
```

- [ ] **Step 2: Run test to verify failure**

```bash
python -m pytest tests/test_stage_4.py -v
```

- [ ] **Step 3: Implement motif tagger**

```python
# pipeline/stage_4_motif_tagging.py
"""Stage 4: Motif tagging via text extraction and CLIP embeddings."""
import json
import os
import re
import logging

import numpy as np

from pipeline.provenance import load_manifest, save_manifest, create_provenance
from pipeline.config import (
    ARTIFACTS_DIR, EMBEDDINGS_DIR, IMAGES_DIR, MANIFESTS_DIR, CLIP_MODEL,
)

logger = logging.getLogger(__name__)

MOTIF_PATTERNS = {
    "spiral": r"\bspirals?\b",
    "meander": r"\bmeanders?\b",
    "cross": r"\bcross(?:es|ed)?\b",
    "chevron": r"\bchevrons?\b",
    "wave": r"\bwav(?:e|es|y)\b",
    "guilloche": r"\bguilloch(?:e|es)\b",
    "rosette": r"\brosettes?\b",
    "palmette": r"\bpalmettes?\b",
    "zigzag": r"\bzig-?zags?\b",
    "concentric_circles": r"\bconcentric\s+circles?\b",
    "hatching": r"\bhatch(?:ed|ing)\b",
    "geometric": r"\bgeometric\b",
    "floral": r"\bfloral\b",
    "figural": r"\bfigur(?:al|ative|ed)\b",
    "animal": r"\b(?:animal|zoomorphic)\b",
    "anthropomorphic": r"\banthropomorphic\b",
}


def extract_motif_tags(text: str) -> list[str]:
    if not text:
        return []
    text_lower = text.lower()
    tags = []
    for tag, pattern in MOTIF_PATTERNS.items():
        if re.search(pattern, text_lower):
            tags.append(tag)
    return sorted(tags)


def compute_clip_embeddings(image_paths: list[str]) -> np.ndarray | None:
    """Compute CLIP embeddings for a batch of images. Returns (N, 512) array."""
    if not image_paths:
        return None
    try:
        from transformers import CLIPProcessor, CLIPModel
        from PIL import Image

        model = CLIPModel.from_pretrained(CLIP_MODEL)
        processor = CLIPProcessor.from_pretrained(CLIP_MODEL)

        images = []
        valid_indices = []
        for i, path in enumerate(image_paths):
            try:
                img = Image.open(path).convert("RGB")
                images.append(img)
                valid_indices.append(i)
            except Exception as e:
                logger.warning(f"Could not open image {path}: {e}")

        if not images:
            return None

        inputs = processor(images=images, return_tensors="pt", padding=True)
        outputs = model.get_image_features(**inputs)
        embeddings = outputs.detach().numpy()
        # Normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / norms
        return embeddings

    except ImportError:
        logger.error("transformers/torch not installed, skipping CLIP embeddings")
        return None


def run(artifacts_dir: str = ARTIFACTS_DIR):
    manifest_path = os.path.join(MANIFESTS_DIR, "stage_4.json")
    manifest = load_manifest(manifest_path)
    processed = set(manifest.get("processed", []))

    all_embeddings = {}
    artifact_ids = []

    for filename in os.listdir(artifacts_dir):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(artifacts_dir, filename)
        with open(filepath) as f:
            data = json.load(f)

        art_id = data["id"]
        if art_id in processed:
            continue

        # Text tagging
        desc = data.get("description", "")
        name = data.get("name", "")
        tags = extract_motif_tags(f"{name} {desc}")
        data["motif_tags"] = tags

        # Collect first valid image path per artifact for CLIP
        for img in data.get("images", []):
            local_path = img.get("local_path", "")
            if local_path and os.path.exists(local_path) and art_id not in all_embeddings:
                all_embeddings[art_id] = local_path
                break  # one embedding per artifact

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        processed.add(art_id)

    # Batch CLIP embeddings
    if all_embeddings:
        ids = list(all_embeddings.keys())
        paths = [all_embeddings[k] for k in ids]
        embeddings = compute_clip_embeddings(paths)
        if embeddings is not None:
            os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
            np.savez_compressed(
                os.path.join(EMBEDDINGS_DIR, "clip_embeddings.npz"),
                embeddings=embeddings,
            )
            index = {aid: i for i, aid in enumerate(ids)}
            with open(os.path.join(EMBEDDINGS_DIR, "index.json"), "w") as f:
                json.dump(index, f, indent=2)

    save_manifest(manifest_path, {"processed": list(processed)})
    logger.info(f"Stage 4 complete: {len(processed)} artifacts tagged")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_stage_4.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/stage_4_motif_tagging.py tests/test_stage_4.py
git commit -m "feat(stage4): text motif extraction and CLIP embedding pipeline"
```

---

## Chunk 5: Stages 5-6 — Similarity and Export

### Task 11: Similarity computation

**Files:**
- Create: `pipeline/stage_5_similarity.py`
- Test: `tests/test_stage_5.py`

- [ ] **Step 1: Write failing test for similarity functions**

```python
# tests/test_stage_5.py
import pytest
import numpy as np
from pipeline.stage_5_similarity import jaccard_similarity, combined_score


def test_jaccard_identical():
    assert jaccard_similarity(["spiral", "wave"], ["spiral", "wave"]) == 1.0


def test_jaccard_partial():
    score = jaccard_similarity(["spiral", "wave"], ["spiral", "cross"])
    assert score == pytest.approx(1 / 3)  # intersection=1, union=3


def test_jaccard_empty():
    assert jaccard_similarity([], []) == 0.0


def test_combined_score():
    score = combined_score(
        tag_score=0.5, embedding_score=0.8,
        tag_weight=0.4, embedding_weight=0.6,
    )
    assert score == pytest.approx(0.5 * 0.4 + 0.8 * 0.6)
```

- [ ] **Step 2: Run test to verify failure**

```bash
python -m pytest tests/test_stage_5.py -v
```

- [ ] **Step 3: Implement similarity computation**

```python
# pipeline/stage_5_similarity.py
"""Stage 5: Compute pairwise similarity between artifacts."""
import json
import os
import logging

import numpy as np

from pipeline.provenance import load_manifest, save_manifest
from pipeline.config import (
    ARTIFACTS_DIR, EMBEDDINGS_DIR, SIMILARITY_DIR, MANIFESTS_DIR,
    SIMILARITY_TOP_N, SIMILARITY_TAG_WEIGHT, SIMILARITY_EMBEDDING_WEIGHT,
)

logger = logging.getLogger(__name__)


def jaccard_similarity(tags_a: list[str], tags_b: list[str]) -> float:
    if not tags_a and not tags_b:
        return 0.0
    set_a, set_b = set(tags_a), set(tags_b)
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def combined_score(
    tag_score: float,
    embedding_score: float,
    tag_weight: float = SIMILARITY_TAG_WEIGHT,
    embedding_weight: float = SIMILARITY_EMBEDDING_WEIGHT,
) -> float:
    return tag_score * tag_weight + embedding_score * embedding_weight


def load_all_artifacts(artifacts_dir: str) -> list[dict]:
    artifacts = []
    for filename in os.listdir(artifacts_dir):
        if not filename.endswith(".json"):
            continue
        with open(os.path.join(artifacts_dir, filename)) as f:
            artifacts.append(json.load(f))
    return artifacts


def run(artifacts_dir: str = ARTIFACTS_DIR):
    artifacts = load_all_artifacts(artifacts_dir)
    logger.info(f"Computing similarity for {len(artifacts)} artifacts")

    # Load CLIP embeddings if available
    embeddings = None
    embed_index = {}
    npz_path = os.path.join(EMBEDDINGS_DIR, "clip_embeddings.npz")
    index_path = os.path.join(EMBEDDINGS_DIR, "index.json")
    if os.path.exists(npz_path) and os.path.exists(index_path):
        data = np.load(npz_path)
        embeddings = data["embeddings"]
        with open(index_path) as f:
            embed_index = json.load(f)

    os.makedirs(SIMILARITY_DIR, exist_ok=True)

    for i, art_a in enumerate(artifacts):
        edges = []
        a_id = art_a["id"]
        a_tags = art_a.get("motif_tags", [])
        a_embed = None
        if embeddings is not None and a_id in embed_index:
            a_embed = embeddings[embed_index[a_id]]

        for j, art_b in enumerate(artifacts):
            if i == j:
                continue
            b_id = art_b["id"]
            b_tags = art_b.get("motif_tags", [])

            tag_score = jaccard_similarity(a_tags, b_tags)

            embed_score = 0.0
            if a_embed is not None and embeddings is not None and b_id in embed_index:
                b_embed = embeddings[embed_index[b_id]]
                embed_score = float(np.dot(a_embed, b_embed))

            if tag_score > 0 or embed_score > 0:
                score = combined_score(tag_score, embed_score)
                edges.append({
                    "artifact_b_id": b_id,
                    "score": round(score, 4),
                    "method": "combined",
                })

        # Keep top N
        edges.sort(key=lambda e: e["score"], reverse=True)
        edges = edges[:SIMILARITY_TOP_N]

        with open(os.path.join(SIMILARITY_DIR, f"{a_id}.json"), "w") as f:
            json.dump({"artifact_id": a_id, "similar": edges}, f, indent=2)

        if (i + 1) % 100 == 0:
            logger.info(f"Computed similarity for {i + 1}/{len(artifacts)}")

    logger.info("Stage 5 complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_stage_5.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/stage_5_similarity.py tests/test_stage_5.py
git commit -m "feat(stage5): pairwise similarity with Jaccard + CLIP cosine scoring"
```

---

### Task 12: Static export for Next.js

**Files:**
- Create: `pipeline/stage_6_export.py`
- Test: `tests/test_stage_6.py`

- [ ] **Step 1: Write failing test for export site summary**

```python
# tests/test_stage_6.py
import json
import os
import tempfile
from pipeline.stage_6_export import build_site_summary


def test_build_site_summary():
    site = {
        "id": "1", "name": "Abdera", "region": "Aegean",
        "latitude": 40.93, "longitude": 24.97,
        "external_ids": {"wikidata": "Q12345"},
    }
    artifacts = [
        {"id": "art_1", "site_id": "1", "motif_tags": ["spiral"]},
        {"id": "art_2", "site_id": "1", "motif_tags": ["wave", "spiral"]},
    ]
    summary = build_site_summary(site, artifacts)
    assert summary["artifact_count"] == 2
    assert "spiral" in summary["motif_tags"]
    assert "wave" in summary["motif_tags"]
```

- [ ] **Step 2: Run test to verify failure**

```bash
python -m pytest tests/test_stage_6.py -v
```

- [ ] **Step 3: Implement export**

```python
# pipeline/stage_6_export.py
"""Stage 6: Export pipeline data for Next.js static consumption."""
import json
import os
import shutil
import logging

from pipeline.config import (
    SITES_DIR, ARTIFACTS_DIR, SVGS_DIR, SIMILARITY_DIR,
    EXPORT_DIR, EXPORT_SIZE_BUDGET_MB, SIMILARITY_EXPORT_TOP_N,
)

logger = logging.getLogger(__name__)


def build_site_summary(site: dict, artifacts: list[dict]) -> dict:
    all_tags = set()
    for art in artifacts:
        all_tags.update(art.get("motif_tags", []))
    return {
        "id": site["id"],
        "name": site.get("name"),
        "region": site.get("region"),
        "latitude": site.get("latitude"),
        "longitude": site.get("longitude"),
        "artifact_count": len(artifacts),
        "motif_tags": sorted(all_tags),
    }


def run():
    os.makedirs(EXPORT_DIR, exist_ok=True)

    # Load all sites
    sites = {}
    for f in os.listdir(SITES_DIR):
        if not f.endswith(".json"):
            continue
        with open(os.path.join(SITES_DIR, f)) as fh:
            site = json.load(fh)
            sites[site["id"]] = site

    # Load all artifacts, group by site
    artifacts_by_site: dict[str, list[dict]] = {}
    all_artifacts = []
    for f in os.listdir(ARTIFACTS_DIR):
        if not f.endswith(".json"):
            continue
        with open(os.path.join(ARTIFACTS_DIR, f)) as fh:
            art = json.load(fh)
            all_artifacts.append(art)
            sid = art.get("site_id") or "unlinked"
            artifacts_by_site.setdefault(sid, []).append(art)

    # Export sites.json
    site_summaries = []
    for sid, site in sites.items():
        arts = artifacts_by_site.get(sid, [])
        if arts:  # only export sites with artifacts
            site_summaries.append(build_site_summary(site, arts))
    with open(os.path.join(EXPORT_DIR, "sites.json"), "w") as f:
        json.dump(site_summaries, f)
    logger.info(f"Exported {len(site_summaries)} sites to sites.json")

    # Export artifacts per site
    arts_dir = os.path.join(EXPORT_DIR, "artifacts")
    os.makedirs(arts_dir, exist_ok=True)
    for sid, arts in artifacts_by_site.items():
        with open(os.path.join(arts_dir, f"{sid}.json"), "w") as f:
            json.dump(arts, f)

    # Export SVGs
    export_svgs = os.path.join(EXPORT_DIR, "svgs")
    if os.path.exists(SVGS_DIR):
        shutil.copytree(SVGS_DIR, export_svgs, dirs_exist_ok=True)

    # Export similarity (chunked, capped)
    sim_export = os.path.join(EXPORT_DIR, "similarity")
    os.makedirs(sim_export, exist_ok=True)
    if os.path.exists(SIMILARITY_DIR):
        for f in os.listdir(SIMILARITY_DIR):
            if not f.endswith(".json"):
                continue
            with open(os.path.join(SIMILARITY_DIR, f)) as fh:
                sim = json.load(fh)
            sim["similar"] = sim["similar"][:SIMILARITY_EXPORT_TOP_N]
            with open(os.path.join(sim_export, f), "w") as fh:
                json.dump(sim, fh)

    # Export provenance per site
    prov_dir = os.path.join(EXPORT_DIR, "provenance")
    os.makedirs(prov_dir, exist_ok=True)
    for sid, arts in artifacts_by_site.items():
        prov_records = []
        for art in arts:
            prov_records.extend(art.get("provenance", []))
        with open(os.path.join(prov_dir, f"{sid}.json"), "w") as f:
            json.dump(prov_records, f)

    # Check size budget
    total_size = 0
    for dirpath, _, filenames in os.walk(EXPORT_DIR):
        for fn in filenames:
            total_size += os.path.getsize(os.path.join(dirpath, fn))
    size_mb = total_size / (1024 * 1024)
    logger.info(f"Total export size: {size_mb:.1f} MB (budget: {EXPORT_SIZE_BUDGET_MB} MB)")
    if size_mb > EXPORT_SIZE_BUDGET_MB:
        logger.warning("Export exceeds size budget! Consider filtering artifacts.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_stage_6.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/stage_6_export.py tests/test_stage_6.py
git commit -m "feat(stage6): static export with chunked similarity, provenance, and size budget"
```

---

## Chunk 6: Next.js Web App

### Task 13: Next.js project scaffolding

**Files:**
- Create: `web/` directory with Next.js app

- [ ] **Step 1: Initialize Next.js project**

```bash
cd /Users/crashy/Development/ancient-locs
npx create-next-app@latest web --typescript --tailwind --eslint --app --src-dir --no-import-alias
```

- [ ] **Step 2: Configure static export**

In `web/next.config.js` (or `.ts`):
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  basePath: '/ancient-locs',
  images: { unoptimized: true },
}
module.exports = nextConfig
```

- [ ] **Step 3: Install MapLibre**

```bash
cd /Users/crashy/Development/ancient-locs/web && npm install maplibre-gl
```

- [ ] **Step 4: Verify build**

```bash
cd /Users/crashy/Development/ancient-locs/web && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add web/
git commit -m "feat(web): scaffold Next.js app with static export and MapLibre"
```

---

### Task 14: Data loading utilities

**Files:**
- Create: `web/src/lib/data.ts`
- Create: `web/src/lib/types.ts`

- [ ] **Step 1: Define TypeScript types matching data model**

```typescript
// web/src/lib/types.ts
export interface SiteSummary {
  id: string;
  name: string | null;
  region: string;
  latitude: number;
  longitude: number;
  artifact_count: number;
  motif_tags: string[];
}

export interface ProvenanceRecord {
  source_id: string;
  source_url: string;
  fetch_date: string;
  license: string;
  raw_response_hash: string;
  transformation: string;
}

export interface ArtifactImage {
  id: string;
  artifact_id: string;
  source_image_url: string;
  local_path: string;
  svg_path: string | null;
  provenance: ProvenanceRecord;
}

export interface Artifact {
  id: string;
  name: string;
  description: string;
  type: string;
  site_id: string | null;
  region: string | null;
  period: string | null;
  date_range_start: number | null;
  date_range_end: number | null;
  materials: string[];
  techniques: string[];
  motif_tags: string[];
  provenance: ProvenanceRecord[];
  images: ArtifactImage[];
}

export interface SimilarityEdge {
  artifact_b_id: string;
  score: number;
  method: string;
}

export interface SimilarityData {
  artifact_id: string;
  similar: SimilarityEdge[];
}
```

- [ ] **Step 2: Create data loading utilities**

```typescript
// web/src/lib/data.ts
import { SiteSummary, Artifact, SimilarityData, ProvenanceRecord } from './types';

const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || '/ancient-locs';
const DATA_BASE = `${BASE_PATH}/data`;

export async function loadSites(): Promise<SiteSummary[]> {
  const res = await fetch(`${DATA_BASE}/sites.json`);
  return res.json();
}

export async function loadArtifactsForSite(siteId: string): Promise<Artifact[]> {
  const res = await fetch(`${DATA_BASE}/artifacts/${siteId}.json`);
  if (!res.ok) return [];
  return res.json();
}

export async function loadSimilarity(artifactId: string): Promise<SimilarityData | null> {
  const res = await fetch(`${DATA_BASE}/similarity/${artifactId}.json`);
  if (!res.ok) return null;
  return res.json();
}

export async function loadProvenance(siteId: string): Promise<ProvenanceRecord[]> {
  const res = await fetch(`${DATA_BASE}/provenance/${siteId}.json`);
  if (!res.ok) return [];
  return res.json();
}
```

- [ ] **Step 3: Commit**

```bash
git add web/src/lib/
git commit -m "feat(web): add TypeScript types and data loading utilities"
```

---

### Task 15: Map component

**Files:**
- Create: `web/src/components/Map.tsx`
- Modify: `web/src/app/page.tsx`

- [ ] **Step 1: Create Map component**

```typescript
// web/src/components/Map.tsx
'use client';

import { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { SiteSummary } from '@/lib/types';
import { loadSites } from '@/lib/data';

interface MapProps {
  onSiteSelect: (site: SiteSummary) => void;
}

export default function Map({ onSiteSelect }: MapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [sites, setSites] = useState<SiteSummary[]>([]);

  useEffect(() => {
    loadSites().then(setSites);
  }, []);

  useEffect(() => {
    if (!mapContainer.current || sites.length === 0) return;

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: 'https://demotiles.maplibre.org/style.json',
      center: [30, 35],
      zoom: 3,
    });

    map.on('load', () => {
      map.addSource('sites', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: sites.map(site => ({
            type: 'Feature' as const,
            geometry: {
              type: 'Point' as const,
              coordinates: [site.longitude, site.latitude],
            },
            properties: {
              id: site.id,
              name: site.name,
              region: site.region,
              artifact_count: site.artifact_count,
              motif_tags: site.motif_tags.join(', '),
            },
          })),
        },
        cluster: true,
        clusterMaxZoom: 14,
        clusterRadius: 50,
      });

      map.addLayer({
        id: 'clusters',
        type: 'circle',
        source: 'sites',
        filter: ['has', 'point_count'],
        paint: {
          'circle-color': '#c2703e',
          'circle-radius': ['step', ['get', 'point_count'], 15, 10, 20, 50, 30],
        },
      });

      map.addLayer({
        id: 'cluster-count',
        type: 'symbol',
        source: 'sites',
        filter: ['has', 'point_count'],
        layout: {
          'text-field': '{point_count_abbreviated}',
          'text-size': 12,
        },
      });

      map.addLayer({
        id: 'site-points',
        type: 'circle',
        source: 'sites',
        filter: ['!', ['has', 'point_count']],
        paint: {
          'circle-color': '#8b4513',
          'circle-radius': 6,
          'circle-stroke-width': 1,
          'circle-stroke-color': '#fff',
        },
      });

      map.on('click', 'site-points', (e) => {
        if (e.features && e.features[0]) {
          const props = e.features[0].properties;
          const site = sites.find(s => s.id === props.id);
          if (site) onSiteSelect(site);
        }
      });

      map.on('mouseenter', 'site-points', () => {
        map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', 'site-points', () => {
        map.getCanvas().style.cursor = '';
      });
    });

    mapRef.current = map;
    return () => map.remove();
  }, [sites, onSiteSelect]);

  return <div ref={mapContainer} style={{ width: '100%', height: '100%' }} />;
}
```

- [ ] **Step 2: Create main page**

```typescript
// web/src/app/page.tsx
'use client';

import { useState } from 'react';
import Map from '@/components/Map';
import { SiteSummary } from '@/lib/types';

export default function Home() {
  const [selectedSite, setSelectedSite] = useState<SiteSummary | null>(null);

  return (
    <main style={{ display: 'flex', height: '100vh' }}>
      <div style={{ flex: 1 }}>
        <Map onSiteSelect={setSelectedSite} />
      </div>
      {selectedSite && (
        <aside style={{
          width: 360, padding: 16, overflowY: 'auto',
          borderLeft: '1px solid #333', background: '#1a1a1a', color: '#eee',
        }}>
          <h2>{selectedSite.name || 'Unnamed Site'}</h2>
          <p><strong>Region:</strong> {selectedSite.region}</p>
          <p><strong>Artifacts:</strong> {selectedSite.artifact_count}</p>
          {selectedSite.motif_tags.length > 0 && (
            <p><strong>Motifs:</strong> {selectedSite.motif_tags.join(', ')}</p>
          )}
        </aside>
      )}
    </main>
  );
}
```

- [ ] **Step 3: Build and verify**

```bash
cd /Users/crashy/Development/ancient-locs/web && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add web/src/components/Map.tsx web/src/app/page.tsx
git commit -m "feat(web): interactive MapLibre map with site clustering and sidebar"
```

---

### Task 16: Artifact detail and similarity views

**Files:**
- Create: `web/src/components/ArtifactCard.tsx`
- Create: `web/src/components/ProvenanceChain.tsx`
- Create: `web/src/components/SimilarityView.tsx`
- Create: `web/src/app/sites/[id]/page.tsx`
- Create: `web/src/app/artifacts/[id]/page.tsx`
- Create: `web/src/app/similarity/page.tsx`

- [ ] **Step 1: Create ArtifactCard component**

```typescript
// web/src/components/ArtifactCard.tsx
import { Artifact } from '@/lib/types';

interface ArtifactCardProps {
  artifact: Artifact;
  onClick?: () => void;
}

export default function ArtifactCard({ artifact, onClick }: ArtifactCardProps) {
  const svgImage = artifact.images.find(img => img.svg_path);
  const originalImage = artifact.images[0];

  return (
    <div onClick={onClick} style={{
      border: '1px solid #444', borderRadius: 8, padding: 12,
      cursor: onClick ? 'pointer' : 'default', marginBottom: 8,
      background: '#2a2a2a',
    }}>
      <h3 style={{ margin: '0 0 8px' }}>{artifact.name}</h3>
      <div style={{ display: 'flex', gap: 8 }}>
        {originalImage && (
          <img
            src={originalImage.source_image_url}
            alt={artifact.name}
            style={{ width: 80, height: 80, objectFit: 'cover', borderRadius: 4 }}
          />
        )}
        {svgImage?.svg_path && (
          <img
            src={`/ancient-locs/data/svgs/${artifact.id}/${svgImage.id}.svg`}
            alt={`${artifact.name} traced`}
            style={{ width: 80, height: 80, objectFit: 'contain', borderRadius: 4 }}
          />
        )}
      </div>
      {artifact.period && <p style={{ fontSize: 12, color: '#aaa' }}>{artifact.period}</p>}
      {artifact.motif_tags.length > 0 && (
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
          {artifact.motif_tags.map(tag => (
            <span key={tag} style={{
              background: '#8b4513', color: '#fff', borderRadius: 4,
              padding: '2px 6px', fontSize: 11,
            }}>{tag}</span>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Create ProvenanceChain component**

```typescript
// web/src/components/ProvenanceChain.tsx
import { ProvenanceRecord } from '@/lib/types';

export default function ProvenanceChain({ records }: { records: ProvenanceRecord[] }) {
  return (
    <div style={{ fontSize: 12, color: '#999' }}>
      <h4>Provenance</h4>
      {records.map((pr, i) => (
        <div key={i} style={{ marginBottom: 8, paddingLeft: 8, borderLeft: '2px solid #555' }}>
          <div><strong>{pr.source_id}</strong></div>
          <div>Fetched: {new Date(pr.fetch_date).toLocaleDateString()}</div>
          <div>License: {pr.license}</div>
          <a href={pr.source_url} target="_blank" rel="noopener noreferrer"
            style={{ color: '#7aa2f7' }}>Source</a>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Create site detail page**

```typescript
// web/src/app/sites/[id]/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Artifact } from '@/lib/types';
import { loadArtifactsForSite } from '@/lib/data';
import ArtifactCard from '@/components/ArtifactCard';
import ProvenanceChain from '@/components/ProvenanceChain';

export default function SiteDetail() {
  const { id } = useParams<{ id: string }>();
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);

  useEffect(() => {
    if (id) loadArtifactsForSite(id).then(setArtifacts);
  }, [id]);

  return (
    <main style={{ padding: 24, maxWidth: 800, margin: '0 auto', color: '#eee' }}>
      <h1>Site {id}</h1>
      <p>{artifacts.length} artifacts found</p>
      {artifacts.map(art => (
        <div key={art.id}>
          <ArtifactCard artifact={art} />
          <ProvenanceChain records={art.provenance} />
        </div>
      ))}
    </main>
  );
}
```

- [ ] **Step 4: Create SimilarityView component**

```typescript
// web/src/components/SimilarityView.tsx
'use client';

import { useEffect, useState } from 'react';
import { SimilarityData } from '@/lib/types';
import { loadSimilarity } from '@/lib/data';

interface SimilarityViewProps {
  artifactId: string;
}

export default function SimilarityView({ artifactId }: SimilarityViewProps) {
  const [data, setData] = useState<SimilarityData | null>(null);

  useEffect(() => {
    loadSimilarity(artifactId).then(setData);
  }, [artifactId]);

  if (!data || data.similar.length === 0) {
    return <p style={{ color: '#888' }}>No similar artifacts found.</p>;
  }

  return (
    <div>
      <h4>Similar Artifacts</h4>
      {data.similar.map((edge, i) => (
        <div key={i} style={{
          display: 'flex', justifyContent: 'space-between',
          padding: '4px 0', borderBottom: '1px solid #333',
        }}>
          <a href={`/ancient-locs/artifacts/${edge.artifact_b_id}`}
            style={{ color: '#7aa2f7' }}>{edge.artifact_b_id}</a>
          <span style={{ color: '#aaa' }}>
            {(edge.score * 100).toFixed(1)}% similar ({edge.method})
          </span>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 5: Build and verify**

```bash
cd /Users/crashy/Development/ancient-locs/web && npm run build
```

- [ ] **Step 6: Commit**

```bash
git add web/src/
git commit -m "feat(web): artifact cards, provenance display, similarity view, site detail page"
```

---

### Task 17: GitHub Pages deployment

**Files:**
- Create: `.github/workflows/deploy.yml`

- [ ] **Step 1: Create GitHub Actions workflow**

```yaml
# .github/workflows/deploy.yml
name: Deploy to GitHub Pages

on:
  push:
    branches: [master]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: web/package-lock.json
      - run: cd web && npm ci
      - run: cd web && npm run build
      - uses: actions/upload-pages-artifact@v3
        with:
          path: web/out

  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    needs: build
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: add GitHub Pages deployment workflow"
```

---

## Chunk 7: Integration and Pipeline Runner

### Task 18: Pipeline runner script

**Files:**
- Create: `pipeline/run.py`

- [ ] **Step 1: Create orchestrator**

```python
# pipeline/run.py
"""Run all pipeline stages in sequence."""
import argparse
import logging
import sys

logger = logging.getLogger("pipeline")


def main():
    parser = argparse.ArgumentParser(description="Run artifact motif pipeline")
    parser.add_argument("--stages", nargs="+", type=int, default=[1, 2, 3, 4, 5, 6],
                        help="Which stages to run (default: all)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    stage_map = {
        1: ("Site Matching", "pipeline.stage_1_site_matching"),
        2: ("Artifact Harvesting", "pipeline.stage_2_artifact_harvest"),
        3: ("Image Collection", "pipeline.stage_3_image_collection"),
        4: ("Motif Tagging", "pipeline.stage_4_motif_tagging"),
        5: ("Similarity Computation", "pipeline.stage_5_similarity"),
        6: ("Export", "pipeline.stage_6_export"),
    }

    for stage_num in args.stages:
        if stage_num not in stage_map:
            logger.error(f"Unknown stage: {stage_num}")
            sys.exit(1)
        name, module_path = stage_map[stage_num]
        logger.info(f"=== Stage {stage_num}: {name} ===")
        import importlib
        module = importlib.import_module(module_path)
        module.run()
        logger.info(f"=== Stage {stage_num} complete ===\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add pipeline/run.py
git commit -m "feat: pipeline orchestrator to run stages selectively"
```

---

### Task 19: Run all tests

- [ ] **Step 1: Run full test suite**

```bash
cd /Users/crashy/Development/ancient-locs && python -m pytest tests/ -v
```
Expected: all PASS

- [ ] **Step 2: Fix any failures, commit fixes**

---

## Chunk 8: Missing Components (Review Fixes)

### Task 20: Python package configuration

**Files:**
- Create: `pyproject.toml`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create pyproject.toml**

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

- [ ] **Step 2: Create tests/__init__.py**

```python
# tests/__init__.py
# (empty)
```

- [ ] **Step 3: Install in dev mode**

```bash
cd /Users/crashy/Development/ancient-locs && pip install -e .
```

- [ ] **Step 4: Verify tests can import pipeline**

```bash
python -m pytest tests/test_models.py -v
```

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml tests/__init__.py
git commit -m "chore: add pyproject.toml and test package init for importability"
```

---

### Task 21: British Museum SPARQL harvester

**Files:**
- Create: `pipeline/harvesters/british_museum.py`
- Test: `tests/test_harvester_bm.py`

- [ ] **Step 1: Write failing test for BM SPARQL query builder and parser**

```python
# tests/test_harvester_bm.py
from pipeline.harvesters.british_museum import build_bm_query, parse_bm_result


def test_build_bm_query():
    query = build_bm_query(lat=51.5, lng=-0.1, radius_km=5.0)
    assert "51.5" in query
    assert "ceramic" in query.lower() or "pottery" in query.lower()


def test_parse_bm_result():
    binding = {
        "object": {"value": "http://collection.britishmuseum.org/id/object/123"},
        "label": {"value": "Painted pottery vessel"},
        "image": {"value": "https://example.com/img.jpg"},
        "material": {"value": "ceramic"},
    }
    artifact, images = parse_bm_result(binding, site_id="1", region="Levant")
    assert artifact.id == "bm_123"
    assert artifact.name == "Painted pottery vessel"
    assert artifact.materials == ["ceramic"]
    assert len(images) == 1
```

- [ ] **Step 2: Run test to verify failure**

```bash
python -m pytest tests/test_harvester_bm.py -v
```

- [ ] **Step 3: Implement British Museum harvester**

```python
# pipeline/harvesters/british_museum.py
"""British Museum Linked Open Data SPARQL harvester."""
import logging
import uuid

from SPARQLWrapper import SPARQLWrapper, JSON

from pipeline.models import Artifact, ArtifactImage
from pipeline.provenance import create_provenance
from pipeline.config import BM_SPARQL_ENDPOINT, BM_RATE_LIMIT

logger = logging.getLogger(__name__)


def build_bm_query(lat: float, lng: float, radius_km: float = 5.0) -> str:
    return f"""
    PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>

    SELECT ?object ?label ?image ?material WHERE {{
      ?object crm:P45_consists_of ?mat .
      ?mat rdfs:label ?material .
      FILTER(CONTAINS(LCASE(?material), "ceramic") || CONTAINS(LCASE(?material), "pottery") || CONTAINS(LCASE(?material), "terracotta"))
      ?object rdfs:label ?label .
      OPTIONAL {{ ?object crm:P138i_has_representation ?image . }}
      ?object crm:P16i_was_used_for ?find .
      ?find crm:P7_took_place_at ?place .
      ?place geo:lat ?lat .
      ?place geo:long ?lng .
      FILTER(ABS(?lat - {lat}) < {radius_km / 111.0} && ABS(?lng - {lng}) < {radius_km / 111.0})
    }}
    LIMIT 100
    """


def parse_bm_result(
    binding: dict,
    site_id: str | None,
    region: str | None,
) -> tuple[Artifact, list[ArtifactImage]]:
    obj_uri = binding["object"]["value"]
    obj_id = obj_uri.split("/")[-1]
    artifact_id = f"bm_{obj_id}"

    prov = create_provenance(
        source_id="british_museum",
        source_url=obj_uri,
        raw_data=str(binding).encode(),
        license="CC-BY-NC-SA-4.0",
    )

    artifact = Artifact(
        id=artifact_id,
        name=binding.get("label", {}).get("value", ""),
        description="",
        type="pottery",
        site_id=site_id,
        region=region,
        period=None,
        date_range_start=None,
        date_range_end=None,
        materials=[binding.get("material", {}).get("value", "")] if binding.get("material") else [],
        techniques=[],
        motif_tags=[],
        provenance=[prov],
    )

    images = []
    image_url = binding.get("image", {}).get("value")
    if image_url:
        images.append(ArtifactImage(
            id=f"img_{uuid.uuid4().hex[:12]}",
            artifact_id=artifact_id,
            source_image_url=image_url,
            local_path="",
            svg_path=None,
            provenance=prov,
        ))

    return artifact, images


def query_bm_artifacts(lat: float, lng: float, radius_km: float = 5.0) -> list[dict]:
    sparql = SPARQLWrapper(BM_SPARQL_ENDPOINT)
    sparql.setQuery(build_bm_query(lat, lng, radius_km))
    sparql.setReturnFormat(JSON)
    try:
        results = sparql.query().convert()
        return results["results"]["bindings"]
    except Exception as e:
        logger.warning(f"BM SPARQL query failed for ({lat}, {lng}): {e}")
        return []
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_harvester_bm.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/harvesters/british_museum.py tests/test_harvester_bm.py
git commit -m "feat(stage2): British Museum SPARQL harvester"
```

---

### Task 22: Harvard Art Museums harvester

**Files:**
- Create: `pipeline/harvesters/harvard.py`
- Test: `tests/test_harvester_harvard.py`

- [ ] **Step 1: Write failing test for Harvard response parser**

```python
# tests/test_harvester_harvard.py
from pipeline.harvesters.harvard import parse_harvard_object
from pipeline.models import ProvenanceRecord


def test_parse_harvard_object():
    raw = {
        "id": 54321,
        "title": "Bowl with spiral decoration",
        "classification": "Vessels",
        "medium": "Terracotta, painted",
        "culture": "Greek",
        "dated": "5th century BCE",
        "datebegin": -500,
        "dateend": -400,
        "primaryimageurl": "https://nrs.harvard.edu/example.jpg",
        "images": [{"baseimageurl": "https://nrs.harvard.edu/example.jpg"}],
    }
    prov = ProvenanceRecord(
        source_id="harvard", source_url="", fetch_date="",
        license="", raw_response_hash="", transformation="none",
    )
    artifact, images = parse_harvard_object(raw, prov, site_id="1", region="Aegean")
    assert artifact.id == "harv_54321"
    assert artifact.name == "Bowl with spiral decoration"
    assert artifact.date_range_start == -500
    assert len(images) == 1
```

- [ ] **Step 2: Run test to verify failure**

```bash
python -m pytest tests/test_harvester_harvard.py -v
```

- [ ] **Step 3: Implement Harvard harvester**

```python
# pipeline/harvesters/harvard.py
"""Harvard Art Museums API harvester."""
import json
import logging
import uuid

from pipeline.api_client import CachedAPIClient
from pipeline.models import Artifact, ArtifactImage, ProvenanceRecord
from pipeline.config import HARVARD_API_BASE, HARVARD_API_KEY, RAW_DIR

logger = logging.getLogger(__name__)


def parse_medium(medium: str) -> tuple[list[str], list[str]]:
    if not medium:
        return [], []
    parts = [p.strip() for p in medium.split(",")]
    materials = [parts[0]] if parts else []
    techniques = parts[1:] if len(parts) > 1 else []
    return materials, techniques


def parse_harvard_object(
    raw: dict,
    provenance: ProvenanceRecord,
    site_id: str | None,
    region: str | None,
) -> tuple[Artifact, list[ArtifactImage]]:
    materials, techniques = parse_medium(raw.get("medium", ""))
    artifact_id = f"harv_{raw['id']}"

    artifact = Artifact(
        id=artifact_id,
        name=raw.get("title", ""),
        description=f"{raw.get('classification', '')}. {raw.get('culture', '')}".strip(),
        type=raw.get("classification", ""),
        site_id=site_id,
        region=region,
        period=raw.get("dated") or None,
        date_range_start=raw.get("datebegin"),
        date_range_end=raw.get("dateend"),
        materials=materials,
        techniques=techniques,
        motif_tags=[],
        provenance=[provenance],
    )

    images = []
    for img_data in raw.get("images", []):
        url = img_data.get("baseimageurl")
        if url:
            images.append(ArtifactImage(
                id=f"img_{uuid.uuid4().hex[:12]}",
                artifact_id=artifact_id,
                source_image_url=url,
                local_path="",
                svg_path=None,
                provenance=provenance,
            ))

    return artifact, images


def search_harvard(culture: str, classification: str, client: CachedAPIClient) -> list[dict]:
    """Search Harvard Art Museums API."""
    if not HARVARD_API_KEY:
        logger.warning("No HARVARD_API_KEY set, skipping Harvard API")
        return []
    url = f"{HARVARD_API_BASE}/object"
    params = {
        "apikey": HARVARD_API_KEY,
        "culture": culture,
        "classification": classification,
        "hasimage": 1,
        "size": 50,
    }
    data = client.get(url, params=params)
    if data is None:
        return []
    result = json.loads(data)
    return result.get("records", [])
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_harvester_harvard.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline/harvesters/harvard.py tests/test_harvester_harvard.py
git commit -m "feat(stage2): Harvard Art Museums API harvester"
```

---

### Task 23: Wire BM and Harvard into Stage 2 runner

**Files:**
- Modify: `pipeline/stage_2_artifact_harvest.py`

- [ ] **Step 1: Add BM and Harvard imports and calls to harvest_site**

Add imports at top of `pipeline/stage_2_artifact_harvest.py`:
```python
from pipeline.harvesters.british_museum import query_bm_artifacts, parse_bm_result
from pipeline.harvesters.harvard import search_harvard, parse_harvard_object
from pipeline.config import BM_RATE_LIMIT, HARVARD_API_KEY
```

Add to `harvest_site` function, after Met Museum block:

```python
    # British Museum
    bm_bindings = query_bm_artifacts(site.latitude, site.longitude)
    for b in bm_bindings:
        art, imgs = parse_bm_result(b, site_id=site.id, region=site.region)
        all_artifacts.append((art, imgs))

    # Harvard Art Museums
    if HARVARD_API_KEY:
        harvard_client = CachedAPIClient("harvard", RAW_DIR, 1.5)
        culture = site.region.split(":")[0].strip() if site.region else ""
        records = search_harvard(culture, "Vessels", harvard_client)
        for raw in records:
            prov = harvard_client.create_provenance(
                source_url=f"{HARVARD_API_BASE}/object/{raw['id']}",
                raw_data=json.dumps(raw).encode(),
                license="Restricted",
            )
            art, imgs = parse_harvard_object(raw, prov, site_id=site.id, region=site.region)
            all_artifacts.append((art, imgs))
```

- [ ] **Step 2: Commit**

```bash
git add pipeline/stage_2_artifact_harvest.py
git commit -m "feat(stage2): wire British Museum and Harvard harvesters into Stage 2 runner"
```

---

### Task 24: FilterPanel component

**Files:**
- Create: `web/src/components/FilterPanel.tsx`
- Modify: `web/src/app/page.tsx`

- [ ] **Step 1: Create FilterPanel**

```typescript
// web/src/components/FilterPanel.tsx
'use client';

import { useState } from 'react';

export interface Filters {
  region: string;
  motifTag: string;
  period: string;
}

interface FilterPanelProps {
  regions: string[];
  motifTags: string[];
  onChange: (filters: Filters) => void;
}

export default function FilterPanel({ regions, motifTags, onChange }: FilterPanelProps) {
  const [filters, setFilters] = useState<Filters>({ region: '', motifTag: '', period: '' });

  const update = (key: keyof Filters, value: string) => {
    const next = { ...filters, [key]: value };
    setFilters(next);
    onChange(next);
  };

  const selectStyle = {
    background: '#333', color: '#eee', border: '1px solid #555',
    borderRadius: 4, padding: '4px 8px', width: '100%', marginBottom: 8,
  };

  return (
    <div style={{ padding: 12, borderBottom: '1px solid #444' }}>
      <h4 style={{ margin: '0 0 8px', color: '#ccc' }}>Filters</h4>
      <select value={filters.region} onChange={e => update('region', e.target.value)} style={selectStyle}>
        <option value="">All Regions</option>
        {regions.map(r => <option key={r} value={r}>{r}</option>)}
      </select>
      <select value={filters.motifTag} onChange={e => update('motifTag', e.target.value)} style={selectStyle}>
        <option value="">All Motifs</option>
        {motifTags.map(t => <option key={t} value={t}>{t}</option>)}
      </select>
      <input
        placeholder="Period (e.g. Bronze Age)"
        value={filters.period}
        onChange={e => update('period', e.target.value)}
        style={{ ...selectStyle, padding: '6px 8px' }}
      />
    </div>
  );
}
```

- [ ] **Step 2: Wire FilterPanel into main page**

Update `web/src/app/page.tsx` to add filter state and pass filtered sites to Map. Add `FilterPanel` in the sidebar above the site detail, extract unique regions and motif tags from the loaded sites, and filter the GeoJSON source data accordingly.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/FilterPanel.tsx web/src/app/page.tsx
git commit -m "feat(web): add FilterPanel for region, motif, and period filtering"
```

---

### Task 25: Artifact detail page and Similarity explorer page

**Files:**
- Create: `web/src/app/artifacts/[id]/page.tsx`
- Create: `web/src/app/similarity/page.tsx`

- [ ] **Step 1: Create artifact detail page**

```typescript
// web/src/app/artifacts/[id]/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Artifact } from '@/lib/types';
import ProvenanceChain from '@/components/ProvenanceChain';
import SimilarityView from '@/components/SimilarityView';

export default function ArtifactDetail() {
  const { id } = useParams<{ id: string }>();
  const [artifact, setArtifact] = useState<Artifact | null>(null);

  useEffect(() => {
    // Search across all site artifact files to find this artifact
    // In production, you'd have an artifact index; for now, we rely on site linkage
    if (!id) return;
    // Attempt to load from the artifact's site file
    fetch(`/ancient-locs/data/artifacts/`)
      .then(() => {
        // For static export, artifacts are grouped by site.
        // The artifact ID encodes the source, so we search known files.
        // This will be refined during implementation.
      });
  }, [id]);

  if (!artifact) {
    return <main style={{ padding: 24, color: '#eee' }}>Loading artifact {id}...</main>;
  }

  const svgImage = artifact.images.find(img => img.svg_path);
  const originalImage = artifact.images[0];

  return (
    <main style={{ padding: 24, maxWidth: 900, margin: '0 auto', color: '#eee' }}>
      <h1>{artifact.name}</h1>
      <div style={{ display: 'flex', gap: 24, marginBottom: 24 }}>
        {originalImage && (
          <img src={originalImage.source_image_url} alt={artifact.name}
            style={{ maxWidth: 300, borderRadius: 8 }} />
        )}
        {svgImage?.svg_path && (
          <img src={`/ancient-locs/data/svgs/${artifact.id}/${svgImage.id}.svg`}
            alt={`${artifact.name} traced`}
            style={{ maxWidth: 300, borderRadius: 8, background: '#fff', padding: 8 }} />
        )}
      </div>
      <p><strong>Type:</strong> {artifact.type}</p>
      <p><strong>Period:</strong> {artifact.period || 'Unknown'}</p>
      <p><strong>Materials:</strong> {artifact.materials.join(', ') || 'Unknown'}</p>
      {artifact.motif_tags.length > 0 && (
        <p><strong>Motifs:</strong> {artifact.motif_tags.join(', ')}</p>
      )}
      <p>{artifact.description}</p>

      <hr style={{ borderColor: '#444', margin: '24px 0' }} />
      <SimilarityView artifactId={artifact.id} />

      <hr style={{ borderColor: '#444', margin: '24px 0' }} />
      <ProvenanceChain records={artifact.provenance} />
    </main>
  );
}
```

- [ ] **Step 2: Create similarity explorer page**

```typescript
// web/src/app/similarity/page.tsx
'use client';

import { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { SiteSummary } from '@/lib/types';
import { loadSites } from '@/lib/data';

export default function SimilarityExplorer() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const [sites, setSites] = useState<SiteSummary[]>([]);
  const [selectedMotif, setSelectedMotif] = useState('');

  useEffect(() => { loadSites().then(setSites); }, []);

  const allMotifs = [...new Set(sites.flatMap(s => s.motif_tags))].sort();
  const filteredSites = selectedMotif
    ? sites.filter(s => s.motif_tags.includes(selectedMotif))
    : sites;

  useEffect(() => {
    if (!mapContainer.current || filteredSites.length === 0) return;

    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: 'https://demotiles.maplibre.org/style.json',
      center: [30, 35],
      zoom: 3,
    });

    map.on('load', () => {
      // Add site points
      map.addSource('filtered-sites', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: filteredSites.map(s => ({
            type: 'Feature' as const,
            geometry: { type: 'Point' as const, coordinates: [s.longitude, s.latitude] },
            properties: { id: s.id, name: s.name, region: s.region },
          })),
        },
      });

      map.addLayer({
        id: 'motif-sites',
        type: 'circle',
        source: 'filtered-sites',
        paint: {
          'circle-color': '#c2703e',
          'circle-radius': 8,
          'circle-stroke-width': 2,
          'circle-stroke-color': '#fff',
        },
      });

      // Draw arcs between sites sharing the selected motif
      if (selectedMotif && filteredSites.length > 1) {
        const lines: GeoJSON.Feature[] = [];
        for (let i = 0; i < filteredSites.length; i++) {
          for (let j = i + 1; j < filteredSites.length && j < i + 5; j++) {
            lines.push({
              type: 'Feature',
              geometry: {
                type: 'LineString',
                coordinates: [
                  [filteredSites[i].longitude, filteredSites[i].latitude],
                  [filteredSites[j].longitude, filteredSites[j].latitude],
                ],
              },
              properties: {},
            });
          }
        }
        map.addSource('connections', {
          type: 'geojson',
          data: { type: 'FeatureCollection', features: lines },
        });
        map.addLayer({
          id: 'connection-lines',
          type: 'line',
          source: 'connections',
          paint: {
            'line-color': '#7aa2f7',
            'line-width': 1,
            'line-opacity': 0.4,
          },
        });
      }
    });

    return () => map.remove();
  }, [filteredSites, selectedMotif]);

  return (
    <main style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: 12, background: '#1a1a1a', borderBottom: '1px solid #444', color: '#eee' }}>
        <h2 style={{ margin: 0 }}>Motif Similarity Explorer</h2>
        <select value={selectedMotif} onChange={e => setSelectedMotif(e.target.value)}
          style={{ marginTop: 8, background: '#333', color: '#eee', border: '1px solid #555', borderRadius: 4, padding: '4px 8px' }}>
          <option value="">Select a motif...</option>
          {allMotifs.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
        {selectedMotif && <p style={{ margin: '4px 0 0', color: '#aaa' }}>
          {filteredSites.length} sites with "{selectedMotif}" motif
        </p>}
      </div>
      <div ref={mapContainer} style={{ flex: 1 }} />
    </main>
  );
}
```

- [ ] **Step 3: Build and verify**

```bash
cd /Users/crashy/Development/ancient-locs/web && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add web/src/app/artifacts/ web/src/app/similarity/
git commit -m "feat(web): artifact detail page and motif similarity explorer with connection lines"
```

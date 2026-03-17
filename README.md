<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 280" fill="none">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="900" y2="280" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#1a0e0a"/>
      <stop offset="50%" stop-color="#2d1810"/>
      <stop offset="100%" stop-color="#1a0e0a"/>
    </linearGradient>
    <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#c2703e"/>
      <stop offset="50%" stop-color="#e8a86d"/>
      <stop offset="100%" stop-color="#c2703e"/>
    </linearGradient>
    <linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#e8a86d" stop-opacity="0.6"/>
      <stop offset="100%" stop-color="#e8a86d" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="900" height="280" rx="12" fill="url(#bg)"/>
  <rect x="1" y="1" width="898" height="278" rx="11" stroke="url(#gold)" stroke-width="1" fill="none" opacity="0.3"/>

  <!-- Spiral motif left -->
  <g transform="translate(80, 140)" opacity="0.15">
    <path d="M0,0 C0,-20 20,-35 35,-35 C55,-35 70,-20 70,0 C70,25 50,45 25,45 C-5,45 -25,25 -25,0 C-25,-30 0,-55 30,-55 C65,-55 85,-30 85,5 C85,45 55,70 20,70" stroke="#e8a86d" stroke-width="2.5" fill="none"/>
  </g>

  <!-- Wave motif bottom -->
  <g opacity="0.08">
    <path d="M0,230 Q50,200 100,230 Q150,260 200,230 Q250,200 300,230 Q350,260 400,230 Q450,200 500,230 Q550,260 600,230 Q650,200 700,230 Q750,260 800,230 Q850,200 900,230" stroke="#e8a86d" stroke-width="1.5" fill="none"/>
    <path d="M0,245 Q50,215 100,245 Q150,275 200,245 Q250,215 300,245 Q350,275 400,245 Q450,215 500,245 Q550,275 600,245 Q650,215 700,245 Q750,275 800,245 Q850,215 900,245" stroke="#e8a86d" stroke-width="1" fill="none"/>
  </g>

  <!-- Cross motif right -->
  <g transform="translate(790, 80)" opacity="0.12">
    <line x1="-20" y1="0" x2="20" y2="0" stroke="#e8a86d" stroke-width="2.5"/>
    <line x1="0" y1="-20" x2="0" y2="20" stroke="#e8a86d" stroke-width="2.5"/>
    <circle cx="0" cy="0" r="25" stroke="#e8a86d" stroke-width="1.5" fill="none"/>
  </g>

  <!-- Concentric circles motif -->
  <g transform="translate(790, 190)" opacity="0.1">
    <circle cx="0" cy="0" r="8" stroke="#e8a86d" stroke-width="1.5" fill="none"/>
    <circle cx="0" cy="0" r="16" stroke="#e8a86d" stroke-width="1.5" fill="none"/>
    <circle cx="0" cy="0" r="24" stroke="#e8a86d" stroke-width="1.5" fill="none"/>
  </g>

  <!-- Dots pattern -->
  <g opacity="0.06">
    <circle cx="160" cy="50" r="2" fill="#e8a86d"/>
    <circle cx="200" cy="70" r="1.5" fill="#e8a86d"/>
    <circle cx="240" cy="45" r="2.5" fill="#e8a86d"/>
    <circle cx="680" cy="55" r="2" fill="#e8a86d"/>
    <circle cx="720" cy="40" r="1.5" fill="#e8a86d"/>
    <circle cx="650" cy="65" r="2" fill="#e8a86d"/>
  </g>

  <!-- Title -->
  <text x="450" y="95" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif" font-size="42" font-weight="bold" fill="url(#gold)" letter-spacing="2">ANCIENT LOCS</text>
  <text x="450" y="130" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif" font-size="16" fill="#e8a86d" opacity="0.7" letter-spacing="6">MOTIF ENCYCLOPEDIA</text>

  <!-- Divider -->
  <line x1="280" y1="148" x2="620" y2="148" stroke="url(#gold)" stroke-width="0.5" opacity="0.4"/>

  <!-- Subtitle -->
  <text x="450" y="175" text-anchor="middle" font-family="'Helvetica Neue', Arial, sans-serif" font-size="13" fill="#b8977a" letter-spacing="1">Tracing decorative motifs across 8,860 ancient sites</text>
  <text x="450" y="198" text-anchor="middle" font-family="'Helvetica Neue', Arial, sans-serif" font-size="12" fill="#8a6e58" letter-spacing="0.5">CLIPSeg segmentation  ·  CLIP embeddings  ·  HDBSCAN clustering</text>

  <!-- Bottom motif labels -->
  <text x="80" y="265" text-anchor="middle" font-family="'Courier New', monospace" font-size="9" fill="#6b5040" letter-spacing="1">SPIRAL</text>
  <text x="790" y="265" text-anchor="middle" font-family="'Courier New', monospace" font-size="9" fill="#6b5040" letter-spacing="1">CROSS</text>
</svg>

# Ancient Locs — Motif Encyclopedia

An ancient art motif encyclopedia that extracts, embeds, and compares decorative motifs across all publicly available artifact imagery — cave art, relief carvings, pottery, mosaics, seals, and textiles — to reveal visual pattern alignment across cultures, geographies, and time periods.

## How It Works

The pipeline takes **8,860 archaeological sites** from [ancientlocations.net](http://www.ancientlocations.net/), enriches them with artifact records from 5 public APIs, uses **CLIPSeg** to isolate decorative motif regions from artifact photos, generates **CLIP embeddings** on the isolated segments, clusters them with **HDBSCAN** to discover emergent motif types, and generates canonical SVGs for each discovered cluster.

```
places.json ──→ Site Matching ──→ Artifact Harvesting ──→ Image Collection
                  (Wikidata)       (5 APIs, dedup)         (checkpointed)
                                                                │
    ┌───────────────────────────────────────────────────────────┘
    ▼
CLIPSeg Segmentation ──→ CLIP Embedding ──→ Similarity + Clustering ──→ Export
  (motif isolation)       (segment vectors)   (HDBSCAN, canonical SVGs)   (static JSON)
```

## Getting Started

### Prerequisites

- Python 3.11+
- [vtracer](https://github.com/nicois/vtracer) (for SVG tracing) — `cargo install vtracer` or download binary
- Optional: `HARVARD_API_KEY` environment variable for Harvard Art Museums API

### Installation

```bash
git clone https://github.com/ebrinz/ancient-locs.git
cd ancient-locs
pip install -e .
pip install -r pipeline/requirements.txt
```

### Running the Pipeline

```bash
python -m pipeline.run --stages 1 2 3 4 5 6 7 -v
```

#### Stage-by-Stage Breakdown

| Flag | Stage | What it does | Time estimate |
|------|-------|-------------|---------------|
| `1` | **Site Matching** | Links 8,860 sites to Wikidata/Pleiades IDs via SPARQL + fuzzy name matching | ~2-3 hrs (API rate limited) |
| `2` | **Artifact Harvesting** | Pulls artifact records from Wikidata, Met Museum, British Museum, Harvard, Wikimedia Commons | ~4-8 hrs |
| `3` | **Image Collection** | Downloads artifact images with checkpointing (resumable) | ~2-6 hrs |
| `4` | **Motif Segmentation** | Runs CLIPSeg to isolate decorative motif regions, traces to SVG via vtracer | ~1-3 hrs (GPU helps) |
| `5` | **Motif Embedding** | CLIP embeddings on isolated segments + text motif tagging from descriptions | ~30 min - 1 hr |
| `6` | **Similarity + Clustering** | Pairwise cosine similarity, HDBSCAN clustering, canonical SVG generation | ~15-45 min |
| `7` | **Export** | Packages everything as static JSON/SVG for the Next.js frontend | < 1 min |

#### Running Individual Stages

You can run any subset of stages. Each stage is **idempotent** — safe to re-run without duplicating work:

```bash
# Just site matching
python -m pipeline.run --stages 1 -v

# Just the ML stages (segmentation + embedding + clustering)
python -m pipeline.run --stages 4 5 6 -v

# Re-export after tweaking config
python -m pipeline.run --stages 7
```

#### Pipeline Modes

Set via environment variable:

```bash
# Dev mode (default) — saves everything, limits batch sizes for fast iteration
PIPELINE_MODE=dev python -m pipeline.run --stages 1 2 3 4 5 6 7 -v

# Production mode — saves only embeddings + SVGs + metadata, processes at full scale
PIPELINE_MODE=production python -m pipeline.run --stages 1 2 3 4 5 6 7 -v
```

### Configuration

Key settings in `pipeline/config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `PIPELINE_MODE` | `"dev"` | `dev` saves everything; `production` saves only embeddings + SVGs |
| `DEV_MAX_SITES` | `100` | Max sites to process in dev mode |
| `DEV_MAX_ARTIFACTS_PER_SITE` | `10` | Max artifacts per site in dev mode |
| `SITE_MATCH_RADIUS_KM` | `5.0` | Radius for Wikidata spatial queries |
| `SIMILARITY_TOP_N` | `20` | Similar motifs stored per segment |
| `HDBSCAN_MIN_CLUSTER_SIZES` | `[5, 15, 30, 50]` | Tested during clustering; best picked by silhouette score |
| `EXPORT_SIZE_BUDGET_MB` | `50` | Max export size for GitHub Pages |

### Tests

```bash
python -m pytest tests/ -v
```

## Progress Tracker

| Milestone | Status | Notes |
|-----------|--------|-------|
| Site scraping (8,860 sites) | :white_check_mark: Complete | `data/raw/places.json` |
| Repo reorganization | :white_check_mark: Complete | Pipeline package structure |
| Data models + provenance | :white_check_mark: Complete | 9 dataclasses, full provenance chain |
| Stage 1: Site matching | :white_check_mark: Complete | Wikidata SPARQL + Levenshtein scoring |
| Stage 2: Artifact harvesting | :white_check_mark: Complete | 5 sources, multi-signal dedup |
| Stage 3: Image collection | :white_check_mark: Complete | Checkpointed downloads, dev/prod modes |
| Stage 4: CLIPSeg segmentation | :white_check_mark: Complete | Otsu thresholding, segment filtering, SVG tracing |
| Stage 5: CLIP embedding | :white_check_mark: Complete | Segment embeddings (.npz) + text motif tags |
| Stage 6: Similarity + clustering | :white_check_mark: Complete | HDBSCAN, medoid canonical SVGs |
| Stage 7: Static export | :white_check_mark: Complete | Chunked JSON, size budget enforcement |
| Pipeline orchestrator | :white_check_mark: Complete | `python -m pipeline.run` |
| Test suite (73 tests) | :white_check_mark: Passing | All stages covered |
| First pipeline run | :hourglass_flowing_sand: Pending | Awaiting execution on full dataset |
| Next.js frontend | :hourglass_flowing_sand: Pending | MapLibre map, motif explorer |
| GitHub Pages deployment | :hourglass_flowing_sand: Pending | Static export → GH Pages |

## Data Sources

| Source | Type | License | What it provides |
|--------|------|---------|-----------------|
| [Wikidata](https://www.wikidata.org/) | SPARQL | CC0 | Structured artifact records, materials, dates, images |
| [Metropolitan Museum](https://metmuseum.github.io/) | REST API | CC0 (public domain items) | 500K+ objects, excellent image quality |
| [British Museum](https://collection.britishmuseum.org/) | SPARQL (LOD) | CC-BY-NC-SA 4.0 | Near East, Egypt, Classical world |
| [Harvard Art Museums](https://harvardartmuseums.org/collections/api) | REST API | Restricted | 250K objects, requires API key |
| [Wikimedia Commons](https://commons.wikimedia.org/) | MediaWiki API | CC-BY-SA / CC0 | Cave art, petroglyphs, archaeological photos |

## Project Structure

```
ancient-locs/
  pipeline/
    run.py                     # Pipeline orchestrator
    config.py                  # All configuration
    models.py                  # Data models (9 dataclasses)
    provenance.py              # Provenance tracking utilities
    api_client.py              # Cached API client with rate limiting
    dedup.py                   # Multi-signal deduplication
    scrape.py                  # Original site scraper (Stage 0)
    stage_1_site_matching.py   # Wikidata/Pleiades matching
    stage_2_artifact_harvest.py
    stage_3_image_collection.py
    stage_4_segmentation.py    # CLIPSeg motif extraction
    stage_5_embedding.py       # CLIP embeddings + text tagging
    stage_6_similarity.py      # Similarity + HDBSCAN clustering
    stage_7_export.py          # Static export for frontend
    harvesters/
      wikidata.py / met.py / british_museum.py / harvard.py / wikimedia_commons.py

  data/                        # Pipeline outputs (gitignored)
    raw/places.json            # 8,860 archaeological sites

  web/                         # Next.js frontend (coming soon)
  docs/superpowers/specs/      # Design specifications
  tests/                       # 73 tests
```

## Design Documents

- [Design Spec](docs/superpowers/specs/2026-03-16-ancient-motif-encyclopedia-design.md) — Full architecture and data model
- [Implementation Plan](docs/superpowers/plans/2026-03-16-ancient-motif-pipeline.md) — Task breakdown

## License

MIT

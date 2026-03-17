<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 300" fill="none">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="900" y2="300" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#0f0a07"/>
      <stop offset="30%" stop-color="#1e140d"/>
      <stop offset="70%" stop-color="#1e140d"/>
      <stop offset="100%" stop-color="#0f0a07"/>
    </linearGradient>
    <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#9e6b3a"/>
      <stop offset="40%" stop-color="#d4a05a"/>
      <stop offset="60%" stop-color="#e8bf7e"/>
      <stop offset="100%" stop-color="#9e6b3a"/>
    </linearGradient>
    <linearGradient id="goldV" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#d4a05a"/>
      <stop offset="100%" stop-color="#9e6b3a"/>
    </linearGradient>
    <radialGradient id="glow" cx="450" cy="130" r="280" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#d4a05a" stop-opacity="0.06"/>
      <stop offset="100%" stop-color="#d4a05a" stop-opacity="0"/>
    </radialGradient>
    <pattern id="noise" x="0" y="0" width="200" height="200" patternUnits="userSpaceOnUse">
      <circle cx="23" cy="17" r="0.5" fill="#d4a05a" opacity="0.04"/>
      <circle cx="67" cy="43" r="0.4" fill="#d4a05a" opacity="0.03"/>
      <circle cx="112" cy="8" r="0.6" fill="#d4a05a" opacity="0.03"/>
      <circle cx="156" cy="61" r="0.3" fill="#d4a05a" opacity="0.05"/>
      <circle cx="34" cy="89" r="0.5" fill="#d4a05a" opacity="0.03"/>
      <circle cx="89" cy="72" r="0.4" fill="#d4a05a" opacity="0.04"/>
      <circle cx="145" cy="97" r="0.5" fill="#d4a05a" opacity="0.03"/>
      <circle cx="178" cy="134" r="0.4" fill="#d4a05a" opacity="0.04"/>
      <circle cx="12" cy="156" r="0.6" fill="#d4a05a" opacity="0.03"/>
      <circle cx="56" cy="178" r="0.3" fill="#d4a05a" opacity="0.05"/>
      <circle cx="101" cy="145" r="0.5" fill="#d4a05a" opacity="0.03"/>
      <circle cx="190" cy="167" r="0.4" fill="#d4a05a" opacity="0.04"/>
    </pattern>
    <clipPath id="bannerClip"><rect width="900" height="300" rx="8"/></clipPath>
  </defs>

  <!-- Background -->
  <g clip-path="url(#bannerClip)">
    <rect width="900" height="300" fill="url(#bg)"/>
    <rect width="900" height="300" fill="url(#noise)"/>
    <rect width="900" height="300" fill="url(#glow)"/>

    <!-- Greek meander border top -->
    <g opacity="0.18" stroke="#d4a05a" stroke-width="1.2" fill="none">
      <path d="M0,16 L900,16"/>
      <path d="M0,28 L900,28"/>
      <!-- Meander keys -->
      <g transform="translate(20,16)">
        <path d="M0,0 L0,12 L8,12 L8,4 L4,4 L4,8 L0,8" />
        <path d="M16,0 L16,12 L24,12 L24,4 L20,4 L20,8 L16,8" />
        <path d="M32,0 L32,12 L40,12 L40,4 L36,4 L36,8 L32,8" />
        <path d="M48,0 L48,12 L56,12 L56,4 L52,4 L52,8 L48,8" />
        <path d="M64,0 L64,12 L72,12 L72,4 L68,4 L68,8 L64,8" />
      </g>
      <g transform="translate(780,16) scale(-1,1)">
        <path d="M0,0 L0,12 L8,12 L8,4 L4,4 L4,8 L0,8" />
        <path d="M16,0 L16,12 L24,12 L24,4 L20,4 L20,8 L16,8" />
        <path d="M32,0 L32,12 L40,12 L40,4 L36,4 L36,8 L32,8" />
        <path d="M48,0 L48,12 L56,12 L56,4 L52,4 L52,8 L48,8" />
        <path d="M64,0 L64,12 L72,12 L72,4 L68,4 L68,8 L64,8" />
      </g>
    </g>

    <!-- Greek meander border bottom -->
    <g opacity="0.18" stroke="#d4a05a" stroke-width="1.2" fill="none" transform="translate(0,256)">
      <path d="M0,16 L900,16"/>
      <path d="M0,28 L900,28"/>
      <g transform="translate(20,16)">
        <path d="M0,0 L0,12 L8,12 L8,4 L4,4 L4,8 L0,8" />
        <path d="M16,0 L16,12 L24,12 L24,4 L20,4 L20,8 L16,8" />
        <path d="M32,0 L32,12 L40,12 L40,4 L36,4 L36,8 L32,8" />
        <path d="M48,0 L48,12 L56,12 L56,4 L52,4 L52,8 L48,8" />
        <path d="M64,0 L64,12 L72,12 L72,4 L68,4 L68,8 L64,8" />
      </g>
      <g transform="translate(780,16) scale(-1,1)">
        <path d="M0,0 L0,12 L8,12 L8,4 L4,4 L4,8 L0,8" />
        <path d="M16,0 L16,12 L24,12 L24,4 L20,4 L20,8 L16,8" />
        <path d="M32,0 L32,12 L40,12 L40,4 L36,4 L36,8 L32,8" />
        <path d="M48,0 L48,12 L56,12 L56,4 L52,4 L52,8 L48,8" />
        <path d="M64,0 L64,12 L72,12 L72,4 L68,4 L68,8 L64,8" />
      </g>
    </g>

    <!-- Left decorative panel: Spiral / Triskelion -->
    <g transform="translate(90, 130)" opacity="0.22">
      <!-- Triple spiral (triskelion) -->
      <path d="M0,-2 C0,-14 10,-24 22,-24 C36,-24 46,-14 46,-2 C46,14 34,26 18,26 C0,26 -12,14 -12,-2 C-12,-20 2,-34 22,-34 C44,-34 58,-20 58,-2 C58,22 40,38 18,38" stroke="#d4a05a" stroke-width="1.8" fill="none" stroke-linecap="round"/>
      <path d="M0,-2 C0,8 -8,16 -18,16 C-30,16 -38,8 -38,-2 C-38,-16 -28,-26 -14,-26 C2,-26 14,-16 14,-2" stroke="#d4a05a" stroke-width="1.8" fill="none" stroke-linecap="round" transform="rotate(120)"/>
      <path d="M0,-2 C0,8 -8,16 -18,16 C-30,16 -38,8 -38,-2 C-38,-16 -28,-26 -14,-26 C2,-26 14,-16 14,-2" stroke="#d4a05a" stroke-width="1.8" fill="none" stroke-linecap="round" transform="rotate(240)"/>
      <circle cx="0" cy="0" r="3" fill="#d4a05a" opacity="0.4"/>
    </g>

    <!-- Right decorative panel: Rosette / Sun disc -->
    <g transform="translate(810, 130)" opacity="0.22">
      <!-- 8-petal rosette -->
      <circle cx="0" cy="0" r="5" fill="#d4a05a" opacity="0.3"/>
      <circle cx="0" cy="0" r="30" stroke="#d4a05a" stroke-width="1" fill="none"/>
      <g stroke="#d4a05a" stroke-width="1.5" fill="none">
        <ellipse cx="0" cy="-18" rx="7" ry="14" transform="rotate(0)"/>
        <ellipse cx="0" cy="-18" rx="7" ry="14" transform="rotate(45)"/>
        <ellipse cx="0" cy="-18" rx="7" ry="14" transform="rotate(90)"/>
        <ellipse cx="0" cy="-18" rx="7" ry="14" transform="rotate(135)"/>
        <ellipse cx="0" cy="-18" rx="7" ry="14" transform="rotate(180)"/>
        <ellipse cx="0" cy="-18" rx="7" ry="14" transform="rotate(225)"/>
        <ellipse cx="0" cy="-18" rx="7" ry="14" transform="rotate(270)"/>
        <ellipse cx="0" cy="-18" rx="7" ry="14" transform="rotate(315)"/>
      </g>
      <circle cx="0" cy="0" r="38" stroke="#d4a05a" stroke-width="0.8" fill="none" stroke-dasharray="3 5"/>
    </g>

    <!-- Left column: Chevrons / zigzag -->
    <g transform="translate(32, 50)" opacity="0.10" stroke="#d4a05a" stroke-width="1.2" fill="none">
      <path d="M0,0 L8,10 L16,0"/>
      <path d="M0,16 L8,26 L16,16"/>
      <path d="M0,32 L8,42 L16,32"/>
      <path d="M0,48 L8,58 L16,48"/>
      <path d="M0,64 L8,74 L16,64"/>
      <path d="M0,80 L8,90 L16,80"/>
      <path d="M0,96 L8,106 L16,96"/>
      <path d="M0,112 L8,122 L16,112"/>
      <path d="M0,128 L8,138 L16,128"/>
      <path d="M0,144 L8,154 L16,144"/>
      <path d="M0,160 L8,170 L16,160"/>
    </g>

    <!-- Right column: Chevrons / zigzag -->
    <g transform="translate(852, 50)" opacity="0.10" stroke="#d4a05a" stroke-width="1.2" fill="none">
      <path d="M0,0 L8,10 L16,0"/>
      <path d="M0,16 L8,26 L16,16"/>
      <path d="M0,32 L8,42 L16,32"/>
      <path d="M0,48 L8,58 L16,48"/>
      <path d="M0,64 L8,74 L16,64"/>
      <path d="M0,80 L8,90 L16,80"/>
      <path d="M0,96 L8,106 L16,96"/>
      <path d="M0,112 L8,122 L16,112"/>
      <path d="M0,128 L8,138 L16,128"/>
      <path d="M0,144 L8,154 L16,144"/>
      <path d="M0,160 L8,170 L16,160"/>
    </g>

    <!-- Scattered archaeological dots -->
    <g opacity="0.08" fill="#d4a05a">
      <circle cx="170" cy="60" r="1.5"/><circle cx="195" cy="78" r="1"/>
      <circle cx="220" cy="52" r="1.8"/><circle cx="260" cy="70" r="1.2"/>
      <circle cx="640" cy="58" r="1.5"/><circle cx="680" cy="72" r="1"/>
      <circle cx="720" cy="48" r="1.8"/><circle cx="745" cy="68" r="1.2"/>
      <circle cx="175" cy="220" r="1.2"/><circle cx="210" cy="235" r="1"/>
      <circle cx="690" cy="225" r="1.5"/><circle cx="730" cy="210" r="1"/>
    </g>

    <!-- Title ornament: left rule -->
    <g opacity="0.35">
      <line x1="170" y1="92" x2="330" y2="92" stroke="url(#goldV)" stroke-width="0.6"/>
      <line x1="200" y1="88" x2="200" y2="96" stroke="#d4a05a" stroke-width="0.6"/>
      <line x1="230" y1="88" x2="230" y2="96" stroke="#d4a05a" stroke-width="0.6"/>
      <line x1="260" y1="88" x2="260" y2="96" stroke="#d4a05a" stroke-width="0.6"/>
      <line x1="290" y1="88" x2="290" y2="96" stroke="#d4a05a" stroke-width="0.6"/>
      <circle cx="170" cy="92" r="2.5" fill="#d4a05a" opacity="0.5"/>
      <circle cx="330" cy="92" r="2.5" fill="#d4a05a" opacity="0.5"/>
    </g>
    <!-- Title ornament: right rule -->
    <g opacity="0.35">
      <line x1="570" y1="92" x2="730" y2="92" stroke="url(#goldV)" stroke-width="0.6"/>
      <line x1="610" y1="88" x2="610" y2="96" stroke="#d4a05a" stroke-width="0.6"/>
      <line x1="640" y1="88" x2="640" y2="96" stroke="#d4a05a" stroke-width="0.6"/>
      <line x1="670" y1="88" x2="670" y2="96" stroke="#d4a05a" stroke-width="0.6"/>
      <line x1="700" y1="88" x2="700" y2="96" stroke="#d4a05a" stroke-width="0.6"/>
      <circle cx="570" cy="92" r="2.5" fill="#d4a05a" opacity="0.5"/>
      <circle cx="730" cy="92" r="2.5" fill="#d4a05a" opacity="0.5"/>
    </g>

    <!-- Title -->
    <text x="450" y="100" text-anchor="middle" font-family="Georgia, 'Palatino Linotype', 'Book Antiqua', serif" font-size="46" font-weight="bold" fill="url(#gold)" letter-spacing="8">ANCIENT LOCS</text>

    <!-- Subtitle band -->
    <text x="450" y="128" text-anchor="middle" font-family="Georgia, 'Palatino Linotype', serif" font-size="13" fill="#d4a05a" opacity="0.55" letter-spacing="10" font-variant="small-caps">MOTIF ENCYCLOPEDIA</text>

    <!-- Thin divider with diamond -->
    <g opacity="0.3">
      <line x1="240" y1="148" x2="440" y2="148" stroke="#d4a05a" stroke-width="0.5"/>
      <rect x="445" y="143" width="10" height="10" transform="rotate(45 450 148)" fill="none" stroke="#d4a05a" stroke-width="0.8"/>
      <line x1="460" y1="148" x2="660" y2="148" stroke="#d4a05a" stroke-width="0.5"/>
    </g>

    <!-- Description -->
    <text x="450" y="175" text-anchor="middle" font-family="'Helvetica Neue', 'Segoe UI', Arial, sans-serif" font-size="14" fill="#c4a882" letter-spacing="0.8">Tracing decorative motifs across 8,860 ancient sites</text>

    <!-- Tech stack pills -->
    <g font-family="'SF Mono', 'Fira Code', 'Consolas', monospace" font-size="10" text-anchor="middle">
      <g transform="translate(300, 200)">
        <rect x="-52" y="-11" width="104" height="22" rx="11" fill="#d4a05a" opacity="0.08" stroke="#d4a05a" stroke-width="0.5" stroke-opacity="0.2"/>
        <text fill="#b8956a" letter-spacing="0.5">CLIPSeg</text>
      </g>
      <g transform="translate(450, 200)">
        <rect x="-60" y="-11" width="120" height="22" rx="11" fill="#d4a05a" opacity="0.08" stroke="#d4a05a" stroke-width="0.5" stroke-opacity="0.2"/>
        <text fill="#b8956a" letter-spacing="0.5">CLIP embeddings</text>
      </g>
      <g transform="translate(600, 200)">
        <rect x="-52" y="-11" width="104" height="22" rx="11" fill="#d4a05a" opacity="0.08" stroke="#d4a05a" stroke-width="0.5" stroke-opacity="0.2"/>
        <text fill="#b8956a" letter-spacing="0.5">HDBSCAN</text>
      </g>
    </g>

    <!-- Bottom motif labels -->
    <text x="90" y="248" text-anchor="middle" font-family="'SF Mono', 'Fira Code', 'Consolas', monospace" font-size="8" fill="#6b5040" letter-spacing="2">TRISKELION</text>
    <text x="810" y="248" text-anchor="middle" font-family="'SF Mono', 'Fira Code', 'Consolas', monospace" font-size="8" fill="#6b5040" letter-spacing="2">ROSETTE</text>

    <!-- Outer border -->
    <rect x="1" y="1" width="898" height="298" rx="7" stroke="#d4a05a" stroke-width="0.8" fill="none" opacity="0.15"/>
    <rect x="6" y="6" width="888" height="288" rx="5" stroke="#d4a05a" stroke-width="0.4" fill="none" opacity="0.10"/>
  </g>
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

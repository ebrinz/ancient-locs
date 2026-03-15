# Artifact Motif Influence Pipeline — Design Spec

## Overview

A data enrichment pipeline and interactive map application for tracing decorative motif influence (spirals, crosses, waves, etc.) across ancient cultures and geographies. The pipeline enriches an existing dataset of 8,860 archaeological sites with artifact records, images, traced SVGs, and CLIP embeddings, then precomputes motif similarity. A static Next.js app deployed to GitHub Pages visualizes the results on an interactive map.

## Goals

- Enrich archaeological site data with artifact records from multiple external sources
- Collect artifact images and trace them to SVG for map display
- Tag motifs from text descriptions and generate CLIP embeddings from images
- Precompute similarity between artifacts based on visual and textual features
- Maintain full data provenance for every record, embedding, and transformation
- Present results in a static interactive map with SVG motif markers

## Data Model

### ProvenanceRecord

Every piece of data carries a provenance chain.

```
ProvenanceRecord:
  source_id: str          # e.g., "met_museum", "wikidata", "british_museum"
  source_url: str         # exact URL/query that produced this data
  fetch_date: str         # ISO 8601 timestamp
  license: str            # CC0, CC-BY, etc.
  raw_response_hash: str  # SHA256 of the raw response for reproducibility
  transformation: str     # what processing was applied (e.g., "clip_embedding_v1")
```

### Site

Extended from the existing `places.json` schema.

```
Site:
  id: str
  name: str
  other_names: str | null
  modern_names: str | null
  region: str
  section: str | null
  latitude: float
  longitude: float
  status: str
  info: str | null
  sources: str | null
  external_ids:
    wikidata: str | null    # Q-ID
    pleiades: str | null    # Pleiades URI
```

### Artifact

```
Artifact:
  id: str
  name: str
  description: str
  type: str                 # pottery, sculpture, jewelry, etc.
  site_id: str              # FK to Site
  period: str | null        # e.g., "Late Bronze Age", "300-200 BCE"
  date_range_start: int | null  # year (negative for BCE)
  date_range_end: int | null
  materials: [str]
  techniques: [str]
  motif_tags: [str]         # e.g., ["spiral", "wave", "cross"]
  provenance: [ProvenanceRecord]
```

### ArtifactImage

```
ArtifactImage:
  id: str
  artifact_id: str          # FK to Artifact
  source_image_url: str
  local_path: str
  svg_path: str | null       # traced SVG version
  provenance: ProvenanceRecord
```

### Embedding

```
Embedding:
  id: str
  artifact_id: str           # FK to Artifact
  model: str                 # e.g., "clip-vit-b-32"
  vector: [float]
  embedding_type: "image" | "text"
  provenance: ProvenanceRecord
```

### SimilarityEdge

```
SimilarityEdge:
  artifact_a_id: str
  artifact_b_id: str
  score: float
  method: str                # "clip_cosine", "tag_jaccard", "combined"
```

## Pipeline Stages

All stages are idempotent and write manifests of what they processed.

### Stage 0 — Scrape (existing)

`pipeline/scrape.py` — the existing scraper from ancientlocations.net. Output: `data/raw/places.json`.

### Stage 1 — Site Matching

`pipeline/stage_1_site_matching.py`

- Parse coordinates from the raw `places.json` format ("40.93360567 N") into numeric lat/lng
- Query Wikidata SPARQL for archaeological sites within radius of each site's coordinates + fuzzy name matching
- Query Pleiades API by name and coordinates
- Store matched external IDs onto each Site record
- Output: `data/sites/` — one JSON file per site with enriched data
- Expected match rate: ~30-50%

### Stage 2 — Artifact Harvesting

`pipeline/stage_2_artifact_harvest.py`

For matched sites, query multiple APIs:

- **Wikidata** — SPARQL for artifacts with `P189` (location of discovery) linking to matched site
- **Metropolitan Museum API** — search by geography/culture/medium, filtered to ceramics and decorated objects
- **British Museum API** — search by find-spot coordinates
- **Harvard Peabody Museum** — search by site name/region

Features:
- Deduplication across sources (same artifact may appear in multiple)
- Rate limiting and caching — APIs hit once, raw responses saved to `data/raw/`
- Output: `data/artifacts/` — one JSON file per artifact with full provenance

### Stage 3 — Image Collection

`pipeline/stage_3_image_collection.py`

- Download available images per artifact, respecting licenses
- Run **vtracer** to convert raster images to SVG (better quality than potrace for this use case)
- Store originals in `data/images/`, traced SVGs in `data/svgs/`
- Output: updated ArtifactImage records with provenance

### Stage 4 — Motif Tagging

`pipeline/stage_4_motif_tagging.py`

Two paths:

- **Text path:** NLP extraction from artifact descriptions — regex + keyword matching for known motif vocabulary: spiral, meander, cross, chevron, wave, guilloche, rosette, palmette, zigzag, concentric circles, hatching, etc.
- **Vision path:** Run CLIP (`clip-vit-b-32`) on artifact images, store embeddings in `data/embeddings/`

Both paths produce provenance records noting model version and parameters.

### Stage 5 — Similarity Computation

`pipeline/stage_5_similarity.py`

- **Tag-based:** Jaccard similarity on motif tag sets
- **Embedding-based:** Cosine similarity on CLIP vectors
- **Combined score:** Weighted blend (configurable in `config.py`)
- Precompute top-N similar artifacts per artifact (default: top 20)
- Output: `data/similarity/` — adjacency list format

### Stage 6 — Export

`pipeline/stage_6_export.py`

Package for Next.js consumption into `web/public/data/`:

- `sites.json` — all sites with linked artifact counts
- `artifacts/{site_id}.json` — artifacts per site
- `svgs/` — traced SVG files
- `similarity.json` — precomputed similarity graph
- `provenance.json` — full provenance chain for every record

## Next.js Static App

### Pages

```
app/
  page.tsx                    # Map view (default)
  artifacts/[id]/page.tsx     # Artifact detail
  sites/[id]/page.tsx         # Site detail with linked artifacts
  similarity/page.tsx         # Similarity cluster explorer
```

### Map View

- **MapLibre GL** (open source, no API key needed)
- Sites rendered as clusters at zoom-out, individual markers at zoom-in
- Artifacts with traced SVGs render their motif as the marker icon on the map
- Color coding by region or motif type (user toggle)
- Filter panel: region, period, motif type, data source
- Click marker: sidebar with site info, artifact thumbnails, SVG previews

### Artifact Detail

- Original image + traced SVG side by side
- Description, period, materials, motif tags
- Full provenance chain displayed
- "Similar artifacts" grid from precomputed similarity index
- Click similar artifact: see both on map with connecting line

### Similarity Explorer

- Select an artifact or motif type
- Map highlights all similar artifacts with arcs/lines connecting sites
- Line opacity/thickness proportional to similarity score
- Visualizes motif influence corridors across cultures and geographies

### Tech Stack

- Next.js with `output: 'export'` for static generation
- MapLibre GL JS
- Data loaded from `public/data/` JSON at build time or client-side
- SVGs inlined or loaded as React components
- Deployed to GitHub Pages

## Project Structure

```
ancient-locs/
  pipeline/
    scrape.py                    # Stage 0 — existing scraper
    config.py                    # API keys, rate limits, thresholds
    provenance.py                # Shared provenance utilities
    stage_1_site_matching.py
    stage_2_artifact_harvest.py
    stage_3_image_collection.py
    stage_4_motif_tagging.py
    stage_5_similarity.py
    stage_6_export.py
    requirements.txt

  data/                          # Pipeline outputs (gitignored)
    raw/
      places.json                # Original scraped data
    sites/                       # Enriched site records
    artifacts/                   # Artifact records with provenance
    images/                      # Downloaded artifact images
    svgs/                        # Traced SVGs
    embeddings/                  # CLIP vectors
    similarity/                  # Precomputed similarity graph
    manifests/                   # Stage run logs

  web/                           # Next.js app
    public/data/                 # Stage 6 export target
    src/
      app/
      components/
        Map.tsx
        ArtifactCard.tsx
        SimilarityView.tsx
        ProvenanceChain.tsx
        FilterPanel.tsx
      lib/
        data.ts                  # Static data loading utilities
    next.config.js
    package.json

  docs/
    superpowers/specs/
```

`data/` is gitignored (too large). `web/public/data/` contains the exported subset for the static app.

## Key Design Decisions

1. **Provenance-first:** every record, embedding, and transformation carries a full provenance chain back to its source. This is non-negotiable for academic credibility.
2. **Static output:** the pipeline produces static JSON and SVG files. No runtime database or backend. This keeps deployment trivial (GitHub Pages) and data reproducible.
3. **Dual embedding strategy:** text tags for interpretable filtering, CLIP embeddings for visual similarity. Combined scoring lets either pathway contribute.
4. **SVGs traced from real artifacts:** authentic representations, not stylized icons. Maintains academic integrity.
5. **Idempotent stages:** each pipeline stage can be re-run safely. Manifests track what was processed.
6. **Multi-source deduplication:** artifacts appearing in multiple APIs are merged, with all source provenance preserved.

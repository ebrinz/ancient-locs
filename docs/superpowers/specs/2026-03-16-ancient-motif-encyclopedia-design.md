# Ancient Art Motif Encyclopedia — Design Spec

## Overview

An ancient art motif encyclopedia that extracts, embeds, and compares decorative motifs across all publicly available artifact imagery — spanning cave art, relief carvings, pottery, mosaics, seals, and textiles — to reveal visual pattern alignment across cultures, geographies, and time periods.

The pipeline enriches an existing dataset of 8,860 archaeological sites with artifact records from 5 public sources, uses CLIPSeg to isolate decorative motif regions from artifact photos, generates CLIP embeddings on the isolated segments, clusters them to discover emergent motif types, and generates canonical SVGs for each cluster. A static Next.js app on GitHub Pages visualizes results on an interactive map.

## Goals

- Harvest artifact records and images from 5 public APIs — all artifact types, not filtered by medium
- Segment motif regions from artifact images using CLIPSeg
- Embed isolated motif segments with CLIP for visual similarity comparison
- Cluster embeddings to discover emergent motif types and generate canonical SVGs per cluster
- Maintain full data provenance for every record, segment, embedding, and transformation
- Support two pipeline modes: dev (save images for debugging) and production (save only embeddings + SVGs + metadata)
- Present results in a static interactive map with canonical motif SVG markers

## Data Model

### ProvenanceRecord

Every piece of data carries a provenance chain.

```
ProvenanceRecord:
  source_id: str          # e.g., "met_museum", "wikidata", "wikimedia_commons"
  source_url: str         # exact URL/query that produced this data
  fetch_date: str         # ISO 8601 timestamp
  license: str            # CC0, CC-BY, etc.
  raw_response_hash: str  # SHA256 of the raw response for reproducibility
  transformation: str     # what processing was applied (e.g., "clipseg_v1", "clip_embedding_v1")
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
  type: str                 # pottery, sculpture, relief, cave_art, mosaic, seal, textile, etc.
  site_id: str | null        # FK to Site. Null if artifact matches a region but not a specific site.
  region: str | null          # Fallback geographic context when site_id is null
  period: str | null        # e.g., "Late Bronze Age", "300-200 BCE"
  date_range_start: int | null  # year (negative for BCE)
  date_range_end: int | null
  materials: [str]
  techniques: [str]
  motif_tags: [str]         # e.g., ["spiral", "wave", "cross"] — from text extraction
  provenance: [ProvenanceRecord]
```

### ArtifactImage

```
ArtifactImage:
  id: str
  artifact_id: str          # FK to Artifact
  source_image_url: str
  local_path: str           # populated in dev mode, empty in production mode
  provenance: ProvenanceRecord
```

### MotifSegment

A region of an artifact image identified by CLIPSeg as containing a decorative motif.

```
MotifSegment:
  id: str
  artifact_image_id: str     # FK to ArtifactImage
  artifact_id: str            # FK to Artifact
  mask_index: int             # which CLIPSeg segment
  bbox: [x, y, w, h]         # bounding box in original image
  area_ratio: float           # segment area / image area
  contour_complexity: float   # perimeter² / area (circularity metric)
  cropped_image_path: str     # dev mode only — empty in production
  svg_path: str | null        # traced SVG of isolated segment
  provenance: ProvenanceRecord
```

### Embedding

```
Embedding:
  id: str
  segment_id: str            # FK to MotifSegment (not artifact — we embed segments)
  artifact_id: str            # FK to Artifact (denormalized for convenience)
  model: str                 # e.g., "clip-vit-b-32"
  vector: [float]
  embedding_type: "image" | "text"
  provenance: ProvenanceRecord
```

### MotifCluster

Emergent motif types discovered by clustering segment embeddings.

```
MotifCluster:
  id: str
  label: str | null           # auto-generated or manually named later
  member_count: int
  centroid_embedding: [float]  # cluster center in CLIP space
  canonical_svg_path: str      # medoid SVG representing this motif type
  member_segment_ids: [str]    # FK to MotifSegments in this cluster
  provenance: ProvenanceRecord # records HDBSCAN params, embedding model, input count, timestamp
```

### SimilarityEdge

```
SimilarityEdge:
  segment_a_id: str           # FK to MotifSegment
  segment_b_id: str
  score: float
  method: str                # "clip_cosine", "tag_jaccard", "combined"
```

## Pipeline Modes

Configured via `PIPELINE_MODE` in `config.py`:

- **`dev`** — Save everything: raw images, cropped segments, SVGs, embeddings, metadata. Limit batch sizes for fast iteration. For debugging and visual QA.
- **`production`** — Save only: motif embeddings (.npz), segment SVGs, metadata JSON, canonical cluster SVGs. Discard source images and raw segment crops after processing. For scale runs.

In both modes, provenance records are always saved.

## Pipeline Stages

All stages are idempotent and write manifests of what they processed.

### Stage 0 — Scrape (existing)

`pipeline/scrape.py` — the existing scraper from ancientlocations.net. Output: `data/raw/places.json`.

### Stage 1 — Site Matching

`pipeline/stage_1_site_matching.py`

- Parse coordinates from the raw `places.json` format ("40.93360567 N") into numeric lat/lng, negating for S/W directions
- Handle edge cases: 2 records in the dataset have null names — these are matched by coordinates only
- Query Wikidata SPARQL for archaeological sites within radius of each site's coordinates + fuzzy name matching
- Query Pleiades API by name and coordinates
- Store matched external IDs onto each Site record
- Output: `data/sites/` — one JSON file per site with enriched data
- Expected match rate: ~30-50%

### Stage 2 — Artifact Harvesting

`pipeline/stage_2_artifact_harvest.py`

For matched sites, query 5 APIs — **all artifact types with images, no medium/type filter**:

- **Wikidata** — SPARQL for artifacts with `P189` (location of discovery) linking to matched site. All types.
- **Metropolitan Museum API** — search by geography/culture across all ancient departments (Greek & Roman, Egyptian, Ancient Near Eastern, Asian, Arts of Africa/Oceania/Americas). No medium filter.
- **British Museum Linked Open Data** — SPARQL queries against `collection.britishmuseum.org` for objects by find-spot. All types. Note: the BM does not have a REST search API; all queries go through their SPARQL endpoint. **Reliability warning:** this endpoint has historically gone offline for extended periods. The pipeline must gracefully skip BM if unavailable — log a warning and continue with the other 4 sources.
- **Harvard Art Museums API** — search by culture/classification (requires API key). All types. Note: this is the Harvard Art Museums collection, not the Peabody Museum of Archaeology, which does not expose a public API.
- **Wikimedia Commons** — query via MediaWiki API using categories ("Ancient art", "Petroglyphs", "Cave paintings", "Archaeological artifacts by country", etc.). Large volume, CC-licensed, geographic metadata in categories.

Features:
- Deduplication across sources using a multi-signal matching approach:
  - Primary: accession number / inventory ID match across sources
  - Secondary: fuzzy name + site + date range match (Levenshtein distance < 3 on name, same site, overlapping date range)
  - When duplicates are found, all source provenance records are preserved on the merged artifact. Metadata conflicts are resolved by source priority: Wikidata (most structured) > Met > Harvard > British Museum > Wikimedia Commons.
- Rate limiting per source: Wikidata SPARQL (respect User-Agent policy, 60s query timeout), Met Museum (1 req/s), Harvard (2500 req/day with key), BM SPARQL (conservative 1 req/2s), Wikimedia Commons (respect maxlag, 200 req/s with good User-Agent)
- File-based response caching — raw responses saved to `data/raw/{source}/` with content hash filenames
- Output: `data/artifacts/` — one JSON file per artifact with full provenance
- Expected yield: ~10,000-50,000 artifacts with images

### Stage 3 — Image Collection

`pipeline/stage_3_image_collection.py`

- Download available images per artifact, respecting licenses
- Checkpoint tracking: a download manifest (`data/manifests/stage_3_downloads.json`) records each successfully downloaded image with its hash. Partial/failed downloads are detected by size/hash mismatch and re-fetched on re-run.
- In **dev mode**: save images to `data/images/`. In **production mode**: images are processed one-at-a-time in a streaming fashion (download → segment → embed → discard) to avoid memory pressure. This means Stages 3-5 run as a fused streaming pipeline in production mode, while in dev mode they remain separate stages for debuggability.
- Output: updated ArtifactImage records with provenance

### Stage 4 — Motif Segmentation

`pipeline/stage_4_segmentation.py`

**CLIPSeg-based motif extraction:**

1. Run CLIPSeg on each artifact image with text prompts: "decorative motif", "carved pattern", "painted design", "geometric decoration", "engraved symbol"
2. **Heatmap to mask conversion:** CLIPSeg produces a single activation heatmap per prompt, not discrete masks. Conversion process:
   - For each prompt, threshold the heatmap using Otsu's method (adaptive per image)
   - Take the maximum activation across all prompts (union strategy — a region matching any prompt is kept)
   - Run connected-component analysis (OpenCV `connectedComponentsWithStats`) to extract discrete regions
3. **Segment filtering** — keep segments likely to be decorative motifs:
   - Size: between 3% and 40% of total image area (too small = noise, too large = the whole object)
   - Contour complexity: segment boundary has enough complexity to be "interesting" (perimeter² / area ratio above threshold)
   - Aspect ratio: discard extremely elongated segments (likely edges/borders)
4. Crop each passing segment as its own image
5. Run **vtracer** on cropped segments to produce SVGs (much cleaner than tracing full photos since the motif is isolated)
6. **SVG quality gate**: traced SVGs with path count below minimum (too simple) or above maximum (too noisy) are excluded
7. In **dev mode**: save cropped segments to `data/segments/`. In **production mode**: segments held in memory for embedding, then discarded.
- Output: MotifSegment records with SVGs in `data/svgs/`

### Stage 5 — Motif Embedding

`pipeline/stage_5_embedding.py`

- **Vision path:** Run CLIP (`clip-vit-b-32`) on cropped motif segments (not full images), store embeddings in `data/embeddings/` as NumPy `.npz` archives. A separate metadata index (`data/embeddings/index.json`) maps segment IDs to their position in the archive.
- **Text path:** NLP extraction from artifact descriptions — regex + keyword matching for known motif vocabulary: spiral, meander, cross, chevron, wave, guilloche, rosette, palmette, zigzag, concentric circles, hatching, geometric, floral, figural, anthropomorphic, zoomorphic, etc. Tags stored on the parent Artifact record.
- Both paths produce provenance records noting model version and parameters.

### Stage 6 — Similarity + Clustering

`pipeline/stage_6_similarity.py`

**Similarity:**
- **Embedding-based:** Cosine similarity on CLIP vectors of segments (primary signal — operates at segment level)
- **Tag-based:** Jaccard similarity on motif tag sets from parent artifacts (secondary signal — operates at artifact level, inherited by all segments of that artifact). Note: this creates an asymmetry where segments from the same artifact share identical tag scores. This is acceptable because tag similarity serves as a coarse filter while embedding similarity provides fine-grained visual matching.
- **Combined score:** Weighted blend (configurable in `config.py`), defaulting to heavier embedding weight (0.7 embedding / 0.3 tag) given the segment-level focus
- Precompute top-N similar segments per segment (default: top 20)

**Clustering:**
- Run HDBSCAN on the full CLIP embedding space to discover emergent motif types
- `min_cluster_size` is sensitive and requires empirical tuning. Strategy: run with multiple values (e.g., 5, 15, 30, 50), evaluate using silhouette scores and manual inspection of canonical SVGs in dev mode, select the value that produces interpretable clusters. Store the chosen parameter in the cluster provenance record.
- Each cluster = a discovered motif category (spirals, concentric circles, crosses, etc.)
- Clusters are not predefined — they emerge from the data
- For each cluster:
  - Assign an auto-generated label based on the most common text motif tags among member artifacts
  - Compute centroid embedding
  - **Generate canonical SVG:** Primary method: select the medoid (member whose embedding is closest to the centroid) and use its SVG as the canonical representation. This is deterministic and always produces a real motif. Optional experimental variant: normalize member SVGs (center, scale to uniform size), rasterize to same-size bitmaps, average pixel values, threshold to binary, re-trace to SVG via vtracer. The averaged variant may produce blurred results if members have different orientations; the medoid is the safe default.

- Output: `data/similarity/` (adjacency lists) and `data/clusters/` (MotifCluster records with canonical SVGs)

### Stage 7 — Export

`pipeline/stage_7_export.py`

Package for Next.js consumption into `web/public/data/`:

- `sites.json` — all sites with linked artifact counts and motif cluster IDs (lightweight, ~1-2 MB)
- `artifacts/{site_id}.json` — artifacts per site with segment metadata (chunked, lazy-loaded)
- `clusters.json` — all MotifCluster records with member counts and labels
- `svgs/segments/` — individual motif segment SVGs
- `svgs/canonical/` — one canonical SVG per motif cluster (used as map markers)
- `similarity/{segment_id}.json` — similarity edges per segment (chunked, lazy-loaded)
- `provenance/{site_id}.json` — provenance chains per site (chunked, lazy-loaded)
- Size budget: total `web/public/data/` should stay under 50 MB for viable GitHub Pages hosting. If exceeded, Stage 7 applies filters in priority order: (1) reduce similarity edges to top-5 per segment, (2) drop segments without SVGs, (3) subsample segments per cluster to top-50 by centroid proximity, (4) drop smallest clusters.

## Next.js Static App

### Pages

```
app/
  page.tsx                    # Map view (default)
  artifacts/[id]/page.tsx     # Artifact detail with segments
  sites/[id]/page.tsx         # Site detail with linked artifacts
  clusters/[id]/page.tsx      # Motif cluster detail — canonical SVG, member segments, geographic spread
  similarity/page.tsx         # Similarity explorer
```

### Map View

- **MapLibre GL** (open source, no API key needed)
- Sites rendered as clusters at zoom-out, individual markers at zoom-in
- **Canonical motif SVGs as map markers** — each site's dominant motif cluster determines its marker icon
- Color coding by region or motif cluster (user toggle)
- Filter panel: region, period, motif cluster, data source
- Click marker: sidebar with site info, artifact thumbnails, motif segment SVGs

### Artifact Detail

- Artifact image with motif segments highlighted (bounding boxes overlaid)
- Each segment: cropped view + traced SVG side by side
- Cluster assignment per segment with link to cluster page
- Full provenance chain displayed
- "Similar motifs" grid from precomputed similarity index

### Motif Cluster Detail

- Canonical SVG displayed prominently
- Grid of member segments showing the variety within the cluster
- Geographic distribution map — where does this motif appear?
- Timeline showing temporal distribution of the motif
- Links to similar clusters

### Similarity Explorer

- Select a motif segment or cluster
- Map highlights all similar motifs with arcs/lines connecting sites
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
    config.py                    # API keys, rate limits, thresholds, PIPELINE_MODE
    provenance.py                # Shared provenance utilities
    models.py                    # Data model classes
    api_client.py                # Cached API client base
    dedup.py                     # Deduplication logic
    harvesters/
      __init__.py
      wikidata.py
      met.py
      british_museum.py
      harvard.py
      wikimedia_commons.py
    stage_1_site_matching.py
    stage_2_artifact_harvest.py
    stage_3_image_collection.py
    stage_4_segmentation.py      # CLIPSeg motif extraction
    stage_5_embedding.py         # CLIP embeddings + text tagging
    stage_6_similarity.py        # Similarity + HDBSCAN clustering + canonical SVGs
    stage_7_export.py
    run.py                       # Pipeline orchestrator
    requirements.txt

  data/                          # Pipeline outputs (gitignored)
    raw/
      places.json                # Original scraped data
      wikidata/                  # Cached API responses
      met_museum/
      british_museum/
      harvard/
      wikimedia_commons/
    sites/                       # Enriched site records
    artifacts/                   # Artifact records with provenance
    images/                      # Downloaded artifact images (dev mode only)
    segments/                    # Cropped motif segments (dev mode only)
    svgs/                        # Traced SVGs (always kept)
    embeddings/                  # CLIP vectors (.npz)
    similarity/                  # Precomputed similarity graph
    clusters/                    # MotifCluster records + canonical SVGs
    manifests/                   # Stage run logs

  web/                           # Next.js app
    public/data/                 # Stage 7 export target
    src/
      app/
      components/
        Map.tsx
        ArtifactCard.tsx
        MotifSegmentView.tsx
        ClusterCard.tsx
        SimilarityView.tsx
        ProvenanceChain.tsx
        FilterPanel.tsx
      lib/
        data.ts                  # Static data loading utilities
        types.ts                 # TypeScript type definitions
    next.config.js
    package.json

  docs/
    superpowers/specs/
    superpowers/plans/

  pyproject.toml
  tests/
```

`data/` is gitignored (too large). `web/public/data/` contains the exported subset for the static app.

## Key Design Decisions

1. **Provenance-first:** every record, segment, embedding, and transformation carries a full provenance chain back to its source. Non-negotiable for academic credibility.
2. **Segment, don't embed whole images:** CLIPSeg isolates motif regions before CLIP embedding. This compares motif-to-motif, not photo-to-photo, dramatically improving similarity quality.
3. **Emergent taxonomy:** motif categories are discovered by HDBSCAN clustering, not predefined. The data tells us what patterns repeat across cultures.
4. **Canonical SVGs from averaging:** each cluster gets a "platonic" SVG generated by averaging member SVGs. These serve as map markers and visual taxonomy entries.
5. **Dev/production modes:** dev saves everything for visual QA; production saves only embeddings + SVGs + metadata for scale.
6. **Static output:** the pipeline produces static JSON, SVG, and NPZ files. No runtime database or backend. Deployment is trivial (GitHub Pages) and data is reproducible.
7. **CLIPSeg over SAM:** uses CLIPSeg for segmentation instead of Meta's SAM, avoiding Facebook/Meta model gating requirements. CLIPSeg is also semantically guided (segments "decorative motifs" specifically, not arbitrary regions).
8. **All artifact types:** no medium filter. Cave art, reliefs, pottery, mosaics, seals, textiles — anything with a decorative motif.
9. **Idempotent stages:** each pipeline stage can be re-run safely. Manifests track what was processed.
10. **Multi-source deduplication:** artifacts appearing in multiple APIs are merged, with all source provenance preserved.

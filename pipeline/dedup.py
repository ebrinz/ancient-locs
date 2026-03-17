"""Artifact deduplication across multiple sources."""

import logging

from Levenshtein import distance as levenshtein_distance

from pipeline.config import SITE_NAME_FUZZY_THRESHOLD
from pipeline.models import Artifact

logger = logging.getLogger(__name__)

SOURCE_PRIORITY: dict[str, int] = {
    "wikidata": 5,
    "met_museum": 4,
    "harvard": 3,
    "british_museum": 2,
    "wikimedia_commons": 1,
}


def _dates_overlap(a: Artifact, b: Artifact) -> bool:
    """Return True if date ranges overlap or either endpoint is None."""
    if (a.date_range_start is None or a.date_range_end is None
            or b.date_range_start is None or b.date_range_end is None):
        return True
    return a.date_range_start <= b.date_range_end and b.date_range_start <= a.date_range_end


def _is_dup(a: Artifact, b: Artifact, threshold: int = SITE_NAME_FUZZY_THRESHOLD) -> bool:
    """Return True if a and b are duplicates.

    Criteria: same site_id, overlapping dates, and Levenshtein distance
    between names is at or below the threshold.
    """
    if a.site_id != b.site_id:
        return False
    if not _dates_overlap(a, b):
        return False
    return levenshtein_distance(a.name.lower(), b.name.lower()) <= threshold


def _priority(artifact: Artifact) -> int:
    """Return the maximum source priority across all provenance records."""
    if not artifact.provenance:
        return 0
    return max(
        SOURCE_PRIORITY.get(p.source_id, 0)
        for p in artifact.provenance
    )


def deduplicate_artifacts(artifacts: list[Artifact]) -> list[Artifact]:
    """Deduplicate artifacts by merging duplicates into higher-priority records.

    Sorts by source priority descending, then greedily merges: each new
    artifact is compared against already-kept artifacts; if it is a duplicate,
    its provenance records are appended to the existing one.  Otherwise it is
    kept as a new unique artifact.
    """
    sorted_arts = sorted(artifacts, key=_priority, reverse=True)

    merged: list[Artifact] = []
    for art in sorted_arts:
        matched = False
        for kept in merged:
            if _is_dup(kept, art):
                kept.provenance.extend(art.provenance)
                logger.debug("Merged duplicate %s into %s", art.id, kept.id)
                matched = True
                break
        if not matched:
            merged.append(art)

    logger.info("Dedup: %d -> %d artifacts", len(artifacts), len(merged))
    return merged

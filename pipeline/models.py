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
            id=raw["id"], name=raw.get("name"),
            other_names=raw.get("other_names"), modern_names=raw.get("modern_names"),
            region=raw.get("region", ""), section=raw.get("section"),
            latitude=parse_coordinate(raw.get("latitude", "0 N")),
            longitude=parse_coordinate(raw.get("longitude", "0 E")),
            status=raw.get("status", ""), info=raw.get("info"), sources=raw.get("sources"),
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

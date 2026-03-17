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

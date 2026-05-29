import hashlib
import json
import logging
from datetime import datetime, timezone
from src.utils.s3_client import get_minio_client

logger = logging.getLogger(__name__)

MANIFEST_BUCKET = "bronze"
MANIFEST_KEY = "manifest.json"

def compute_sha256(file_path: str) -> str:
    """Compute SHA-256 hash for unique filenames in minIO storage"""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _load_manifest(client) -> list:
    """Load existing manifest from MinIO or return empty list."""
    try:
        response = client.get_object(Bucket=MANIFEST_BUCKET, Key=MANIFEST_KEY)
        return json.loads(response["Body"].read().decode("utf-8"))
    except client.exceptions.NoSuchKey:
        return []


def _save_manifest(client, entries: list) -> None:
    """Save manifest back to MinIO."""
    client.put_object(
        Bucket=MANIFEST_BUCKET,
        Key=MANIFEST_KEY,
        Body=json.dumps(entries, indent=2).encode("utf-8"),
        ContentType="application/json"
    )


def append_manifest_entry(
    source: str,
    source_url: str,
    filename: str,
    minio_path: str,
    row_count: int,
    sha256: str,
    skipped: bool = False
) -> None:
    """Append a new ingestion run entry to the manifest."""
    client = get_minio_client()

    entry = {
        "source": source,
        "source_url": source_url,
        "filename": filename,
        "minio_path": minio_path,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "row_count": row_count,
        "sha256": sha256,
        "skipped": skipped
    }

    entries = _load_manifest(client)
    entries.append(entry)
    _save_manifest(client, entries)
    logger.info(f"Manifest updated — total entries: {len(entries)}")
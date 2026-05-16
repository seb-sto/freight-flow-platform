import hashlib
from pathlib import Path

def compute_sha256(file_path: str) -> str:
    """Compute SHA-256 hash for unique filenames in minIO storage"""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexidigest()
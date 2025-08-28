import os, shutil, hashlib
from pathlib import Path

# TODO: Change to S3 later (local now)

def ensure_dir(p: str):
    Path(p).mkdir(parents=True, exist_ok=True)

def checksum(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def write_text(path: str, text: str):
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
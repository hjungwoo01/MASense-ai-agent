import os, yaml, shutil, hashlib
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import requests

from lib.pdf_utils import pdf_to_markdown

def _ensure_dir(p: str): Path(p).mkdir(parents=True, exist_ok=True)

def _checksum(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def _download(url: str, dest: str):
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    with open(dest, "wb") as f:
        f.write(r.content)

def run(pipeline_cfg: str):
    """
    Ingest:
      - If ingest.offline_only=true: copy PDFs from configs/seed_docs/.
      - Else: download from ingest.sources[].url
    Also converts any PDFs to markdown and stores them in parsed/YYYY-MM-DD/.
    Returns: {"raw_dir": ..., "parsed_dir": ...}
    """
    with open(pipeline_cfg, "r") as f:
        cfg = yaml.safe_load(f)

    raw_root = cfg["paths"]["raw_dir"]
    parsed_root = cfg["paths"]["parsed_dir"]
    _ensure_dir(raw_root); _ensure_dir(parsed_root)

    date_tag = datetime.utcnow().strftime("%Y-%m-%d")
    raw_out = os.path.join(raw_root, date_tag)
    parsed_out = os.path.join(parsed_root, date_tag)
    _ensure_dir(raw_out); _ensure_dir(parsed_out)

    sources = cfg.get("ingest", {}).get("sources", [])
    offline_only = cfg.get("ingest", {}).get("offline_only", True)
    seed_dir = cfg.get("ingest", {}).get("seed_dir", "configs/seed_docs")

    # 1) Acquire PDFs (copy or download)
    pdf_paths = []
    if offline_only:
        if os.path.isdir(seed_dir):
            for name in os.listdir(seed_dir):
                src = os.path.join(seed_dir, name)
                if not os.path.isfile(src): continue
                dst = os.path.join(raw_out, name)
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
                if name.lower().endswith(".pdf"):
                    pdf_paths.append(dst)
        else:
            print(f"[ingest_docs] No seed dir at {seed_dir}; creating placeholders.")
    else:
        for s in sources:
            url = s.get("url")
            if not url: continue
            filename = os.path.basename(urlparse(url).path) or "doc.pdf"
            dst = os.path.join(raw_out, filename)
            if not os.path.exists(dst):
                _download(url, dst)
            if filename.lower().endswith(".pdf"):
                pdf_paths.append(dst)

    # 2) Convert PDFs → markdown into parsed_out
    converted = 0
    for pdf in pdf_paths:
        name = os.path.splitext(os.path.basename(pdf))[0] + ".md"
        md_path = os.path.join(parsed_out, name)
        if not os.path.exists(md_path):
            try:
                md = pdf_to_markdown(pdf)
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(md)
                converted += 1
            except Exception as e:
                print(f"[ingest_docs] PDF parse failed {pdf}: {e}")

    print(f"[ingest_docs] raw={raw_out} parsed={parsed_out} pdfs={len(pdf_paths)} converted={converted}")
    return {"raw_dir": raw_out, "parsed_dir": parsed_out}

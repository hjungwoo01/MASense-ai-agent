import os, yaml, json, glob, re, argparse
from pathlib import Path

HEADING_RE = re.compile(r"^##\s+(\d+(\.\d+)*)\s+(.+)$")
CLAUSE_ID_RE = re.compile(r"\b(GFIT|MAS|ENRM|DNSH|MSS)[-\w\.]*\b", re.IGNORECASE)

def _ensure_dir(p: str): Path(p).mkdir(parents=True, exist_ok=True)

def _iter_md_files(preferred_dir: str, fallback_dir: str):
    md_files = sorted(glob.glob(os.path.join(preferred_dir, "*.md")))
    if md_files:
        return md_files
    return sorted(glob.glob(os.path.join(fallback_dir, "*.md")))

def _estimate_tokens(text: str) -> int:
    words = len(text.split())
    return int(words / 0.75) if words else 0

def _flush_chunk(buf_lines, doc_meta, out, max_tokens):
    if not buf_lines:
        return
    text = "\n".join(buf_lines).strip()
    if not text:
        return
    chunk = {
        "id": len(out),
        "text": text,
        "meta": {**doc_meta},
    }
    
    m = CLAUSE_ID_RE.search(text)
    if m:
        chunk["meta"]["clause_id"] = m.group(0).upper()
    out.append(chunk)
    buf_lines.clear()

def _chunk_markdown_doc(path: str, max_tokens: int, overlap_tokens: int):
    """
    Clause-aware chunking:
      - Start new chunk at headings (## 1.2.3 Title) or when token budget exceeded.
      - Try to keep clause IDs inside a single chunk.
      - Add overlap across chunk boundaries for retriever context.
    """
    out = []
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    doc_meta = {
        "source_path": path,
        "source_name": os.path.basename(path),
    }

    buf, buf_tokens = [], 0
    for i, line in enumerate(lines):
        start_new = HEADING_RE.match(line) is not None

        if start_new:
            _flush_chunk(buf, doc_meta, out, max_tokens)
            buf_tokens = 0
            buf = [line]
            buf_tokens = _estimate_tokens(line)
            continue

        line_tokens = _estimate_tokens(line)
        if buf_tokens + line_tokens > max_tokens:
            _flush_chunk(buf, doc_meta, out, max_tokens)
            if out:
                tail = out[-1]["text"].split()
                if overlap_tokens > 0 and len(tail) > overlap_tokens:
                    overlap = " ".join(tail[-overlap_tokens:])
                    buf = [overlap]
                    buf_tokens = _estimate_tokens(overlap)
                else:
                    buf, buf_tokens = [], 0
            else:
                buf, buf_tokens = [], 0

        buf.append(line)
        buf_tokens += line_tokens

    _flush_chunk(buf, doc_meta, out, max_tokens)

    for ch in out:
        if "clause_id" not in ch["meta"]:
            m = CLAUSE_ID_RE.search(ch["text"])
            if m:
                ch["meta"]["clause_id"] = m.group(0).upper()

    return out

def run(pipeline_cfg: str):
    with open(pipeline_cfg, "r") as f:
        cfg = yaml.safe_load(f)

    paths = cfg["paths"]
    parsed_root = paths["parsed_dir"]
    raw_root = paths["raw_dir"]
    chunks_dir = paths["chunks_dir"]
    _ensure_dir(chunks_dir)

    parsed_dates = sorted(glob.glob(os.path.join(parsed_root, "*")))
    raw_dates = sorted(glob.glob(os.path.join(raw_root, "*")))
    if not parsed_dates and not raw_dates:
        raise RuntimeError("No input docs. Run ingest_docs first.")
    parsed_latest = parsed_dates[-1] if parsed_dates else ""
    raw_latest = raw_dates[-1] if raw_dates else ""

    md_files = _iter_md_files(parsed_latest, raw_latest)
    if not md_files:
        raise RuntimeError("No markdown files found in parsed/ or raw/.")

    max_tokens = int(cfg.get("chunking", {}).get("max_tokens", 1600))
    overlap_tokens = int(cfg.get("chunking", {}).get("overlap_tokens", 220))

    all_chunks = []
    for md in md_files:
        chunks = _chunk_markdown_doc(md, max_tokens=max_tokens, overlap_tokens=overlap_tokens)
        all_chunks.extend(chunks)

    out_path = os.path.join(chunks_dir, "chunks.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    print(f"[chunk_docs] {len(md_files)} files → chunks={len(all_chunks)} -> {out_path}")
    return {"chunks_path": out_path, "files": md_files}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yml")
    ap.add_argument("--ingest-first", action="store_true",
                    help="Run PDF parsing (parser/pdf_parser.py) before chunking")
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text())
    paths = cfg["paths"]

    if args.ingest_first:
        from parser.pdf_parser import docs_to_md
        from parser.pdf_parser import parsing_instruction as PARSE_INSTR
        docs_to_md(
            raw_dir=paths["raw_dir"],
            parsed_dir=paths["parsed_dir"],
            parsing_instructions=PARSE_INSTR,
            result_type="text",
            verbose=True,
        )

    run(args.config)

if __name__ == "__main__":
    main()

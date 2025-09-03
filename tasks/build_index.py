import os, yaml, json
from pathlib import Path

def _ensure_dir(p: str): Path(p).mkdir(parents=True, exist_ok=True)

def run(pipeline_cfg: str):
    """
    Build a trivial 'index' cache (vector/BM25 can be added later).
    Writes chunks_cache.jsonl for fast retrieval by the agent service.
    """
    with open(pipeline_cfg, "r") as f:
        cfg = yaml.safe_load(f)

    chunks_path = os.path.join(cfg["paths"]["chunks_dir"], "chunks.jsonl")
    if not os.path.exists(chunks_path):
        raise RuntimeError("Chunks not found. Run chunk_docs first.")

    index_dir = cfg["paths"]["index_dir"]
    _ensure_dir(index_dir)
    cache_path = os.path.join(index_dir, "chunks_cache.jsonl")

    with open(chunks_path, "r", encoding="utf-8") as src, open(cache_path, "w", encoding="utf-8") as dst:
        for line in src:
            json.loads(line)
            dst.write(line)

    print(f"[build_index] index cache -> {cache_path}")
    return {"index_ready": True, "index_cache": cache_path}

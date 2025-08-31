import os, yaml, json
from collections import Counter
from pathlib import Path
from datetime import datetime

def _ensure_dir(p: str): Path(p).mkdir(parents=True, exist_ok=True)

def _rollup(items):
    labels = Counter([(i.get("result", {}).get("decision", {}) or {}).get("label","Unknown") for i in items])
    total = sum(labels.values()) or 1
    pct = {k: round(v*100/total, 1) for k,v in labels.items()}
    return {"counts": dict(labels), "percent": pct, "total": total}

def run(pipeline_cfg: str):
    """
    Aggregate decisions.jsonl into a single report.json (for Streamlit to download).
    """
    with open(pipeline_cfg, "r") as f:
        cfg = yaml.safe_load(f)
    p = cfg["paths"]

    decisions_path = os.path.join(p["decisions_dir"], "decisions.jsonl")
    if not os.path.exists(decisions_path):
        raise RuntimeError("decisions.jsonl not found. Run classify_actions first.")

    items = [json.loads(l) for l in open(decisions_path, "r", encoding="utf-8").read().splitlines()]
    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "policy_version": cfg.get("policy_version","mock-v1"),
        "summary": _rollup(items),
        "items": items[:100],  # truncate for size
    }

    _ensure_dir(p["decisions_dir"])
    out_path = os.path.join(p["decisions_dir"], "report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"[generate_report] report -> {out_path}")
    return {"report_path": out_path}

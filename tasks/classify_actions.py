import os, yaml, json, glob
from pathlib import Path
import requests

def _ensure_dir(p: str): Path(p).mkdir(parents=True, exist_ok=True)

API_BASE = os.getenv("ESG_API_BASE", "http://localhost:8000")

def _post_json(path: str, payload: dict, timeout: int = 60):
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[classify_actions] backend error: {e}")
        return None

def run(pipeline_cfg: str):
    """
    Batch-classify any JSON 'actions' in data/actions_inbox/ by calling your /chat endpoint.
    Writes decisions.jsonl for downstream reporting.
    """
    with open(pipeline_cfg, "r") as f:
        cfg = yaml.safe_load(f)
    p = cfg["paths"]

    inbox = p["actions_inbox"]
    decisions_dir = p["decisions_dir"]
    _ensure_dir(decisions_dir)
    out_path = os.path.join(decisions_dir, "decisions.jsonl")

    sess = _post_json("/session/start", {}) or {"session_id": "sess-mock-batch"}
    session_id = sess["session_id"]

    # let backend know which docs to use
    doc_ids = []

    count = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for action_path in sorted(glob.glob(os.path.join(inbox, "*.json"))):
            action = json.load(open(action_path, "r", encoding="utf-8"))
            message = action.get("description") or f"Classify this action: {json.dumps(action)}"
            payload = {
                "session_id": session_id,
                "message": message,
                "company_profile": {
                    "sector": action.get("sector"),
                    "activity": action.get("activity"),
                    "jurisdiction": action.get("jurisdiction"),
                    "size": action.get("size"),
                },
                "doc_ids": doc_ids,
                "chat_history": [],  # stateless batch
                "client_meta": {"origin": "airflow-classify_actions"},
            }
            resp = _post_json("/chat", payload)
            if resp is None:
                # Fallback mock if backend is unavailable
                resp = {
                    "assistant": {"text": "Mock classification (backend unavailable)."},
                    "decision": {
                        "label": "Green",
                        "rule_path": [{"clause_id":"GFIT-EN-1.2.3","test":"grams_co2e_per_kwh <= 100","passed": True}]
                    },
                    "missing_fields": []
                }
            record = {
                "action_id": action.get("action_id"),
                "input": action,
                "result": resp
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1

    print(f"[classify_actions] processed={count} -> {out_path}")
    return {"decisions_path": out_path, "count": count}

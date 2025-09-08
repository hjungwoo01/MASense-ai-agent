from typing import Dict, Any
from datetime import datetime
import logging
import json
import os

logger = logging.getLogger(__name__)

PERSIST_REPORTS = os.getenv("PERSIST_EVAL_REPORTS", "false").lower() in {"1", "true", "yes"}
REPORT_DIR = os.getenv("EVAL_REPORT_DIR", "evaluations")

def emit_artifacts(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate evaluation artifacts for the UI / API.
    Optionally persists a JSON report if PERSIST_REPORTS is enabled.
    """
    try:
        if state.get("status") == "error":
            return state

        context = state.get("context", {}) or {}
        evaluation = state.get("evaluation", {}) or {}
        explanation = state.get("explanation", {}) or {}

        if not evaluation:
            errs = list(state.get("errors", [])) + ["No evaluation results to process"]
            return {**state, "status": "error", "errors": errs}

        artifacts = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": context.get("action", state.get("action", {})) or {},
            "organization": context.get("organization", {}) or {},
            "evaluation": evaluation,
            "explanation": explanation,
            "recommendations": explanation.get("recommendations", []),
        }

        if PERSIST_REPORTS:
            try:
                os.makedirs(REPORT_DIR, exist_ok=True)
                fname = f"{evaluation.get('classification','Unknown')}_{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.json"
                path = os.path.join(REPORT_DIR, fname)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(artifacts, f, ensure_ascii=False, indent=2)
                artifacts["report_path"] = path
            except Exception as io_err:
                logger.warning("[emit_artifacts] Failed to persist report: %s", io_err)

        return {**state, "status": "success", "artifacts": artifacts}

    except Exception as e:
        logger.exception("[emit_artifacts] Unexpected error")
        errs = list(state.get("errors", [])) + [f"Error generating artifacts: {e}"]
        return {**state, "status": "error", "errors": errs}
    
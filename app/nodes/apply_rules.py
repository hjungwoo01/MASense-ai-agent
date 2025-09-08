from typing import Dict, Any, List
import logging
import re

logger = logging.getLogger(__name__)

_TRAFFIC_PATTERNS = {
    "Green": re.compile(r"\bGreen\b", re.IGNORECASE),
    "Amber": re.compile(r"\bAmber\b", re.IGNORECASE),
    "Ineligible": re.compile(r"\bIneligible\b", re.IGNORECASE),
}

def _normalize_clause_text(clause: Any) -> str:
    if isinstance(clause, str):
        return clause
    if isinstance(clause, dict):
        return clause.get("content") or clause.get("text") or str(clause)
    return str(clause)

def parse_traffic_light_from_clause(clause: Any) -> Dict[str, Any]:
    text = _normalize_clause_text(clause)
    traffic_light = None
    matched_criteria: List[str] = []

    for label, pattern in _TRAFFIC_PATTERNS.items():
        if pattern.search(text):
            traffic_light = label
            if label == "Green":
                matched_criteria.append("Meets Green criteria")
            elif label == "Amber":
                matched_criteria.append("Falls under Amber transition criteria")
            elif label == "Ineligible":
                matched_criteria.append("Fails eligibility criteria")

    low = text.lower()
    if ("impact assessment" in low) or (" eia" in low) or low.startswith("eia"):
        matched_criteria.append("Environmental Impact Assessment required")
    if "biodiversity" in low:
        matched_criteria.append("Biodiversity safeguards required")
    if "water" in low:
        matched_criteria.append("Water conservation plan required")
    if ("waste" in low) or ("recycling" in low):
        matched_criteria.append("Waste management/recycling plan required")

    return {"traffic_light": traffic_light, "criteria": matched_criteria}


def apply_rules(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply MAS traffic-light rules to classify the action based on retrieved clauses.
    Always sets state['evaluation'].
    """
    try:
        ctx = state.get("context", {}) or {}
        action = ctx.get("action", {}) or {}
        clauses = ctx.get("clauses", []) or []

        logger.info("[apply_rules] Evaluating sector=%s activity=%s",
                    action.get("sector"), action.get("activity"))

        all_criteria: List[str] = []
        detected_labels: List[str] = []

        for clause in clauses:
            parsed = parse_traffic_light_from_clause(clause)
            if parsed["traffic_light"]:
                detected_labels.append(parsed["traffic_light"])
            all_criteria.extend(parsed["criteria"])

        seen = set()
        dedup_criteria: List[str] = []
        for c in all_criteria:
            if c not in seen:
                seen.add(c)
                dedup_criteria.append(c)

        classification = None
        if detected_labels:
            if "Ineligible" in detected_labels:
                classification = "Ineligible"
            elif "Amber" in detected_labels:
                classification = "Amber"
            elif "Green" in detected_labels:
                classification = "Green"

        if not classification:
            if any("biodiversity" in c.lower() for c in dedup_criteria):
                classification = "Amber"
            else:
                classification = "Green" if clauses else "Ineligible"

        evaluation = {
            "classification": classification,
            "matched_criteria": dedup_criteria,
            "required_documentation": [c for c in dedup_criteria if "required" in c.lower()],
        }

        return {**state, "status": "success", "evaluation": evaluation}

    except Exception as e:
        error_msg = f"Error in apply_rules: {e}"
        logger.exception(error_msg)
        errs = list(state.get("errors", [])) + [error_msg]
        fallback_eval = {
            "classification": "Unknown",
            "matched_criteria": [],
            "required_documentation": []
        }
        return {**state, "status": "success", "errors": errs, "evaluation": fallback_eval}

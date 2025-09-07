from typing import Dict, Any, List
import logging
import re

logger = logging.getLogger(__name__)

def parse_traffic_light_from_clause(clause: str) -> Dict[str, Any]:
    """
    Try to detect explicit MAS taxonomy traffic-light classification
    (Green / Amber / Ineligible) from retrieved clause text.
    """
    traffic_light = None
    matched_criteria = []

    # Look for explicit table rows or keywords
    if re.search(r"\bGreen\b", clause, re.IGNORECASE):
        traffic_light = "Green"
        matched_criteria.append("Meets Green criteria")

    if re.search(r"\bAmber\b", clause, re.IGNORECASE):
        traffic_light = "Amber"
        matched_criteria.append("Falls under Amber transition criteria")

    if re.search(r"Ineligible", clause, re.IGNORECASE):
        traffic_light = "Ineligible"
        matched_criteria.append("Fails eligibility criteria")

    # Also check for common requirements in DNSH or TSC
    if "impact assessment" in clause.lower() or "EIA" in clause:
        matched_criteria.append("Environmental Impact Assessment required")
    if "biodiversity" in clause.lower():
        matched_criteria.append("Biodiversity safeguards required")
    if "water" in clause.lower():
        matched_criteria.append("Water conservation plan required")
    if "waste" in clause.lower() or "recycling" in clause.lower():
        matched_criteria.append("Waste management/recycling plan required")

    return {"traffic_light": traffic_light, "criteria": matched_criteria}


def apply_rules(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply MAS traffic-light rules to classify the action based on retrieved clauses.
    """
    try:
        context = state.get("context", {})
        action = context.get("action", {})
        clauses = context.get("clauses", [])

        logger.info(f"[apply_rules] Evaluating action in sector={action.get('sector')}")

        all_criteria = []
        detected_labels = []

        for clause in clauses:
            parsed = parse_traffic_light_from_clause(clause)
            if parsed["traffic_light"]:
                detected_labels.append(parsed["traffic_light"])
            if parsed["criteria"]:
                all_criteria.extend(parsed["criteria"])

        # Deduplicate
        all_criteria = list(set(all_criteria))

        # Final classification:
        # 1. If at least one explicit MAS label was retrieved → pick the "worst case" (Ineligible > Amber > Green)
        classification = None
        if detected_labels:
            if "Ineligible" in detected_labels:
                classification = "Ineligible"
            elif "Amber" in detected_labels:
                classification = "Amber"
            elif "Green" in detected_labels:
                classification = "Green"

        # 2. Fallback if no explicit label found
        if not classification:
            if "Biodiversity" in " ".join(all_criteria):
                classification = "Amber"
            else:
                classification = "Green" if clauses else "Ineligible"

        evaluation = {
            "classification": classification,
            "matched_criteria": all_criteria,
            "required_documentation": [
                crit for crit in all_criteria if "required" in crit.lower()
            ]
        }

        return {
            **state,
            "status": "success",
            "evaluation": evaluation
        }

    except Exception as e:
        error_msg = f"Error in apply_rules: {str(e)}"
        logger.exception(error_msg)
        return {**state, "status": "error", "errors": [error_msg]}

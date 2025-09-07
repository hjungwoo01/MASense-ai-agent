from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

RULESET_PATH = "mas_ruleset.json"

def apply_rules(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply MAS taxonomy rules to the financial action.
    """
    try:
        action = state["context"]["action"]
        clauses = state["context"].get("clauses", [])
        sector = action.get("sector")

        # Load MAS ruleset
        try:
            with open(RULESET_PATH, "r") as f:
                ruleset = json.load(f)
        except FileNotFoundError:
            return {**state, "status": "error", "errors": ["MAS ruleset not found"]}

        sector_rules = ruleset.get(sector, {})
        matched = []

        # Match clauses to sector rules
        for rule in sector_rules.get("criteria", []):
            if any(keyword.lower() in action["description"].lower()
                   for keyword in rule.get("keywords", [])):
                matched.append(rule)

        if matched:
            classification = "Green"
            docs = [m.get("required_docs", "Supporting evidence") for m in matched]
        else:
            classification = "Amber"
            docs = ["Additional information required"]

        return {
            **state,
            "status": "success",
            "evaluation": {
                "classification": classification,
                "matched_criteria": matched,
                "required_documentation": docs
            }
        }

    except Exception as e:
        logger.exception("Error in apply_rules")
        return {**state, "status": "error", "errors": [str(e)]}

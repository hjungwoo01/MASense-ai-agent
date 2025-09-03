from typing import Dict, Any
import json
import os
import logging

logger = logging.getLogger(__name__)

def retrieve_clauses(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve relevant MAS framework clauses based on the action's industry.
    """
    try:
        context = state.get("context", {})
        org = context.get("organization", {})
        action = context.get("action", {})

        industry = org.get("industry", "").lower()

        if not industry:
            return {
                **state,
                "status": "error",
                "errors": ["Industry is missing from organization context"]
            }

        # Load MAS ruleset (JSON file)
        ruleset_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "mas_ruleset.json"
        )

        with open(ruleset_path, "r") as f:
            rules = json.load(f)

        if industry not in rules:
            return {
                **state,
                "status": "error",
                "errors": [f"No rules found for industry: {industry}"]
            }

        # ✅ Extract sector metadata
        sector_info = rules[industry]
        criteria = sector_info.get("criteria", [])
        objectives = sector_info.get("objectives", [])

        logger.debug(f"[retrieve_clauses] Found {len(criteria)} criteria for industry: {industry}")

        return {
            **state,
            "status": "success",
            "context": {
                **context,
                "clauses": criteria,
                "sector_objectives": objectives,
            }
        }

    except Exception as e:
        error_msg = f"Error retrieving clauses: {str(e)}"
        logger.exception(error_msg)
        return {
            **state,
            "status": "error",
            "errors": [error_msg]
        }

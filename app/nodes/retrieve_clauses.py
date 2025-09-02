from typing import Dict, Any
import json
import os
import logging

logger = logging.getLogger(__name__)

def retrieve_clauses(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve relevant MAS framework clauses based on the action
    """
    try:
        context = state.get("context", {})
        action = context.get("action", {})
        org = context.get("organization", {})
        
        if not action or not org:
            return {
                **state,
                "status": "error",
                "errors": ["Missing action or organization context"]
            }
            
        # Load MAS ruleset
        ruleset_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "mas_ruleset.json")
        try:
            with open(ruleset_path, "r") as f:
                ruleset = json.load(f)
        except FileNotFoundError:
            logger.warning("MAS ruleset not found, using default classification logic")
            ruleset = {
                "sectors": {
                    "Energy": {
                        "green": ["solar", "wind", "renewable"],
                        "amber": ["efficiency", "upgrade"]
                    },
                    "Real Estate": {
                        "green": ["energy efficiency", "renewable energy"],
                        "amber": ["renovation", "upgrade"]
                    }
                }
            }

        # Extract relevant clauses based on industry
        industry = org.get("industry", "")
        sector_rules = ruleset.get("sectors", {}).get(industry, {})
        
        if not sector_rules:
            return {
                **state,
                "status": "error",
                "errors": [f"No rules found for industry: {industry}"]
            }
        
        return {
            **state,
            "status": "success",
            "context": {
                **context,
                "rules": {
                    "sector": industry,
                    "clauses": sector_rules
                }
            }
        }
            
    except Exception as e:
        error_msg = f"Error retrieving clauses: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "status": "error",
            "errors": [error_msg]
        }

        if sector not in ruleset:
            return {
                **state,
                "status": "error",
                "errors": [f"Sector {sector} not found in MAS ruleset"]
            }
            
        # Get sector criteria
        criteria = ruleset[sector]["criteria"]
        
        # Find relevant criteria based on activity
        relevant_criteria = []
        for criterion in criteria:
            if (action["activity"].lower() in criterion["activity"].lower() or
                any(example.lower() in action["description"].lower() 
                    for example in criterion["examples"])):
                relevant_criteria.append(criterion)
        
        return {
            **state,
            "status": "clauses_retrieved",
            "context": {
                "relevant_criteria": relevant_criteria,
                "sector_objectives": ruleset[sector]["objectives"]
            }
        }
        
    except Exception as e:
        return {
            **state,
            "status": "error",
            "errors": [f"Error retrieving clauses: {str(e)}"]
        }

from typing import Dict, Any, List
import json

def retrieve_clauses(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve relevant MAS framework clauses based on the action
    """
    action = state["action"]
    
    try:
        # Load MAS ruleset
        with open("mas_ruleset.json", "r") as f:
            ruleset = json.load(f)
            
        sector = action["sector"]
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

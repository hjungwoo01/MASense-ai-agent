from typing import Dict, Any, List
import json

from ..bedrock_client import BedrockClient

def retrieve_clauses(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve relevant MAS framework clauses based on the action
    """
    action = state["action"]["action"]  # Nested under state["action"]["action"]
    bedrock_client = BedrockClient()
    
    try:
        # Load MAS ruleset
        with open("mas_ruleset.json", "r") as f:
            ruleset = json.load(f)
            
        # If sector is not provided, use Bedrock to analyze the description
        if "sector" not in action:
            # Create a prompt to analyze the description and determine sector
            prompt = f"""Given this financial action description, determine the most appropriate sector from the MAS ruleset:
            
            Description: {action['description']}
            Organization Type: {action['organization']['industry']}
            
            Available sectors: {', '.join(ruleset.keys())}
            
            Return only the sector name that best matches."""
            
            # Get sector from Bedrock
            response = bedrock_client.generate_response(prompt)

            if response["status"] != "success":
                return {
                    **state,
                    "status": "error",
                    "errors": [f"Bedrock failed to classify sector: {response.get('error', 'Unknown error')}"]
                }

            sector = response["content"].strip().lower()
        else:
            sector = action["sector"].lower()

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

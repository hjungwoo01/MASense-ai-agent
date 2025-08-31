from typing import Dict, Any, List
from ..bedrock_client import BedrockClient

def draft_explanation(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate organization-specific detailed explanation of evaluation results
    """
    if state.get("status") in ["error", "no_matching_criteria"]:
        return state
        
    evaluation = state["evaluation"]
    action = state["action"]
    org_context = state["context"]["organization"]
    compliance_level = state["context"]["compliance_level"]
    reporting_reqs = state["context"]["reporting_requirements"]
    
    bedrock = BedrockClient()
    
    prompt = f"""
    Generate a detailed explanation for this sustainability evaluation:
    
    Action: {action['activity']} in {action['sector']} sector
    Amount: {action['amount']} {action.get('currency', 'SGD')}
    Classification: {evaluation['classification']}
    
    Key Points:
    1. Matched Criteria: {evaluation['matched_criteria']}
    2. Suggestions: {evaluation['suggestions']}
    
    Please provide:
    1. Clear rationale for the classification
    2. Impact analysis
    3. Specific improvement recommendations
    4. Compliance pathway
    """
    
    detailed_explanation = bedrock.generate_response(prompt)
    
    return {
        **state,
        "status": "explanation_drafted",
        "explanation": {
            "detailed": detailed_explanation,
            "summary": evaluation["explanation"]
        }
    }

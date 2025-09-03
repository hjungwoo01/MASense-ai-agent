from typing import Dict, Any, List
import logging
from ..bedrock_client import BedrockClient

logger = logging.getLogger(__name__)

def draft_explanation(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate organization-specific detailed explanation of evaluation results
    """
    try:
        if state.get("status") == "error":
            return state
            
        context = state.get("context", {})
        evaluation = state.get("evaluation", {})
        
        if not evaluation:
            return {
                **state,
                "status": "error",
                "errors": ["No evaluation results to explain"]
            }
            
        # Get the action details
        action = context.get("action", {})
        org = context.get("organization", {})
        rules = context.get("rules", {})
        
        if not all([action, org, rules]):
            return {
                **state,
                "status": "error",
                "errors": ["Missing required context for explanation"]
            }
            
        client = BedrockClient()
        
        # Create explanation request
        explanation_request = {
            "description": action.get("description", ""),
            "classification": evaluation.get("classification", ""),
            "organization": org,
            "rules": rules
        }
        
        # Get detailed explanation from Bedrock
        result = client.analyze_financial_action(explanation_request)
        
        if result.get("status") == "error":
            return {
                **state,
                "status": "error",
                "errors": [result.get("error", "Failed to generate explanation")]
            }
            
        return {
            **state,
            "status": "success",
            "explanation": result.get("content", {})
        }
        
    except Exception as e:
        error_msg = f"Error generating explanation: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "status": "error",
            "errors": [error_msg]
        }
    prompt = """   
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

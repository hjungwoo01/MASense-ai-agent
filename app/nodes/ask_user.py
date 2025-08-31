from typing import Dict, Any, List
from ..bedrock_client import BedrockClient

def ask_user(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate clarifying questions if needed
    """
    if state.get("status") == "error":
        return state
        
    # Check if confidence score is too low
    if state["evaluation"]["confidence_score"] < 0.7:
        bedrock = BedrockClient()
        
        prompt = f"""
        Based on this financial action evaluation:
        
        Sector: {state['action']['sector']}
        Activity: {state['action']['activity']}
        Description: {state['action']['description']}
        Current Classification: {state['evaluation']['classification']}
        Confidence Score: {state['evaluation']['confidence_score']}
        
        Generate 2-3 specific questions that would help clarify:
        1. The nature of the activity
        2. Its alignment with MAS frameworks
        3. Implementation details
        
        Format as a JSON list of questions.
        """
        
        questions_response = bedrock.generate_response(prompt)
        try:
            questions = json.loads(questions_response)
        except json.JSONDecodeError:
            questions = ["Could you provide more details about this activity?"]
            
        return {
            **state,
            "status": "needs_clarification",
            "clarifying_questions": questions
        }
    
    return {
        **state,
        "status": "evaluation_complete"
    }

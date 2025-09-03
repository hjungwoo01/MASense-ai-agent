from typing import Dict, Any
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def emit_artifacts(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate evaluation artifacts
    """
    if state.get("status") == "error":
        return state
        
    try:
        context = state.get("context", {})
        evaluation = state.get("evaluation", {})
        explanation = state.get("explanation", {})
        
        if not evaluation:
            return {
                **state,
                "status": "error",
                "errors": ["No evaluation results to process"]
            }
            
        # Create evaluation report
        artifacts = {
            "timestamp": datetime.now().isoformat(),
            "action": context.get("action", {}),
            "organization": context.get("organization", {}),
            "evaluation": evaluation,
            "explanation": explanation,
            "recommendations": explanation.get("recommendations", [])
        }
        
        return {
            **state,
            "status": "success",
            "artifacts": artifacts
        }
        
    except Exception as e:
        error_msg = f"Error generating artifacts: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "status": "error",
            "errors": [error_msg]
        }
    
    
    # Generate unique filename
    filename = f"evaluations/{state['action']['sector']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        # Ensure directory exists
        os.makedirs("evaluations", exist_ok=True)
        
        # Save report
        with open(filename, "w") as f:
            json.dump(report, f, indent=2)
            
        return {
            **state,
            "status": "complete",
            "artifacts": {
                "report_path": filename,
                "report": report
            }
        }
        
    except Exception as e:
        return {
            **state,
            "status": "error",
            "errors": [f"Error saving artifacts: {str(e)}"]
        }

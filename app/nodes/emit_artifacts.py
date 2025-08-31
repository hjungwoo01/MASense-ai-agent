from typing import Dict, Any, List
import json
from datetime import datetime

def emit_artifacts(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate and save evaluation artifacts
    """
    if state.get("status") == "error":
        return state
        
    # Create evaluation report
    report = {
        "timestamp": datetime.now().isoformat(),
        "action": state["action"],
        "evaluation": state["evaluation"],
        "explanation": state.get("explanation", {}),
        "status": state["status"],
        "clarifying_questions": state.get("clarifying_questions", [])
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

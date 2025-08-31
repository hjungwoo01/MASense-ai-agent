from typing import Dict, Any
from langchain.graph import Graph
from nodes import (
    extract_inputs,
    retrieve_clauses,
    apply_rules,
    draft_explanation,
    ask_user,
    emit_artifacts
)

def create_evaluation_graph() -> Graph:
    """
    Create the LangGraph workflow for financial action evaluation
    """
    workflow = Graph()
    
    # Add nodes
    workflow.add_node("extract_inputs", extract_inputs.extract_inputs)
    workflow.add_node("retrieve_clauses", retrieve_clauses.retrieve_clauses)
    workflow.add_node("apply_rules", apply_rules.apply_rules)
    workflow.add_node("draft_explanation", draft_explanation.draft_explanation)
    workflow.add_node("ask_user", ask_user.ask_user)
    workflow.add_node("emit_artifacts", emit_artifacts.emit_artifacts)
    
    # Define edges
    workflow.add_edge("extract_inputs", "retrieve_clauses")
    workflow.add_edge("retrieve_clauses", "apply_rules")
    workflow.add_edge("apply_rules", "draft_explanation")
    workflow.add_edge("draft_explanation", "ask_user")
    workflow.add_edge("ask_user", "emit_artifacts")
    
    return workflow

def evaluate_financial_action(action_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the evaluation workflow for a financial action
    """
    workflow = create_evaluation_graph()
    
    try:
        # Initialize state with action data
        initial_state = {
            "action": action_data,
            "status": "started",
            "errors": [],
            "context": {}
        }
        
        # Execute workflow
        final_state = workflow.execute(initial_state)
        
        return final_state
        
    except Exception as e:
        return {
            "status": "error",
            "errors": [f"Workflow execution failed: {str(e)}"],
            "action": action_data
        }

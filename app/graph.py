from typing import Dict, Any, TypedDict, Annotated, Union
from langgraph.graph import StateGraph, END
import json
from .nodes import (
    extract_inputs,
    retrieve_clauses,
    apply_rules,
    draft_explanation,
    ask_user,
    emit_artifacts
)

# Define our state type
class State(TypedDict):
    action: Dict[str, Any]
    status: str
    errors: list[str]
    context: Dict[str, Any]
    evaluation: Dict[str, Any]
    explanation: Dict[str, Any]
    artifacts: Dict[str, Any]

def should_continue(state: State) -> bool:
    """Determine if we should continue processing or need clarification"""
    return state["status"] not in ["needs_clarification", "error"]

def create_evaluation_graph() -> StateGraph:
    """
    Create the LangGraph workflow for financial action evaluation
    """
    # Initialize the graph
    workflow = StateGraph(State)

    # Add nodes to the graph
    workflow.add_node("extract_inputs", extract_inputs.extract_inputs)
    workflow.add_node("retrieve_clauses", retrieve_clauses.retrieve_clauses)
    workflow.add_node("apply_rules", apply_rules.apply_rules)
    workflow.add_node("draft_explanation", draft_explanation.draft_explanation)
    workflow.add_node("ask_user", ask_user.ask_user)
    workflow.add_node("emit_artifacts", emit_artifacts.emit_artifacts)

    # Define the conditional edges
    workflow.add_edge("extract_inputs", "retrieve_clauses")
    workflow.add_edge("retrieve_clauses", "apply_rules")
    workflow.add_edge("apply_rules", "draft_explanation")
    workflow.add_edge("draft_explanation", "ask_user")
    
    # Add conditional branching
    workflow.add_conditional_edges(
        "ask_user",
        should_continue,
        {
            True: "emit_artifacts",
            False: END  # End if we need clarification
        }
    )
    
    workflow.add_edge("emit_artifacts", END)

    # Set the entry point
    workflow.set_entry_point("extract_inputs")

    return workflow

def evaluate_financial_action(action_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the evaluation workflow for a financial action
    """
    try:
        # Create the workflow
        workflow = create_evaluation_graph()
        
        # Compile the graph
        app = workflow.compile()
        
        # Initialize state
        initial_state: State = {
            "action": action_data,
            "status": "started",
            "errors": [],
            "context": {},
            "evaluation": {},
            "explanation": {},
            "artifacts": {}
        }
        
        # Execute the workflow
        final_state = None
        for state in app.stream(initial_state):
            print(f"Current step: {state.get('status', 'unknown')}")
            if state.get("errors"):
                print(f"Errors encountered: {state['errors']}")
            final_state = state
            
            # If we encounter an error, break early
            if state.get("status") == "error":
                break
                
        return final_state  # Return the final state
        
    except Exception as e:
        return {
            "status": "error",
            "errors": [f"Workflow execution failed: {str(e)}"],
            "action": action_data,
            "context": {},
            "evaluation": {},
            "explanation": {},
            "artifacts": {}
        }

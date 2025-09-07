from typing import Dict, Any
import json
import os
import logging

logger = logging.getLogger(__name__)

def retrieve_clauses(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve relevant MAS framework clauses using RAG.
    """
    try:
        context = state.get("context", {})
        action = context.get("action", {})
        
        # Create search query from action details
        search_query = f"""
        Sector: {action.get('sector', '')}
        Activity: {action.get('activity', '')}
        Description: {action.get('description', '')}
        Amount: {action.get('amount')} {action.get('currency', 'SGD')}
        """
        
        logger.info(f"Retrieving clauses for query: {search_query}")
        
        try:
            from chromadb import Chroma
            # Initialize ChromaDB client
            chroma_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data",
                "chroma"
            )
            db = Chroma(persist_directory=chroma_dir)
            
            # Query for relevant clauses
            results = db.query(
                query_texts=[search_query],
                n_results=5  # Get top 5 most relevant clauses
            )
            
            if not results or not results.get('documents'):
                logger.error("No relevant clauses found in vector store")
                return {
                    **state,
                    "status": "error",
                    "errors": ["No relevant clauses found"]
                }
            
            clauses = results['documents'][0]  # Get the first batch of results
            logger.info(f"Retrieved {len(clauses)} relevant clauses")

            return {
                **state,
                "status": "success",
                "context": {
                    **context,
                    "clauses": clauses,
                    "sector": action.get('sector', ''),
                    "search_query": search_query,
                }
            }
            
        except Exception as e:
            logger.error(f"ChromaDB error: {str(e)}")
            return {
                **state,
                "status": "error",
                "errors": [f"Failed to query vector store: {str(e)}"]
            }

    except Exception as e:
        error_msg = f"Error retrieving clauses: {str(e)}"
        logger.exception(error_msg)
        return {
            **state,
            "status": "error",
            "errors": [error_msg]
        }

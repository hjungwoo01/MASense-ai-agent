from typing import Dict, Any
import os, logging
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)

CHROMA_DB_PATH = "data/chroma"

def retrieve_clauses(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve relevant MAS framework clauses using Chroma RAG,
    with fallback to MAS ruleset if retrieval fails.
    """
    try:
        context = state.get("context", {})
        action = context.get("action", {})

        search_query = (
            f"Sector: {action.get('sector', '')}\n"
            f"Activity: {action.get('activity', '')}\n"
            f"Description: {action.get('description', '')}"
        )
        logger.info(f"[retrieve_clauses] Query: {search_query}")

        # Load embeddings
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

        # Reload persisted Chroma vectorstore
        vectorstore = Chroma(
            persist_directory=CHROMA_DB_PATH,
            embedding_function=embeddings
        )

        # Perform similarity search
        docs = vectorstore.similarity_search(search_query, k=5)

        if not docs:
            logger.warning("[retrieve_clauses] No relevant clauses found, returning empty list.")
            clauses = []
        else:
            clauses = [doc.page_content for doc in docs]
            logger.info(f"[retrieve_clauses] Retrieved {len(clauses)} clauses")

        return {
            **state,
            "status": "success",
            "context": {
                **context,
                "clauses": clauses,
                "search_query": search_query
            }
        }

    except Exception as e:
        error_msg = f"Error in retrieve_clauses: {str(e)}"
        logger.exception(error_msg)
        return {**state, "status": "error", "errors": [error_msg]}

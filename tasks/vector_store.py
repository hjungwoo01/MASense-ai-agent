import os
import json
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document

from typing import List, Dict

JSON_PATH = "data/parsed/parsed_docs.json"
CHROMA_DB_PATH = "data/chroma"

def load_chunks_from_json(json_path: str) -> List[Dict]:
    """
    Loads chunked data from a JSON file.
    """
    if not os.path.exists(json_path):
        print(f"File {json_path} does not exist.")
        return []
    
    with open(json_path, "r", encoding = "utf-8") as f:
        data = json.load(f)

    print(f"Loaded {len(data)} pages from {json_path}.")
    return data

def build_vector_store():
    """
    Builds a Chroma vector store from chunked data.
    """
    
    #1. Load the chunked data from the JSON file
def load_chunks_from_json(json_path: str) -> List[Dict]:
    """
    Loads chunked data from a JSON file.
    """
    if not os.path.exists(json_path):
        print(f"Error: JSON file not found at {json_path}. Please run the chunker script first.")
        return []
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Loaded {len(data)} pages from JSON file.")
    return data


def build_vector_store():
    """
    Builds a ChromaDB vector store from a list of chunked documents.
    """
    # 1. Load the chunked data from the JSON file
    all_chunks = load_chunks_from_json(JSON_PATH)
    if not all_chunks:
        print("No chunks loaded. Exiting.")
        return

    # 2. Prepare documents for ChromaDB. 
    # The `from_documents` method requires LangChain's Document object format.
    documents = []
    for chunk in all_chunks:
        # Create a LangChain Document object for each chunk
        doc = Document(
            page_content=chunk.get("text"),
            metadata={
                "doc_id": chunk.get("doc_id"),
                "section_title": chunk.get("section_title"),
                "page_number": chunk.get("page_number")
            }
        )
        documents.append(doc)

    print(f"Prepared {len(documents)} documents for the vector store.")

    # 3. Initialize the embedding model.
    print("Initializing embedding model...")
    embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # 4. Create and store embeddings using ChromaDB.
    # The `persist_directory` argument tells ChromaDB to save the vectors to disk.
    print(f"Creating vector store at {CHROMA_DB_PATH}...")
    try:
        vector_store = Chroma.from_documents(
            documents=documents,
            embedding=embedding_model,
            persist_directory=CHROMA_DB_PATH
        )
        print("Vector store created and persisted successfully!")
    except Exception as e:
        print(f"An error occurred while creating the vector store: {e}")
    
def test_vector_store():
    # Initialize the same embedding model used to create the store
    embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # Load the persisted vector store from disk
    print(f"Loading vector store from {CHROMA_DB_PATH}...")
    if not os.path.exists(CHROMA_DB_PATH):
        print("Error: ChromaDB directory not found. Please run vector_store_builder.py first.")
        return

    vector_store = Chroma(
        persist_directory=CHROMA_DB_PATH,
        embedding_function=embedding_model
    )
    print("Vector store loaded successfully.")

    # A simple query to test the search functionality
    query = "What is the green criteria for the Energy sector?"

    # Perform a similarity search
    # `k=3` will return the top 3 most similar documents
    print(f"\nPerforming a similarity search for: '{query}'")
    retrieved_docs = vector_store.similarity_search_with_score(query, k=3)

    # Print the results
    if not retrieved_docs:
        print("No documents found. The search may have failed.")
    else:
        print("\nTop 3 most relevant documents:")
        for i, (doc, score) in enumerate(retrieved_docs):
            print(f"\n--- Document {i+1} (Score: {score:.4f}) ---")
            print(f"Doc ID: {doc.metadata.get('doc_id')}")
            print(f"Page Number: {doc.metadata.get('page_number')}")
            print(f"Section: {doc.metadata.get('section_title')}")
            print("\nContent:")
            print(doc.page_content[:200] + "...") # Print first 200 characters


if __name__ == "__main__":
    test_vector_store()



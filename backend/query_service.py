import os
from dotenv import load_dotenv
from typing import List

load_dotenv()

def get_relevant_documents(query: str, k: int = 5) -> List:
    """Legacy helper routing to the new VectorStoreManager."""
    try:
        from .app.services.vector_store import get_vector_store
    except ImportError:
        from app.services.vector_store import get_vector_store
    
    vs = get_vector_store()
    results = vs.similarity_search_with_score(query, k=k)
    return [doc for doc, _ in results]

from .base import BaseRetriever
from .vector import VectorRetriever
from .multi_query import MultiQueryRetriever
from .rrf import RRFRetriever
from .hybrid import HybridRetriever
from .reranker import RerankerRetriever
from ..vector_store import VectorStoreManager, get_vector_store


def get_retriever(
    strategy: str = "vector",
    vector_store: VectorStoreManager = None,
    **kwargs
) -> BaseRetriever:
    """Factory creating appropriate retriever strategy instance."""
    vs = vector_store or get_vector_store()
    strat = strategy.lower().strip()

    if strat == "multi_query":
        return MultiQueryRetriever(vector_store=vs, **kwargs)
    elif strat == "rrf":
        return RRFRetriever(vector_store=vs, **kwargs)
    elif strat == "hybrid":
        return HybridRetriever(vector_store=vs, **kwargs)
    elif strat in ("rerank", "reranker"):
        return RerankerRetriever(vector_store=vs, **kwargs)
    else:
        return VectorRetriever(vector_store=vs)


__all__ = [
    "BaseRetriever",
    "VectorRetriever",
    "MultiQueryRetriever",
    "RRFRetriever",
    "HybridRetriever",
    "RerankerRetriever",
    "get_retriever",
]

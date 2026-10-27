from typing import List
from .base import BaseRetriever
from ...schemas.retrieval import RetrievalResultItem
from ..vector_store import VectorStoreManager


class VectorRetriever(BaseRetriever):
    """Dense vector cosine similarity retriever."""

    def __init__(self, vector_store: VectorStoreManager):
        self.vector_store = vector_store

    def retrieve(
        self, query: str, k: int = 5, score_threshold: float = 0.0
    ) -> List[RetrievalResultItem]:
        results = self.vector_store.similarity_search_with_score(
            query=query, k=k, score_threshold=score_threshold
        )
        items: List[RetrievalResultItem] = []
        for rank, (doc, score) in enumerate(results, start=1):
            source = doc.metadata.get("source", "Unknown")
            items.append(
                RetrievalResultItem(
                    rank=rank,
                    content=doc.page_content,
                    source=source,
                    score=round(score, 4),
                    metadata=doc.metadata,
                )
            )
        return items

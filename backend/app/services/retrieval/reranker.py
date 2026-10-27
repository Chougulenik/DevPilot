from typing import List, Tuple
from langchain_core.documents import Document
from .base import BaseRetriever
from ...schemas.retrieval import RetrievalResultItem
from ..vector_store import VectorStoreManager
from ...core.config import settings
from ...core.logging import get_logger

logger = get_logger("reranker")


class RerankerRetriever(BaseRetriever):
    """Retrieval pipeline fetching a candidate pool and re-scoring with a Cross-Encoder / Reranker."""

    def __init__(
        self,
        vector_store: VectorStoreManager,
        initial_pool_factor: int = 3,
    ):
        self.vector_store = vector_store
        self.initial_pool_factor = initial_pool_factor

    def _cohere_rerank(self, query: str, docs: List[Document], top_n: int) -> List[Tuple[Document, float]]:
        """Applies Cohere Rerank if API key and library are present."""
        try:
            from langchain_cohere import CohereRerank
            api_key = settings.COHERE_API_KEY
            if not api_key:
                return []
            reranker = CohereRerank(
                cohere_api_key=api_key,
                model="rerank-english-v3.0",
                top_n=top_n,
            )
            compressed_docs = reranker.compress_documents(docs, query)
            results = []
            for doc in compressed_docs:
                relevance_score = getattr(doc, "metadata", {}).get("relevance_score", 0.9)
                results.append((doc, relevance_score))
            return results
        except Exception as e:
            logger.warning(f"Cohere rerank failed or unavailable: {e}")
            return []

    def _llm_rerank(self, query: str, candidate_docs: List[Tuple[Document, float]], top_n: int) -> List[Tuple[Document, float]]:
        """Contextual fallback ranking candidate chunks."""
        # Sort candidates primarily by semantic similarity
        candidate_docs.sort(key=lambda x: x[1], reverse=True)
        return candidate_docs[:top_n]

    def retrieve(
        self, query: str, k: int = 5, score_threshold: float = 0.0
    ) -> List[RetrievalResultItem]:
        # 1. Fetch larger candidate pool
        pool_size = max(k * self.initial_pool_factor, 12)
        candidates = self.vector_store.similarity_search_with_score(
            query=query, k=pool_size, score_threshold=0.0
        )

        if not candidates:
            return []

        docs_only = [doc for doc, _ in candidates]

        # 2. Attempt Cohere Reranking first
        reranked = []
        if settings.COHERE_API_KEY:
            reranked = self._cohere_rerank(query=query, docs=docs_only, top_n=k)

        # 3. Fallback to contextual scoring if Cohere wasn't run
        if not reranked:
            reranked = self._llm_rerank(query=query, candidate_docs=candidates, top_n=k)

        items: List[RetrievalResultItem] = []
        for rank, (doc, score) in enumerate(reranked[:k], start=1):
            if score < score_threshold:
                continue
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

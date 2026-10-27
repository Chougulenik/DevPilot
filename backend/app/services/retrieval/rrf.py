from collections import defaultdict
from typing import List, Dict, Tuple, Optional
from pydantic import BaseModel, Field
from langchain_core.documents import Document
from .base import BaseRetriever
from ...schemas.retrieval import RetrievalResultItem
from ..vector_store import VectorStoreManager
from ...core.config import settings
from ...core.logging import get_logger

logger = get_logger("rrf")


class QueryVariations(BaseModel):
    queries: List[str] = Field(description="List of alternative queries")


class RRFRetriever(BaseRetriever):
    """Reciprocal Rank Fusion retriever combining multiple query expansion passes."""

    def __init__(
        self,
        vector_store: VectorStoreManager,
        rrf_constant: int = 60,
        model_name: str = None,
    ):
        self.vector_store = vector_store
        self.rrf_constant = rrf_constant
        self.model_name = model_name or settings.FAST_LLM_MODEL

    def _get_llm(self):
        if settings.GOOGLE_API_KEY:
            from langchain_google_genai import ChatGoogleGenerativeAI
            m = self.model_name
            if "gpt" in m:
                m = "gemini-1.5-flash"
            return ChatGoogleGenerativeAI(
                model=m,
                temperature=0.0,
                google_api_key=settings.GOOGLE_API_KEY,
            )
        elif settings.OPENAI_API_KEY:
            try:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model=self.model_name,
                    temperature=0.0,
                    openai_api_key=settings.OPENAI_API_KEY,
                )
            except ImportError:
                pass
        return None

    def _generate_variations(self, query: str) -> List[str]:
        llm = self._get_llm()
        if llm is None:
            return [query]

        try:
            prompt = (
                "Generate 3 different variations of this query that would help retrieve relevant documents:\n\n"
                f"Original query: {query}\n\n"
                "Return 3 alternative queries that rephrase or approach the same question from different angles."
            )
            try:
                structured_llm = llm.with_structured_output(QueryVariations)
                response = structured_llm.invoke(prompt)
                queries = response.queries
            except Exception:
                res = llm.invoke(prompt)
                queries = [
                    line.strip("- 1234567890.").strip()
                    for line in res.content.split("\n")
                    if line.strip()
                ]

            variations = [query] + [q for q in queries if q.strip() and q != query]
            return variations[:4]
        except Exception as e:
            logger.warning(f"RRF query variation generation failed: {e}. Using original query.")
            return [query]

    def retrieve(
        self, query: str, k: int = 5, score_threshold: float = 0.0
    ) -> List[RetrievalResultItem]:
        variations = self._generate_variations(query)
        rrf_scores: Dict[str, float] = defaultdict(float)
        chunk_map: Dict[str, Tuple[Document, Dict]] = {}

        # Retrieve candidate pool for each query variation
        for q in variations:
            docs_with_scores = self.vector_store.similarity_search_with_score(
                query=q, k=max(k, 5), score_threshold=score_threshold
            )
            for position, (doc, _) in enumerate(docs_with_scores, start=1):
                content = doc.page_content.strip()
                chunk_map[content] = (doc, doc.metadata)
                # RRF Formula: 1 / (k_rrf + position)
                rrf_scores[content] += 1.0 / (self.rrf_constant + position)

        # Sort chunks by highest RRF score
        sorted_chunks = sorted(
            rrf_scores.items(), key=lambda item: item[1], reverse=True
        )

        results: List[RetrievalResultItem] = []
        for rank, (content, score) in enumerate(sorted_chunks[:k], start=1):
            doc, meta = chunk_map[content]
            source = meta.get("source", "Unknown")
            results.append(
                RetrievalResultItem(
                    rank=rank,
                    content=doc.page_content,
                    source=source,
                    score=round(score, 5),
                    metadata=meta,
                )
            )

        return results

from typing import List, Optional
from pydantic import BaseModel, Field
from .base import BaseRetriever
from ...schemas.retrieval import RetrievalResultItem
from ..vector_store import VectorStoreManager
from ...core.config import settings
from ...core.logging import get_logger

logger = get_logger("multi_query")


class QueryVariations(BaseModel):
    queries: List[str] = Field(description="3 alternative search query variations")


class MultiQueryRetriever(BaseRetriever):
    """Generates query variations with LLM and pools retrieved results."""

    def __init__(self, vector_store: VectorStoreManager, model_name: str = None):
        self.vector_store = vector_store
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
            logger.warning(f"Query variation generation failed: {e}. Using original query.")
            return [query]

    def retrieve(
        self, query: str, k: int = 5, score_threshold: float = 0.0
    ) -> List[RetrievalResultItem]:
        variations = self._generate_variations(query)
        seen_contents = set()
        pooled_results: List[RetrievalResultItem] = []

        for q in variations:
            res = self.vector_store.similarity_search_with_score(
                query=q, k=k, score_threshold=score_threshold
            )
            for doc, score in res:
                content = doc.page_content.strip()
                if content not in seen_contents:
                    seen_contents.add(content)
                    source = doc.metadata.get("source", "Unknown")
                    pooled_results.append(
                        RetrievalResultItem(
                            rank=len(pooled_results) + 1,
                            content=doc.page_content,
                            source=source,
                            score=round(score, 4),
                            metadata=doc.metadata,
                        )
                    )
                if len(pooled_results) >= k:
                    break
            if len(pooled_results) >= k:
                break

        return pooled_results[:k]

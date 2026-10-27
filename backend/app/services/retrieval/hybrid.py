import math
import re
from collections import defaultdict
from typing import List, Dict, Any, Tuple
from langchain_core.documents import Document
from .base import BaseRetriever
from ...schemas.retrieval import RetrievalResultItem
from ..vector_store import VectorStoreManager
from ...core.logging import get_logger

logger = get_logger("hybrid")


class HybridRetriever(BaseRetriever):
    """Hybrid search combining dense vector similarity with sparse BM25 keyword matching."""

    def __init__(
        self,
        vector_store: VectorStoreManager,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ):
        self.vector_store = vector_store
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

    def _tokenize(self, text: str) -> List[str]:
        return [w.lower() for w in re.findall(r"\w+", text)]

    def _bm25_search(self, query: str, corpus_docs: List[Document], k: int) -> List[Tuple[Document, float]]:
        """Calculates standard BM25 scores over corpus documents."""
        if not corpus_docs:
            return []

        tokenized_corpus = [self._tokenize(doc.page_content) for doc in corpus_docs]
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        N = len(tokenized_corpus)
        avgdl = sum(len(doc) for doc in tokenized_corpus) / max(1, N)
        k1 = 1.5
        b = 0.75

        # Document frequencies
        df: Dict[str, int] = defaultdict(int)
        for doc in tokenized_corpus:
            unique_terms = set(doc)
            for t in unique_terms:
                df[t] += 1

        # Calculate scores
        scores = []
        for i, doc in enumerate(tokenized_corpus):
            doc_len = len(doc)
            score = 0.0
            term_counts: Dict[str, int] = defaultdict(int)
            for term in doc:
                term_counts[term] += 1

            for term in query_tokens:
                if term in df:
                    # IDF formula
                    n_q = df[term]
                    idf = math.log((N - n_q + 0.5) / (n_q + 0.5) + 1.0)
                    f_q = term_counts[term]
                    denom = f_q + k1 * (1 - b + b * (doc_len / avgdl))
                    score += idf * (f_q * (k1 + 1)) / max(1e-6, denom)

            scores.append((corpus_docs[i], score))

        # Sort descending
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[: max(k * 2, 10)]

    def retrieve(
        self, query: str, k: int = 5, score_threshold: float = 0.0
    ) -> List[RetrievalResultItem]:
        # 1. Dense vector search
        vector_candidates = self.vector_store.similarity_search_with_score(
            query=query, k=max(k * 2, 10), score_threshold=0.0
        )

        # 2. Extract corpus documents from vector store for BM25
        try:
            raw = self.vector_store.db._collection.get(include=["metadatas", "documents"])
            raw_docs = [
                Document(page_content=txt, metadata=meta or {})
                for txt, meta in zip(raw.get("documents") or [], raw.get("metadatas") or [])
            ]
        except Exception:
            raw_docs = [doc for doc, _ in vector_candidates]

        bm25_candidates = self._bm25_search(query=query, corpus_docs=raw_docs, k=k)

        # 3. Normalize scores and fuse using weighted combination
        combined_scores: Dict[str, float] = defaultdict(float)
        meta_map: Dict[str, Tuple[Document, Dict[str, Any]]] = {}

        # Max vector score normalization
        max_vec = max([s for _, s in vector_candidates], default=1.0) or 1.0
        for doc, score in vector_candidates:
            norm_score = score / max_vec
            content = doc.page_content.strip()
            combined_scores[content] += self.vector_weight * norm_score
            meta_map[content] = (doc, doc.metadata)

        # Max BM25 score normalization
        max_bm25 = max([s for _, s in bm25_candidates], default=1.0) or 1.0
        for doc, score in bm25_candidates:
            norm_score = (score / max_bm25) if max_bm25 > 0 else 0.0
            content = doc.page_content.strip()
            combined_scores[content] += self.keyword_weight * norm_score
            if content not in meta_map:
                meta_map[content] = (doc, doc.metadata)

        # Sort combined results
        sorted_results = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)

        items: List[RetrievalResultItem] = []
        for rank, (content, final_score) in enumerate(sorted_results[:k], start=1):
            if final_score < score_threshold:
                continue
            doc, meta = meta_map[content]
            source = meta.get("source", "Unknown")
            items.append(
                RetrievalResultItem(
                    rank=rank,
                    content=doc.page_content,
                    source=source,
                    score=round(final_score, 4),
                    metadata=meta,
                )
            )

        return items

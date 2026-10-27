from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from .base import BaseChunker
from .recursive import RecursiveChunker
from ...core.config import settings
from ...core.logging import get_logger

logger = get_logger("semantic_chunker")


class SemanticChunker(BaseChunker):
    """Semantic chunking splitting text based on embedding cosine similarity drops."""

    def __init__(
        self,
        breakpoint_threshold_type: str = "percentile",
        breakpoint_threshold_amount: float = 70.0,
    ):
        self.breakpoint_threshold_type = breakpoint_threshold_type
        self.breakpoint_threshold_amount = breakpoint_threshold_amount
        self._splitter = None
        self._fallback_splitter = RecursiveChunker(chunk_size=1000, chunk_overlap=100)

    def _get_splitter(self):
        if self._splitter is None:
            try:
                from langchain_experimental.text_splitter import SemanticChunker as LC_SemanticChunker
                if settings.GOOGLE_API_KEY:
                    from langchain_google_genai import GoogleGenerativeAIEmbeddings
                    model_name = settings.EMBEDDING_MODEL
                    if "text-embedding" in model_name or model_name in ("models/embedding-001", "embedding-001"):
                        model_name = "models/gemini-embedding-001"
                    embeddings = GoogleGenerativeAIEmbeddings(
                        model=model_name,
                        google_api_key=settings.GOOGLE_API_KEY,
                    )
                elif settings.OPENAI_API_KEY:
                    try:
                        from langchain_openai import OpenAIEmbeddings
                        embeddings = OpenAIEmbeddings(
                            model=settings.EMBEDDING_MODEL,
                            openai_api_key=settings.OPENAI_API_KEY,
                        )
                    except ImportError:
                        self._splitter = False
                        return self._splitter
                else:
                    self._splitter = False
                    return self._splitter

                self._splitter = LC_SemanticChunker(
                    embeddings=embeddings,
                    breakpoint_threshold_type=self.breakpoint_threshold_type,
                    breakpoint_threshold_amount=self.breakpoint_threshold_amount,
                )
            except Exception as e:
                logger.warning(f"Could not initialize SemanticChunker, using recursive fallback: {e}")
                self._splitter = False
        return self._splitter

    def split_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        meta = metadata.copy() if metadata else {}
        splitter = self._get_splitter()

        has_key = bool(settings.GOOGLE_API_KEY or settings.OPENAI_API_KEY)
        if splitter is False or not has_key:
            # Fallback to recursive chunking if no valid API key or library error
            return self._fallback_splitter.split_text(text, metadata=meta)

        try:
            texts = splitter.split_text(text)
            return [
                Document(page_content=t, metadata={**meta, "chunk_index": i, "strategy": "semantic"})
                for i, t in enumerate(texts)
            ]
        except Exception as e:
            logger.warning(f"Semantic chunking failed at runtime: {e}. Falling back to recursive chunker.")
            return self._fallback_splitter.split_text(text, metadata=meta)

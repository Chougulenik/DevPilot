from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from .base import BaseChunker
from .recursive import RecursiveChunker
from ...core.config import settings
from ...core.logging import get_logger

logger = get_logger("agentic_chunker")


class AgenticChunker(BaseChunker):
    """LLM-guided agentic chunker that detects semantic topic shifts."""

    def __init__(self, target_chunk_chars: int = 500, model_name: Optional[str] = None):
        self.target_chunk_chars = target_chunk_chars
        self.model_name = model_name or settings.FAST_LLM_MODEL
        self._fallback_splitter = RecursiveChunker(chunk_size=self.target_chunk_chars, chunk_overlap=50)

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

    def split_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        meta = metadata.copy() if metadata else {}
        llm = self._get_llm()

        # If no API key or text is very small, use fast recursive fallback
        if llm is None or len(text.strip()) < self.target_chunk_chars:
            return self._fallback_splitter.split_text(text, metadata=meta)

        window_size = 4000
        text_windows = [text[i : i + window_size] for i in range(0, len(text), window_size)]

        all_clean_chunks = []
        try:
            for window in text_windows:
                prompt = (
                    "You are a text chunking expert. Split this text into logical chunks.\n\n"
                    "Rules:\n"
                    f"- Each chunk should ideally be around {self.target_chunk_chars} characters or less\n"
                    "- Split strictly at natural topic boundaries or complete paragraphs\n"
                    "- Keep related thoughts together\n"
                    "- Put '<<<SPLIT>>>' between chunks without altering or omitting any text\n\n"
                    f"Text:\n{window}\n\n"
                    "Return the exact text with <<<SPLIT>>> markers inserted where to split:"
                )
                response = llm.invoke(prompt)
                marked_text = response.content
                chunks = marked_text.split("<<<SPLIT>>>")
                for c in chunks:
                    cleaned = c.strip()
                    if cleaned:
                        all_clean_chunks.append(cleaned)
        except Exception as e:
            logger.warning(f"Agentic chunking failed: {e}. Falling back to recursive chunker.")
            return self._fallback_splitter.split_text(text, metadata=meta)

        if not all_clean_chunks:
            return self._fallback_splitter.split_text(text, metadata=meta)

        return [
            Document(page_content=c, metadata={**meta, "chunk_index": i, "strategy": "agentic"})
            for i, c in enumerate(all_clean_chunks)
        ]

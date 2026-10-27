from typing import List, Dict, Any, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from .base import BaseChunker


class RecursiveChunker(BaseChunker):
    """Recursive character text splitter using hierarchical separators."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        separators: Optional[List[str]] = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators,
        )

    def split_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        meta = metadata.copy() if metadata else {}
        texts = self.splitter.split_text(text)
        return [
            Document(page_content=t, metadata={**meta, "chunk_index": i, "strategy": "recursive"})
            for i, t in enumerate(texts)
        ]

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document


class BaseChunker(ABC):
    """Abstract base class for all text chunking strategies."""

    @abstractmethod
    def split_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Split a raw text string into a list of Document chunks."""
        pass

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split a batch of Document objects into smaller chunks."""
        all_chunks: List[Document] = []
        for doc in documents:
            chunks = self.split_text(doc.page_content, metadata=doc.metadata)
            all_chunks.extend(chunks)
        return all_chunks

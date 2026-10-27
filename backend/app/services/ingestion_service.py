import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document

from ..core.config import settings
from ..core.logging import get_logger
from ..core.exceptions import IngestionException
from .vector_store import VectorStoreManager, get_vector_store
from .chunking import get_chunker
from ..schemas.document import DocumentMetadataSchema, ChunkSchema

logger = get_logger("ingestion_service")


class IngestionService:
    """Enterprise document ingestion, parsing, chunking, and indexing pipeline."""

    def __init__(self, vector_store: Optional[VectorStoreManager] = None):
        self.vector_store = vector_store or get_vector_store()
        self.docs_dir = Path(settings.DOCS_DIR)

    def load_file_content(self, file_path: Path) -> str:
        """Extract text from .txt, .md, and .pdf files."""
        ext = file_path.suffix.lower()
        if ext in (".txt", ".md", ".json", ".csv"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif ext == ".pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(file_path))
                text = ""
                for page_idx, page in enumerate(reader.pages):
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n\n"
                return text
            except Exception as e:
                logger.error(f"Failed to read PDF {file_path}: {e}")
                raise IngestionException(f"Error parsing PDF file: {e}")
        else:
            # Default text reading fallback
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

    def ingest_text_document(
        self,
        content: str,
        source: str,
        strategy: str = "recursive",
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
    ) -> Dict[str, Any]:
        """Process, chunk, and index an in-memory document."""
        if not content.strip():
            raise IngestionException("Document content is empty")

        chunker = get_chunker(strategy=strategy, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = chunker.split_text(content, metadata={"source": source, "strategy": strategy})

        if not chunks:
            raise IngestionException("Chunking yielded 0 segments")

        self.vector_store.add_documents(chunks, batch_size=20, pause_seconds=1.5)

        return {
            "source": source,
            "filename": Path(source).name,
            "chunk_count": len(chunks),
            "characters": len(content),
            "strategy": strategy,
        }

    def ingest_file(
        self,
        file_path: Path,
        strategy: str = "recursive",
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
    ) -> Dict[str, Any]:
        """Ingest a physical file from disk."""
        content = self.load_file_content(file_path)
        # Store clean relative or display path
        display_source = str(file_path).replace("\\", "/")
        return self.ingest_text_document(
            content=content,
            source=display_source,
            strategy=strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def reindex_docs_directory(
        self,
        strategy: str = "recursive",
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
    ) -> Dict[str, Any]:
        """Clear vector store and re-index all compatible files in docs/ folder."""
        start_time = time.time()
        logger.info(f"Starting batch re-indexing of {self.docs_dir} with strategy '{strategy}'")

        if not self.docs_dir.exists():
            self.docs_dir.mkdir(parents=True, exist_ok=True)
            raise IngestionException(f"Documents directory '{self.docs_dir}' was missing (now created). Add files and retry.")

        # Reset vector store to ensure clean indexing
        self.vector_store.reset_collection()

        supported_extensions = {".txt", ".md", ".pdf"}
        files_to_process = [
            f for f in self.docs_dir.iterdir()
            if f.is_file() and f.suffix.lower() in supported_extensions
        ]

        if not files_to_process:
            logger.warning(f"No documents found in {self.docs_dir}")
            return {
                "success": True,
                "message": f"No files found in {self.docs_dir} to index.",
                "documents_indexed": 0,
                "chunks_created": 0,
                "duration_seconds": round(time.time() - start_time, 2),
            }

        total_chunks = 0
        indexed_docs = 0

        for file_path in files_to_process:
            try:
                res = self.ingest_file(
                    file_path=file_path,
                    strategy=strategy,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
                total_chunks += res["chunk_count"]
                indexed_docs += 1
                logger.info(f"Indexed {file_path.name}: {res['chunk_count']} chunks")
                # Pause between files to protect velocity limits
                time.sleep(1.0)
            except Exception as e:
                logger.error(f"Failed to ingest {file_path.name}: {e}")

        duration = round(time.time() - start_time, 2)
        logger.info(f"Re-indexing complete: {indexed_docs} documents, {total_chunks} chunks in {duration}s")

        return {
            "success": True,
            "message": f"Successfully indexed {indexed_docs} documents into {total_chunks} chunks.",
            "documents_indexed": indexed_docs,
            "chunks_created": total_chunks,
            "duration_seconds": duration,
        }

    def list_documents(self) -> List[DocumentMetadataSchema]:
        """List all indexed documents with chunk previews."""
        raw_catalog = self.vector_store.get_all_documents_metadata()
        documents: List[DocumentMetadataSchema] = []

        for item in raw_catalog:
            chunk_schemas = [
                ChunkSchema(
                    page_content=c["page_content"],
                    length=c["length"],
                    metadata=c.get("metadata", {}),
                )
                for c in item.get("chunks", [])
            ]
            documents.append(
                DocumentMetadataSchema(
                    source=item["source"],
                    filename=item["filename"],
                    chunk_count=item["chunk_count"],
                    total_chars=item["total_chars"],
                    chunks=chunk_schemas,
                )
            )

        return documents


_ingestion_service_instance: Optional[IngestionService] = None


def get_ingestion_service() -> IngestionService:
    global _ingestion_service_instance
    if _ingestion_service_instance is None:
        _ingestion_service_instance = IngestionService()
    return _ingestion_service_instance

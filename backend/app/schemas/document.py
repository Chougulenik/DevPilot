from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ChunkSchema(BaseModel):
    """Schema representing an individual indexed text chunk."""
    page_content: str = Field(default="", description="Raw chunk text content")
    length: int = Field(default=0, description="Character length of chunk")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata dictionary")


class DocumentMetadataSchema(BaseModel):
    """Schema for parent document metadata with its chunks."""
    source: str = Field(default="Unknown", description="Original file path or identifier")
    filename: str = Field(default="Document", description="Clean file name")
    chunk_count: int = Field(default=0, description="Total chunks for this document")
    total_chars: int = Field(default=0, description="Total character count across chunks")
    chunks: List[ChunkSchema] = Field(default_factory=list, description="Array of chunk objects")


class DocumentListResponse(BaseModel):
    """Response returned by GET /api/v1/documents."""
    documents: List[DocumentMetadataSchema] = Field(default_factory=list)
    total_documents: int = Field(default=0)
    total_chunks: int = Field(default=0)


class ReindexRequest(BaseModel):
    """Request payload for POST /api/v1/documents/reindex."""
    strategy: str = Field(default="recursive", description="Chunking strategy: recursive, semantic, or agentic")
    chunk_size: int = Field(default=1000, description="Chunk size in characters")
    chunk_overlap: int = Field(default=100, description="Overlap between consecutive chunks")


class IndexingJobResponse(BaseModel):
    """Response summary for re-indexing jobs."""
    success: bool = True
    message: str = Field(description="Outcome status message")
    documents_indexed: int = Field(default=0)
    chunks_created: int = Field(default=0)
    duration_seconds: float = Field(default=0.0)


class UploadResponse(BaseModel):
    """Response returned after file upload & ingestion."""
    success: bool = True
    message: str = Field(description="Upload outcome summary")
    filename: str
    chunk_count: int
    characters: int

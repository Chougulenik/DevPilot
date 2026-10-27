from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check diagnostic response."""
    status: str = Field(default="healthy", description="Application status: healthy or degraded")
    version: str = Field(default="1.0.0", description="Backend semantic version")
    timestamp: str = Field(description="Current UTC timestamp")
    database_status: str = Field(default="connected", description="ChromaDB connection status")
    document_count: int = Field(default=0, description="Total indexed parent documents")
    chunk_count: int = Field(default=0, description="Total indexed embedding chunks")
    environment: str = Field(default="development", description="Environment mode")


class SystemStatsResponse(BaseModel):
    """Detailed system diagnostic statistics."""
    status: str = Field(default="online")
    version: str = Field(default="1.0.0")
    document_count: int = Field(default=0)
    chunk_count: int = Field(default=0)
    active_embedding_model: str = Field(default="text-embedding-3-small")
    active_llm_model: str = Field(default="gpt-4o")
    docs_directory: str = Field(default="docs")
    persist_directory: str = Field(default="db/chroma_db")
    has_google_key: bool = Field(default=False)
    has_openai_key: bool = Field(default=False)
    has_cohere_key: bool = Field(default=False)

import os
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from ....schemas.document import (
    DocumentListResponse,
    ReindexRequest,
    IndexingJobResponse,
    UploadResponse,
)
from ....services.ingestion_service import IngestionService, get_ingestion_service
from ....core.config import settings
from ....core.logging import get_logger

logger = get_logger("documents_endpoint")
router = APIRouter(prefix="/documents", tags=["Knowledge Base Documents"])


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    ingestion: IngestionService = Depends(get_ingestion_service),
):
    """Retrieve catalog of all indexed documents and their chunks."""
    documents = ingestion.list_documents()
    total_chunks = sum(doc.chunk_count for doc in documents)
    return DocumentListResponse(
        documents=documents,
        total_documents=len(documents),
        total_chunks=total_chunks,
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    strategy: str = Form("recursive"),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(100),
    ingestion: IngestionService = Depends(get_ingestion_service),
):
    """Upload a text, markdown, or PDF file and index it into ChromaDB."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty")

    docs_folder = Path(settings.DOCS_DIR)
    docs_folder.mkdir(parents=True, exist_ok=True)
    destination_path = docs_folder / file.filename

    try:
        content_bytes = await file.read()
        with open(destination_path, "wb") as f:
            f.write(content_bytes)

        # Ingest the saved file
        res = ingestion.ingest_file(
            file_path=destination_path,
            strategy=strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        return UploadResponse(
            success=True,
            message=f"Successfully indexed '{file.filename}' into {res['chunk_count']} chunks.",
            filename=file.filename,
            chunk_count=res["chunk_count"],
            characters=res["characters"],
        )
    except Exception as e:
        logger.error(f"Upload failed for {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process file upload: {str(e)}")


@router.post("/reindex", response_model=IndexingJobResponse)
async def reindex_documents(
    request: ReindexRequest = ReindexRequest(),
    ingestion: IngestionService = Depends(get_ingestion_service),
):
    """Batch re-index all files currently in the docs/ directory."""
    try:
        summary = ingestion.reindex_docs_directory(
            strategy=request.strategy,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
        )
        return IndexingJobResponse(
            success=summary.get("success", True),
            message=summary.get("message", "Re-indexing complete"),
            documents_indexed=summary.get("documents_indexed", 0),
            chunks_created=summary.get("chunks_created", 0),
            duration_seconds=summary.get("duration_seconds", 0.0),
        )
    except Exception as e:
        logger.error(f"Re-indexing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Reindexing failed: {str(e)}")

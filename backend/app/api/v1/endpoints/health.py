import datetime
from fastapi import APIRouter, Depends
from ....core.config import settings
from ....schemas.health import HealthResponse, SystemStatsResponse
from ....services.vector_store import VectorStoreManager, get_vector_store
from ....services.ingestion_service import IngestionService, get_ingestion_service

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])


@router.get("", response_model=HealthResponse)
async def health_check(
    vector_store: VectorStoreManager = Depends(get_vector_store),
    ingestion: IngestionService = Depends(get_ingestion_service),
):
    """Basic health check and telemetry status."""
    chunk_count = vector_store.get_count()
    docs = ingestion.list_documents()
    doc_count = len(docs)

    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        timestamp=datetime.datetime.utcnow().isoformat() + "Z",
        database_status="connected",
        document_count=doc_count,
        chunk_count=chunk_count,
        environment=settings.ENVIRONMENT,
    )


@router.get("/stats", response_model=SystemStatsResponse)
async def system_stats(
    vector_store: VectorStoreManager = Depends(get_vector_store),
    ingestion: IngestionService = Depends(get_ingestion_service),
):
    """Detailed diagnostic telemetry for the frontend Navbar and dashboard."""
    chunk_count = vector_store.get_count()
    docs = ingestion.list_documents()
    doc_count = len(docs)

    return SystemStatsResponse(
        status="online",
        version=settings.APP_VERSION,
        document_count=doc_count,
        chunk_count=chunk_count,
        active_embedding_model=settings.EMBEDDING_MODEL,
        active_llm_model=settings.DEFAULT_LLM_MODEL,
        docs_directory=settings.DOCS_DIR,
        persist_directory=settings.CHROMA_PERSIST_DIR,
        has_google_key=bool(settings.GOOGLE_API_KEY),
        has_openai_key=bool(settings.OPENAI_API_KEY),
        has_cohere_key=bool(settings.COHERE_API_KEY),
    )

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import settings
from .core.logging import configure_logging, get_logger
from .core.exceptions import register_exception_handlers
from .api.v1.router import api_router
from .services.vector_store import get_vector_store
from .services.ingestion_service import get_ingestion_service

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifespan manager."""
    configure_logging()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")

    # Verify vector database and perform initial auto-indexing if database is empty
    try:
        vs = get_vector_store()
        count = vs.get_count()
        logger.info(f"Vector store active with {count} chunks")
        if count == 0:
            logger.info("Vector database is empty. Auto-indexing initial documents from docs/ directory...")
            ingestion = get_ingestion_service()
            ingestion.reindex_docs_directory(strategy="recursive", chunk_size=1000, chunk_overlap=100)
    except Exception as e:
        logger.warning(f"Startup vector store check encountered issue: {e}")

    yield

    logger.info(f"Shutting down {settings.APP_NAME}")


def create_app() -> FastAPI:
    """Factory to create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Production Enterprise Retrieval-Augmented Generation (RAG) Platform API",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Configure CORS for frontend access (Vite on port 5173, production domains)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register centralized exception handlers
    register_exception_handlers(app)

    # Mount API v1 router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Root welcome / ping
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "api_v1": settings.API_V1_PREFIX,
            "status": "operational",
        }

    # Backward compatibility endpoint for legacy test scripts
    @app.post("/query", tags=["Legacy"])
    async def legacy_query(payload: dict):
        q = payload.get("query", "")
        vs = get_vector_store()
        res = vs.similarity_search_with_score(q, k=5)
        return [
            {"source": doc.metadata.get("source", ""), "content": doc.page_content}
            for doc, _ in res
        ]

    return app


app = create_app()

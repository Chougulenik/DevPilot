import datetime
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from .logging import get_logger

logger = get_logger("exceptions")


class RAGException(Exception):
    """Base domain exception for all RAG system failures."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class DocumentNotFoundException(RAGException):
    """Raised when a requested document cannot be located."""

    def __init__(self, message: str = "Requested document not found"):
        super().__init__(message=message, status_code=404)


class IngestionException(RAGException):
    """Raised when document loading, chunking, or indexing fails."""

    def __init__(self, message: str):
        super().__init__(message=message, status_code=422)


class RetrievalException(RAGException):
    """Raised when vector or sparse retrieval fails."""

    def __init__(self, message: str):
        super().__init__(message=message, status_code=500)


class VectorStoreException(RAGException):
    """Raised when ChromaDB operations fail."""

    def __init__(self, message: str):
        super().__init__(message=message, status_code=503)


class ConfigurationException(RAGException):
    """Raised when configuration or essential API keys are invalid/missing."""

    def __init__(self, message: str):
        super().__init__(message=message, status_code=500)


def register_exception_handlers(app: FastAPI) -> None:
    """Registers centralized domain exception handlers on the FastAPI application."""

    @app.exception_handler(RAGException)
    async def rag_exception_handler(request: Request, exc: RAGException):
        logger.error(f"Domain Exception [{exc.__class__.__name__}]: {exc.message} on path {request.url.path}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "error_type": exc.__class__.__name__,
                "detail": exc.message,
                "path": request.url.path,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled Exception on {request.url.path}: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "error_type": "InternalServerError",
                "detail": str(exc) if str(exc) else "An unexpected internal server error occurred",
                "path": request.url.path,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            },
        )

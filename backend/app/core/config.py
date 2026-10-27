import os
import json
from functools import lru_cache
from typing import List, Optional, Union, Any
from pathlib import Path
from dotenv import load_dotenv

# Search for .env in current folder, backend folder, or project root
current_dir = Path.cwd()
backend_dir = Path(__file__).resolve().parent.parent.parent
project_root = backend_dir.parent

for candidate in (current_dir / ".env", backend_dir / ".env", project_root / ".env"):
    if candidate.exists():
        load_dotenv(dotenv_path=candidate)
        break
else:
    load_dotenv()

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic import field_validator

    class Settings(BaseSettings):
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
        )

        # Application Metadata
        APP_NAME: str = "Enterprise RAG Platform"
        APP_VERSION: str = "1.0.0"
        ENVIRONMENT: str = "development"
        DEBUG: bool = False

        # API & CORS
        API_V1_PREFIX: str = "/api/v1"
        CORS_ORIGINS: Union[List[str], str] = ["*"]

        @field_validator("CORS_ORIGINS", mode="before")
        @classmethod
        def parse_cors_origins(cls, v: Any) -> List[str]:
            if isinstance(v, str):
                val = v.strip()
                if not val:
                    return ["*"]
                if val.startswith("[") and val.endswith("]"):
                    try:
                        return json.loads(val)
                    except Exception:
                        pass
                return [item.strip() for item in val.split(",") if item.strip()]
            elif isinstance(v, list):
                return v
            return ["*"]

        # LLM & Embedding Settings (Google AI Studio / Gemini)
        GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", ""))
        OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", "")
        COHERE_API_KEY: Optional[str] = os.getenv("COHERE_API_KEY", "")
        EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")
        DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "gemini-1.5-flash")
        FAST_LLM_MODEL: str = os.getenv("FAST_LLM_MODEL", "gemini-1.5-flash")
        DEFAULT_TEMPERATURE: float = 0.2
        DEFAULT_K: int = 4

        # Storage & Persistence
        CHROMA_PERSIST_DIR: str = os.getenv(
            "CHROMA_PERSIST_DIR", str(project_root / "db" / "chroma_db")
        )
        DOCS_DIR: str = os.getenv("DOCS_DIR", str(project_root / "docs"))

        # Chunking Defaults
        DEFAULT_CHUNK_SIZE: int = 1000
        DEFAULT_CHUNK_OVERLAP: int = 100

except ImportError:
    from pydantic import BaseModel

    class Settings(BaseModel):  # Fallback
        APP_NAME: str = "Enterprise RAG Platform"
        APP_VERSION: str = "1.0.0"
        ENVIRONMENT: str = "development"
        DEBUG: bool = False
        API_V1_PREFIX: str = "/api/v1"
        CORS_ORIGINS: List[str] = ["*"]
        GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", ""))
        OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", "")
        COHERE_API_KEY: Optional[str] = os.getenv("COHERE_API_KEY", "")
        EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")
        DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "gemini-1.5-flash")
        FAST_LLM_MODEL: str = os.getenv("FAST_LLM_MODEL", "gemini-1.5-flash")
        DEFAULT_TEMPERATURE: float = 0.2
        DEFAULT_K: int = 4
        CHROMA_PERSIST_DIR: str = os.getenv(
            "CHROMA_PERSIST_DIR", str(project_root / "db" / "chroma_db")
        )
        DOCS_DIR: str = os.getenv("DOCS_DIR", str(project_root / "docs"))
        DEFAULT_CHUNK_SIZE: int = 1000
        DEFAULT_CHUNK_OVERLAP: int = 100


@lru_cache()
def get_settings() -> Settings:
    """Singleton getter for application configuration."""
    return Settings()


settings = get_settings()

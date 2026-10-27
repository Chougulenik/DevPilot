"""Top-level entrypoint for Uvicorn / Gunicorn server executions."""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
project_root = backend_dir.parent
for p in (str(backend_dir), str(project_root)):
    if p not in sys.path:
        sys.path.insert(0, p)

import uvicorn
try:
    from .app.main import app, create_app
except ImportError:
    from app.main import app, create_app

__all__ = ["app", "create_app"]

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

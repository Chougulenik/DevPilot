"""Enterprise RAG Application Package."""
import sys
from pathlib import Path

current_file = Path(__file__).resolve()
backend_dir = current_file.parent.parent
project_root = backend_dir.parent

for p in (str(backend_dir), str(project_root)):
    if p not in sys.path:
        sys.path.insert(0, p)

__version__ = "1.0.0"

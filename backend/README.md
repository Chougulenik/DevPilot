# DevPilot Backend

AI Engineering & Support Agent — FastAPI SSE Backend

## Setup

```bash
# Install uv (if not installed)
pip install uv

# Create virtual environment and install dependencies
uv sync

# Copy environment variables
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Run the development server
uv run uvicorn main:app --reload --port 8000
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/query` | Submit a new investigation query |
| GET | `/stream/{session_id}` | SSE stream for real-time agent events |
| GET | `/session/{session_id}` | Get session state |
| POST | `/approve/{session_id}` | Human-in-the-loop approval |
| GET | `/health` | Health check |

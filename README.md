# DevPilot

> AI Engineering & Support Agent — Autonomous production debugging in your browser

## Project Structure

```
DevPilot/
├── backend/          # Python FastAPI + SSE backend
│   ├── pyproject.toml
│   ├── main.py
│   ├── agents/       # Orchestrator, LogAgent, CodeAgent, DocsAgent
│   ├── tools/        # search_logs, search_code, get_deployment, search_docs
│   ├── sse/          # Event bus with async queues
│   └── models/       # Pydantic event schemas
│
└── frontend/         # Vite + React frontend
    ├── src/
    │   ├── App.jsx
    │   ├── components/
    │   │   ├── QueryInput.jsx   — Hero query input
    │   │   ├── Timeline.jsx     — Visual agent execution graph
    │   │   ├── AgentCard.jsx    — Per-agent status + tool calls
    │   │   ├── FinalAnswer.jsx  — Synthesized investigation report
    │   │   └── ApprovalModal.jsx — Human-in-the-loop approval
    │   └── store/
    │       └── useStore.js      — Zustand state management
    └── package.json
```

## Quick Start

### 1. Backend

```bash
cd backend

# Install uv (Python package manager)
pip install uv
# OR: winget install astral-sh.uv

# Create venv and install all dependencies
uv sync

# Configure environment
copy .env.example .env
# Edit .env and set your GEMINI_API_KEY

# Start development server
uv run uvicorn main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Open http://localhost:5173

## API Key

Get a free Gemini API key at: https://aistudio.google.com/app/apikey

Set it in `backend/.env`:
```
GEMINI_API_KEY=AIza...
```

## How It Works

1. User submits a query (e.g., "Production users getting 500 errors")
2. Orchestrator (Gemini-powered) plans the investigation
3. LogAgent + CodeAgent run **in parallel**, each:
   - Emitting SSE events (thoughts → tool calls → results → findings)
   - Using Gemini to analyze their findings
4. DocsAgent runs next, finds runbooks, and creates a mitigation plan
5. DocsAgent emits an `approval_required` event for any privileged command
6. Human approves/rejects via the modal UI
7. Orchestrator synthesizes a final root cause analysis

All events stream in real-time via Server-Sent Events to the React frontend.

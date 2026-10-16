@echo off
REM DevPilot Setup Script (Windows CMD)

echo === DevPilot Setup ===
echo.

echo [1/2] Setting up Backend...
cd backend

REM Check for uv, fall back to pip
where uv >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Installing uv via pip...
    pip install uv
)

echo Installing Python dependencies...
uv sync

if not exist ".env" (
    copy ".env.example" ".env"
    echo Created .env - IMPORTANT: Add your GEMINI_API_KEY to backend\.env
)

cd ..

echo.
echo [2/2] Setting up Frontend...
cd frontend
npm install
cd ..

echo.
echo === Setup Complete! ===
echo.
echo Next steps:
echo   1. Edit backend\.env and add your GEMINI_API_KEY
echo      (Get one free at https://aistudio.google.com/app/apikey)
echo.
echo   2. Start backend:    cd backend ^&^& uv run uvicorn main:app --reload --port 8000
echo   3. Start frontend:   cd frontend ^&^& npm run dev
echo   4. Open:             http://localhost:5173

#!/usr/bin/env pwsh
# DevPilot Setup Script
# Run this from the DevPilot/ root directory

Write-Host "🚀 DevPilot Setup" -ForegroundColor Cyan
Write-Host "==================" -ForegroundColor Cyan

# ---- Backend Setup ----
Write-Host "`n[1/4] Setting up Backend..." -ForegroundColor Yellow

Set-Location backend

# Install uv if not available
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv..." -ForegroundColor Gray
    pip install uv
}

Write-Host "Installing Python dependencies via uv..." -ForegroundColor Gray
uv sync

# Create .env from example
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example" -ForegroundColor Green
    Write-Host "⚠️  IMPORTANT: Edit backend/.env and add your GEMINI_API_KEY" -ForegroundColor Red
} else {
    Write-Host ".env already exists" -ForegroundColor Gray
}

Set-Location ..

# ---- Frontend Setup ----
Write-Host "`n[2/4] Setting up Frontend..." -ForegroundColor Yellow

Set-Location frontend

Write-Host "Installing Node.js dependencies..." -ForegroundColor Gray
npm install

Set-Location ..

Write-Host "`n✅ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Edit backend/.env and add your GEMINI_API_KEY"
Write-Host "     Get one free at: https://aistudio.google.com/app/apikey"
Write-Host ""
Write-Host "  2. Start the backend:"
Write-Host "     cd backend && uv run uvicorn main:app --reload --port 8000"
Write-Host ""
Write-Host "  3. Start the frontend (new terminal):"
Write-Host "     cd frontend && npm run dev"
Write-Host ""
Write-Host "  4. Open: http://localhost:5173" -ForegroundColor Cyan

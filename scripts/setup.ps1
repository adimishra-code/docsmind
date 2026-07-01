#!/usr/bin/env pwsh
<#
.SYNOPSIS
    DocsMind one-shot setup script for Windows (PowerShell).
.DESCRIPTION
    Clones, configures, and launches DocsMind locally including Docker
    infrastructure, backend, and frontend.
#>

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $PSScriptRoot

Write-Host "=== DocsMind Setup ===" -ForegroundColor Cyan

# 1. Check prerequisites
Write-Host "[1/6] Checking prerequisites..." -ForegroundColor Yellow
$missing = @()
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { $missing += "Python 3.11+" }
if (-not (Get-Command node -ErrorAction SilentlyContinue))   { $missing += "Node.js 18+" }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { $missing += "Docker" }
if (-not (Get-Command tesseract -ErrorAction SilentlyContinue)) {
    Write-Host "  WARNING: Tesseract OCR not found. PDF OCR will fail." -ForegroundColor DarkYellow
}
if ($missing.Count -gt 0) {
    Write-Host "  Missing: $($missing -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "  All core prerequisites found." -ForegroundColor Green

# 2. Create .env
Write-Host "[2/6] Configuring environment..." -ForegroundColor Yellow
$envFile = Join-Path $ROOT "backend" ".env"
if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $ROOT "backend" ".env.example") $envFile
    Write-Host "  Created backend/.env from .env.example" -ForegroundColor Green
    # Auto-generate SECRET_KEY
    $key = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | ForEach-Object { [char]$_ })
    (Get-Content $envFile) -replace "CHANGE_ME.*", $key | Set-Content $envFile
    Write-Host "  Generated random SECRET_KEY" -ForegroundColor Green
} else {
    Write-Host "  backend/.env already exists, skipping." -ForegroundColor DarkGray
}

$frontendEnv = Join-Path $ROOT "frontend" ".env"
if (-not (Test-Path $frontendEnv)) {
    Set-Content $frontendEnv "VITE_API_URL=http://localhost:8006"
    Write-Host "  Created frontend/.env" -ForegroundColor Green
} else {
    Write-Host "  frontend/.env already exists, skipping." -ForegroundColor DarkGray
}

# 3. Start Docker infrastructure
Write-Host "[3/6] Starting Docker infrastructure (PostgreSQL, Redis, Qdrant)..." -ForegroundColor Yellow
docker compose -f (Join-Path $ROOT "docker-compose.dev.yml") up -d postgres redis qdrant
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Docker startup failed." -ForegroundColor Red
    exit 1
}
Write-Host "  Docker services started." -ForegroundColor Green

# 4. Backend setup
Write-Host "[4/6] Setting up backend..." -ForegroundColor Yellow
$backendDir = Join-Path $ROOT "backend"
Push-Location $backendDir
try {
    # Create virtualenv if missing
    if (-not (Test-Path ".venv")) {
        python -m venv .venv
        Write-Host "  Created Python virtualenv" -ForegroundColor Green
    }
    # Install deps
    & ".venv\Scripts\pip" install --quiet -r requirements.txt
    Write-Host "  Installed Python dependencies" -ForegroundColor Green
    # Run migrations
    & ".venv\Scripts\alembic" upgrade head
    Write-Host "  Database migrations applied" -ForegroundColor Green
} finally {
    Pop-Location
}

# 5. Frontend setup
Write-Host "[5/6] Setting up frontend..." -ForegroundColor Yellow
$frontendDir = Join-Path $ROOT "frontend"
Push-Location $frontendDir
try {
    npm install --silent
    Write-Host "  Installed Node.js dependencies" -ForegroundColor Green
} finally {
    Pop-Location
}

# 6. Done
Write-Host "[6/6] Setup complete!" -ForegroundColor Cyan
Write-Host ""
Write-Host "Start the application with:" -ForegroundColor White
Write-Host "  cd backend   && .venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8006 --reload" -ForegroundColor Magenta
Write-Host "  cd frontend  && npm run dev" -ForegroundColor Magenta
Write-Host ""
Write-Host "Verify: curl http://localhost:8006/health" -ForegroundColor White

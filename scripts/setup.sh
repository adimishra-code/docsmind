#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== DocsMind Setup ==="

# 1. Check prerequisites
echo "[1/6] Checking prerequisites..."
MISSING=()
command -v python3 &>/dev/null || MISSING+=("Python 3.11+")
command -v node     &>/dev/null || MISSING+=("Node.js 18+")
command -v docker   &>/dev/null || MISSING+=("Docker")
command -v tesseract &>/dev/null || echo "  WARNING: Tesseract OCR not found. PDF OCR will fail."
if [ ${#MISSING[@]} -gt 0 ]; then
    echo "  Missing: ${MISSING[*]}" >&2
    exit 1
fi
echo "  All core prerequisites found."

# 2. Create .env
echo "[2/6] Configuring environment..."
if [ ! -f "$ROOT/backend/.env" ]; then
    cp "$ROOT/backend/.env.example" "$ROOT/backend/.env"
    KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
    sed -i.bak "s/CHANGE_ME.*/$KEY/" "$ROOT/backend/.env" && rm -f "$ROOT/backend/.env.bak"
    echo "  Created backend/.env with random SECRET_KEY"
else
    echo "  backend/.env already exists, skipping."
fi

if [ ! -f "$ROOT/frontend/.env" ]; then
    echo "VITE_API_URL=http://localhost:8006" > "$ROOT/frontend/.env"
    echo "  Created frontend/.env"
else
    echo "  frontend/.env already exists, skipping."
fi

# 3. Start Docker
echo "[3/6] Starting Docker infrastructure (PostgreSQL, Redis, Qdrant)..."
docker compose -f "$ROOT/docker-compose.dev.yml" up -d postgres redis qdrant
echo "  Docker services started."

# 4. Backend
echo "[4/6] Setting up backend..."
cd "$ROOT/backend"
if [ ! -d .venv ]; then
    python3 -m venv .venv
    echo "  Created Python virtualenv"
fi
source .venv/bin/activate
pip install --quiet -r requirements.txt
echo "  Installed Python dependencies"
alembic upgrade head
echo "  Database migrations applied"

# 5. Frontend
echo "[5/6] Setting up frontend..."
cd "$ROOT/frontend"
npm install --silent
echo "  Installed Node.js dependencies"

# 6. Done
echo "[6/6] Setup complete!"
echo ""
echo "Start the application with:"
echo "  cd backend   && source .venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8006 --reload"
echo "  cd frontend  && npm run dev"
echo ""
echo "Verify: curl http://localhost:8006/health"

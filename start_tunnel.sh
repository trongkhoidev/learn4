#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
NGROK_DOMAIN="https://measureless-trogonoid-marisha.ngrok-free.dev"

echo "=== LexiLearn Backend & Tunnel Service ==="

# 1. Stop any dangling processes on port 8000
if lsof -ti :8000 >/dev/null 2>&1; then
    echo "Stopping existing process on port 8000..."
    kill $(lsof -ti :8000) 2>/dev/null || true
    sleep 1
fi

# 2. Stop any existing ngrok process using the static domain
if pgrep -f "measureless-trogonoid" >/dev/null 2>&1; then
    echo "Stopping existing ngrok tunnel..."
    pkill -f "measureless-trogonoid" 2>/dev/null || true
    sleep 1
fi

# 3. Start LexiLearn FastAPI Backend
echo "Starting FastAPI backend on port 8000..."
cd "$ROOT/backend"
PYTHONPATH=. "$ROOT/backend/.venv/bin/uvicorn" app.main:app --port 8000 &
BACKEND_PID=$!

# Wait for backend to be ready
echo "Waiting for backend readiness..."
for i in $(seq 1 30); do
    if curl -s "http://127.0.0.1:8000/ready" | grep -q '"status":"ready"'; then
        echo "Backend is ready!"
        break
    fi
    sleep 1
done

# 4. Start ngrok tunnel
echo "Starting ngrok tunnel for $NGROK_DOMAIN -> http://127.0.0.1:8000..."
ngrok http http://127.0.0.1:8000 --url="$NGROK_DOMAIN" --log=stdout &
NGROK_PID=$!

cleanup() {
    echo "Stopping tunnel (PID: $NGROK_PID)..."
    kill $NGROK_PID 2>/dev/null || true
    echo "Stopping backend (PID: $BACKEND_PID)..."
    kill $BACKEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "=== LexiLearn Services Running ==="
echo "Local Backend: http://127.0.0.1:8000"
echo "Public Tunnel: $NGROK_DOMAIN"
echo "Vercel Web App: https://learn4-app.vercel.app/speaking/practice"
echo "Press Ctrl+C to stop both services."

wait $BACKEND_PID $NGROK_PID

#!/usr/bin/env bash
# Beyond Distance - Quick Start Script

PORT=${PORT:-8000}
HOST=${HOST:-"127.0.0.1"}

echo "✦ Starting Beyond Distance Connection Space..."
echo "✦ Server running at http://${HOST}:${PORT}"

python3 -m uvicorn app.main:app --host "${HOST}" --port "${PORT}" --reload

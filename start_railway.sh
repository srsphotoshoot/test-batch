#!/bin/bash
# SRS BATCH MODE - RAILWAY PRODUCTION STARTUP SCRIPT
# Starts both the FastAPI Web Server and the Background Generation Worker

echo "🚀 Starting Production Services..."

# 1. Start Background Worker
echo "⚙️ Starting Background Generation Worker..."
python3 service.py &
WORKER_PID=$!

# 2. Start Web API (Uvicorn)
echo "🌐 Starting FastAPI Web Server..."
# Using --proxy-headers for Railway/Vercel compatibility
uvicorn api.index:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips='*'

# Cleanup on exit
trap "kill $WORKER_PID" SIGINT SIGTERM
wait

#!/bin/bash

# ==================================================
# SRS BATCH MODE - MASTER STARTUP SCRIPT
# Runs: Backend API + React Frontend
# ==================================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════╗"
echo "║     SRS BATCH MODE - COMPLETE SYSTEM STARTUP      ║"
echo "║   React Frontend + FastAPI Backend + Gemini API   ║"
echo "╚════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ==================================================
# VALIDATION & DEPENDENCIES
# ==================================================
echo -e "${YELLOW}📋 Validating Setup & Dependencies...${NC}"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ ERROR: python3 not found!${NC}"
    exit 1
fi

# Check for Node/NPM
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ ERROR: npm not found!${NC}"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo -e "${RED}❌ ERROR: .env file not found!${NC}"
    echo ""
    echo "Create .env file with:"
    echo "  ENVIRONMENT=dev"
    echo "  DEBUG=true"
    echo "  FASTAPI_HOST=localhost"
    echo "  FASTAPI_PORT=8000"
    echo "  FASTAPI_BASE_URL=http://localhost:8000"
    echo "  SRS_KEY=your_gemini_api_key"
    exit 1
fi

if ! grep -q "SRS_KEY=" .env; then
    echo -e "${RED}❌ ERROR: SRS_KEY not found in .env file!${NC}"
    exit 1
fi

if [ ! -f "api/index.py" ]; then
    echo -e "${RED}❌ ERROR: api/index.py not found${NC}"
    exit 1
fi

if [ ! -d "frontend" ]; then
    echo -e "${RED}❌ ERROR: frontend directory not found${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment and dependencies valid${NC}"
echo ""

# ==================================================
# CLEANUP FUNCTION
# ==================================================
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down all services...${NC}"
    
    # Kill background processes
    jobs -p | xargs kill &>/dev/null || true
    
    # Force kill if needed
    pkill -f "python.*api.py" || true
    pkill -f "uvicorn" || true
    pkill -f "react-scripts" || true
    pkill -f "ngrok" || true
    
    echo -e "${GREEN}✅ All services stopped${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# ==================================================
# SETUP VIRTUAL ENVIRONMENT
# ==================================================
echo -e "${YELLOW}📦 Setting up Python environment...${NC}"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "Installing/Updating backend dependencies..."
pip install -q -r requirements.txt || pip install -r requirements.txt

echo -e "${GREEN}✅ Python environment ready${NC}"
echo ""

# ==================================================
# START BACKEND API
# ==================================================
echo -e "${YELLOW}🚀 Starting FastAPI Backend...${NC}"

python api/index.py &
BACKEND_PID=$!

# Wait for backend to be ready via health check
echo "Waiting for API health check..."
MAX_RETRIES=15
RETRY_COUNT=0
until $(curl --output /dev/null --silent --fail http://localhost:8000/health); do
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo -e "${RED}❌ ERROR: API failed to start after $MAX_RETRIES seconds${NC}"
        kill $BACKEND_PID || true
        exit 1
    fi
    echo -n "."
    sleep 1
    ((RETRY_COUNT++))
done

echo -e "\n${GREEN}✅ Backend is healthy and responding${NC}"
echo ""

# ==================================================
# START REACT FRONTEND
# ==================================================
echo -e "${YELLOW}🚀 Starting React Frontend...${NC}"

cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies (this may take a moment)..."
    npm install --no-audit --no-fund --silent || npm install
fi

echo "Starting development server..."
BROWSER=none npm start &
FRONTEND_PID=$!

cd ..

echo -e "${GREEN}✅ Frontend started${NC}"
echo ""

# ==================================================
# START NGROK TUNNEL (OPTIONAL)
# ==================================================
NGROK_STATUS="${YELLOW}Ngrok not required (local mode)${NC}"

# Check if ngrok is installed and user wants to use it
if command -v ngrok &> /dev/null; then
    echo -e "${YELLOW}🚀 Starting Ngrok Tunnel on Port 8000...${NC}"
    
    # Kill any existing ngrok tunnels to prevent port collisions
    pkill -f "ngrok" || true
    sleep 1
    
    # Start ngrok in background
    nohup ngrok http 8000 > /tmp/ngrok.log 2>&1 &
    NGROK_PID=$!
    
    echo "Waiting for Ngrok tunnel to initialize..."
    sleep 4
    
    # Fetch the public URL from ngrok's local API with retry logic
    NGROK_URL=""
    for i in {1..5}; do
        NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"[^"]*' | head -n 1 | cut -d'"' -f4 || true)
        if [ -n "$NGROK_URL" ]; then
            break
        fi
        echo "  Attempt $i/5: Waiting for tunnel..."
        sleep 2
    done
    
    if [ -z "$NGROK_URL" ]; then
        NGROK_STATUS="${RED}⚠️ Ngrok tunnel failed to start${NC}"
        echo -e "${RED}Note: Ngrok may require authentication. Check /tmp/ngrok.log for details${NC}"
        echo -e "${YELLOW}You can still access the app locally at http://localhost:3000${NC}"
    else
        NGROK_STATUS="${GREEN}${NGROK_URL}${NC}"
        echo -e "${GREEN}✅ Ngrok tunnel started successfully${NC}"
    fi
else
    echo -e "${YELLOW}ℹ️  Ngrok not installed (optional for public access)${NC}"
    echo -e "${YELLOW}   Install with: npm install -g ngrok${NC}"
fi

# Wait a moment for all services to stabilize
sleep 2

echo ""
echo -e "${YELLOW}⏳ All services starting... Please wait 5-10 seconds for React to fully load${NC}"
sleep 3

echo ""

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                        ✅ SYSTEM READY                             ║"
echo "╠════════════════════════════════════════════════════════════════════╣"
echo -e "║  🌐 Frontend UI:    ${GREEN}http://localhost:3000${BLUE}                         ║"
echo -e "║  🔧 Backend API:    ${GREEN}http://localhost:8000${BLUE}                         ║"
echo -e "║  📚 API Docs:       ${GREEN}http://localhost:8000/docs${BLUE}                      ║"
echo "║                                                                    ║"

if [ -n "$NGROK_URL" ]; then
    echo -e "║  🌍 Public Link:    ${GREEN}$NGROK_URL${BLUE}${NC}"
else
    echo -e "║  🌍 Public Link:    ${YELLOW}Ngrok not available (local only)${BLUE}${NC}"
fi

echo "║                                                                    ║"
echo -e "║  ${YELLOW}Press Ctrl+C to stop all services${BLUE}                           ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Keep script running
wait

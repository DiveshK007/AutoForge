#!/bin/bash
# AutoForge — Quick Start Script
set -e

echo "⚒️  AutoForge — Autonomous AI Engineering Orchestrator"
echo "======================================================="
echo ""

# Check for .env file
if [ ! -f .env ]; then
    echo "📋 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your ANTHROPIC_API_KEY and GITLAB_TOKEN"
    echo ""
fi

# Check if Docker is available
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "🐳 Docker detected — starting with Docker Compose..."
    docker-compose up --build -d
    echo ""
    echo "✅ AutoForge is starting!"
    echo "   Backend:    http://localhost:8000"
    echo "   Dashboard:  http://localhost:3000"
    echo "   Health:     http://localhost:8000/health"
    echo ""
    echo "📊 View logs: docker-compose logs -f"
    echo "🛑 Stop:      docker-compose down"
else
    echo "🐍 Starting without Docker (local development)..."
    echo ""

    # Backend
    echo "📦 Installing backend dependencies..."
    cd backend
    pip install -r requirements.txt
    cd ..

    echo ""
    echo "🚀 Starting backend..."
    cd backend
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!
    cd ..

    echo ""
    echo "✅ Backend running at http://localhost:8000"
    echo ""

    # Dashboard
    if command -v npm &> /dev/null; then
        echo "📦 Installing dashboard dependencies..."
        cd dashboard
        npm install
        echo ""
        echo "🚀 Starting dashboard..."
        npm run dev &
        DASHBOARD_PID=$!
        cd ..
        echo "✅ Dashboard running at http://localhost:3000"
    else
        echo "⚠️  npm not found — skipping dashboard"
    fi

    echo ""
    echo "🛑 Press Ctrl+C to stop all services"

    # Trap SIGINT to clean up
    trap "kill $BACKEND_PID $DASHBOARD_PID 2>/dev/null; exit 0" SIGINT
    wait
fi

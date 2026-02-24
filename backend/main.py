"""
AutoForge — Autonomous AI Engineering Orchestrator for GitLab
Main application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from api.router import api_router
from brain.orchestrator import CommandBrain
from memory.store import MemoryStore
from telemetry.collector import TelemetryCollector


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager."""
    # ─── Startup ───
    app.state.brain = CommandBrain()
    app.state.memory = MemoryStore()
    app.state.telemetry = TelemetryCollector()

    await app.state.memory.initialize()
    await app.state.telemetry.initialize()
    app.state.brain.set_memory(app.state.memory)
    app.state.brain.set_telemetry(app.state.telemetry)

    print("🔥 AutoForge Command Brain initialized")
    print("🧠 Agent workforce standing by")
    print(f"🌐 Listening on {settings.APP_HOST}:{settings.APP_PORT}")

    yield

    # ─── Shutdown ───
    await app.state.memory.shutdown()
    await app.state.telemetry.shutdown()
    print("🛑 AutoForge shutting down gracefully")


app = FastAPI(
    title="AutoForge",
    description="Autonomous AI Engineering Orchestrator for GitLab",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS Middleware ───
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── API Routes ───
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "operational",
        "system": "AutoForge",
        "version": "1.0.0",
        "brain": "online",
        "agents": "standing_by",
    }

"""
AutoForge — Autonomous AI Engineering Orchestrator for GitLab
Main application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from logging_config import setup_logging, get_logger
from config import settings
from api.router import api_router
from api.websocket import router as ws_router, ws_manager
from api.explain import router as explain_router
from brain.orchestrator import CommandBrain
from memory.store import MemoryStore
from telemetry.collector import TelemetryCollector
from middleware.correlation import CorrelationMiddleware
from middleware.rate_limiter import RateLimitMiddleware

# ─── Initialize structured logging before anything else ───
setup_logging()
log = get_logger("main")


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

    # Start WebSocket broadcast worker
    await ws_manager.start()

    log.info(
        "autoforge_started",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        demo_mode=settings.DEMO_MODE,
        environment=settings.APP_ENV,
    )

    yield

    # ─── Shutdown ───
    await ws_manager.stop()
    await app.state.memory.shutdown()
    await app.state.telemetry.shutdown()
    log.info("autoforge_shutdown")


app = FastAPI(
    title="AutoForge",
    description="Autonomous AI Engineering Orchestrator for GitLab",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── Middleware Stack (order matters: outermost first) ───
app.add_middleware(CorrelationMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── API Routes ───
app.include_router(api_router, prefix="/api/v1")
app.include_router(explain_router, prefix="/api/v1/explain", tags=["explain"])
app.include_router(ws_router)


@app.get("/health")
async def health_check():
    """Health check endpoint — liveness probe."""
    return {
        "status": "operational",
        "system": "AutoForge",
        "version": "1.0.0",
        "brain": "online",
        "agents": "standing_by",
    }


@app.get("/ready")
async def readiness_probe():
    """
    Readiness probe — checks that all subsystems are initialized.
    Returns 503 if not ready.
    """
    checks = {
        "brain": hasattr(app.state, "brain") and app.state.brain is not None,
        "memory": hasattr(app.state, "memory") and app.state.memory is not None,
        "telemetry": hasattr(app.state, "telemetry") and app.state.telemetry is not None,
        "websocket": ws_manager.is_running,
    }

    all_ready = all(checks.values())

    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=200 if all_ready else 503,
        content={
            "ready": all_ready,
            "checks": checks,
            "version": "1.0.0",
        },
    )


@app.get("/api/v1/system/version")
async def system_version():
    """Build and runtime version info — for ops dashboards and debugging."""
    import platform
    import sys
    import os

    _git_sha = os.environ.get("GIT_SHA", "")
    if not _git_sha:
        try:
            import subprocess
            _git_sha = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=os.path.dirname(__file__),
                stderr=subprocess.DEVNULL,
            ).decode().strip()
        except Exception:
            _git_sha = "unknown"

    return {
        "name": "AutoForge",
        "version": "1.0.0",
        "git_sha": _git_sha,
        "python": sys.version.split()[0],
        "platform": platform.system(),
        "environment": settings.APP_ENV,
        "demo_mode": settings.DEMO_MODE,
        "agents": list((app.state.brain.get_agent_registry() if hasattr(app.state, "brain") else {}).keys()),
        "capabilities": [
            "multi_agent_orchestration",
            "self_healing_pipelines",
            "dag_execution",
            "cognitive_reasoning",
            "learning_memory",
            "human_in_the_loop",
            "sustainability_tracking",
            "real_time_websocket",
        ],
    }

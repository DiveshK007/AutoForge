"""
AutoForge Celery Worker — Async task processing for agent workloads.

In production, this handles heavy agent workloads asynchronously.
In DEMO_MODE, the brain processes everything in-process via asyncio.
"""

from celery import Celery

from config import settings
from logging_config import get_logger

log = get_logger("worker")

celery_app = Celery(
    "autoforge",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_default_queue="autoforge",
    task_routes={
        "autoforge.process_event": {"queue": "events"},
        "autoforge.execute_agent": {"queue": "agents"},
    },
)


@celery_app.task(name="autoforge.process_event", bind=True, max_retries=3)
def process_event_task(self, event_data: dict):
    """
    Process a GitLab event asynchronously.

    In production, this is dispatched from the webhook endpoint
    to offload heavy LLM calls from the API server.
    """
    log.info("celery_process_event", event=event_data.get("event_type", "unknown"))
    try:
        # Import here to avoid circular imports at module level
        import asyncio
        from models.events import NormalizedEvent, EventType
        from brain.orchestrator import CommandBrain

        brain = CommandBrain()
        normalized = NormalizedEvent(**event_data)
        workflow_id = asyncio.get_event_loop().run_until_complete(
            brain.ingest_event(normalized)
        )
        return {"status": "processed", "workflow_id": workflow_id}
    except Exception as exc:
        log.error("celery_process_event_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=10 * (self.request.retries + 1))


@celery_app.task(name="autoforge.execute_agent", bind=True, max_retries=3)
def execute_agent_task(self, agent_type: str, task_data: dict):
    """Execute a single agent task asynchronously."""
    log.info("celery_execute_agent", agent=agent_type)
    try:
        return {"status": "executed", "agent": agent_type, "task": task_data}
    except Exception as exc:
        log.error("celery_execute_agent_failed", agent=agent_type, error=str(exc))
        raise self.retry(exc=exc, countdown=10 * (self.request.retries + 1))

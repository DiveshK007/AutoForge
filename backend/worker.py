"""
AutoForge Celery Worker — Async task processing for agent workloads.
"""

from celery import Celery

from config import settings

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
)


@celery_app.task(name="autoforge.process_event")
def process_event_task(event_data: dict):
    """Process a GitLab event asynchronously."""
    # This would be called when using Celery for async processing
    # For the demo, we use asyncio directly in the brain
    return {"status": "processed", "event": event_data}


@celery_app.task(name="autoforge.execute_agent")
def execute_agent_task(agent_type: str, task_data: dict):
    """Execute an agent task asynchronously."""
    return {"status": "executed", "agent": agent_type, "task": task_data}

"""
AutoForge Celery Worker — Async task processing for agent workloads.

In production, this handles heavy agent workloads asynchronously.
In DEMO_MODE, the brain processes everything in-process via asyncio.
"""

import asyncio

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


def _get_or_create_event_loop():
    """Get the running event loop or create a new one for sync Celery context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


@celery_app.task(name="autoforge.process_event", bind=True, max_retries=3)
def process_event_task(self, event_data: dict):
    """
    Process a GitLab event asynchronously via Celery.

    Dispatched from the webhook endpoint in production mode.
    Creates a CommandBrain, hydrates the event, and runs the full pipeline.
    """
    log.info("celery_process_event", event=event_data.get("event_type", "unknown"))
    try:
        from models.events import NormalizedEvent
        from brain.orchestrator import CommandBrain
        from memory.store import MemoryStore
        from telemetry.collector import TelemetryCollector

        # Build a minimal brain with memory + telemetry
        brain = CommandBrain()
        memory = MemoryStore()
        telemetry = TelemetryCollector()

        loop = _get_or_create_event_loop()
        loop.run_until_complete(memory.initialize())
        loop.run_until_complete(telemetry.initialize())
        brain.set_memory(memory)
        brain.set_telemetry(telemetry)

        # Hydrate normalized event
        normalized = NormalizedEvent(**event_data)

        # Run the full workflow pipeline
        workflow_id = loop.run_until_complete(brain.ingest_event(normalized))

        # Cleanup
        loop.run_until_complete(memory.shutdown())
        loop.run_until_complete(telemetry.shutdown())

        log.info("celery_process_event_done", workflow_id=workflow_id)
        return {"status": "processed", "workflow_id": workflow_id}
    except Exception as exc:
        log.error("celery_process_event_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=10 * (self.request.retries + 1))


@celery_app.task(name="autoforge.execute_agent", bind=True, max_retries=3)
def execute_agent_task(self, agent_type: str, task_data: dict):
    """Execute a single agent task asynchronously via Celery."""
    log.info("celery_execute_agent", agent=agent_type)
    try:
        from brain.orchestrator import CommandBrain

        brain = CommandBrain()
        agent = brain.get_agent(agent_type)
        if not agent:
            return {"status": "error", "error": f"Unknown agent: {agent_type}"}

        # Build a minimal AgentTask
        from models.workflows import AgentTask, Workflow
        task = AgentTask(
            workflow_id=task_data.get("workflow_id", "celery-task"),
            agent_type=agent_type,
            action=task_data.get("action", "execute"),
            input_data=task_data.get("input_data", {}),
        )
        workflow = Workflow(
            workflow_id=task_data.get("workflow_id", "celery-task"),
            event_type=task_data.get("event_type", "unknown"),
            project_id=task_data.get("project_id", "unknown"),
        )

        loop = _get_or_create_event_loop()
        result = loop.run_until_complete(agent.execute(task, workflow))

        log.info("celery_execute_agent_done", agent=agent_type, confidence=result.get("confidence", 0))
        return {"status": "executed", "agent": agent_type, "result": result}
    except Exception as exc:
        log.error("celery_execute_agent_failed", agent=agent_type, error=str(exc))
        raise self.retry(exc=exc, countdown=10 * (self.request.retries + 1))


# ─── Result Callbacks — Feed Celery outcomes back to the system ───

@celery_app.task(name="autoforge.on_task_success")
def on_task_success_callback(result, task_id: str, workflow_id: str = ""):
    """
    Callback invoked after a Celery task completes successfully.
    Broadcasts the result via WebSocket so the dashboard gets real-time updates.
    """
    try:
        from api.websocket import broadcast_workflow_update

        loop = _get_or_create_event_loop()
        wf_id = workflow_id or (result.get("workflow_id", "") if isinstance(result, dict) else "")
        if wf_id:
            loop.run_until_complete(broadcast_workflow_update(
                wf_id,
                status="completed",
                event_type="celery_result",
                detail=f"Celery task {task_id} completed",
            ))
        log.info("celery_result_callback", task_id=task_id, workflow_id=wf_id)
    except Exception as exc:
        log.warning("celery_result_callback_failed", error=str(exc))


# ─── Signal handlers for automatic result tracking ───

from celery.signals import task_success, task_failure


@task_success.connect
def handle_task_success(sender=None, result=None, **kwargs):
    """Signal handler: log Celery task success and broadcast."""
    task_id = sender.request.id if sender else "unknown"
    wf_id = result.get("workflow_id", "") if isinstance(result, dict) else ""
    log.info("celery_task_success_signal", task_id=task_id, workflow_id=wf_id)


@task_failure.connect
def handle_task_failure(sender=None, exception=None, **kwargs):
    """Signal handler: log Celery task failure."""
    task_id = sender.request.id if sender else "unknown"
    log.warning("celery_task_failure_signal", task_id=task_id, error=str(exception))

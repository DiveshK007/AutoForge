"""
AutoForge WebSocket Hub — Real-time event broadcasting to dashboard clients.

Provides:
- WebSocket endpoint at /ws for dashboard connections
- Broadcast system events (workflow updates, agent actions, metrics)
- Per-client subscription filtering
- Heartbeat / keepalive
- Automatic reconnection support
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from logging_config import get_logger

log = get_logger("websocket")

router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts."""

    def __init__(self):
        self._connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._broadcast_task: asyncio.Task | None = None

    @property
    def active_count(self) -> int:
        return len(self._connections)

    @property
    def is_running(self) -> bool:
        return self._broadcast_task is not None and not self._broadcast_task.done()

    async def start(self):
        """Start the broadcast worker."""
        if self._broadcast_task is None or self._broadcast_task.done():
            self._broadcast_task = asyncio.create_task(self._broadcast_worker())
            log.info("ws_broadcast_started")

    async def stop(self):
        """Stop the broadcast worker."""
        if self._broadcast_task and not self._broadcast_task.done():
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
        log.info("ws_connected", total_connections=len(self._connections))

        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Connected to AutoForge real-time stream",
        })

    async def disconnect(self, websocket: WebSocket):
        """Remove a disconnected WebSocket."""
        async with self._lock:
            self._connections.discard(websocket)
        log.info("ws_disconnected", total_connections=len(self._connections))

    async def broadcast(self, message: Dict[str, Any]):
        """Queue a message for broadcast to all connected clients."""
        message.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        try:
            self._message_queue.put_nowait(message)
        except asyncio.QueueFull:
            # Drop oldest message if queue is full
            try:
                self._message_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            self._message_queue.put_nowait(message)

    async def _broadcast_worker(self):
        """Background worker that drains the queue and sends to all clients."""
        while True:
            try:
                message = await self._message_queue.get()
                payload = json.dumps(message, default=str)

                async with self._lock:
                    dead: List[WebSocket] = []
                    for ws in self._connections:
                        try:
                            await ws.send_text(payload)
                        except Exception:
                            dead.append(ws)

                    for ws in dead:
                        self._connections.discard(ws)

            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error("ws_broadcast_error", error=str(e))
                await asyncio.sleep(0.1)


# ─── Global connection manager (singleton) ──────────────────────

ws_manager = ConnectionManager()


# ─── WebSocket Endpoint ─────────────────────────────────────────

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time dashboard updates.

    Messages sent to clients:
    - type: "connected"         — initial handshake
    - type: "workflow_update"   — workflow status change
    - type: "agent_action"      — agent completed a task
    - type: "activity"          — new activity feed item
    - type: "metrics_update"    — metrics snapshot
    - type: "heartbeat"         — keepalive ping
    """
    await ws_manager.connect(websocket)

    try:
        while True:
            # Wait for client messages (ping/pong or subscription changes)
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0,
                )

                # Handle client messages
                try:
                    msg = json.loads(data)
                    if msg.get("type") == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
                except json.JSONDecodeError:
                    pass

            except asyncio.TimeoutError:
                # Send heartbeat on timeout
                try:
                    await websocket.send_json({
                        "type": "heartbeat",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "connections": ws_manager.active_count,
                    })
                except Exception:
                    break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.warning("ws_error", error=str(e))
    finally:
        await ws_manager.disconnect(websocket)


# ─── Broadcast Helpers (called from other modules) ──────────────

async def broadcast_workflow_update(
    workflow_id: str,
    status: str,
    event_type: str = "",
    detail: str = "",
    **extra,
):
    """Broadcast a workflow status change."""
    await ws_manager.broadcast({
        "type": "workflow_update",
        "workflow_id": workflow_id,
        "status": status,
        "event_type": event_type,
        "detail": detail,
        **extra,
    })


async def broadcast_agent_action(
    agent_type: str,
    action: str,
    success: bool,
    confidence: float = 0.0,
    workflow_id: str = "",
    detail: str = "",
):
    """Broadcast an agent action completion."""
    await ws_manager.broadcast({
        "type": "agent_action",
        "agent_type": agent_type,
        "action": action,
        "success": success,
        "confidence": confidence,
        "workflow_id": workflow_id,
        "detail": detail,
    })


async def broadcast_activity(
    event: str,
    description: str,
    agent: str = "",
    status: str = "completed",
):
    """Broadcast a new activity feed item."""
    await ws_manager.broadcast({
        "type": "activity",
        "event": event,
        "description": description,
        "agent": agent,
        "status": status,
    })


async def broadcast_metrics_snapshot(metrics: Dict[str, Any]):
    """Broadcast a metrics update."""
    await ws_manager.broadcast({
        "type": "metrics_update",
        "metrics": metrics,
    })

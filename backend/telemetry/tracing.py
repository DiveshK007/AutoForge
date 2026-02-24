"""
AutoForge OpenTelemetry Integration — Distributed tracing & observability.

Provides:
- Span creation for workflows, agent executions, and API calls
- Trace context propagation across async boundaries
- Metric export (when collector is available)
- Graceful degradation when OTel is not installed
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Dict, Optional

from logging_config import get_logger

log = get_logger("tracing")

# ─── Try to import OpenTelemetry (optional dependency) ───
_OTEL_AVAILABLE = False
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        SimpleSpanProcessor,
        ConsoleSpanExporter,
    )
    from opentelemetry.sdk.resources import Resource

    _OTEL_AVAILABLE = True
except ImportError:
    pass


class AutoForgeTracer:
    """
    Unified tracing facade.

    Falls back to structured-log-based span tracking when
    OpenTelemetry SDK is not installed (lightweight environments).
    """

    def __init__(self, service_name: str = "autoforge"):
        self._service_name = service_name
        self._tracer = None
        self._active_spans: Dict[str, Dict[str, Any]] = {}

        if _OTEL_AVAILABLE:
            resource = Resource.create({"service.name": service_name})
            provider = TracerProvider(resource=resource)
            # Console exporter for dev; replace with OTLP exporter in prod
            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer(service_name)
            log.info("otel_initialized", service=service_name)
        else:
            log.info("otel_unavailable_using_fallback", service=service_name)

    # ─── Context-managed spans ──────────────────────────

    @contextmanager
    def span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Synchronous span context manager."""
        attrs = attributes or {}
        start = time.perf_counter()

        if self._tracer:
            with self._tracer.start_as_current_span(name, attributes=attrs) as otel_span:
                try:
                    yield otel_span
                except Exception as exc:
                    otel_span.set_status(trace.StatusCode.ERROR, str(exc))
                    otel_span.record_exception(exc)
                    raise
                finally:
                    elapsed = time.perf_counter() - start
                    otel_span.set_attribute("duration_ms", round(elapsed * 1000, 2))
        else:
            span_id = f"{name}_{id(attrs)}"
            log.debug("span_start", span=name, **attrs)
            try:
                yield None
            except Exception as exc:
                log.error("span_error", span=name, error=str(exc), **attrs)
                raise
            finally:
                elapsed = time.perf_counter() - start
                log.debug("span_end", span=name, duration_ms=round(elapsed * 1000, 2), **attrs)

    @asynccontextmanager
    async def async_span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Async span context manager."""
        attrs = attributes or {}
        start = time.perf_counter()

        if self._tracer:
            with self._tracer.start_as_current_span(name, attributes=attrs) as otel_span:
                try:
                    yield otel_span
                except Exception as exc:
                    otel_span.set_status(trace.StatusCode.ERROR, str(exc))
                    otel_span.record_exception(exc)
                    raise
                finally:
                    elapsed = time.perf_counter() - start
                    otel_span.set_attribute("duration_ms", round(elapsed * 1000, 2))
        else:
            log.debug("async_span_start", span=name, **attrs)
            try:
                yield None
            except Exception as exc:
                log.error("async_span_error", span=name, error=str(exc), **attrs)
                raise
            finally:
                elapsed = time.perf_counter() - start
                log.debug("async_span_end", span=name, duration_ms=round(elapsed * 1000, 2), **attrs)

    # ─── Manual span tracking (for long-lived operations) ─

    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> str:
        """Start a manual span and return its ID."""
        import uuid
        span_id = str(uuid.uuid4())[:8]
        self._active_spans[span_id] = {
            "name": name,
            "start": time.perf_counter(),
            "attributes": attributes or {},
        }
        log.debug("manual_span_start", span=name, span_id=span_id)
        return span_id

    def end_span(self, span_id: str, status: str = "ok", error: Optional[str] = None):
        """End a manual span."""
        info = self._active_spans.pop(span_id, None)
        if not info:
            return
        elapsed = time.perf_counter() - info["start"]
        log.debug(
            "manual_span_end",
            span=info["name"],
            span_id=span_id,
            status=status,
            duration_ms=round(elapsed * 1000, 2),
            error=error,
        )

    # ─── Workflow-specific helpers ──────────────────────

    @asynccontextmanager
    async def workflow_span(self, workflow_id: str, event_type: str):
        """Trace an entire workflow lifecycle."""
        async with self.async_span(
            "workflow",
            {"workflow.id": workflow_id, "workflow.event_type": event_type},
        ) as span:
            yield span

    @asynccontextmanager
    async def agent_span(self, agent_type: str, action: str, workflow_id: str):
        """Trace an agent execution within a workflow."""
        async with self.async_span(
            f"agent.{agent_type}",
            {
                "agent.type": agent_type,
                "agent.action": action,
                "workflow.id": workflow_id,
            },
        ) as span:
            yield span


# ─── Module-level singleton ──────────────────────────

tracer = AutoForgeTracer()

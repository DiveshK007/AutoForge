"""
AutoForge GitLab Integration — Base API client.

Single source of truth for all GitLab REST calls.  All domain-specific
service modules (pipelines, merge_requests, etc.) delegate through this
client, which provides:

- Authenticated HTTP (token from env)
- Automatic retry with exponential backoff
- Rate-limit awareness
- Structured JSON logging (no token leakage)
- DEMO_MODE switching (returns simulated responses)
- Telemetry hooks on every request
"""

import logging
import time
from typing import Any, Dict, Optional
from uuid import uuid4

import httpx

from config import settings
from integrations.gitlab.auth import build_headers, get_base_url, sanitize_log
from integrations.gitlab.rate_limiter import RateLimiter
from integrations.gitlab.retry_handler import (
    retry_async,
    RetryExhausted,
    is_retryable_status,
)
from integrations.gitlab.models import APICallTelemetry

logger = logging.getLogger("autoforge.integrations.gitlab.client")

# Connection pool settings
_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0)


class GitLabAPIError(Exception):
    """Raised when a GitLab API call fails after retries."""

    def __init__(self, message: str, status_code: int = 0, response_body: str = ""):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)


class GitLabAPIClient:
    """
    Enterprise-grade async HTTP client for the GitLab REST v4 API.

    Usage:
        client = GitLabAPIClient()
        result = await client.get("/projects/42/pipelines/101")
    """

    def __init__(self) -> None:
        self.base_url = get_base_url()
        self._headers = build_headers()
        self._rate_limiter = RateLimiter()
        self._telemetry_log: list[APICallTelemetry] = []

    # ─── Public HTTP verbs ─────────────────────────────────────────────────

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        agent: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._request("GET", endpoint, params=params, agent=agent, workflow_id=workflow_id)

    async def post(
        self,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        agent: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._request("POST", endpoint, json_body=payload, agent=agent, workflow_id=workflow_id)

    async def put(
        self,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        agent: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._request("PUT", endpoint, json_body=payload, agent=agent, workflow_id=workflow_id)

    async def delete(
        self,
        endpoint: str,
        *,
        agent: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._request("DELETE", endpoint, agent=agent, workflow_id=workflow_id)

    async def get_raw(
        self,
        endpoint: str,
        *,
        agent: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ) -> str:
        """GET that returns raw text (e.g. job logs)."""
        return await self._request_raw("GET", endpoint, agent=agent, workflow_id=workflow_id)

    # ─── Internal request engine ───────────────────────────────────────────

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        agent: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute an authenticated JSON request with retry + rate-limit."""
        # DEMO_MODE — return empty success without hitting the network
        if settings.DEMO_MODE:
            self._emit_telemetry(method, endpoint, agent, workflow_id, True, 0, demo=True)
            return {}

        request_id = str(uuid4())[:8]
        start = time.monotonic()

        try:
            result = await retry_async(
                self._do_request,
                method,
                endpoint,
                params,
                json_body,
                request_id,
                max_attempts=settings.AGENT_MAX_RETRIES,
                retryable_exceptions=(httpx.HTTPStatusError, httpx.TransportError),
            )
            elapsed_ms = (time.monotonic() - start) * 1000
            self._emit_telemetry(method, endpoint, agent, workflow_id, True, elapsed_ms)
            return result

        except RetryExhausted as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            error_msg = sanitize_log(str(exc.last_error))
            logger.error("[%s] %s %s FAILED after retries: %s", request_id, method, endpoint, error_msg)
            self._emit_telemetry(method, endpoint, agent, workflow_id, False, elapsed_ms, error=error_msg)
            raise GitLabAPIError(
                f"GitLab API {method} {endpoint} failed: {error_msg}",
                status_code=getattr(exc.last_error, "response", None) and exc.last_error.response.status_code or 0,
            ) from exc

    async def _do_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]],
        json_body: Optional[Dict[str, Any]],
        request_id: str,
    ) -> Dict[str, Any]:
        """Single HTTP attempt (called by retry wrapper)."""
        await self._rate_limiter.acquire()

        url = f"{self.base_url}/api/v4{endpoint}"
        logger.debug("[%s] %s %s", request_id, method, endpoint)

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.request(
                method,
                url,
                headers=self._headers,
                params=params,
                json=json_body,
            )
            self._rate_limiter.update_from_headers(dict(response.headers))

            if is_retryable_status(response.status_code):
                response.raise_for_status()  # triggers retry

            response.raise_for_status()
            return response.json() if response.content else {}

    async def _request_raw(
        self,
        method: str,
        endpoint: str,
        agent: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ) -> str:
        """Execute a request that returns raw text."""
        if settings.DEMO_MODE:
            self._emit_telemetry(method, endpoint, agent, workflow_id, True, 0, demo=True)
            return ""

        start = time.monotonic()
        url = f"{self.base_url}/api/v4{endpoint}"

        try:
            await self._rate_limiter.acquire()
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.request(method, url, headers=self._headers)
                self._rate_limiter.update_from_headers(dict(response.headers))
                response.raise_for_status()
                elapsed_ms = (time.monotonic() - start) * 1000
                self._emit_telemetry(method, endpoint, agent, workflow_id, True, elapsed_ms)
                return response.text
        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            error_msg = sanitize_log(str(exc))
            self._emit_telemetry(method, endpoint, agent, workflow_id, False, elapsed_ms, error=error_msg)
            raise GitLabAPIError(f"Raw request failed: {error_msg}") from exc

    # ─── Telemetry ─────────────────────────────────────────────────────────

    def _emit_telemetry(
        self,
        method: str,
        endpoint: str,
        agent: Optional[str],
        workflow_id: Optional[str],
        success: bool,
        elapsed_ms: float,
        demo: bool = False,
        error: Optional[str] = None,
    ) -> None:
        record = APICallTelemetry(
            tool="gitlab_api",
            action=f"{method} {endpoint}",
            agent=agent,
            workflow_id=workflow_id,
            success=success,
            execution_time_ms=round(elapsed_ms, 2),
            demo_mode=demo,
            error=error,
        )
        self._telemetry_log.append(record)
        # Keep bounded
        if len(self._telemetry_log) > 5000:
            self._telemetry_log = self._telemetry_log[-2500:]

    def get_telemetry(self, limit: int = 100) -> list[dict]:
        return [t.to_dict() for t in self._telemetry_log[-limit:]]

    @property
    def rate_limiter(self) -> RateLimiter:
        return self._rate_limiter

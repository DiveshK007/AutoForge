"""
AutoForge Correlation Middleware — Request tracing with correlation IDs.

Every request gets a unique X-Request-ID that propagates through logs,
responses, and downstream calls for distributed tracing.
"""

import secrets

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from logging_config import get_logger

log = get_logger("correlation")


class CorrelationMiddleware(BaseHTTPMiddleware):
    """
    Injects a correlation/request ID into every request.

    - Reads X-Request-ID from incoming headers (forwarded from gateway)
    - Generates one if missing
    - Binds it to structlog context for all downstream logs
    - Returns it in the response header
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Extract or generate request ID
        request_id = (
            request.headers.get("X-Request-ID")
            or secrets.token_hex(8)
        )

        # Bind to structlog context vars (available in all log calls)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        # Store on request state for access in route handlers
        request.state.request_id = request_id

        response = await call_next(request)

        # Return correlation ID in response
        response.headers["X-Request-ID"] = request_id

        return response

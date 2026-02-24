"""
AutoForge Middleware Package — Enterprise middleware stack.
"""

from middleware.auth import get_auth_context, require_role, AuthContext
from middleware.rate_limiter import RateLimitMiddleware
from middleware.correlation import CorrelationMiddleware

__all__ = [
    "get_auth_context",
    "require_role",
    "AuthContext",
    "RateLimitMiddleware",
    "CorrelationMiddleware",
]

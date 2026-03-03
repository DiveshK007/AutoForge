"""
AutoForge Authentication & Authorization — Enterprise API security layer.

Provides:
- API key authentication for machine-to-machine calls
- JWT bearer token auth for dashboard sessions (real JWT via python-jose)
- Webhook signature verification
- Role-based access control (RBAC)
- Rate-aware request context with correlation IDs
- Token issuance endpoint support
"""

import hashlib
import hmac
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from config import settings
from logging_config import get_logger

log = get_logger("auth")

# ─── Security Schemes ───────────────────────────────────────────

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


# ─── Models ──────────────────────────────────────────────────────

class AuthContext(BaseModel):
    """Authenticated request context attached to every request."""
    request_id: str
    authenticated: bool = False
    auth_method: str = "none"  # "api_key" | "bearer" | "webhook" | "demo"
    principal: str = "anonymous"
    roles: list[str] = []
    timestamp: datetime = datetime.now(timezone.utc)

    def has_role(self, role: str) -> bool:
        """Check if the auth context has a specific role."""
        return role in self.roles


class TokenRequest(BaseModel):
    """Request body for token issuance."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    roles: list[str] = []


# ─── JWT Helpers ─────────────────────────────────────────────────

def _create_jwt(subject: str, roles: list[str], expires_delta: Optional[timedelta] = None) -> str:
    """Create a real JWT token using python-jose."""
    from jose import jwt as jose_jwt

    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    payload = {
        "sub": subject,
        "roles": roles,
        "iat": datetime.now(timezone.utc),
        "exp": expire,
        "iss": "autoforge",
    }
    return jose_jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def _verify_jwt(token: str) -> Optional[dict]:
    """Verify and decode a JWT token. Returns claims dict or None."""
    try:
        from jose import jwt as jose_jwt, JWTError, ExpiredSignatureError
        claims = jose_jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False},
        )
        return claims
    except Exception:
        return None


# ─── Helpers ─────────────────────────────────────────────────────

def _generate_request_id() -> str:
    """Generate a short unique request ID for correlation."""
    return secrets.token_hex(8)


def _verify_api_key(key: str) -> Optional[AuthContext]:
    """Verify an API key against configured keys."""
    # In demo mode, accept the demo key
    if settings.DEMO_MODE and key == "demo":
        return AuthContext(
            request_id=_generate_request_id(),
            authenticated=True,
            auth_method="api_key",
            principal="demo-user",
            roles=["admin", "viewer", "operator"],
        )

    # Check against configured API key
    configured_key = settings.SECRET_KEY
    if configured_key and hmac.compare_digest(key, configured_key):
        return AuthContext(
            request_id=_generate_request_id(),
            authenticated=True,
            auth_method="api_key",
            principal="api-client",
            roles=["admin", "viewer", "operator"],
        )

    return None


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitLab webhook HMAC-SHA256 signature."""
    if not secret:
        return True  # No secret configured — skip verification

    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


# ─── Dependencies ────────────────────────────────────────────────

async def get_auth_context(
    request: Request,
    api_key: Optional[str] = Security(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> AuthContext:
    """
    Extract and validate authentication from the request.

    Priority:
    1. API Key header (X-API-Key)
    2. Bearer token (real JWT verification)
    3. Demo mode passthrough
    4. Reject

    In demo/development mode, unauthenticated requests are allowed
    with viewer-level access.
    """
    request_id = _generate_request_id()

    # 1. Check API key
    if api_key:
        ctx = _verify_api_key(api_key)
        if ctx:
            ctx.request_id = request_id
            log.info(
                "authenticated",
                method="api_key",
                principal=ctx.principal,
                request_id=request_id,
            )
            return ctx
        raise HTTPException(status_code=401, detail="Invalid API key")

    # 2. Check Bearer token — real JWT verification
    if bearer:
        claims = _verify_jwt(bearer.credentials)
        if claims:
            return AuthContext(
                request_id=request_id,
                authenticated=True,
                auth_method="bearer",
                principal=claims.get("sub", "jwt-user"),
                roles=claims.get("roles", ["viewer"]),
            )
        # Token invalid / expired
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Demo / development mode — allow unauthenticated full access
    if settings.DEMO_MODE or settings.APP_ENV == "development":
        return AuthContext(
            request_id=request_id,
            authenticated=True,
            auth_method="demo",
            principal="demo-user",
            roles=["admin", "operator", "viewer"],
        )

    # 4. Reject in production without credentials
    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide X-API-Key header or Bearer token.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(role: str):
    """Dependency that requires a specific role."""

    async def _check(auth: AuthContext = Depends(get_auth_context)):
        if role not in auth.roles:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required role: {role}",
            )
        return auth

    return _check

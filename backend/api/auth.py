"""
AutoForge Auth API — JWT token issuance endpoint.

Provides:
- POST /auth/token — Issue a JWT for dashboard sessions
- GET  /auth/me     — Introspect current auth context
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException

from config import settings
from middleware.auth import (
    AuthContext,
    TokenRequest,
    TokenResponse,
    _create_jwt,
    get_auth_context,
)
from logging_config import get_logger

log = get_logger("api.auth")

router = APIRouter()

# ─── Demo credentials (in production, use a real user store / LDAP / OIDC) ───
_DEMO_USERS = {
    "admin": {"password": "admin", "roles": ["admin", "viewer", "operator"]},
    "operator": {"password": "operator", "roles": ["operator", "viewer"]},
    "viewer": {"password": "viewer", "roles": ["viewer"]},
    "demo": {"password": "demo", "roles": ["admin", "viewer", "operator"]},
}


@router.post("/token", response_model=TokenResponse)
async def issue_token(body: TokenRequest):
    """
    Issue a JWT access token.

    In demo mode, accepts demo credentials.
    In production, integrate with your identity provider.
    """
    # Look up user
    user = _DEMO_USERS.get(body.username)

    if not user or user["password"] != body.password:
        # In demo mode, also allow API key as password
        if settings.DEMO_MODE and body.password == "demo":
            user = {"password": "demo", "roles": ["admin", "viewer", "operator"]}
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")

    expires = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    token = _create_jwt(
        subject=body.username,
        roles=user["roles"],
        expires_delta=expires,
    )

    log.info("token_issued", user=body.username, roles=user["roles"])

    return TokenResponse(
        access_token=token,
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
        roles=user["roles"],
    )


@router.get("/me")
async def get_current_user(auth: AuthContext = Depends(get_auth_context)):
    """Introspect the current authentication context."""
    return {
        "authenticated": auth.authenticated,
        "method": auth.auth_method,
        "principal": auth.principal,
        "roles": auth.roles,
        "request_id": auth.request_id,
    }

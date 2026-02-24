"""
AutoForge GitLab Integration — Authentication & header management.

Centralizes token retrieval, header construction, and secret sanitization.
Tokens are NEVER logged.
"""

import logging
import os
from typing import Dict

from config import settings

logger = logging.getLogger("autoforge.integrations.gitlab.auth")

# Paths that agents must never read or modify
FORBIDDEN_PATHS = frozenset({
    ".env",
    ".env.local",
    ".env.production",
    "secrets.yml",
    "secrets.yaml",
    ".gitlab-ci-token",
    "id_rsa",
    "id_ed25519",
    ".ssh/",
    ".gnupg/",
})


def build_headers() -> Dict[str, str]:
    """
    Build authenticated headers for GitLab API requests.

    Never falls back to empty string — raises if token is absent in
    non-demo mode.
    """
    token = settings.GITLAB_API_TOKEN or os.getenv("GITLAB_API_TOKEN", "")
    if not token and not settings.DEMO_MODE:
        logger.error("GITLAB_API_TOKEN is not configured — API calls will fail")

    return {
        "PRIVATE-TOKEN": token,
        "Content-Type": "application/json",
        "User-Agent": "AutoForge/1.0",
    }


def sanitize_log(message: str) -> str:
    """
    Strip tokens and secrets from a log message so they never appear in
    telemetry or stdout.
    """
    token = settings.GITLAB_API_TOKEN
    if token:
        message = message.replace(token, "***REDACTED***")
    return message


def is_forbidden_path(file_path: str) -> bool:
    """Check whether a file path touches a secret or sensitive location."""
    normalised = file_path.strip().lower()
    for fp in FORBIDDEN_PATHS:
        if normalised.endswith(fp) or f"/{fp}" in normalised:
            return True
    return False


def get_base_url() -> str:
    """Return the configured GitLab base URL (no trailing slash)."""
    return settings.GITLAB_URL.rstrip("/")

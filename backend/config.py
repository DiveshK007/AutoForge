"""
AutoForge configuration module.
Loads environment variables and provides typed settings.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ─── GitLab ───
    GITLAB_URL: str = "https://gitlab.com"
    GITLAB_API_TOKEN: str = ""
    GITLAB_WEBHOOK_SECRET: str = ""
    GITLAB_DEFAULT_PROJECT_ID: Optional[str] = None

    # ─── Anthropic ───
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    ANTHROPIC_MAX_TOKENS: int = 4096

    # ─── Database ───
    DATABASE_URL: str = "postgresql://autoforge:autoforge@localhost:5432/autoforge"
    REDIS_URL: str = "redis://localhost:6379/0"

    # ─── Vector DB ───
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8100
    CHROMA_COLLECTION: str = "autoforge_memory"

    # ─── Application ───
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_PORT: int = 8000
    APP_HOST: str = "0.0.0.0"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    LOG_LEVEL: str = "INFO"
    DEMO_MODE: bool = True  # Deterministic demo mode — precomputed reasoning, no LLM calls

    # ─── Agent Configuration ───
    AGENT_MAX_RETRIES: int = 3
    AGENT_TIMEOUT_SECONDS: int = 120
    AGENT_CONFIDENCE_THRESHOLD: float = 0.7
    AGENT_RISK_THRESHOLD: float = 0.8

    # ─── Celery ───
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ─── GreenOps ───
    GREENOPS_CARBON_FACTOR: float = 0.000475
    GREENOPS_CPU_POWER_DRAW: float = 65.0
    GREENOPS_MEMORY_POWER_DRAW: float = 0.3


settings = Settings()

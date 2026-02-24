"""
AutoForge GitLab Integration — Retry handler with exponential backoff.

Wraps async callables and retries on transient HTTP errors (429, 5xx,
timeouts) with jittered exponential backoff.
"""

import asyncio
import logging
import random
from typing import Any, Callable, Coroutine, Optional, TypeVar

logger = logging.getLogger("autoforge.integrations.gitlab.retry")

T = TypeVar("T")

# HTTP status codes that are considered transient and retryable
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class RetryExhausted(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, attempts: int, last_error: Exception):
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(f"All {attempts} retry attempts exhausted: {last_error}")


async def retry_async(
    fn: Callable[..., Coroutine[Any, Any, T]],
    *args: Any,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None,
    **kwargs: Any,
) -> T:
    """
    Execute an async function with exponential backoff retry.

    Args:
        fn: Async callable to execute.
        max_attempts: Maximum number of attempts (including first).
        base_delay: Initial delay in seconds before first retry.
        max_delay: Maximum delay cap.
        backoff_factor: Multiplier for each subsequent delay.
        retryable_exceptions: Tuple of exception types that trigger a retry.
        on_retry: Optional callback invoked before each retry (attempt, error).

    Returns:
        Result of the successful call.

    Raises:
        RetryExhausted: If all attempts fail.
    """
    last_error: Optional[Exception] = None
    delay = base_delay

    for attempt in range(1, max_attempts + 1):
        try:
            return await fn(*args, **kwargs)
        except retryable_exceptions as exc:
            last_error = exc

            if attempt >= max_attempts:
                break

            # Jittered delay
            jitter = random.uniform(0, delay * 0.3)
            sleep_time = min(delay + jitter, max_delay)

            logger.warning(
                "Retry %d/%d after %.1fs — %s: %s",
                attempt,
                max_attempts,
                sleep_time,
                type(exc).__name__,
                str(exc)[:200],
            )

            if on_retry:
                on_retry(attempt, exc)

            await asyncio.sleep(sleep_time)
            delay *= backoff_factor

    raise RetryExhausted(max_attempts, last_error)  # type: ignore[arg-type]


def is_retryable_status(status_code: int) -> bool:
    """Check if an HTTP status code warrants a retry."""
    return status_code in RETRYABLE_STATUS_CODES

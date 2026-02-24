"""
AutoForge GitLab Integration — Event normalizer (thin facade).

Provides the same public interface as the legacy
``integrations.event_normalizer.EventNormalizer`` but delegates to
``WebhookProcessor`` under the hood.  Existing code that imported
``EventNormalizer`` will continue to work after updating the import path.
"""

from typing import Dict, Any, Optional

from integrations.gitlab.webhooks import WebhookProcessor
from models.events import NormalizedEvent

_processor = WebhookProcessor()


class GitLabEventNormalizer:
    """
    Convenience wrapper so callers can do::

        normalizer = GitLabEventNormalizer()
        event = normalizer.normalize(event_header, payload)
    """

    def __init__(self) -> None:
        self._processor = WebhookProcessor()

    def normalize(
        self, event_header: str, payload: Dict[str, Any],
    ) -> Optional[NormalizedEvent]:
        """Return a NormalizedEvent or None if the event is not actionable."""
        event, _raw = self._processor.parse(event_header, payload)
        return event

    def validate_token(self, token: Optional[str]) -> bool:
        return self._processor.validate_token(token)

"""
AutoForge Event Normalizer — Converts raw GitLab events to structured format.
"""

from datetime import datetime, timezone
from typing import Optional

from models.events import GitLabEvent, NormalizedEvent, EventType


class EventNormalizer:
    """
    Normalizes raw GitLab webhook events into structured events
    that the Command Brain can process.
    """

    def normalize(self, raw_event: GitLabEvent) -> Optional[NormalizedEvent]:
        """
        Normalize a raw GitLab event.

        Returns None if the event is not actionable.
        """
        event_type = raw_event.event_type.lower()
        payload = raw_event.payload

        # ─── Pipeline Events ───
        if event_type in ("pipeline hook", "pipeline"):
            return self._normalize_pipeline(payload)

        # ─── Merge Request Events ───
        if event_type in ("merge request hook", "merge_request"):
            return self._normalize_merge_request(payload)

        # ─── Push Events ───
        if event_type in ("push hook", "push"):
            return self._normalize_push(payload)

        # ─── Note (Comment) Events ───
        if event_type in ("note hook", "note"):
            return None  # Ignored for now

        return None

    def _normalize_pipeline(self, payload: dict) -> Optional[NormalizedEvent]:
        """Normalize pipeline webhook events."""
        attrs = payload.get("object_attributes", {})
        status = attrs.get("status", "")

        if status == "failed":
            event_type = EventType.PIPELINE_FAILURE
        elif status == "success":
            event_type = EventType.PIPELINE_SUCCESS
        else:
            return None

        project = payload.get("project", {})
        failed_jobs = []
        error_logs = ""

        for build in payload.get("builds", []):
            if build.get("status") == "failed":
                failed_jobs.append({
                    "id": build.get("id"),
                    "name": build.get("name"),
                    "stage": build.get("stage"),
                    "status": build.get("status"),
                })

        return NormalizedEvent(
            event_type=event_type,
            source="gitlab_webhook",
            project_id=str(project.get("id", "")),
            project_name=project.get("name", ""),
            ref=attrs.get("ref", "main"),
            payload={
                "pipeline_id": attrs.get("id"),
                "pipeline_url": attrs.get("url"),
                "status": status,
                "failed_jobs": failed_jobs,
                "error_logs": error_logs,
                "commit_sha": attrs.get("sha"),
                "commit_message": payload.get("commit", {}).get("message", ""),
                "duration": attrs.get("duration"),
            },
            metadata={
                "user": payload.get("user", {}).get("username"),
                "source": attrs.get("source"),
            },
        )

    def _normalize_merge_request(self, payload: dict) -> Optional[NormalizedEvent]:
        """Normalize merge request webhook events."""
        attrs = payload.get("object_attributes", {})
        action = attrs.get("action", "")

        if action == "open":
            event_type = EventType.MERGE_REQUEST_OPENED
        elif action == "update":
            event_type = EventType.MERGE_REQUEST_UPDATED
        elif action == "merge":
            event_type = EventType.MERGE_REQUEST_MERGED
        else:
            return None

        project = payload.get("project", {})

        return NormalizedEvent(
            event_type=event_type,
            source="gitlab_webhook",
            project_id=str(project.get("id", "")),
            project_name=project.get("name", ""),
            ref=attrs.get("target_branch", "main"),
            payload={
                "mr_id": attrs.get("iid"),
                "mr_title": attrs.get("title"),
                "mr_description": attrs.get("description", ""),
                "source_branch": attrs.get("source_branch"),
                "target_branch": attrs.get("target_branch"),
                "state": attrs.get("state"),
                "action": action,
                "diff": "",  # Would be fetched via API
                "changed_files": [],
            },
            metadata={
                "author": attrs.get("author_id"),
                "assignee": attrs.get("assignee_id"),
                "labels": payload.get("labels", []),
            },
        )

    def _normalize_push(self, payload: dict) -> Optional[NormalizedEvent]:
        """Normalize push webhook events."""
        project = payload.get("project", {})
        commits = payload.get("commits", [])

        if not commits:
            return None

        return NormalizedEvent(
            event_type=EventType.PUSH,
            source="gitlab_webhook",
            project_id=str(project.get("id", "")),
            project_name=project.get("name", ""),
            ref=payload.get("ref", "").replace("refs/heads/", ""),
            payload={
                "before": payload.get("before"),
                "after": payload.get("after"),
                "commits": [
                    {
                        "id": c.get("id"),
                        "message": c.get("message"),
                        "added": c.get("added", []),
                        "modified": c.get("modified", []),
                        "removed": c.get("removed", []),
                    }
                    for c in commits
                ],
                "total_commits": payload.get("total_commits_count", len(commits)),
            },
            metadata={
                "user": payload.get("user_username"),
            },
        )

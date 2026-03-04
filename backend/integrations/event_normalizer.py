"""
AutoForge Event Normalizer — Converts raw GitLab events to structured format.
"""

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
                "diff": "",  # Populated below via API
                "changed_files": [],  # Populated below via API
            },
            metadata={
                "author": attrs.get("author_id"),
                "assignee": attrs.get("assignee_id"),
                "labels": payload.get("labels", []),
                "_needs_diff_fetch": True,
                "_project_id": str(project.get("id", "")),
                "_mr_iid": attrs.get("iid"),
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

    async def enrich_with_diff(self, event: NormalizedEvent) -> NormalizedEvent:
        """
        Fetch MR diff from GitLab API and attach to the event payload.

        Called by the webhook handler after normalization when the event
        has _needs_diff_fetch metadata.
        """
        needs_fetch = event.metadata.get("_needs_diff_fetch", False)
        if not needs_fetch:
            return event

        project_id = event.metadata.get("_project_id", event.project_id)
        mr_iid = event.metadata.get("_mr_iid")
        if not project_id or not mr_iid:
            return event

        try:
            from integrations.gitlab import MergeRequestService
            mrs = MergeRequestService()
            mr_info = await mrs.get_changes(project_id, mr_iid)

            # Extract diff text and changed file paths
            diff_parts = []
            changed_files = []
            for change in mr_info.changes:
                changed_files.append(change.new_path)
                if change.diff:
                    diff_parts.append(f"--- {change.old_path}\n+++ {change.new_path}\n{change.diff}")

            event.payload["diff"] = "\n".join(diff_parts)[:10000]  # Cap at 10k chars
            event.payload["changed_files"] = changed_files
        except Exception:
            pass  # Diff fetch is best-effort; agents work without it

        return event

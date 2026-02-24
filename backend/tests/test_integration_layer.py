"""
AutoForge — Integration Layer Test Suite.

Tests for the enterprise GitLab integration layer, tool gateway,
and enhanced API endpoints.
"""

import pytest
import asyncio

# Use bare imports (matching runtime path) to avoid dual-module-identity issues
from integrations.gitlab.models import (
    PipelineStatus, MergeRequestState, VulnerabilitySeverity,
    PipelineInfo, JobInfo, MergeRequestInfo, FileContent, BranchInfo,
    CommitAction, CommitResult, VulnerabilityInfo, DependencyAlert,
    APICallTelemetry, GitLabAPIResponse, DiffInfo,
)


# ═══════════════════════════════════════════════════════════════════
# 1.  Pydantic Models
# ═══════════════════════════════════════════════════════════════════

class TestGitLabModels:
    """Tests for integration layer Pydantic models."""

    def test_pipeline_status_enum(self):
        assert PipelineStatus.FAILED.value == "failed"
        assert PipelineStatus.SUCCESS.value == "success"
        assert PipelineStatus.RUNNING.value == "running"
        assert PipelineStatus.PENDING.value == "pending"

    def test_merge_request_state_enum(self):
        assert MergeRequestState.OPENED.value == "opened"
        assert MergeRequestState.MERGED.value == "merged"
        assert MergeRequestState.CLOSED.value == "closed"

    def test_vulnerability_severity_enum(self):
        assert VulnerabilitySeverity.CRITICAL.value == "critical"
        assert VulnerabilitySeverity.HIGH.value == "high"

    def test_pipeline_info_model(self):
        pi = PipelineInfo(
            id=42, project_id=1, ref="main", sha="abc123",
            status=PipelineStatus.SUCCESS,
            web_url="https://gitlab.com/p/42",
        )
        assert pi.id == 42
        assert pi.status == PipelineStatus.SUCCESS

    def test_job_info_model(self):
        ji = JobInfo(id=101, name="build", stage="test", status="failed")
        assert ji.id == 101
        assert ji.name == "build"

    def test_merge_request_info_model(self):
        mr = MergeRequestInfo(
            id=1, iid=7, project_id=1, title="Fix bug",
            state=MergeRequestState.OPENED,
            source_branch="fix/bug", target_branch="main",
            web_url="https://gitlab.com/mr/7",
        )
        assert mr.iid == 7
        assert mr.state == MergeRequestState.OPENED

    def test_file_content_decoded(self):
        import base64
        raw = base64.b64encode(b"hello world").decode()
        fc = FileContent(
            file_name="test.txt", file_path="src/test.txt",
            size=11, encoding="base64", content=raw,
            ref="main",
        )
        assert fc.decoded_content == "hello world"

    def test_file_content_plain(self):
        fc = FileContent(
            file_name="test.txt", file_path="src/test.txt",
            size=5, encoding="text", content="plain",
            ref="main",
        )
        assert fc.decoded_content == "plain"

    def test_branch_info_model(self):
        bi = BranchInfo(name="fix/dep", commit_sha="abc123")
        assert bi.name == "fix/dep"

    def test_commit_action_model(self):
        ca = CommitAction(action="create", file_path="test.py", content="pass")
        assert ca.action == "create"
        assert ca.file_path == "test.py"

    def test_commit_result_model(self):
        cr = CommitResult(
            id="abc123", short_id="abc", title="fix",
            message="fix things", web_url="https://gitlab.com/c/abc",
        )
        assert cr.short_id == "abc"

    def test_vulnerability_info_model(self):
        vi = VulnerabilityInfo(
            id=1, name="SQL Injection",
            severity=VulnerabilitySeverity.HIGH,
            description="Bad query",
        )
        assert vi.severity == VulnerabilitySeverity.HIGH

    def test_dependency_alert_model(self):
        da = DependencyAlert(
            dependency_name="lodash", dependency_version="4.17.20",
            vulnerability="Prototype Pollution", severity="high",
            cve_id="CVE-2021-23337",
        )
        assert da.cve_id == "CVE-2021-23337"

    def test_api_call_telemetry_model(self):
        t = APICallTelemetry(
            tool="get_pipeline", action="GET /pipelines/42",
            success=True, execution_time_ms=150.0,
        )
        assert t.success is True
        assert t.execution_time_ms == 150.0

    def test_gitlab_api_response_ok(self):
        r = GitLabAPIResponse.ok({"id": 1})
        assert r.success is True
        assert r.data == {"id": 1}
        assert r.error is None

    def test_gitlab_api_response_fail(self):
        r = GitLabAPIResponse.fail("not found")
        assert r.success is False
        assert r.error == "not found"

    def test_diff_info_model(self):
        d = DiffInfo(
            old_path="a.py", new_path="a.py", diff="@@ -1 +1 @@\n-old\n+new",
        )
        assert d.old_path == "a.py"


# ═══════════════════════════════════════════════════════════════════
# 2.  Auth helpers
# ═══════════════════════════════════════════════════════════════════

class TestAuth:
    def test_build_headers(self):
        from integrations.gitlab.auth import build_headers
        h = build_headers()
        assert "PRIVATE-TOKEN" in h
        assert h["Content-Type"] == "application/json"
        assert "User-Agent" in h

    def test_sanitize_log_redacts_token(self):
        from integrations.gitlab.auth import sanitize_log
        from config import settings
        # In demo mode the token is empty, so sanitize is a no-op
        if settings.GITLAB_API_TOKEN:
            msg = f"token={settings.GITLAB_API_TOKEN} found"
            sanitized = sanitize_log(msg)
            assert settings.GITLAB_API_TOKEN not in sanitized
        else:
            # No token to redact — function should still return the message
            msg = "no token here"
            assert sanitize_log(msg) == msg

    def test_is_forbidden_path(self):
        from integrations.gitlab.auth import is_forbidden_path
        assert is_forbidden_path(".env") is True
        assert is_forbidden_path("secrets.yml") is True
        assert is_forbidden_path("id_rsa") is True
        assert is_forbidden_path("src/main.py") is False
        assert is_forbidden_path("README.md") is False

    def test_get_base_url(self):
        from integrations.gitlab.auth import get_base_url
        url = get_base_url()
        assert url.startswith("http")
        assert "gitlab" in url.lower()


# ═══════════════════════════════════════════════════════════════════
# 3.  Retry handler
# ═══════════════════════════════════════════════════════════════════

class TestRetryHandler:
    def test_retryable_status_codes(self):
        from integrations.gitlab.retry_handler import is_retryable_status
        assert is_retryable_status(429) is True
        assert is_retryable_status(500) is True
        assert is_retryable_status(502) is True
        assert is_retryable_status(503) is True
        assert is_retryable_status(504) is True
        assert is_retryable_status(200) is False
        assert is_retryable_status(404) is False

    def test_retry_exhausted_exception(self):
        from integrations.gitlab.retry_handler import RetryExhausted
        exc = RetryExhausted(attempts=3, last_error=ValueError("gave up"))
        assert "gave up" in str(exc)
        assert exc.attempts == 3

    @pytest.mark.asyncio
    async def test_retry_async_succeeds_first_try(self):
        from integrations.gitlab.retry_handler import retry_async

        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await retry_async(fn, max_attempts=3)
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_async_retries_on_failure(self):
        from integrations.gitlab.retry_handler import retry_async

        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("transient")
            return "ok"

        result = await retry_async(
            fn, max_attempts=5, base_delay=0.01,
            retryable_exceptions=(ValueError,),
        )
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_async_exhausted(self):
        from integrations.gitlab.retry_handler import retry_async, RetryExhausted

        async def fn():
            raise ValueError("permanent")

        with pytest.raises(RetryExhausted):
            await retry_async(
                fn, max_attempts=2, base_delay=0.01,
                retryable_exceptions=(ValueError,),
            )


# ═══════════════════════════════════════════════════════════════════
# 4.  Rate limiter
# ═══════════════════════════════════════════════════════════════════

class TestRateLimiter:
    def test_rate_limiter_creation(self):
        from integrations.gitlab.rate_limiter import RateLimiter
        rl = RateLimiter(requests_per_second=10.0)
        assert rl is not None

    @pytest.mark.asyncio
    async def test_rate_limiter_acquire(self):
        from integrations.gitlab.rate_limiter import RateLimiter
        rl = RateLimiter(requests_per_second=100.0)
        # Should not block / raise
        await rl.acquire()

    def test_rate_limiter_update_from_headers(self):
        from integrations.gitlab.rate_limiter import RateLimiter
        rl = RateLimiter()
        rl.update_from_headers({
            "ratelimit-remaining": "50",
            "ratelimit-reset": "1700000000",
        })
        assert rl._remaining == 50


# ═══════════════════════════════════════════════════════════════════
# 5.  Demo-mode simulator
# ═══════════════════════════════════════════════════════════════════

class TestDemoModeSimulator:
    def test_get_pipeline(self):
        from integrations.gitlab.demo_mode import DemoModeSimulator
        pi = DemoModeSimulator.get_pipeline("proj-1", 42)
        assert isinstance(pi, PipelineInfo)
        assert pi.id == 42

    def test_get_pipeline_jobs(self):
        from integrations.gitlab.demo_mode import DemoModeSimulator
        jobs = DemoModeSimulator.get_pipeline_jobs("proj-1", 42)
        assert isinstance(jobs, list)
        assert all(isinstance(j, JobInfo) for j in jobs)
        assert len(jobs) > 0

    def test_get_job_log(self):
        from integrations.gitlab.demo_mode import DemoModeSimulator
        log = DemoModeSimulator.get_job_log("proj-1", 101)
        assert isinstance(log, str)
        assert len(log) > 0

    def test_retry_pipeline(self):
        from integrations.gitlab.demo_mode import DemoModeSimulator
        pi = DemoModeSimulator.retry_pipeline("proj-1", 42)
        assert isinstance(pi, PipelineInfo)

    def test_trigger_pipeline(self):
        from integrations.gitlab.demo_mode import DemoModeSimulator
        pi = DemoModeSimulator.trigger_pipeline("proj-1", "main")
        assert isinstance(pi, PipelineInfo)

    def test_create_merge_request(self):
        from integrations.gitlab.demo_mode import DemoModeSimulator
        mr = DemoModeSimulator.create_merge_request(
            "proj-1", "fix/dep", "main", "Fix", "desc",
        )
        assert isinstance(mr, MergeRequestInfo)
        assert mr.source_branch == "fix/dep"

    def test_comment_on_mr(self):
        from integrations.gitlab.demo_mode import DemoModeSimulator
        result = DemoModeSimulator.comment_on_mr("proj-1", 7, "LGTM")
        assert result is not None

    def test_approve_mr(self):
        from integrations.gitlab.demo_mode import DemoModeSimulator
        result = DemoModeSimulator.approve_mr("proj-1", 7)
        assert result is not None

    def test_get_mr_changes(self):
        from integrations.gitlab.demo_mode import DemoModeSimulator
        result = DemoModeSimulator.get_mr_changes("proj-1", 7)
        # get_mr_changes returns a MergeRequestInfo (not a list)
        assert isinstance(result, MergeRequestInfo)

    def test_get_file(self):
        from integrations.gitlab.demo_mode import DemoModeSimulator
        fc = DemoModeSimulator.get_file("proj-1", "requirements.txt", "main")
        assert isinstance(fc, FileContent)
        assert "requirements" in fc.file_name

    def test_update_file(self):
        from integrations.gitlab.demo_mode import DemoModeSimulator
        result = DemoModeSimulator.update_file(
            "proj-1", "test.py", "pass", "fix/branch", "commit msg",
        )
        assert result is not None

    def test_create_branch(self):
        from integrations.gitlab.demo_mode import DemoModeSimulator
        bi = DemoModeSimulator.create_branch("proj-1", "fix/dep", "main")
        assert isinstance(bi, BranchInfo)
        assert bi.name == "fix/dep"

    def test_create_commit(self):
        from integrations.gitlab.demo_mode import DemoModeSimulator
        actions = [CommitAction(action="create", file_path="a.py", content="pass")]
        cr = DemoModeSimulator.create_commit("proj-1", "fix/br", "msg", actions)
        assert isinstance(cr, CommitResult)

    def test_get_vulnerabilities(self):
        from integrations.gitlab.demo_mode import DemoModeSimulator
        vulns = DemoModeSimulator.get_vulnerabilities("proj-1")
        assert isinstance(vulns, list)
        assert len(vulns) >= 1
        assert all(isinstance(v, VulnerabilityInfo) for v in vulns)

    def test_get_dependency_alerts(self):
        from integrations.gitlab.demo_mode import DemoModeSimulator
        alerts = DemoModeSimulator.get_dependency_alerts("proj-1")
        assert isinstance(alerts, list)
        assert len(alerts) >= 1
        assert all(isinstance(a, DependencyAlert) for a in alerts)


# ═══════════════════════════════════════════════════════════════════
# 6.  Service layers (demo mode — no real API calls)
# ═══════════════════════════════════════════════════════════════════

class TestPipelineService:
    @pytest.mark.asyncio
    async def test_get_pipeline(self):
        from integrations.gitlab.pipelines import PipelineService
        svc = PipelineService()
        pi = await svc.get_pipeline("proj-1", 42)
        assert pi.id == 42

    @pytest.mark.asyncio
    async def test_get_pipeline_jobs(self):
        from integrations.gitlab.pipelines import PipelineService
        svc = PipelineService()
        jobs = await svc.get_pipeline_jobs("proj-1", 42)
        assert len(jobs) > 0

    @pytest.mark.asyncio
    async def test_get_failed_jobs(self):
        from integrations.gitlab.pipelines import PipelineService
        svc = PipelineService()
        failed = await svc.get_failed_jobs("proj-1", 42)
        assert isinstance(failed, list)
        for j in failed:
            assert j.status == "failed"

    @pytest.mark.asyncio
    async def test_get_job_log(self):
        from integrations.gitlab.pipelines import PipelineService
        svc = PipelineService()
        log = await svc.get_job_log("proj-1", 101)
        assert isinstance(log, str)

    @pytest.mark.asyncio
    async def test_retry_pipeline(self):
        from integrations.gitlab.pipelines import PipelineService
        svc = PipelineService()
        pi = await svc.retry_pipeline("proj-1", 42)
        assert pi.id is not None

    @pytest.mark.asyncio
    async def test_trigger_pipeline(self):
        from integrations.gitlab.pipelines import PipelineService
        svc = PipelineService()
        pi = await svc.trigger_pipeline("proj-1", "main")
        assert pi.id is not None


class TestRepositoryService:
    @pytest.mark.asyncio
    async def test_get_file(self):
        from integrations.gitlab.repository import RepositoryService
        svc = RepositoryService()
        fc = await svc.get_file("proj-1", "requirements.txt")
        assert fc.file_name == "requirements.txt"

    @pytest.mark.asyncio
    async def test_create_branch(self):
        from integrations.gitlab.repository import RepositoryService
        svc = RepositoryService()
        bi = await svc.create_branch("proj-1", "fix/dep", "main")
        assert bi.name == "fix/dep"

    @pytest.mark.asyncio
    async def test_update_file(self):
        from integrations.gitlab.repository import RepositoryService
        svc = RepositoryService()
        result = await svc.update_file(
            "proj-1", "src/app.py", "new content",
            "fix/dep", "update file",
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_guard_blocks_forbidden_path(self):
        from integrations.gitlab.repository import RepositoryService
        svc = RepositoryService()
        with pytest.raises(PermissionError):
            await svc.update_file(
                "proj-1", ".env", "secrets",
                "fix/dep", "update secrets",
            )

    @pytest.mark.asyncio
    async def test_guard_blocks_protected_branch(self):
        from integrations.gitlab.repository import RepositoryService
        svc = RepositoryService()
        with pytest.raises(PermissionError):
            await svc.update_file(
                "proj-1", "src/app.py", "content",
                "main", "direct commit to main",
            )


class TestMergeRequestService:
    @pytest.mark.asyncio
    async def test_create_mr(self):
        from integrations.gitlab.merge_requests import MergeRequestService
        svc = MergeRequestService()
        mr = await svc.create(
            "proj-1", "fix/dep", "main", "Fix deps", "desc",
        )
        assert mr.iid is not None
        assert mr.source_branch == "fix/dep"

    @pytest.mark.asyncio
    async def test_comment_on_mr(self):
        from integrations.gitlab.merge_requests import MergeRequestService
        svc = MergeRequestService()
        result = await svc.comment("proj-1", 7, "Looks good!")
        assert result is not None

    @pytest.mark.asyncio
    async def test_approve_mr(self):
        from integrations.gitlab.merge_requests import MergeRequestService
        svc = MergeRequestService()
        result = await svc.approve("proj-1", 7)
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_changes(self):
        from integrations.gitlab.merge_requests import MergeRequestService
        svc = MergeRequestService()
        mr = await svc.get_changes("proj-1", 7)
        # get_changes returns a MergeRequestInfo
        assert isinstance(mr, MergeRequestInfo)

    @pytest.mark.asyncio
    async def test_get_merge_request(self):
        from integrations.gitlab.merge_requests import MergeRequestService
        svc = MergeRequestService()
        mr = await svc.get_merge_request("proj-1", 7)
        assert mr.iid == 7


class TestCommitService:
    @pytest.mark.asyncio
    async def test_create_commit(self):
        from integrations.gitlab.commits import CommitService
        svc = CommitService()
        actions = [
            CommitAction(action="create", file_path="tests/test_new.py", content="pass"),
            CommitAction(action="create", file_path="tests/test_other.py", content="pass"),
        ]
        cr = await svc.create_commit(
            "proj-1", "fix/dep", "add tests", actions,
        )
        assert cr.id is not None
        assert cr.message is not None

    @pytest.mark.asyncio
    async def test_create_commit_rejects_empty_actions(self):
        from integrations.gitlab.commits import CommitService
        svc = CommitService()
        with pytest.raises(ValueError):
            await svc.create_commit("proj-1", "fix/dep", "empty", [])

    @pytest.mark.asyncio
    async def test_create_commit_rejects_protected_branch(self):
        from integrations.gitlab.commits import CommitService
        svc = CommitService()
        actions = [CommitAction(action="create", file_path="a.py", content="pass")]
        with pytest.raises(PermissionError):
            await svc.create_commit("proj-1", "main", "bad commit", actions)

    @pytest.mark.asyncio
    async def test_create_commit_rejects_forbidden_path(self):
        from integrations.gitlab.commits import CommitService
        svc = CommitService()
        actions = [CommitAction(action="create", file_path=".env", content="SECRET=x")]
        with pytest.raises(PermissionError):
            await svc.create_commit("proj-1", "fix/dep", "bad path", actions)


class TestSecurityService:
    @pytest.mark.asyncio
    async def test_get_vulnerabilities(self):
        from integrations.gitlab.security import SecurityService
        svc = SecurityService()
        vulns = await svc.get_vulnerabilities("proj-1")
        assert len(vulns) >= 1
        for v in vulns:
            assert v.severity is not None

    @pytest.mark.asyncio
    async def test_get_dependency_alerts(self):
        from integrations.gitlab.security import SecurityService
        svc = SecurityService()
        alerts = await svc.get_dependency_alerts("proj-1")
        assert len(alerts) >= 1

    @pytest.mark.asyncio
    async def test_get_critical_vulnerabilities(self):
        from integrations.gitlab.security import SecurityService
        svc = SecurityService()
        criticals = await svc.get_critical_vulnerabilities("proj-1")
        for v in criticals:
            assert v.severity.value in ("critical", "high")


# ═══════════════════════════════════════════════════════════════════
# 7.  Webhook processor
# ═══════════════════════════════════════════════════════════════════

class TestWebhookProcessor:
    def test_validate_token_correct(self):
        from integrations.gitlab.webhooks import WebhookProcessor
        wp = WebhookProcessor(webhook_secret="test-secret")
        assert wp.validate_token("test-secret") is True

    def test_validate_token_wrong(self):
        from integrations.gitlab.webhooks import WebhookProcessor
        wp = WebhookProcessor(webhook_secret="test-secret")
        assert wp.validate_token("wrong") is False

    def test_validate_token_none_secret(self):
        from integrations.gitlab.webhooks import WebhookProcessor
        wp = WebhookProcessor(webhook_secret="")
        assert wp.validate_token(None) is True  # no secret → accept all

    def test_parse_pipeline_failure(self):
        from integrations.gitlab.webhooks import WebhookProcessor
        from models.events import EventType
        wp = WebhookProcessor(webhook_secret="")
        event, raw = wp.parse("Pipeline Hook", {
            "object_attributes": {"id": 42, "ref": "main", "status": "failed", "sha": "abc"},
            "project": {"id": 1},
        })
        assert event is not None
        assert event.event_type == EventType.PIPELINE_FAILURE
        assert event.project_id == "1"
        assert event.payload["pipeline_id"] == 42

    def test_parse_pipeline_success(self):
        from integrations.gitlab.webhooks import WebhookProcessor
        from models.events import EventType
        wp = WebhookProcessor(webhook_secret="")
        event, _ = wp.parse("Pipeline Hook", {
            "object_attributes": {"id": 43, "ref": "main", "status": "success", "sha": "def"},
            "project": {"id": 2},
        })
        assert event.event_type == EventType.PIPELINE_SUCCESS

    def test_parse_merge_request_opened(self):
        from integrations.gitlab.webhooks import WebhookProcessor
        from models.events import EventType
        wp = WebhookProcessor(webhook_secret="")
        event, _ = wp.parse("Merge Request Hook", {
            "object_attributes": {
                "iid": 7, "action": "open", "title": "Fix",
                "source_branch": "fix/b", "target_branch": "main",
                "state": "opened", "url": "http://x",
            },
            "project": {"id": 1},
            "user": {"username": "dev"},
        })
        assert event.event_type == EventType.MERGE_REQUEST_OPENED

    def test_parse_merge_request_merged(self):
        from integrations.gitlab.webhooks import WebhookProcessor
        from models.events import EventType
        wp = WebhookProcessor(webhook_secret="")
        event, _ = wp.parse("Merge Request Hook", {
            "object_attributes": {
                "iid": 7, "action": "merge", "title": "Fix",
                "source_branch": "fix/b", "target_branch": "main",
                "state": "merged", "url": "http://x",
            },
            "project": {"id": 1},
            "user": {"username": "dev"},
        })
        assert event.event_type == EventType.MERGE_REQUEST_MERGED

    def test_parse_push(self):
        from integrations.gitlab.webhooks import WebhookProcessor
        from models.events import EventType
        wp = WebhookProcessor(webhook_secret="")
        event, _ = wp.parse("Push Hook", {
            "project_id": 1, "ref": "refs/heads/main",
            "before": "aaa", "after": "bbb",
            "user_username": "dev",
            "total_commits_count": 2,
            "commits": [{"id": "c1", "message": "m1", "author": {"name": "dev"}}],
        })
        assert event.event_type == EventType.PUSH
        assert event.payload["total_commits_count"] == 2

    def test_parse_issue(self):
        from integrations.gitlab.webhooks import WebhookProcessor
        from models.events import EventType
        wp = WebhookProcessor(webhook_secret="")
        event, _ = wp.parse("Issue Hook", {
            "object_attributes": {
                "iid": 5, "action": "open", "title": "Bug",
                "description": "Something broke",
            },
            "project": {"id": 1},
            "user": {"username": "reporter"},
            "labels": [{"title": "bug"}],
        })
        assert event.event_type == EventType.ISSUE_CREATED

    def test_parse_unknown_event(self):
        from integrations.gitlab.webhooks import WebhookProcessor
        wp = WebhookProcessor(webhook_secret="")
        event, _ = wp.parse("Unknown Hook", {})
        assert event is None


# ═══════════════════════════════════════════════════════════════════
# 8.  Event normalizer facade
# ═══════════════════════════════════════════════════════════════════

class TestGitLabEventNormalizer:
    def test_normalize_pipeline(self):
        from integrations.gitlab.event_normalizer import GitLabEventNormalizer
        norm = GitLabEventNormalizer()
        event = norm.normalize("Pipeline Hook", {
            "object_attributes": {"id": 1, "ref": "main", "status": "failed", "sha": "x"},
            "project": {"id": 10},
        })
        assert event is not None
        assert event.event_type.value == "pipeline_failure"

    def test_normalize_returns_none_for_unknown(self):
        from integrations.gitlab.event_normalizer import GitLabEventNormalizer
        norm = GitLabEventNormalizer()
        assert norm.normalize("Foo Hook", {}) is None


# ═══════════════════════════════════════════════════════════════════
# 9.  GitLab API client (demo mode)
# ═══════════════════════════════════════════════════════════════════

class TestGitLabAPIClient:
    def test_client_creation(self):
        from integrations.gitlab.gitlab_client import GitLabAPIClient
        client = GitLabAPIClient()
        assert client is not None

    def test_client_has_telemetry_log(self):
        from integrations.gitlab.gitlab_client import GitLabAPIClient
        client = GitLabAPIClient()
        assert isinstance(client._telemetry_log, list)

    def test_gitlab_api_error(self):
        from integrations.gitlab.gitlab_client import GitLabAPIError
        err = GitLabAPIError("test error", status_code=404)
        assert err.status_code == 404
        assert "test error" in str(err)


# ═══════════════════════════════════════════════════════════════════
# 10. Tool Gateway
# ═══════════════════════════════════════════════════════════════════

class TestToolGateway:
    @pytest.mark.asyncio
    async def test_create_branch(self):
        from tools.tool_gateway import ToolGateway
        gw = ToolGateway()
        result = await gw.create_branch("proj-1", "fix/dep", agent="SRE")
        assert result.success is True
        assert result.data["branch"] == "fix/dep"
        assert result.tool == "create_branch"
        assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_edit_file(self):
        from tools.tool_gateway import ToolGateway
        gw = ToolGateway()
        result = await gw.edit_file(
            "proj-1", "src/app.py", "print('hi')", "fix/dep", "edit",
        )
        assert result.success is True
        assert result.tool == "edit_file"

    @pytest.mark.asyncio
    async def test_get_file_content(self):
        from tools.tool_gateway import ToolGateway
        gw = ToolGateway()
        result = await gw.get_file_content("proj-1", "requirements.txt")
        assert result.success is True
        assert "content" in result.data

    @pytest.mark.asyncio
    async def test_create_merge_request(self):
        from tools.tool_gateway import ToolGateway
        gw = ToolGateway()
        result = await gw.create_merge_request(
            "proj-1", "fix/dep", "main", "Fix dependency",
        )
        assert result.success is True
        assert "mr_iid" in result.data

    @pytest.mark.asyncio
    async def test_comment_on_mr(self):
        from tools.tool_gateway import ToolGateway
        gw = ToolGateway()
        result = await gw.comment_on_mr("proj-1", 7, "LGTM")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_rerun_pipeline(self):
        from tools.tool_gateway import ToolGateway
        gw = ToolGateway()
        result = await gw.rerun_pipeline("proj-1", 42)
        assert result.success is True
        assert "pipeline_id" in result.data

    @pytest.mark.asyncio
    async def test_get_pipeline_logs(self):
        from tools.tool_gateway import ToolGateway
        gw = ToolGateway()
        result = await gw.get_pipeline_logs("proj-1", 42)
        assert result.success is True
        assert "logs" in result.data

    @pytest.mark.asyncio
    async def test_generate_tests(self):
        from tools.tool_gateway import ToolGateway
        gw = ToolGateway()
        files = [
            {"path": "tests/test_a.py", "content": "def test_a(): pass"},
            {"path": "tests/test_b.py", "content": "def test_b(): pass"},
        ]
        result = await gw.generate_tests("proj-1", files, "fix/dep")
        assert result.success is True
        assert result.data.get("files_created", 0) == 2

    @pytest.mark.asyncio
    async def test_update_docs(self):
        from tools.tool_gateway import ToolGateway
        gw = ToolGateway()
        docs = [{"path": "docs/README.md", "content": "# Docs"}]
        result = await gw.update_docs("proj-1", docs, "fix/dep")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_fetch_security_alerts(self):
        from tools.tool_gateway import ToolGateway
        gw = ToolGateway()
        result = await gw.fetch_security_alerts("proj-1")
        assert result.success is True
        assert "vulnerabilities" in result.data
        assert "dependency_alerts" in result.data
        assert result.data["total_findings"] > 0

    @pytest.mark.asyncio
    async def test_fetch_critical_vulnerabilities(self):
        from tools.tool_gateway import ToolGateway
        gw = ToolGateway()
        result = await gw.fetch_critical_vulnerabilities("proj-1")
        assert result.success is True

    def test_tool_result_to_dict(self):
        from tools.tool_gateway import ToolResult
        r = ToolResult(success=True, data={"x": 1}, tool="test", execution_time_ms=5.0)
        d = r.to_dict()
        assert d["success"] is True
        assert d["data"]["x"] == 1
        assert d["tool"] == "test"

    def test_tool_result_error_to_dict(self):
        from tools.tool_gateway import ToolResult
        r = ToolResult(success=False, error="boom", tool="test")
        d = r.to_dict()
        assert d["success"] is False
        assert d["error"] == "boom"


# ═══════════════════════════════════════════════════════════════════
# 11. GitLabTools compatibility shim
# ═══════════════════════════════════════════════════════════════════

class TestGitLabToolsShim:
    @pytest.mark.asyncio
    async def test_create_branch(self):
        from tools.gitlab_tools import GitLabTools
        tools = GitLabTools()
        result = await tools.create_branch("proj-1", "fix/dep")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_edit_file(self):
        from tools.gitlab_tools import GitLabTools
        tools = GitLabTools()
        result = await tools.edit_file(
            "proj-1", "src/app.py", "code", "fix/dep", "msg",
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_create_merge_request(self):
        from tools.gitlab_tools import GitLabTools
        tools = GitLabTools()
        result = await tools.create_merge_request(
            "proj-1", "fix/dep", "main", "Title",
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_rerun_pipeline(self):
        from tools.gitlab_tools import GitLabTools
        tools = GitLabTools()
        result = await tools.rerun_pipeline("proj-1", 42)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_comment_on_mr(self):
        from tools.gitlab_tools import GitLabTools
        tools = GitLabTools()
        result = await tools.comment_on_mr("proj-1", 7, "Nice!")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_get_file_content(self):
        from tools.gitlab_tools import GitLabTools
        tools = GitLabTools()
        result = await tools.get_file_content("proj-1", "requirements.txt")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_get_pipeline_logs(self):
        from tools.gitlab_tools import GitLabTools
        tools = GitLabTools()
        result = await tools.get_pipeline_logs("proj-1", 42)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_generate_tests(self):
        from tools.gitlab_tools import GitLabTools
        tools = GitLabTools()
        files = [{"path": "tests/t.py", "content": "pass"}]
        result = await tools.generate_tests("proj-1", files, "fix/dep")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_update_docs(self):
        from tools.gitlab_tools import GitLabTools
        tools = GitLabTools()
        docs = [{"path": "docs/README.md", "content": "# Hi"}]
        result = await tools.update_docs("proj-1", docs, "fix/dep")
        assert result["success"] is True


# ═══════════════════════════════════════════════════════════════════
# 12. Package-level imports
# ═══════════════════════════════════════════════════════════════════

class TestPackageImports:
    def test_gitlab_package_exports(self):
        from integrations.gitlab import (
            GitLabAPIClient,
            PipelineService,
            MergeRequestService,
            RepositoryService,
            CommitService,
            SecurityService,
            WebhookProcessor,
            GitLabEventNormalizer,
            DemoModeSimulator,
            PipelineInfo,
            JobInfo,
            MergeRequestInfo,
            FileContent,
            BranchInfo,
            CommitResult,
            VulnerabilityInfo,
            GitLabAPIResponse,
        )
        assert GitLabAPIClient is not None
        assert PipelineService is not None
        assert MergeRequestService is not None
        assert RepositoryService is not None
        assert CommitService is not None
        assert SecurityService is not None
        assert WebhookProcessor is not None
        assert GitLabEventNormalizer is not None
        assert DemoModeSimulator is not None

"""AutoForge Workflows package."""

from workflows.pipeline_failure import PipelineFailureWorkflow
from workflows.security_alert import SecurityAlertWorkflow
from workflows.merge_request import MergeRequestWorkflow

__all__ = [
    "PipelineFailureWorkflow",
    "SecurityAlertWorkflow",
    "MergeRequestWorkflow",
]

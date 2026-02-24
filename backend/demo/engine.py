"""
AutoForge Demo Engine — Precomputed reasoning trees and deterministic demo paths.

When DEMO_MODE=True, agents use these precomputed results instead of calling Claude.
This guarantees fast, reproducible demos for live presentations.
"""

import json
import os
from typing import Any, Dict, List, Optional


# ─── Precomputed Reasoning Trees ───────────────────────────────────────────────

DEMO_REASONING_TREES: Dict[str, Dict[str, Any]] = {
    "pipeline_failure": {
        "hypotheses": [
            {
                "description": "Missing Python dependency — 'numpy' was removed from requirements.txt during cleanup refactor",
                "probability": 0.92,
                "evidence": [
                    "ModuleNotFoundError: No module named 'numpy'",
                    "Commit message: 'refactor: clean up requirements and remove unused deps'",
                    "3/24 tests failed, all importing numpy",
                    "requirements.txt was recently modified",
                ],
                "risk_if_wrong": 0.1,
                "suggested_action": "Re-add numpy>=1.24.0 to requirements.txt",
            },
            {
                "description": "Test environment mismatch — numpy installed locally but not in CI",
                "probability": 0.05,
                "evidence": [
                    "Tests pass locally but fail in pipeline",
                    "CI uses clean Docker image",
                ],
                "risk_if_wrong": 0.3,
                "suggested_action": "Verify CI Docker image matches dev environment",
            },
            {
                "description": "Transitive dependency removed — another package previously pulled in numpy",
                "probability": 0.02,
                "evidence": [
                    "Indirect dependencies can satisfy imports",
                    "Package cleanup may remove transitive deps",
                ],
                "risk_if_wrong": 0.2,
                "suggested_action": "Run pip freeze and check dependency tree",
            },
            {
                "description": "Wrong Python version in CI — numpy not compatible",
                "probability": 0.005,
                "evidence": [
                    "Python 3.11.4 shown in logs",
                    "numpy supports 3.11",
                ],
                "risk_if_wrong": 0.4,
                "suggested_action": "Check Python version compatibility",
            },
            {
                "description": "Corrupted pip cache in CI runner",
                "probability": 0.005,
                "evidence": [
                    "Rare but possible",
                    "pip install succeeded for other packages",
                ],
                "risk_if_wrong": 0.1,
                "suggested_action": "Clear CI cache and retry",
            },
        ],
        "selected_hypothesis": 0,
        "root_cause": "Missing Python dependency — 'numpy' was removed from requirements.txt during cleanup refactor",
        "confidence": 0.92,
        "risk_score": 0.08,
        "plan": {
            "chosen_hypothesis": 0,
            "chosen_action": "Re-add numpy>=1.24.0 to requirements.txt and pin version",
            "confidence": 0.92,
            "risk_score": 0.08,
            "reasoning": "Root cause is clear: commit removed numpy from requirements.txt, causing ModuleNotFoundError in 3 test files. Fix is low-risk — re-add the pinned dependency.",
            "alternative_actions": [
                "Add numpy to a separate requirements-data.txt",
                "Pin exact version numpy==1.26.4 for reproducibility",
            ],
        },
        "fix_result": {
            "fix_description": "Re-add numpy to requirements.txt with version pin",
            "files_to_modify": [
                {
                    "path": "requirements.txt",
                    "changes": "numpy>=1.24.0,<2.0.0  # Required by data processing and analytics modules",
                }
            ],
            "commit_message": "fix: re-add numpy dependency removed in cleanup refactor",
            "branch_name": "autoforge/fix-missing-numpy",
            "tests_to_add": [
                "tests/test_dependency_check.py — verify all imports resolve",
            ],
        },
        "reflection": {
            "success": True,
            "outcome": "Pipeline failure resolved — numpy dependency restored with version pin",
            "side_effects": [],
            "improvement_suggestions": [
                "Add a CI step that validates all imports before running tests",
                "Use pipdeptree to detect unused vs required dependencies before cleanup",
            ],
            "extracted_skill": "dependency_restoration_after_cleanup",
            "confidence": 0.95,
            "lesson_learned": "Always run full test suite before committing dependency removals",
        },
    },

    "security_vulnerability": {
        "hypotheses": [
            {
                "description": "Known CVE in lodash — prototype pollution vulnerability CVE-2020-28500",
                "probability": 0.95,
                "evidence": [
                    "CVE-2020-28500 matches lodash < 4.17.21",
                    "Current version 4.17.19 is vulnerable",
                    "CVSS score: 7.5 (High)",
                ],
                "risk_if_wrong": 0.05,
                "suggested_action": "Update lodash to >=4.17.21",
            },
            {
                "description": "Transitive dependency also affected",
                "probability": 0.03,
                "evidence": [
                    "Other packages may bundle lodash",
                ],
                "risk_if_wrong": 0.3,
                "suggested_action": "Run npm audit and check all lodash references",
            },
            {
                "description": "False positive from stale vulnerability database",
                "probability": 0.02,
                "evidence": [
                    "Scanner databases can lag behind patches",
                ],
                "risk_if_wrong": 0.5,
                "suggested_action": "Verify CVE against NVD",
            },
        ],
        "selected_hypothesis": 0,
        "root_cause": "Known CVE in lodash — prototype pollution vulnerability CVE-2020-28500",
        "confidence": 0.95,
        "risk_score": 0.05,
        "plan": {
            "chosen_hypothesis": 0,
            "chosen_action": "Update lodash to 4.17.21 in package.json and package-lock.json",
            "confidence": 0.95,
            "risk_score": 0.05,
            "reasoning": "CVE-2020-28500 is a well-documented prototype pollution vulnerability. Updating to 4.17.21 resolves it with no breaking changes.",
            "alternative_actions": [
                "Apply selective override in package.json resolutions",
                "Replace lodash with lodash-es for tree-shaking",
            ],
        },
        "reflection": {
            "success": True,
            "outcome": "Security vulnerability patched — lodash updated to safe version",
            "side_effects": [],
            "improvement_suggestions": [
                "Enable automated dependency update bot (Dependabot/Renovate)",
                "Add npm audit as a CI gate step",
            ],
            "extracted_skill": "dependency_version_patching",
            "confidence": 0.97,
            "lesson_learned": "Pin security-critical dependencies and automate vulnerability scanning",
        },
    },

    "merge_request_opened": {
        "hypotheses": [
            {
                "description": "Code changes introduce performance regression in database queries",
                "probability": 0.35,
                "evidence": [
                    "New query added without index consideration",
                    "N+1 query pattern detected in review",
                ],
                "risk_if_wrong": 0.3,
                "suggested_action": "Add database index and optimize query",
            },
            {
                "description": "Missing input validation on new API endpoint",
                "probability": 0.30,
                "evidence": [
                    "New endpoint lacks request body validation",
                    "No error handling for malformed input",
                ],
                "risk_if_wrong": 0.4,
                "suggested_action": "Add Pydantic models for request validation",
            },
            {
                "description": "Insufficient test coverage for new feature",
                "probability": 0.25,
                "evidence": [
                    "No new test files added",
                    "Changed logic paths not covered",
                ],
                "risk_if_wrong": 0.2,
                "suggested_action": "Add unit and integration tests",
            },
            {
                "description": "Code style violations and inconsistencies",
                "probability": 0.10,
                "evidence": [
                    "Mixed naming conventions",
                    "Unused imports detected",
                ],
                "risk_if_wrong": 0.05,
                "suggested_action": "Apply linter and formatter",
            },
        ],
        "selected_hypothesis": 0,
        "root_cause": "Code changes introduce performance regression in database queries",
        "confidence": 0.78,
        "risk_score": 0.22,
        "plan": {
            "chosen_hypothesis": 0,
            "chosen_action": "Post review with performance findings and test suggestions",
            "confidence": 0.78,
            "risk_score": 0.22,
            "reasoning": "MR introduces new query patterns that could cause N+1 issues at scale. Recommend adding index and batch loading.",
        },
        "reflection": {
            "success": True,
            "outcome": "Code review posted with 3 issues found, quality score 72%",
            "confidence": 0.80,
            "extracted_skill": "code_review_performance_pattern",
        },
    },

    "inefficient_pipeline": {
        "hypotheses": [
            {
                "description": "Pipeline has redundant build stages that can be parallelized",
                "probability": 0.60,
                "evidence": [
                    "Sequential stages with no data dependency",
                    "Build and lint can run in parallel",
                    "30% of pipeline time is wait time",
                ],
                "risk_if_wrong": 0.1,
                "suggested_action": "Restructure .gitlab-ci.yml to parallelize independent stages",
            },
            {
                "description": "Docker layer caching not utilized",
                "probability": 0.25,
                "evidence": [
                    "Full rebuild every pipeline run",
                    "Base image rarely changes",
                ],
                "risk_if_wrong": 0.2,
                "suggested_action": "Enable Docker layer caching in CI",
            },
            {
                "description": "Oversized runner allocation — using 4 cores when 2 suffice",
                "probability": 0.15,
                "evidence": [
                    "CPU utilization averages 30%",
                    "Memory usage under 2GB on 8GB runner",
                ],
                "risk_if_wrong": 0.15,
                "suggested_action": "Downsize runner to small instance",
            },
        ],
        "selected_hypothesis": 0,
        "root_cause": "Pipeline has redundant build stages that can be parallelized",
        "confidence": 0.82,
        "risk_score": 0.18,
        "plan": {
            "chosen_hypothesis": 0,
            "chosen_action": "Suggest pipeline restructuring with parallel stages and caching",
            "confidence": 0.82,
            "risk_score": 0.18,
            "reasoning": "Pipeline restructuring can reduce duration by ~40% and energy consumption by ~35% through parallelization and caching.",
        },
        "reflection": {
            "success": True,
            "outcome": "Pipeline efficiency analysis complete — 3 optimizations suggested saving ~40% runtime",
            "confidence": 0.85,
            "extracted_skill": "pipeline_optimization_parallel_stages",
        },
    },
}


# ─── Precomputed Energy/Carbon Estimates ───────────────────────────────────────

DEMO_ENERGY_ESTIMATES: Dict[str, Dict[str, Any]] = {
    "pipeline_failure": {
        "energy_kwh": 0.0108,
        "carbon_kg": 0.00000513,
        "retry_waste_kwh": 0.0,
        "efficiency_score": 85,
        "optimizations": [
            {"suggestion": "Cache pip dependencies between runs", "estimated_savings_percent": 15.0, "priority": "high"},
            {"suggestion": "Use smaller Docker base image (slim)", "estimated_savings_percent": 10.0, "priority": "medium"},
            {"suggestion": "Run linting in parallel with tests", "estimated_savings_percent": 20.0, "priority": "high"},
        ],
        "waste_sources": [
            {"source": "Full pip install on every run", "waste_percent": 15.0},
            {"source": "Oversized base image layers", "waste_percent": 8.0},
        ],
    },
    "security_vulnerability": {
        "energy_kwh": 0.0054,
        "carbon_kg": 0.00000257,
        "retry_waste_kwh": 0.0,
        "efficiency_score": 92,
        "optimizations": [
            {"suggestion": "Run security scans only on changed files", "estimated_savings_percent": 25.0, "priority": "high"},
            {"suggestion": "Cache npm audit database locally", "estimated_savings_percent": 10.0, "priority": "low"},
        ],
        "waste_sources": [
            {"source": "Full-repo scan when only 2 files changed", "waste_percent": 20.0},
        ],
    },
    "inefficient_pipeline": {
        "energy_kwh": 0.0216,
        "carbon_kg": 0.00001026,
        "retry_waste_kwh": 0.0086,
        "efficiency_score": 55,
        "optimizations": [
            {"suggestion": "Parallelize build and lint stages", "estimated_savings_percent": 35.0, "priority": "critical"},
            {"suggestion": "Enable Docker layer caching", "estimated_savings_percent": 20.0, "priority": "high"},
            {"suggestion": "Downsize CI runner from large to medium", "estimated_savings_percent": 15.0, "priority": "medium"},
            {"suggestion": "Skip unchanged service rebuilds in monorepo", "estimated_savings_percent": 25.0, "priority": "high"},
        ],
        "waste_sources": [
            {"source": "Sequential stages with no data dependency", "waste_percent": 30.0},
            {"source": "Full rebuild every run (no layer cache)", "waste_percent": 20.0},
            {"source": "Oversized runner allocation", "waste_percent": 15.0},
        ],
    },
}


def get_demo_scenario(event_type: str) -> Optional[Dict[str, Any]]:
    """Get the full precomputed demo scenario for an event type."""
    return DEMO_REASONING_TREES.get(event_type)


def get_demo_hypotheses(event_type: str) -> List[Dict[str, Any]]:
    """Get precomputed hypotheses for a demo scenario."""
    scenario = DEMO_REASONING_TREES.get(event_type, {})
    return scenario.get("hypotheses", [])


def get_demo_plan(event_type: str) -> Dict[str, Any]:
    """Get precomputed plan for a demo scenario."""
    scenario = DEMO_REASONING_TREES.get(event_type, {})
    return scenario.get("plan", {})


def get_demo_fix(event_type: str) -> Dict[str, Any]:
    """Get precomputed fix result for a demo scenario."""
    scenario = DEMO_REASONING_TREES.get(event_type, {})
    return scenario.get("fix_result", {})


def get_demo_reflection(event_type: str) -> Dict[str, Any]:
    """Get precomputed reflection for a demo scenario."""
    scenario = DEMO_REASONING_TREES.get(event_type, {})
    return scenario.get("reflection", {})


def get_demo_energy(event_type: str) -> Dict[str, Any]:
    """Get precomputed energy estimates for a demo scenario."""
    return DEMO_ENERGY_ESTIMATES.get(event_type, DEMO_ENERGY_ESTIMATES.get("pipeline_failure", {}))


def load_demo_scenario_file(name: str) -> Optional[Dict[str, Any]]:
    """Load a demo scenario JSON file."""
    scenario_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "demo_scenarios")
    filepath = os.path.join(scenario_dir, f"{name}.json")
    if os.path.exists(filepath):
        with open(filepath) as f:
            return json.load(f)
    return None

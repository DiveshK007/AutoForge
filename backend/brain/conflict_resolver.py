"""
AutoForge Conflict Resolver — Prevents conflicting agent actions.
"""

from typing import List, Set

from models.workflows import AgentTask, TaskStatus


class ConflictResolver:
    """
    Resolves conflicts between agent tasks.

    Prevents:
    - Two agents editing the same file
    - Redundant fixes
    - Contradictory actions
    """

    def resolve(self, tasks: List[AgentTask]) -> List[AgentTask]:
        """Resolve conflicts across a list of tasks."""
        seen_files: Set[str] = set()
        seen_actions: Set[str] = set()

        for task in tasks:
            # Check for duplicate actions
            action_key = f"{task.agent_type}:{task.action}"
            if action_key in seen_actions:
                task.status = TaskStatus.SKIPPED
                continue
            seen_actions.add(action_key)

            # Check for file conflicts
            target_files = task.input_data.get("target_files", [])
            for f in target_files:
                if f in seen_files:
                    # Conflict detected — lower priority tasks get skipped
                    # The higher priority task (earlier in list) keeps running
                    task.status = TaskStatus.SKIPPED
                    break
                seen_files.add(f)

        return tasks

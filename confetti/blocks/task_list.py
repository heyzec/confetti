from __future__ import annotations

from dataclasses import dataclass

from .block import Block

# Marker stripped from output for now; kept here for potential future use:
#   <!-- confetti:task-list -->


@dataclass
class TaskList(Block):
    tasks: list[tuple[int, str, str]]  # (task_id, status, body_md)

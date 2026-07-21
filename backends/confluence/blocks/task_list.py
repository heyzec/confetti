from __future__ import annotations

from dataclasses import dataclass

from .block import Block

# Marker stripped from output for now; kept here for potential future use:
#   <!-- confetti:task-list -->


@dataclass
class TaskListItem:
    task_id: int
    done: bool
    body: list[Block]


@dataclass
class TaskList(Block):
    tasks: list[TaskListItem]

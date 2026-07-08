from __future__ import annotations

from dataclasses import dataclass
from typing import override

from .block import Block

# Marker stripped from output for now; kept here for potential future use:
#   <!-- confetti:task-list -->


@dataclass
class TaskList(Block):
    tasks: list[tuple[int, str, str]]  # (task_id, status, body_md)

    # @classmethod
    # def from_xhtml(cls, element: ET.Element) -> TaskList | None:
    #     ...

    # @classmethod
    # def from_markdown(cls, lines: list[str], i: int) -> tuple[TaskList, int] | None:
    #     ...

    @override
    def to_markdown(self) -> str:
        raise NotImplementedError()

    @override
    def to_xhtml(self) -> str:
        raise NotImplementedError()

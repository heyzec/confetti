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
        lines = []
        for _task_id, status, body_md in self.tasks:
            check = "x" if status == "complete" else " "
            body_lines = body_md.splitlines()
            first = body_lines[0] if body_lines else ""
            rest = ["    " + l for l in body_lines[1:]]
            lines.append(f"- [{check}] {first}")
            lines.extend(rest)
        return "\n".join(lines)

    @override
    def to_xhtml(self) -> str:
        from ..convert import parse_markdown, render_xhtml

        parts = ["<ac:task-list>"]
        for task_id, status, body_md in self.tasks:
            body_xhtml = render_xhtml(parse_markdown(body_md))
            parts.append(
                f"\n<ac:task>"
                f"\n<ac:task-id>{task_id}</ac:task-id>"
                f"\n<ac:task-status>{status}</ac:task-status>"
                f"\n<ac:task-body>{body_xhtml}</ac:task-body>"
                f"\n</ac:task>"
            )
        parts.append("\n</ac:task-list>")
        return "".join(parts)

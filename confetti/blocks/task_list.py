from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import override

from .block import Block

# Marker stripped from output for now; kept here for potential future use:
#   <!-- confetti:task-list -->


@dataclass
class TaskList(Block):
    tasks: list[tuple[int, str, str]]  # (task_id, status, body_md)

    @classmethod
    def from_xhtml(cls, element: ET.Element) -> TaskList | None:
        from ..helpers import (
            _blocks_from_elements,
            _collect_inline,
            _inline_is_simple,
            _is_macro,
            _local,
            _normalize,
        )

        _BLOCK_LOCALS = {
            "p",
            "ul",
            "ol",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "pre",
            "table",
        }

        if not _is_macro(element.tag) or _local(element.tag) != "task-list":
            return None

        tasks: list[tuple[int, str, str]] = []
        for task_el in element:
            if _local(task_el.tag) != "task":
                continue
            task_id = 0
            status = "incomplete"
            body_md = ""
            for child in task_el:
                loc = _local(child.tag)
                if loc == "task-id":
                    task_id = int(child.text or "0")
                elif loc == "task-status":
                    status = child.text or "incomplete"
                elif loc == "task-body":
                    children = list(child)
                    has_block = any(
                        _local(c.tag) in _BLOCK_LOCALS
                        for c in children
                        if not _is_macro(c.tag)
                    )
                    has_direct_text = bool(child.text and child.text.strip())
                    if has_block and not has_direct_text:
                        blocks = _blocks_from_elements(children)
                        body_md = (
                            "\n".join(b.to_markdown() for b in blocks) if blocks else ""
                        )
                    elif _inline_is_simple(child):
                        body_md = _normalize(_collect_inline(child))
                    else:
                        return None  # unsupported body → fall back to RawBlock
            tasks.append((task_id, status, body_md))

        return cls(tasks=tasks)

    @classmethod
    def from_markdown(cls, lines: list[str], i: int) -> tuple[TaskList, int] | None:
        _TASK_GFM = re.compile(r"^[-*]\s+\[([ x])\]\s*(.*)")
        _CONTINUATION = re.compile(r"^ {2,}(.+)")

        if not _TASK_GFM.match(lines[i]):
            return None

        tasks: list[tuple[int, str, str]] = []
        auto_id = 1
        while i < len(lines):
            m = _TASK_GFM.match(lines[i])
            if not m:
                break
            check, body = m.group(1), m.group(2).strip()
            i += 1
            cont: list[str] = []
            while i < len(lines) and _CONTINUATION.match(lines[i]):
                cont.append(_CONTINUATION.match(lines[i]).group(1))  # type: ignore[union-attr]
                i += 1
            if cont:
                body = (body + "\n" if body else "") + "\n".join(cont)
            status = "incomplete" if check == " " else "complete"
            tasks.append((auto_id, status, body))
            auto_id += 1
        if not tasks:
            return None
        return cls(tasks=tasks), i

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
        from ..convert import ir_to_xhtml, markdown_to_ir

        parts = ["<ac:task-list>"]
        for task_id, status, body_md in self.tasks:
            body_xhtml = ir_to_xhtml(markdown_to_ir(body_md))
            parts.append(
                f"\n<ac:task>"
                f"\n<ac:task-id>{task_id}</ac:task-id>"
                f"\n<ac:task-status>{status}</ac:task-status>"
                f"\n<ac:task-body>{body_xhtml}</ac:task-body>"
                f"\n</ac:task>"
            )
        parts.append("\n</ac:task-list>")
        return "".join(parts)

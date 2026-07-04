from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import override

from ..helpers import (
    _collect_inline,
    _inline_is_simple,
    _is_macro,
    _local,
    render_for_xhtml,
)
from .block import Block

_UL_ITEM = re.compile(r"^[-*]\s+(.+)")
_OL_ITEM = re.compile(r"^\d+\.\s+(.+)")


@dataclass
class List(Block):
    tag: str  # "ul" or "ol"
    items: list[str]  # inline markdown per item

    @classmethod
    def from_xhtml(cls, element: ET.Element) -> List | None:

        local = _local(element.tag)
        if local not in ("ul", "ol") or _is_macro(element.tag):
            return None

        items: list[str] = []
        for child in element:
            if _local(child.tag) != "li":
                return None
            if not _inline_is_simple(child):
                return None
            items.append(_collect_inline(child))

        return cls(tag=local, items=items)

    @classmethod
    def from_markdown(cls, lines: list[str], i: int) -> tuple[List, int] | None:
        ul_m = _UL_ITEM.match(lines[i])
        ol_m = _OL_ITEM.match(lines[i])
        pat, tag = (
            (_UL_ITEM, "ul") if ul_m else (_OL_ITEM, "ol") if ol_m else (None, "")
        )
        if not pat:
            return None

        items: list[str] = []
        while i < len(lines):
            m = pat.match(lines[i])
            if not m:
                break
            items.append(m.group(1))
            i += 1

        return cls(tag=tag, items=items), i

    @override
    def to_markdown(self) -> str:
        if self.tag == "ol":
            return "\n".join(f"{n}. {item}" for n, item in enumerate(self.items, 1))
        return "\n".join(f"- {item}" for item in self.items)

    @override
    def to_xhtml(self) -> str:
        inner = "".join(f"<li>{render_for_xhtml(item)}</li>" for item in self.items)
        return f"<{self.tag}>{inner}</{self.tag}>"

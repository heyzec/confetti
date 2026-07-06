from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import override

from ..xhtml import (
    collect_inline,
    inline_is_simple,
    is_local,
    is_macro,
    render_for_xhtml,
)
from .block import Block


@dataclass
class List(Block):
    tag: str  # "ul" or "ol"
    items: list[str]  # inline markdown per item

    @classmethod
    def from_xhtml(cls, element: ET.Element) -> List | None:

        local = is_local(element.tag)
        if local not in ("ul", "ol") or is_macro(element.tag):
            return None

        items: list[str] = []
        for child in element:
            if is_local(child.tag) != "li":
                return None
            if not inline_is_simple(child):
                return None
            items.append(collect_inline(child))

        return cls(tag=local, items=items)

    # @classmethod
    # def from_markdown(cls, lines: list[str], i: int) -> tuple[List, int] | None:
    #     ...

    @override
    def to_markdown(self) -> str:
        if self.tag == "ol":
            return "\n".join(f"{n}. {item}" for n, item in enumerate(self.items, 1))
        return "\n".join(f"- {item}" for item in self.items)

    @override
    def to_xhtml(self) -> str:
        inner = "".join(f"<li>{render_for_xhtml(item)}</li>" for item in self.items)
        return f"<{self.tag}>{inner}</{self.tag}>"

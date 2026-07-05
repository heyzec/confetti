from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import override

from ..markdown import encode_inline_xml
from ..markdown.constants import ATX_HEADING
from ..xhtml import (
    collect_inline,
    inline_is_simple,
    is_local,
    is_macro,
    normalize,
    render_for_markdown,
    render_for_xhtml,
)
from .block import Block
from .list import _OL_ITEM


@dataclass
class Paragraph(Block):
    text: str

    @classmethod
    def from_xhtml(cls, element: ET.Element) -> Paragraph | None:
        if is_macro(element.tag):
            return None
        if is_local(element.tag) != "p":
            return None
        if element.attrib or not inline_is_simple(element):
            return None
        text = normalize(collect_inline(element))
        return cls(text=text) if text else None

    @classmethod
    def from_markdown(cls, lines: list[str], i: int) -> tuple[Paragraph, int] | None:
        para_lines: list[str] = []
        while i < len(lines):
            cur_s = lines[i].strip()
            if not cur_s or ATX_HEADING.match(lines[i]) or "|" in cur_s:
                break
            if cur_s in (
                "<!-- confetti:raw",
                "<!-- confetti:layout-open",
                "<!-- confetti:layout-close",
            ):
                break
            if (
                cur_s.startswith("```")
                or cur_s.startswith("- ")
                or cur_s.startswith("* ")
                or _OL_ITEM.match(cur_s)
            ):
                break
            para_lines.append(cur_s)
            i += 1
        if para_lines:
            return cls(text=encode_inline_xml(" ".join(para_lines))), i
        return None

    @override
    def to_markdown(self) -> str:
        return render_for_markdown(self.text)

    @override
    def to_xhtml(self) -> str:
        return f"<p>{render_for_xhtml(self.text)}</p>"

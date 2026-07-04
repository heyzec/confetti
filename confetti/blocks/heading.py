from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import override

from ..helpers import (
    _ATX_HEADING,
    _HEADING_TAGS,
    _SETEXT_DASH,
    _SETEXT_EQ,
    _collect_inline,
    _encode_inline_xml,
    _inline_is_simple,
    _is_macro,
    _local,
    _normalize,
    render_for_markdown,
    render_for_xhtml,
)
from .block import Block


@dataclass
class Heading(Block):
    level: int
    text: str

    @classmethod
    def from_xhtml(cls, element: ET.Element) -> Heading | None:

        if _is_macro(element.tag):
            return None
        local = _local(element.tag)
        if local not in _HEADING_TAGS:
            return None
        if element.attrib or not _inline_is_simple(element):
            return None
        text = _normalize(_collect_inline(element))
        return cls(level=int(local[1]), text=text) if text else None

    @classmethod
    def from_markdown(cls, lines: list[str], i: int) -> tuple[Heading, int] | None:
        line = lines[i]
        m = _ATX_HEADING.match(line)
        if m:
            return (
                cls(level=len(m.group(1)), text=_encode_inline_xml(m.group(2).strip())),
                i + 1,
            )
        stripped = line.strip()
        if stripped and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if _SETEXT_EQ.match(nxt):
                return cls(level=1, text=_encode_inline_xml(stripped)), i + 2
            if _SETEXT_DASH.match(nxt):
                return cls(level=2, text=_encode_inline_xml(stripped)), i + 2
        return None

    @override
    def to_markdown(self) -> str:
        return f"{'#' * self.level} {render_for_markdown(self.text)}"

    @override
    def to_xhtml(self) -> str:
        return f"<h{self.level}>{render_for_xhtml(self.text)}</h{self.level}>"

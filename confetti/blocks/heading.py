from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import override

from ..xhtml import (
    _HEADING_TAGS,
    collect_inline,
    inline_is_simple,
    is_local,
    is_macro,
    normalize,
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

        if is_macro(element.tag):
            return None
        local = is_local(element.tag)
        if local not in _HEADING_TAGS:
            return None
        if element.attrib or not inline_is_simple(element):
            return None
        text = normalize(collect_inline(element))
        return cls(level=int(local[1]), text=text) if text else None

    # @classmethod
    # def from_markdown(cls, lines: list[str], i: int) -> tuple[Heading, int] | None:
    #     ...

    @override
    def to_markdown(self) -> str:
        return f"{'#' * self.level} {render_for_markdown(self.text)}"

    @override
    def to_xhtml(self) -> str:
        return f"<h{self.level}>{render_for_xhtml(self.text)}</h{self.level}>"

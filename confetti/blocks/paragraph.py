from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import override

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

    # @classmethod
    # def from_markdown(cls, lines: list[str], i: int) -> tuple[Paragraph, int] | None:
    #     ...

    @override
    def to_markdown(self) -> str:
        return render_for_markdown(self.text)

    @override
    def to_xhtml(self) -> str:
        return f"<p>{render_for_xhtml(self.text)}</p>"

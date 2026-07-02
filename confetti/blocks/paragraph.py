from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import override

from .block import Block
from ..helpers import _render_for_markdown, _render_for_xhtml


@dataclass
class Paragraph(Block):
    text: str

    @classmethod
    def from_xhtml(cls, element: ET.Element) -> Paragraph | None:
        from ..helpers import (
            _collect_inline, _inline_is_simple, _is_macro, _local, _normalize,
        )
        if _is_macro(element.tag):
            return None
        if _local(element.tag) != "p":
            return None
        if element.attrib or not _inline_is_simple(element):
            return None
        text = _normalize(_collect_inline(element))
        return cls(text=text) if text else None

    @classmethod
    def from_markdown(cls, lines: list[str], i: int) -> tuple[Paragraph, int] | None:
        from ..helpers import _ATX_HEADING, _encode_inline_xml
        para_lines: list[str] = []
        while i < len(lines):
            cur_s = lines[i].strip()
            if not cur_s or _ATX_HEADING.match(lines[i]) or "|" in cur_s:
                break
            if cur_s in ("<!-- confetti:raw", "<!-- confetti:layout-open", "<!-- confetti:layout-close"):
                break
            para_lines.append(cur_s)
            i += 1
        if para_lines:
            return cls(text=_encode_inline_xml(" ".join(para_lines))), i
        return None

    @override
    def to_markdown(self) -> str:
        return _render_for_markdown(self.text)

    @override
    def to_xhtml(self) -> str:
        return f"<p>{_render_for_xhtml(self.text)}</p>"

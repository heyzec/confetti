from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from .blocks import Block
from .helpers import (
    _AC_NS, _RI_NS, _blocks_from_elements, _md_blocks_from_lines,
    _replace_html_entities,
)


@dataclass
class Document:
    blocks: list[Block] = field(default_factory=list)

    @classmethod
    def from_xhtml(cls, xhtml: str) -> Document:
        xhtml = _replace_html_entities(xhtml)
        ns = f'xmlns:ac="{_AC_NS}" xmlns:ri="{_RI_NS}"'
        try:
            root = ET.fromstring(f"<root {ns}>{xhtml}</root>")
        except ET.ParseError as exc:
            raise ValueError(f"Failed to parse XHTML: {exc}") from exc
        return cls(blocks=_blocks_from_elements(list(root)))

    @classmethod
    def from_markdown(cls, markdown: str) -> Document:
        return cls(blocks=_md_blocks_from_lines(markdown.splitlines()))

    def to_markdown(self) -> str:
        return "\n\n".join(b.to_markdown() for b in self.blocks)

    def to_xhtml(self) -> str:
        return "".join(b.to_xhtml() for b in self.blocks)

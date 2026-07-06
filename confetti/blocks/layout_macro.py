from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import override

from ..constants import AC_NS
from ..xhtml import (
    _blocks_from_elements,
    et_tag_to_qname,
    is_local,
    is_macro,
    serialize_open_tag,
)
from .block import Block


@dataclass
class LayoutMacro(Block):
    """A layout wrapper macro (e.g. numberedheadings) whose open/close XML is
    preserved verbatim while its inner blocks remain editable in Markdown.

    Markdown representation:
        <!-- confetti:layout-open
        {open_xml}
        -->

        {inner blocks}

        <!-- confetti:layout-close
        {close_xml}
        -->
    """

    open_xml: str
    close_xml: str
    blocks: list[Block]

    @classmethod
    def from_xhtml(cls, element: ET.Element) -> LayoutMacro | None:
        if not is_macro(element.tag):
            return None
        if is_local(element.tag) != "structured-macro":
            return None
        if element.get(f"{{{AC_NS}}}name", "") != "numberedheadings":
            return None
        open_xml = serialize_open_tag(element)
        close_xml = f"</{et_tag_to_qname(element.tag)}>"
        inner_blocks: list[Block] = []
        for child in element:
            if is_local(child.tag) == "rich-text-body":
                open_xml += serialize_open_tag(child)
                close_xml = f"</{et_tag_to_qname(child.tag)}>" + close_xml
                inner_blocks.extend(_blocks_from_elements(list(child)))
            else:
                inner_blocks.extend(_blocks_from_elements([child]))
        return cls(open_xml=open_xml, close_xml=close_xml, blocks=inner_blocks)

    # @classmethod
    # def from_markdown(cls, lines: list[str], i: int) -> tuple[LayoutMacro, int] | None:
    #     ...

    @override
    def to_markdown(self) -> str:
        inner = "\n\n".join(b.to_markdown() for b in self.blocks)
        return (
            f"<!-- confetti:layout-open\n{self.open_xml}\n-->"
            f"\n\n{inner}\n\n"
            f"<!-- confetti:layout-close\n{self.close_xml}\n-->"
        )

    @override
    def to_xhtml(self) -> str:
        return (
            self.open_xml + "".join(b.to_xhtml() for b in self.blocks) + self.close_xml
        )

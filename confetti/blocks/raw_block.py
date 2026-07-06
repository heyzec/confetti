from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import override

from ..xhtml import (
    _HEADING_TAGS,
    _LIST_TAGS,
    collect_inline,
    is_macro,
    is_local,
    _serialize_element,
    inline_is_simple,
    normalize,
)
from .block import Block


@dataclass
class RawBlock(Block):
    """An opaque XML block preserved verbatim."""

    xml: str

    @classmethod
    def from_xhtml(cls, element: ET.Element) -> RawBlock | None:
        local = is_local(element.tag)

        if is_macro(element.tag):
            return cls(xml=_serialize_element(element))

        if local in _LIST_TAGS:
            return cls(xml=_serialize_element(element))

        # Any table Table.from_xhtml couldn't handle (truly complex or unrepresentable cells)
        if local == "table":
            return cls(xml=_serialize_element(element))

        if local in _HEADING_TAGS and (element.attrib or not inline_is_simple(element)):
            return cls(xml=_serialize_element(element))

        if local == "p":
            if element.attrib or not inline_is_simple(element):
                return cls(xml=_serialize_element(element))
            if list(element) and not normalize(collect_inline(element)):
                return cls(xml=_serialize_element(element))

        return None

    # @classmethod
    # def from_markdown(cls, lines: list[str], i: int) -> tuple[RawBlock, int] | None:
    #     ...

    @override
    def to_markdown(self) -> str:
        return f"<!-- confetti:raw\n{self.xml}\n-->"

    @override
    def to_xhtml(self) -> str:
        return self.xml

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import override

from ..helpers import (
    _HEADING_TAGS,
    _LIST_TAGS,
    _collect_inline,
    _inline_is_simple,
    _is_macro,
    _local,
    _normalize,
    _serialize_element,
)
from .block import Block


@dataclass
class RawBlock(Block):
    """An opaque XML block preserved verbatim."""

    xml: str

    @classmethod
    def from_xhtml(cls, element: ET.Element) -> RawBlock | None:
        local = _local(element.tag)

        if _is_macro(element.tag):
            return cls(xml=_serialize_element(element))

        if local in _LIST_TAGS:
            return cls(xml=_serialize_element(element))

        # Any table Table.from_xhtml couldn't handle (truly complex or unrepresentable cells)
        if local == "table":
            return cls(xml=_serialize_element(element))

        if local in _HEADING_TAGS and (
            element.attrib or not _inline_is_simple(element)
        ):
            return cls(xml=_serialize_element(element))

        if local == "p":
            if element.attrib or not _inline_is_simple(element):
                return cls(xml=_serialize_element(element))
            if list(element) and not _normalize(_collect_inline(element)):
                return cls(xml=_serialize_element(element))

        return None

    @classmethod
    def from_markdown(cls, lines: list[str], i: int) -> tuple[RawBlock, int] | None:
        if lines[i].strip() != "<!-- confetti:raw":
            return None
        xml_lines: list[str] = []
        i += 1
        while i < len(lines) and lines[i].rstrip() != "-->":
            xml_lines.append(lines[i])
            i += 1
        i += 1  # skip '-->'
        return cls(xml="\n".join(xml_lines)), i

    @override
    def to_markdown(self) -> str:
        return f"<!-- confetti:raw\n{self.xml}\n-->"

    @override
    def to_xhtml(self) -> str:
        return self.xml

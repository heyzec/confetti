from __future__ import annotations

import xml.etree.ElementTree as ET

from .constants import AC_NS, RI_NS
from .document import Document
from .xhtml import _blocks_from_elements, replace_html_entities


# To deprecate
def md_blocks_from_lines(lines: list[str]) -> list:
    from confetti.blocks import (
        CodeBlock,
        Heading,
        LayoutMacro,
        List,
        Paragraph,
        RawBlock,
        Table,
        TaskList,
    )

    _MD_BLOCK_TYPES = [
        LayoutMacro,
        CodeBlock,
        TaskList,
        RawBlock,
        List,
        Heading,
        Table,
        Paragraph,
    ]

    blocks = []
    i = 0
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        for block_cls in _MD_BLOCK_TYPES:
            result = block_cls.from_markdown(lines, i)
            if result is not None:
                block, i = result
                blocks.append(block)
                break
        else:
            i += 1

    return blocks


def parse_markdown(markdown: str) -> Document:
    lines = markdown.splitlines()
    blocks = md_blocks_from_lines(lines)
    return Document(blocks=blocks)


def render_markdown(doc: Document) -> str:
    return "\n\n".join(b.to_markdown() for b in doc.blocks)


def parse_xhtml(xhtml: str) -> Document:
    xhtml = replace_html_entities(xhtml)
    ns = f'xmlns:ac="{AC_NS}" xmlns:ri="{RI_NS}"'
    try:
        root = ET.fromstring(f"<root {ns}>{xhtml}</root>")
    except ET.ParseError as exc:
        raise ValueError(f"Failed to parse XHTML: {exc}") from exc
    return Document(blocks=_blocks_from_elements(list(root)))


def render_xhtml(doc: Document) -> str:
    return "".join(b.to_xhtml() for b in doc.blocks)


def xhtml_to_markdown(xhtml: str) -> str:
    document = parse_xhtml(xhtml)
    return render_markdown(document)


def markdown_to_xhtml(markdown: str) -> str:
    document = parse_markdown(markdown)
    return render_xhtml(document)

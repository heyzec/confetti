from __future__ import annotations

import xml.etree.ElementTree as ET

from .constants import AC_NS, RI_NS
from .document import Document
from .markdown.parse import parse_markdown
from .xhtml import _blocks_from_elements, replace_html_entities


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

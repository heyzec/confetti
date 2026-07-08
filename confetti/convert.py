from __future__ import annotations

from confetti.xhtml.parse import parse_xhtml

from .document import Document
from .markdown.parse import parse_markdown


def render_markdown(doc: Document) -> str:
    return "\n\n".join(b.to_markdown() for b in doc.blocks)


def render_xhtml(doc: Document) -> str:
    return "".join(b.to_xhtml() for b in doc.blocks)


def xhtml_to_markdown(xhtml: str) -> str:
    document = parse_xhtml(xhtml)
    return render_markdown(document)


def markdown_to_xhtml(markdown: str) -> str:
    document = parse_markdown(markdown)
    return render_xhtml(document)

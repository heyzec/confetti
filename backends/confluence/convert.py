from __future__ import annotations

from .markdown.render import render_markdown
from .xhtml.parse import parse_xhtml
from .xhtml.render import render_xhtml

from .markdown.parse import parse_markdown


def xhtml_to_markdown(xhtml: str) -> str:
    document = parse_xhtml(xhtml)
    return render_markdown(document)


def markdown_to_xhtml(markdown: str) -> str:
    document = parse_markdown(markdown)
    return render_xhtml(document)

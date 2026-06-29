from .ir import Block, Document, Heading, Paragraph, Table
from .convert import xhtml_to_ir, markdown_to_ir, ir_to_markdown, ir_to_xhtml


def xhtml_to_markdown(xhtml: str) -> str:
    return Document.from_xhtml(xhtml).to_markdown()


def markdown_to_xhtml(markdown: str) -> str:
    return Document.from_markdown(markdown).to_xhtml()


__all__ = [
    "Block",
    "Document",
    "Heading",
    "Paragraph",
    "Table",
    "xhtml_to_ir",
    "markdown_to_ir",
    "ir_to_markdown",
    "ir_to_xhtml",
    "xhtml_to_markdown",
    "markdown_to_xhtml",
]

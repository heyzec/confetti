"""Thin re-export module for backward compatibility.

Existing code using ``from confetti.ir import …`` continues to work unchanged.
"""

from .blocks import Block, CodeBlock, Heading, LayoutMacro, Paragraph, RawBlock, Table
from .document import Document

__all__ = [
    "Block",
    "CodeBlock",
    "Document",
    "Heading",
    "LayoutMacro",
    "Paragraph",
    "RawBlock",
    "Table",
]

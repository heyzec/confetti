from __future__ import annotations

from dataclasses import dataclass

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

    def __init__(self, open_xml: str, close_xml: str, blocks: list[Block]):
        print("Initializing LayoutMacro with open_xml:", open_xml)
        self.open_xml = open_xml
        self.close_xml = close_xml
        self.blocks = blocks

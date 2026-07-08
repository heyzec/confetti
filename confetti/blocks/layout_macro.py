from __future__ import annotations

from dataclasses import dataclass
from typing import override

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

    # @classmethod
    # def from_xhtml(cls, element: ET.Element) -> LayoutMacro | None:
    #     ...

    # @classmethod
    # def from_markdown(cls, lines: list[str], i: int) -> tuple[LayoutMacro, int] | None:
    #     ...

    @override
    def to_markdown(self) -> str:
        raise NotImplementedError()

    @override
    def to_xhtml(self) -> str:
        raise NotImplementedError()


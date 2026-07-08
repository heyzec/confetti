from __future__ import annotations

from dataclasses import dataclass
from typing import override

from ..xhtml import render_for_markdown, render_for_xhtml
from .block import Block


@dataclass
class Paragraph(Block):
    text: str

    # @classmethod
    # def from_xhtml(cls, element: ET.Element) -> Paragraph | None:
    #     ...

    # @classmethod
    # def from_markdown(cls, lines: list[str], i: int) -> tuple[Paragraph, int] | None:
    #     ...

    @override
    def to_markdown(self) -> str:
        return render_for_markdown(self.text)

    @override
    def to_xhtml(self) -> str:
        return f"<p>{render_for_xhtml(self.text)}</p>"

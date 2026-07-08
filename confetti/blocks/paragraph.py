from __future__ import annotations

from dataclasses import dataclass
from typing import override

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
        raise NotImplementedError()

    @override
    def to_xhtml(self) -> str:
        raise NotImplementedError()

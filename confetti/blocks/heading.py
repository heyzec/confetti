from __future__ import annotations

from dataclasses import dataclass
from typing import override

from .block import Block


@dataclass
class Heading(Block):
    level: int
    text: str

    # @classmethod
    # def from_xhtml(cls, element: ET.Element) -> Heading | None:
    #     ...

    # @classmethod
    # def from_markdown(cls, lines: list[str], i: int) -> tuple[Heading, int] | None:
    #     ...

    @override
    def to_markdown(self) -> str:
        raise NotImplementedError()

    @override
    def to_xhtml(self) -> str:
        raise NotImplementedError()

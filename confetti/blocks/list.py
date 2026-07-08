from __future__ import annotations

from dataclasses import dataclass
from typing import override

from .block import Block


@dataclass
class List(Block):
    tag: str  # "ul" or "ol"
    items: list[str]  # inline markdown per item

    # @classmethod
    # def from_xhtml(cls, element: ET.Element) -> List | None:
    #     ...

    # @classmethod
    # def from_markdown(cls, lines: list[str], i: int) -> tuple[List, int] | None:
    #     ...

    @override
    def to_markdown(self) -> str:
        raise NotImplementedError()

    @override
    def to_xhtml(self) -> str:
        raise NotImplementedError()

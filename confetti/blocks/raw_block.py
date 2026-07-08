from __future__ import annotations

from dataclasses import dataclass
from typing import override

from .block import Block


@dataclass
class RawBlock(Block):
    """An opaque XML block preserved verbatim."""

    xml: str

    # @classmethod
    # def from_xhtml(cls, element: ET.Element) -> RawBlock | None:
    #     ...

    # @classmethod
    # def from_markdown(cls, lines: list[str], i: int) -> tuple[RawBlock, int] | None:
    #     ...

    @override
    def to_markdown(self) -> str:
        raise NotImplementedError()

    @override
    def to_xhtml(self) -> str:
        raise NotImplementedError()

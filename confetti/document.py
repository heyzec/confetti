from __future__ import annotations

from dataclasses import dataclass, field

from .blocks import Block


@dataclass
class Document:
    blocks: list[Block] = field(default_factory=list)

    # @classmethod
    # def from_xhtml(cls, xhtml: str) -> Document:
    #     ...

    # @classmethod
    # def from_markdown(cls, markdown: str) -> Document:
    #     ...

    # def to_markdown(self) -> str:
    #     ...

    # def to_xhtml(self) -> str:
    #     ...

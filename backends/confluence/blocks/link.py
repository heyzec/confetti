from __future__ import annotations

from dataclasses import dataclass

from .block import Block


@dataclass
class Link(Block):
    url: str
    display_text: list[Block]

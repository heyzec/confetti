from __future__ import annotations

from dataclasses import dataclass

from .block import Block


@dataclass
class List(Block):
    tag: str  # "ul" or "ol"
    items: list[list[Block]]  # inline markdown per item

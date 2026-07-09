from __future__ import annotations

from dataclasses import dataclass

from .block import Block


@dataclass
class Heading(Block):
    level: int
    body: list[Block]  # only inline blocks actually

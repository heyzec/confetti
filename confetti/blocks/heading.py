from __future__ import annotations

from dataclasses import dataclass

from .block import Block


@dataclass
class Heading(Block):
    level: int
    text: str

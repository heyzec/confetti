from __future__ import annotations

from dataclasses import dataclass

from .block import Block


@dataclass
class Code(Block):
    """An inline code."""

    code: str

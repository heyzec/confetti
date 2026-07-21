from __future__ import annotations

from dataclasses import dataclass

from .block import Block


@dataclass
class RawBlock(Block):
    """An opaque XML block preserved verbatim."""

    xml: str

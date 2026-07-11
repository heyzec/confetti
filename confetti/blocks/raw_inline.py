from __future__ import annotations

from dataclasses import dataclass

from .block import Block


@dataclass
class RawInline(Block):
    """An opaque inline XML preserved verbatim."""

    xml: str

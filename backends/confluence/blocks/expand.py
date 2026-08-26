from __future__ import annotations

from dataclasses import dataclass, field

from .block import Block


@dataclass
class ExpandBlock(Block):
    """Confluence expand (collapsible section) macro."""

    macro_id: str
    title: str
    blocks: list[Block] = field(default_factory=list)

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .block import Block


@dataclass
class StyledText(Block):
    kind: Literal["bold", "italic", "strikethrough"]
    body: list[Block]  # only inline blocks actually

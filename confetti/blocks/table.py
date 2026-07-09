from __future__ import annotations

from dataclasses import dataclass, field

from .block import Block


@dataclass
class Merge:
    row: int
    col: int
    rowspan: int
    colspan: int


@dataclass
class Table(Block):
    cells: list[
        list[list[Block] | None]
    ]  # 2D array; first row = headers; None = covered by a merge
    merges: list[Merge] = field(default_factory=list)
    # Metadata for confluence, for now MD doesn't support them
    col_widths: list[float | None] = field(default_factory=list, compare=False)
    alignments: dict[tuple[int, int], str] = field(default_factory=dict, compare=False)

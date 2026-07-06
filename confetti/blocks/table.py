from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import override

from ..xhtml import is_local, is_macro
from ..xhtml.table import xhtml_parse_table
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
        list[str | None]
    ]  # 2D array; first row = headers; None = covered by a merge
    merges: list[Merge] = field(default_factory=list)
    # Metadata for confluence, for now MD doesn't support them
    col_widths: list[float | None] = field(default_factory=list, compare=False)
    alignments: dict[tuple[int, int], str] = field(default_factory=dict, compare=False)

    @classmethod
    def from_xhtml(cls, element: ET.Element) -> Table | None:
        if is_macro(element.tag) or is_local(element.tag) != "table":
            return None
        return xhtml_parse_table(element)

    @override
    def to_markdown(self) -> str:
        from ..markdown.table import render_table_markdown

        return render_table_markdown(self)

    @override
    def to_xhtml(self) -> str:
        from ..xhtml.table import render_table_xhtml

        return render_table_xhtml(self)

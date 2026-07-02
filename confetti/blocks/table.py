from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import override

from .block import Block
from ..helpers import _COLSPAN_MARKER, _ROWSPAN_MARKER, _render_for_markdown, _render_for_xhtml


@dataclass
class Table(Block):
    headers: list[str]
    rows: list[list[str]]

    @classmethod
    def from_xhtml(cls, element: ET.Element) -> Table | None:
        from ..helpers import _is_complex_table, _is_macro, _local, _xhtml_parse_table
        if _is_macro(element.tag):
            return None
        if _local(element.tag) != "table":
            return None
        if _is_complex_table(element):
            return None
        return _xhtml_parse_table(element)

    @classmethod
    def from_markdown(cls, lines: list[str], i: int) -> tuple[Table, int] | None:
        from ..helpers import _md_parse_table
        if "|" not in lines[i]:
            return None
        table_lines: list[str] = []
        while i < len(lines) and "|" in lines[i]:
            table_lines.append(lines[i])
            i += 1
        table = _md_parse_table(table_lines)
        return (table, i) if table else None

    @override
    def to_markdown(self) -> str:
        ncols = max(len(self.headers), max((len(r) for r in self.rows), default=0))
        if ncols == 0:
            return ""

        def pad(row: list[str]) -> list[str]:
            return row + [""] * (ncols - len(row))

        def esc(text: str) -> str:
            if text == _COLSPAN_MARKER:
                return "<"
            if text == _ROWSPAN_MARKER:
                return "^"
            clean = _render_for_markdown(text)
            return clean.replace("|", "\\|").replace("<", "\\<").replace("\n", " ").replace("\r", "")

        header_line = "| " + " | ".join(esc(h) for h in pad(self.headers)) + " |"
        sep_line = "| " + " | ".join("---" for _ in range(ncols)) + " |"
        data_lines = [
            "| " + " | ".join(esc(c) for c in pad(row)) + " |" for row in self.rows
        ]
        return "\n".join([header_line, sep_line, *data_lines])

    @override
    def to_xhtml(self) -> str:
        all_rows: list[list[str]] = []
        if self.headers:
            all_rows.append(self.headers)
        all_rows.extend(self.rows)
        n_rows = len(all_rows)

        lines = ["<table>"]
        for r, row in enumerate(all_rows):
            tag = "th" if r == 0 and bool(self.headers) else "td"
            lines.append("  <tr>")
            c = 0
            while c < len(row):
                cell = row[c]
                if cell in (_COLSPAN_MARKER, _ROWSPAN_MARKER):
                    c += 1
                    continue
                colspan = 1
                while c + colspan < len(row) and row[c + colspan] == _COLSPAN_MARKER:
                    colspan += 1
                rowspan = 1
                while (
                    r + rowspan < n_rows
                    and c < len(all_rows[r + rowspan])
                    and all_rows[r + rowspan][c] == _ROWSPAN_MARKER
                ):
                    rowspan += 1
                attrs = ""
                if colspan > 1:
                    attrs += f' colspan="{colspan}"'
                if rowspan > 1:
                    attrs += f' rowspan="{rowspan}"'
                lines.append(f"    <{tag}{attrs}>{_render_for_xhtml(cell)}</{tag}>")
                c += 1
            lines.append("  </tr>")
        lines.append("</table>")
        return "\n".join(lines)

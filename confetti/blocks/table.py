from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import override

from ..markdown import md_parse_table
from ..xhtml import is_local, is_macro, render_for_markdown, render_for_xhtml
from ..xhtml.table import xhtml_parse_table
from .block import Block


def _attrs_str(attrs: dict) -> str:
    return "".join(
        f' {k}="{v.replace("&", "&amp;").replace(chr(34), "&quot;").replace("<", "&lt;")}"'
        for k, v in attrs.items()
    )


@dataclass
class Table(Block):
    headers: list[str]
    rows: list[list[str]]
    meta: str | None = field(default=None, compare=False)

    @classmethod
    def from_xhtml(cls, element: ET.Element) -> Table | None:
        if is_macro(element.tag) or is_local(element.tag) != "table":
            return None
        return xhtml_parse_table(element)

    @classmethod
    def from_markdown(cls, lines: list[str], i: int) -> tuple[Table, int] | None:
        line = lines[i].strip()

        meta: str | None = None
        if line.startswith("<!-- confetti:table ") and line.endswith(" -->"):
            meta = line[len("<!-- confetti:table ") : -len(" -->")]
            try:
                json.loads(meta)
            except json.JSONDecodeError:
                return None
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            if i >= len(lines) or "|" not in lines[i]:
                return None
        elif "|" not in line:
            return None

        table_lines: list[str] = []
        while i < len(lines) and "|" in lines[i]:
            table_lines.append(lines[i])
            i += 1

        parsed = md_parse_table(table_lines)
        if parsed is None:
            return None
        return cls(headers=parsed.headers, rows=parsed.rows, meta=meta), i

    def _pipe_table(self) -> str:
        ncols = max(len(self.headers), max((len(r) for r in self.rows), default=0))
        if ncols == 0:
            return ""

        def pad(row: list[str]) -> list[str]:
            return row + [""] * (ncols - len(row))

        def esc(text: str) -> str:
            return (
                render_for_markdown(text)
                .replace("|", "\\|")
                .replace("\n", " ")
                .replace("\r", "")
            )

        header_line = "| " + " | ".join(esc(h) for h in pad(self.headers)) + " |"
        sep_line = "| " + " | ".join("---" for _ in range(ncols)) + " |"
        data_lines = [
            "| " + " | ".join(esc(c) for c in pad(row)) + " |" for row in self.rows
        ]
        return "\n".join([header_line, sep_line, *data_lines])

    @override
    def to_markdown(self) -> str:
        pipe = self._pipe_table()
        if self.meta is None:
            return pipe
        return f"<!-- confetti:table {self.meta} -->\n{pipe}"

    @override
    def to_xhtml(self) -> str:
        def _xhtml(text: str) -> str:
            return render_for_xhtml(text.replace("\\<", "<").replace("\\^", "^"))

        if self.meta is None:
            lines = ["<table>"]
            if self.headers:
                lines.append("  <tr>")
                for h in self.headers:
                    lines.append(f"    <th>{_xhtml(h)}</th>")
                lines.append("  </tr>")
            for row in self.rows:
                lines.append("  <tr>")
                for cell in row:
                    lines.append(f"    <td>{_xhtml(cell)}</td>")
                lines.append("  </tr>")
            lines.append("</table>")
            return "\n".join(lines)

        m = json.loads(self.meta)
        table_attrs = m.get("table_attrs", {})
        colgroup = m.get("colgroup", "")
        has_tbody = m.get("tbody", False)
        rows_meta = m.get("rows_meta", [])

        parts = [f"<table{_attrs_str(table_attrs)}>"]
        if colgroup:
            parts.append(colgroup)
        if has_tbody:
            parts.append("<tbody>")

        for row_idx, row in enumerate([self.headers] + self.rows):
            row_meta = rows_meta[row_idx] if row_idx < len(rows_meta) else {}
            tr_attrs = row_meta.get("tr_attrs", {})
            cell_metas = row_meta.get("cells", [])

            parts.append(f"<tr{_attrs_str(tr_attrs)}>")
            logical_col = 0
            for cell_content in row:
                if cell_content in ("<", "^"):
                    continue
                cm = cell_metas[logical_col] if logical_col < len(cell_metas) else {}
                tag = cm.get("tag", "td")
                ca_str = _attrs_str(cm.get("attrs", {}))
                if cm.get("raw"):
                    inner = render_for_markdown(cell_content).replace("\\|", "|")
                    parts.append(f"<{tag}{ca_str}>{inner}</{tag}>")
                else:
                    prefix = cm.get("prefix", "")
                    suffix = cm.get("suffix", "")
                    parts.append(
                        f"<{tag}{ca_str}>{prefix}{_xhtml(cell_content)}{suffix}</{tag}>"
                    )
                logical_col += 1
            parts.append("</tr>")

        if has_tbody:
            parts.append("</tbody>")
        parts.append("</table>")
        return "".join(parts)

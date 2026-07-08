from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from confetti.blocks import Merge, Table

from ..constants import RAW_OPEN
from . import (
    _BLOCK_CONTENT_TAGS,
    _CELL_TAGS,
    _serialize_element,
    collect_inline,
    inline_is_simple,
    is_local,
    is_macro,
    normalize,
    render_for_xhtml,
)


def _serialize_inner_xml(element: ET.Element) -> str:
    xml = _serialize_element(element)
    gt = xml.index(">")
    if xml[gt - 1] == "/":
        return ""
    return xml[gt + 1 : xml.rindex("</")]


def _cell_content(cell_el: ET.Element) -> str | None:
    """Return the cell's markdown content string, or None if not representable simply."""
    block_children = [
        c
        for c in cell_el
        if is_local(c.tag) in _BLOCK_CONTENT_TAGS and not is_macro(c.tag)
    ]
    if not block_children:
        content_el = cell_el
    elif len(block_children) == 1 and is_local(block_children[0].tag) in ("p", "div"):
        content_el = block_children[0]
    else:
        return None

    if not inline_is_simple(content_el):
        return None
    raw_inline = collect_inline(content_el)
    if re.search(re.escape(RAW_OPEN) + r"[^\x03]*\n", raw_inline):
        return None
    return normalize(raw_inline)


def xhtml_parse_table(element: ET.Element) -> Table | None:
    """Parse a <table> element into the Table IR.

    Cells covered by a merge are stored as None in the 2D grid; the merges
    list records each origin cell's (row, col, rowspan, colspan).
    """

    def iter_rows(el: ET.Element) -> list[ET.Element]:
        if is_macro(el.tag):
            return []
        if is_local(el.tag) == "tr":
            return [el]
        if is_local(el.tag) == "table" and el is not element:
            return []
        result: list[ET.Element] = []
        for child in el:
            result.extend(iter_rows(child))
        return result

    def get_cells(tr: ET.Element) -> list[ET.Element]:
        return [c for c in tr if is_local(c.tag) in _CELL_TAGS and not is_macro(c.tag)]

    trs = iter_rows(element)
    if not trs or not get_cells(trs[0]):
        return None

    num_rows = len(trs)
    grid: dict[tuple[int, int], str | None] = {}
    occupied: set[tuple[int, int]] = set()
    merges_out: list = []
    alignments: dict[tuple[int, int], str] = {}

    for row_idx, tr in enumerate(trs):
        col_cursor = 0
        for cell in get_cells(tr):
            while (row_idx, col_cursor) in occupied:
                col_cursor += 1

            colspan = rowspan = 1
            try:
                colspan = int(cell.get("colspan", "1"))
                rowspan = int(cell.get("rowspan", "1"))
            except (ValueError, TypeError):
                pass

            style = cell.get("style", "")
            m = re.search(r"text-align:\s*(\w+)", style)
            if m:
                alignments[(row_idx, col_cursor)] = m.group(1)

            content = _cell_content(cell)
            if content is None:
                # Fall back to raw inner XML for cells we can't represent simply.
                raw = _serialize_inner_xml(cell)
                if "\n" in raw:
                    return None
                content = raw

            grid[(row_idx, col_cursor)] = content

            if colspan > 1 or rowspan > 1:
                merges_out.append((row_idx, col_cursor, rowspan, colspan))
                for dr in range(rowspan):
                    for dc in range(colspan):
                        if dr == 0 and dc == 0:
                            continue
                        pos = (row_idx + dr, col_cursor + dc)
                        occupied.add(pos)
                        grid[pos] = None

            col_cursor += colspan

    if not grid:
        return None

    num_cols = max(c for (_, c) in grid) + 1
    cells_2d: list[list[str | None]] = [
        [grid.get((r, c), "") for c in range(num_cols)] for r in range(num_rows)
    ]

    # Extract per-column pixel widths from <colgroup><col style="width: X.Ypx;" />.
    col_widths: list[float | None] = []
    colgroup = next((c for c in element if is_local(c.tag) == "colgroup"), None)
    if colgroup is not None:
        for col in colgroup:
            if is_local(col.tag) != "col":
                continue
            style = col.get("style", "")
            m = re.search(r"width:\s*([\d.]+)px", style)
            col_widths.append(float(m.group(1)) if m else None)

    return Table(
        cells=cells_2d,
        merges=[
            Merge(row=r, col=c, rowspan=rs, colspan=cs) for r, c, rs, cs in merges_out
        ],
        col_widths=col_widths,
        alignments=alignments,
    )


def render_table_xhtml(table: "Table") -> str:
    if not table.cells:
        return "<table></table>"

    occupied: set[tuple[int, int]] = set()
    merge_at: dict[tuple[int, int], Merge] = {}
    for m in table.merges:
        merge_at[(m.row, m.col)] = m
        for dr in range(m.rowspan):
            for dc in range(m.colspan):
                if dr == 0 and dc == 0:
                    continue
                occupied.add((m.row + dr, m.col + dc))

    ncols = max(len(row) for row in table.cells)
    parts = ["<table>"]

    if table.col_widths:
        parts.append("<colgroup>")
        for i in range(ncols):
            w = table.col_widths[i] if i < len(table.col_widths) else None
            if w is not None:
                parts.append(f'<col style="width: {w}px;" />')
            else:
                parts.append("<col />")
        parts.append("</colgroup>")

    parts.append("<tbody>")
    for r, row in enumerate(table.cells):
        cell_tag = "th" if r == 0 else "td"
        parts.append("<tr>")
        for c in range(ncols):
            if (r, c) in occupied:
                continue
            content = row[c] if c < len(row) else None
            attrs = ""
            if (r, c) in merge_at:
                m = merge_at[(r, c)]
                if m.colspan > 1:
                    attrs += f' colspan="{m.colspan}"'
                if m.rowspan > 1:
                    attrs += f' rowspan="{m.rowspan}"'
            if (r, c) in table.alignments:
                attrs += f' style="text-align: {table.alignments[(r, c)]};"'
            inner = render_for_xhtml(content or "") + "<br />"
            parts.append(f"<{cell_tag}{attrs}>{inner}</{cell_tag}>")
        parts.append("</tr>")
    parts.append("</tbody>")
    parts.append("</table>")
    return "".join(parts)

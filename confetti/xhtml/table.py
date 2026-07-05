from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET

from ..constants import RAW_OPEN
from . import (
    _BLOCK_CONTENT_TAGS,
    _CELL_TAGS,
    et_tag_to_qname,
    _serialize_element,
    serialize_open_tag,
    collect_inline,
    inline_is_simple,
    is_local,
    is_macro,
    normalize,
)


def _serialize_inner_xml(element: ET.Element) -> str:
    """Serialize the inner content of element (text + children), without its outer tags."""
    xml = _serialize_element(element)
    gt = xml.index(">")
    if xml[gt - 1] == "/":  # self-closing
        return ""
    return xml[gt + 1 : xml.rindex("</")]


def _cell_structure(
    cell_el: ET.Element,
) -> tuple[str, str, ET.Element] | None:
    """Return (prefix, suffix, content_el) for a cell, or None if not representable.

    Traverses single-child wrapper elements (p, div) to find the element
    whose _collect_inline gives the cell's text content.  prefix/suffix are
    the serialized opening/closing tags of those wrappers.
    Returns None when the cell has multiple block-level children, or a
    non-transparent block child (ul, ol, nested table, …).
    """
    block_children = [
        c
        for c in cell_el
        if is_local(c.tag) in _BLOCK_CONTENT_TAGS and not is_macro(c.tag)
    ]
    if not block_children:
        return ("", "", cell_el)
    if len(block_children) > 1:
        return None
    child = block_children[0]
    child_local = is_local(child.tag)
    if child_local not in ("p", "div"):
        return None
    inner = _cell_structure(child)
    if inner is None:
        return None
    inner_prefix, inner_suffix, content_el = inner
    return (
        serialize_open_tag(child) + inner_prefix,
        inner_suffix + f"</{child_local}>",
        content_el,
    )


def xhtml_parse_table(element: ET.Element) -> "Table | None":
    """Parse a table element into a Table IR node (with or without meta).

    Cells with colspan/rowspan are expanded into a 2D grid: same-row
    continuation slots are filled with "<", lower-row continuation slots
    with "^".  Actual cell content that is exactly "<" or "^" is escaped
    to "\\<" / "\\^" to avoid ambiguity.
    Returns None only for unrepresentable structure (multiple block children,
    non-simple inline content, etc.).
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
    if not trs:
        return None
    if not get_cells(trs[0]):
        return None

    # --- Structural metadata ---
    table_attrs = {et_tag_to_qname(k): v for k, v in element.attrib.items()}
    has_tbody = any(is_local(c.tag) == "tbody" for c in element)
    colgroup_xml = next(
        (_serialize_element(c) for c in element if is_local(c.tag) == "colgroup"), ""
    )
    needs_meta = bool(table_attrs or colgroup_xml)

    # --- Build 2D grid ---
    grid: dict[tuple[int, int], str] = {}
    cell_metas_grid: dict[tuple[int, int], dict] = {}
    tr_attrs_list: list[dict] = []
    occupied: set[tuple[int, int]] = set()

    for row_idx, tr in enumerate(trs):
        cells = get_cells(tr)
        tr_attrs = {et_tag_to_qname(k): v for k, v in tr.attrib.items()}
        if tr_attrs:
            needs_meta = True
        tr_attrs_list.append(tr_attrs)

        col_cursor = 0
        for cell in cells:
            while (row_idx, col_cursor) in occupied:
                col_cursor += 1

            colspan = rowspan = 1
            try:
                colspan = int(cell.get("colspan", "1"))
                rowspan = int(cell.get("rowspan", "1"))
            except (ValueError, TypeError):
                pass

            cell_local = is_local(cell.tag)
            cell_attrs = {et_tag_to_qname(k): v for k, v in cell.attrib.items()}

            struct = _cell_structure(cell)
            is_raw = False
            content = ""
            prefix = suffix = ""
            if struct is None:
                is_raw = True
            else:
                prefix, suffix, content_el = struct
                if not inline_is_simple(content_el):
                    is_raw = True
                else:
                    raw_inline = collect_inline(content_el)
                    if re.search(re.escape(RAW_OPEN) + r"[^\x03]*\n", raw_inline):
                        is_raw = True
                    else:
                        content = normalize(raw_inline)
                        if not content and list(content_el):
                            is_raw = True
                        elif any(
                            is_local(c.tag) == "br"
                            for c in content_el.iter()
                            if not is_macro(c.tag) and c is not content_el
                        ):
                            is_raw = True

            if is_raw:
                content = _serialize_inner_xml(cell)
                if "\n" in content:
                    return None
                cm: dict = {"tag": cell_local, "raw": True}
                if cell_attrs:
                    cm["attrs"] = cell_attrs
                needs_meta = True
            else:
                # Escape single-char span markers so they aren't confused with grid markers
                if content == "<":
                    content = "\\<"
                elif content == "^":
                    content = "\\^"

                cm = {"tag": cell_local}
                if cell_attrs or prefix or suffix:
                    needs_meta = True
                if cell_attrs:
                    cm["attrs"] = cell_attrs
                if prefix:
                    cm["prefix"] = prefix
                if suffix:
                    cm["suffix"] = suffix

            grid[(row_idx, col_cursor)] = content
            cell_metas_grid[(row_idx, col_cursor)] = cm

            for dc in range(1, colspan):
                grid[(row_idx, col_cursor + dc)] = "<"

            for dr in range(1, rowspan):
                for dc in range(colspan):
                    pos = (row_idx + dr, col_cursor + dc)
                    grid[pos] = "^"
                    occupied.add(pos)

            col_cursor += colspan

    if not grid:
        return None

    num_rows = len(trs)
    num_cols = max(c for (_, c) in grid) + 1

    all_content = [
        [grid.get((r, c), "") for c in range(num_cols)] for r in range(num_rows)
    ]

    has_spans = any(v in ("<", "^") for v in grid.values())
    if has_spans:
        needs_meta = True

    headers = all_content[0]
    rows = all_content[1:]

    if not needs_meta:
        from confetti.blocks import Table

        return Table(headers=headers, rows=rows)

    rows_meta: list[dict] = []
    for row_idx in range(num_rows):
        cells_meta = [
            cell_metas_grid[(row_idx, c)]
            for c in range(num_cols)
            if (row_idx, c) in cell_metas_grid
        ]
        row_entry: dict = {"cells": cells_meta}
        if tr_attrs_list[row_idx]:
            row_entry["tr_attrs"] = tr_attrs_list[row_idx]
        rows_meta.append(row_entry)

    meta_dict: dict = {}
    if table_attrs:
        meta_dict["table_attrs"] = table_attrs
    if colgroup_xml:
        meta_dict["colgroup"] = colgroup_xml
    if has_tbody:
        meta_dict["tbody"] = True
    meta_dict["rows_meta"] = rows_meta

    from confetti.blocks import Table

    return Table(
        headers=headers, rows=rows, meta=json.dumps(meta_dict, separators=(",", ":"))
    )

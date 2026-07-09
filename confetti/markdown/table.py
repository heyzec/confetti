from __future__ import annotations

import json
import re

from confetti.blocks import Table
from confetti.constants import RAW_CLOSE, RAW_OPEN
from confetti.markdown.constants import AC_RI_OPEN, TAG_NAME

from ..blocks import Block, Merge, Table

_WS = " \t\n\r\f\v"


# == Parsing ==


def _is_sep_row(line: str) -> bool:
    s = line.strip()
    return bool(s) and "-" in s and all(c in "|-: \t" for c in s)


def _parse_row(line: str) -> list[str]:
    return [encode_inline_xml(c.strip(_WS)) for c in line.strip().strip("|").split("|")]


def encode_inline_xml(text: str) -> str:
    """Wrap ac:/ri: XML fragments in text with sentinels for round-trip fidelity."""
    result: list[str] = []
    pos = 0
    while pos < len(text):
        m = AC_RI_OPEN.search(text, pos)
        if m is None:
            result.append(text[pos:])
            break

        result.append(text[pos : m.start()])
        start = m.start()

        tag_end = text.find(">", start)
        if tag_end == -1:
            result.append(text[start:])
            break

        if text[tag_end - 1] == "/":
            result.append(f"{RAW_OPEN}{text[start:tag_end + 1]}{RAW_CLOSE}")
            pos = tag_end + 1
        else:
            nm = TAG_NAME.match(text, start)
            tag_name = nm.group(1) if nm else ""
            open_re = re.compile(r"<" + re.escape(tag_name) + r"(?=[\s>/])")
            close_re = re.compile(r"</" + re.escape(tag_name) + r"(?=[\s>])")
            depth = 1
            sp = tag_end + 1
            while depth > 0:
                next_open = open_re.search(text, sp)
                next_close = close_re.search(text, sp)
                if next_close is None:
                    sp = len(text)
                    break
                if next_open and next_open.start() < next_close.start():
                    depth += 1
                    sp = next_open.end()
                else:
                    depth -= 1
                    sp = next_close.end()
            close_gt = text.find(">", sp - 1)
            end = close_gt + 1 if close_gt != -1 else len(text)
            result.append(f"{RAW_OPEN}{text[start:end]}{RAW_CLOSE}")
            pos = end

    return "".join(result)


def parse_table(lines: list[str], i: int) -> tuple[Table, int] | None:
    from confetti.markdown.parse import parse_inline

    col_widths: list[float | None] = []
    alignments: dict = {}
    line = lines[i].strip()
    if line.startswith("<!-- confetti:table ") and line.endswith(" -->"):
        try:
            meta = json.loads(line[len("<!-- confetti:table ") : -len(" -->")])
            col_widths = meta.get("col_widths", [])
            alignments = {
                tuple(int(x) for x in k.split(",")): v
                for k, v in meta.get("alignments", {}).items()
            }
        except (json.JSONDecodeError, AttributeError, ValueError):
            return None
        i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1

    if i >= len(lines) or "|" not in lines[i].strip():
        return None

    table_lines: list[str] = []
    while i < len(lines) and "|" in lines[i]:
        table_lines.append(lines[i])
        i += 1

    sep_idx: int | None = next(
        (j for j, ln in enumerate(table_lines) if _is_sep_row(ln)), None
    )
    if sep_idx is None or sep_idx == 0:
        return None

    raw_rows = [_parse_row(table_lines[sep_idx - 1])]
    raw_rows += [_parse_row(ln) for ln in table_lines[sep_idx + 1 :] if ln.strip()]

    nrows = len(raw_rows)
    ncols = max(len(r) for r in raw_rows)
    raw_grid = [row + [""] * (ncols - len(row)) for row in raw_rows]

    # Reconstruct Merge objects from < (colspan) and ^ (rowspan) markers.
    # A real cell at (r, c) owns consecutive < cells to its right and ^ cells below.
    covered: set[tuple[int, int]] = set()
    merges: list[Merge] = []

    for r in range(nrows):
        for c in range(ncols):
            if (r, c) in covered or raw_grid[r][c] in ("<", "^"):
                continue
            cs = 0
            while c + cs + 1 < ncols and raw_grid[r][c + cs + 1] == "<":
                cs += 1
            rs = 0
            while r + rs + 1 < nrows and raw_grid[r + rs + 1][c] == "^":
                rs += 1
            if cs > 0 or rs > 0:
                merges.append(Merge(row=r, col=c, rowspan=rs + 1, colspan=cs + 1))
                for dr in range(rs + 1):
                    for dc in range(cs + 1):
                        if dr == 0 and dc == 0:
                            continue
                        covered.add((r + dr, c + dc))

    cells: list[list[list[Block] | None]] = []
    for r in range(nrows):
        row: list[list[Block] | None] = []
        for c in range(ncols):
            if (r, c) in covered:
                row.append(None)
            else:
                # Un-escape \< and \^ that were escaped to avoid marker collision.
                escaped = raw_grid[r][c].replace("\\<", "<").replace("\\^", "^")
                row.append(parse_inline(escaped))
        cells.append(row)

    return (
        Table(cells=cells, merges=merges, col_widths=col_widths, alignments=alignments),
        i,
    )


# == Rendering ==


def _symbol_at(table: Table, row: int, col: int) -> str:
    """Return '<' (colspan continuation) or '^' (rowspan continuation) for a None cell."""
    for m in table.merges:
        if not (m.row <= row < m.row + m.rowspan and m.col <= col < m.col + m.colspan):
            continue
        if row == m.row and col > m.col:
            return "<"
        if row > m.row:
            return "^"
    return ""


def render_table_markdown(table: Table) -> str:
    from confetti.markdown.render import render_inline

    if not table.cells:
        return ""
    ncols = max(len(row) for row in table.cells)

    def render_cell(r: int, c: int) -> str:
        cell = table.cells[r][c] if c < len(table.cells[r]) else None
        if cell is None:
            return _symbol_at(table, r, c)

        rendered = "".join(render_inline(b) for b in cell)
        escaped = rendered.replace("|", "\\|").replace("\n", " ").replace("\r", "")
        # Escape literal < and ^ so they aren't misread as span markers on re-parse.
        if escaped == "<":
            return "\\<"
        if escaped == "^":
            return "\\^"
        return escaped

    # Pre-render all cells, then pad each column to its max width.
    grid = [[render_cell(r, c) for c in range(ncols)] for r in range(len(table.cells))]
    col_w = [max(len(grid[r][c]) for r in range(len(grid))) for c in range(ncols)]
    col_w = [max(w, 3) for w in col_w]  # separator row needs at least 3 dashes

    def fmt_row(cells: list[str]) -> str:
        return "| " + " | ".join(c.ljust(col_w[i]) for i, c in enumerate(cells)) + " |"

    lines = []
    for r, row_cells in enumerate(grid):
        lines.append(fmt_row(row_cells))
        if r == 0:
            lines.append("| " + " | ".join("-" * col_w[c] for c in range(ncols)) + " |")

    pipe = "\n".join(lines)
    meta_dict: dict = {}
    if table.col_widths:
        meta_dict["col_widths"] = table.col_widths
    if table.alignments:
        # JSON keys must be strings; encode (r, c) as "r,c".
        meta_dict["alignments"] = {
            f"{r},{c}": v for (r, c), v in table.alignments.items()
        }
    if not meta_dict:
        return pipe
    return f"<!-- confetti:table {json.dumps(meta_dict, separators=(',', ':'))} -->\n{pipe}"

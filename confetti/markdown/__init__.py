import re

from ..constants import RAW_CLOSE, RAW_OPEN
from .constants import AC_RI_OPEN, TAG_NAME


def escape_md_text(s: str) -> str:
    """Escape characters in a plain text node that would be misread as Markdown."""
    return re.sub(r"([_\\])", r"\\\1", s)


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


def _md_is_sep_row(line: str) -> bool:
    s = line.strip()
    return bool(s) and "-" in s and all(c in "|-: \t" for c in s)


def _md_parse_row(line: str) -> list[str]:
    _WS = " \t\n\r\f\v"
    return [encode_inline_xml(c.strip(_WS)) for c in line.strip().strip("|").split("|")]


def md_parse_table(lines: list[str]) -> "Table | None":
    from ..blocks import Table

    sep_idx: int | None = next(
        (i for i, ln in enumerate(lines) if _md_is_sep_row(ln)), None
    )
    if sep_idx is None or sep_idx == 0:
        return None
    headers = _md_parse_row(lines[sep_idx - 1])
    rows = [_md_parse_row(ln) for ln in lines[sep_idx + 1 :] if ln.strip()]

    return Table(headers=headers, rows=rows)

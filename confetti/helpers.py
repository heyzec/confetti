from __future__ import annotations

import html.entities
import re
import xml.etree.ElementTree as ET
from html import escape

# ===========================================================================
# Namespace / XML constants
# ===========================================================================

_AC_NS = "http://atlassian.com/ac"
_RI_NS = "http://atlassian.com/ri"
_MACRO_NS = {_AC_NS, _RI_NS}

ET.register_namespace("ac", _AC_NS)
ET.register_namespace("ri", _RI_NS)

_NS_TO_PREFIX = {_AC_NS: "ac", _RI_NS: "ri"}

_XML_PREDEFINED = {"lt", "gt", "amp", "apos", "quot"}
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_CELL_TAGS = {"td", "th"}
_LIST_TAGS = {"ul", "ol"}

_UNICODE_TO_ENTITY = {
    "\u00a0": "&nbsp;",
    "\u2192": "&rarr;",
    "\u2190": "&larr;",
    "\u2194": "&harr;",
    "\u21d2": "&rArr;",
    "\u2013": "&ndash;",
    "\u2014": "&mdash;",
}


def _re_encode_entities(text: str) -> str:
    for ch, ent in _UNICODE_TO_ENTITY.items():
        text = text.replace(ch, ent)
    return text


def _re_encode_entities_in_text(xml: str) -> str:
    """Re-encode HTML entities only in XML text nodes.

    Skips <![CDATA[...]]> sections and tag content (< ... >) so that
    non-breaking spaces inside code blocks are not converted to &nbsp;
    and attribute values are not double-escaped.
    In text nodes, also encodes " as &quot; to match Confluence XHTML.
    """
    result: list[str] = []
    pos = 0
    n = len(xml)
    while pos < n:
        if xml[pos : pos + 9] == "<![CDATA[":
            end = xml.find("]]>", pos + 9)
            if end == -1:
                result.append(xml[pos:])
                break
            result.append(xml[pos : end + 3])
            pos = end + 3
        elif xml[pos] == "<":
            end = xml.find(">", pos)
            if end == -1:
                result.append(xml[pos:])
                break
            result.append(xml[pos : end + 1])
            pos = end + 1
        else:
            end = xml.find("<", pos)
            chunk = xml[pos:] if end == -1 else xml[pos:end]
            chunk = _re_encode_entities(chunk)
            chunk = chunk.replace('"', "&quot;")
            result.append(chunk)
            if end == -1:
                break
            pos = end
    return "".join(result)


def _replace_html_entities(text: str) -> str:
    def replace(m: re.Match[str]) -> str:
        name = m.group(1)
        if name in _XML_PREDEFINED:
            return m.group(0)
        cp = html.entities.name2codepoint.get(name)
        return chr(cp) if cp else m.group(0)

    return re.sub(r"&([a-zA-Z][a-zA-Z0-9]*);", replace, text)


def _local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _is_macro(tag: str) -> bool:
    ns = tag.split("}")[0][1:] if "}" in tag else ""
    return ns in _MACRO_NS


def _normalize(text: str) -> str:
    """Collapse whitespace, but preserve non-breaking spaces (\u00a0)."""
    return re.sub(r"[ \t\n\r\f\v]+", " ", text).strip()


def _et_tag_to_qname(tag: str) -> str:
    """Convert ET Clark-notation tag '{uri}local' to 'prefix:local'."""
    if "}" in tag:
        uri, local = tag[1:].split("}", 1)
        prefix = _NS_TO_PREFIX.get(uri, "")
        return f"{prefix}:{local}" if prefix else local
    return tag


def _serialize_open_tag(element: ET.Element) -> str:
    """Serialize just the opening tag of an element (no children, no tail)."""
    tag_str = _et_tag_to_qname(element.tag)
    parts = [f"<{tag_str}"]
    for k, v in element.attrib.items():
        k_str = _et_tag_to_qname(k)
        v_esc = v.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
        parts.append(f' {k_str}="{v_esc}"')
    parts.append(">")
    return "".join(parts)


def _restore_cdata(xml: str) -> str:
    """Wrap ac:plain-text-body content back into CDATA sections.

    ET strips CDATA markers on parse; this restores them so the output
    matches the original Confluence XHTML format.
    """

    def _wrap(m: re.Match[str]) -> str:
        open_tag = m.group(1)
        content = m.group(2)
        close_tag = m.group(3)
        content = (
            content.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
        )
        return f"{open_tag}<![CDATA[{content}]]>{close_tag}"

    return re.sub(
        r"(<ac:plain-text-body>)(.*?)(</ac:plain-text-body>)",
        _wrap,
        xml,
        flags=re.DOTALL,
    )


def _serialize_element(element: ET.Element) -> str:
    """Serialize an ET element to an XML string, excluding its tail and
    namespace declarations.  Re-encodes HTML entities and restores CDATA
    sections stripped by ElementTree.
    """
    saved_tail = element.tail
    element.tail = None
    xml = ET.tostring(element, encoding="unicode")
    element.tail = saved_tail
    xml = xml.replace(f' xmlns:ac="{_AC_NS}"', "")
    xml = xml.replace(f' xmlns:ri="{_RI_NS}"', "")
    xml = _restore_cdata(xml)
    xml = _re_encode_entities_in_text(xml)
    return xml


# ===========================================================================
# Inline Markdown ↔ XHTML
# ===========================================================================

_RAW_OPEN = "\x02"
_RAW_CLOSE = "\x03"

_SENTINEL_RE = re.compile(
    re.escape(_RAW_OPEN) + r"(.*?)" + re.escape(_RAW_CLOSE), re.DOTALL
)

_INLINE_MD_PATTERNS = [
    (re.compile(r"\[([^\]]*)\]\(([^)]*)\)"), "link"),
    (re.compile(r"\*\*\*(.+?)\*\*\*", re.DOTALL), "strong_em"),
    (re.compile(r"\*\*(.+?)\*\*", re.DOTALL), "strong"),
    (re.compile(r"~~(.+?)~~", re.DOTALL), "s"),
    (re.compile(r"`([^`\n]+)`"), "code"),
    (re.compile(r"\*([^*\n]+)\*"), "em"),
]

_XHTML_INLINE_TAGS = {
    "strong": ("**", "**"),
    "b": ("**", "**"),
    "em": ("*", "*"),
    "i": ("*", "*"),
    "s": ("~~", "~~"),
    "del": ("~~", "~~"),
    "code": ("`", "`"),
}


def _render_inline_md(text: str) -> str:
    """Convert inline Markdown markers in a plain string to XHTML tags."""
    result: list[str] = []
    pos = 0
    while pos < len(text):
        best_m, best_name, best_start = None, None, len(text)
        for pat, name in _INLINE_MD_PATTERNS:
            m = pat.search(text, pos)
            if m and m.start() < best_start:
                best_m, best_name, best_start = m, name, m.start()

        if best_m is None:
            result.append(escape(text[pos:], quote=False))
            break

        if best_start > pos:
            result.append(escape(text[pos:best_start], quote=False))

        inner = escape(best_m.group(1), quote=False)
        if best_name == "link":
            result.append(f'<a href="{escape(best_m.group(2))}">{inner}</a>')
        elif best_name == "strong_em":
            result.append(f"<em><strong>{inner}</strong></em>")
        elif best_name == "strong":
            result.append(f"<strong>{inner}</strong>")
        elif best_name == "s":
            result.append(f"<s>{inner}</s>")
        elif best_name == "code":
            result.append(f"<code>{inner}</code>")
        elif best_name == "em":
            result.append(f"<em>{inner}</em>")

        pos = best_m.end()

    return "".join(result)


def _render_for_xhtml(text: str) -> str:
    """Convert inline Markdown + sentinel-wrapped raw XML to XHTML.
    Also re-encodes non-breaking spaces and arrow characters as HTML entities.
    """
    if _RAW_OPEN not in text:
        return _re_encode_entities(_render_inline_md(text))

    raw_fragments: list[str] = []

    def _extract(m: re.Match[str]) -> str:
        raw_fragments.append(m.group(1))
        return f"\x01{len(raw_fragments) - 1}\x01"

    placeholder_text = _SENTINEL_RE.sub(_extract, text)
    rendered = _render_inline_md(placeholder_text)
    for i, raw in enumerate(raw_fragments):
        rendered = rendered.replace(f"\x01{i}\x01", raw)
    return _re_encode_entities(rendered)


def _render_for_markdown(text: str) -> str:
    """Strip sentinels from text for Markdown output; raw XML becomes inline HTML."""
    return text.replace(_RAW_OPEN, "").replace(_RAW_CLOSE, "")


_AC_RI_OPEN = re.compile(r"<(ac|ri):")
_TAG_NAME = re.compile(r"<([a-zA-Z][a-zA-Z0-9:._-]*)")


def _encode_inline_xml(text: str) -> str:
    """Wrap ac:/ri: XML fragments in text with sentinels for round-trip fidelity."""
    result: list[str] = []
    pos = 0
    while pos < len(text):
        m = _AC_RI_OPEN.search(text, pos)
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
            result.append(f"{_RAW_OPEN}{text[start:tag_end + 1]}{_RAW_CLOSE}")
            pos = tag_end + 1
        else:
            nm = _TAG_NAME.match(text, start)
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
            result.append(f"{_RAW_OPEN}{text[start:end]}{_RAW_CLOSE}")
            pos = end

    return "".join(result)


def _inline_text(element: ET.Element) -> str:
    """Inline-Markdown representation of a child element (without its tail)."""
    if _is_macro(element.tag):
        return f"{_RAW_OPEN}{_serialize_element(element)}{_RAW_CLOSE}"

    local = _local(element.tag)
    if local == "br":
        return " "
    if local == "time":
        return element.get("datetime", "")
    if local == "a":
        href = element.get("href", "")
        inner = _collect_inline(element)
        return f"[{inner}]({href})" if href else inner
    if local in _XHTML_INLINE_TAGS:
        pre, post = _XHTML_INLINE_TAGS[local]
        inner = _collect_inline(element)
        return f"{pre}{inner}{post}" if inner else ""

    return _collect_inline(element)


def _collect_inline(element: ET.Element) -> str:
    """Collect all inline-Markdown text from within an element."""
    parts: list[str] = []
    if element.text:
        parts.append(element.text)
    for child in element:
        parts.append(_inline_text(child))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


# ===========================================================================
# XHTML traversal
# ===========================================================================

# Transparent layout macros: content traversed, wrapper preserved via LayoutMacro.
_TRANSPARENT_LAYOUT_MACROS = {"easy-heading-free"}

_SUPPORTED_INLINE_LOCALS = frozenset({
    "br", "time", "a", "strong", "b", "em", "i", "s", "del", "code",
})


def _inline_is_simple(element: ET.Element) -> bool:
    """Return True if every descendant (non-macro) element is a supported inline tag."""
    for child in element.iter():
        if child is element:
            continue
        if _is_macro(child.tag):
            continue
        local = _local(child.tag)
        if local not in _SUPPORTED_INLINE_LOCALS:
            return False
        if local == "a" and set(child.attrib.keys()) - {"href"}:
            return False
        if local not in ("a", "br", "time") and child.attrib:
            return False
    return True


def _xhtml_parse_table(element: ET.Element) -> "Table | None":
    """Parse a table (including colspan/rowspan) into the Table IR using span markers."""
    from .blocks import Table

    def iter_rows(el: ET.Element) -> list[ET.Element]:
        if _is_macro(el.tag):
            return []
        if _local(el.tag) == "tr":
            return [el]
        if _local(el.tag) == "table" and el is not element:
            return []
        result: list[ET.Element] = []
        for child in el:
            result.extend(iter_rows(child))
        return result

    def get_cells(tr: ET.Element) -> list[ET.Element]:
        return [c for c in tr if _local(c.tag) in _CELL_TAGS and not _is_macro(c.tag)]

    trs = iter_rows(element)
    if not trs:
        return None
    if not get_cells(trs[0]):
        return None

    grid: dict[tuple[int, int], str] = {}
    occupied: set[tuple[int, int]] = set()

    for r, tr in enumerate(trs):
        c = 0
        for cell in get_cells(tr):
            while (r, c) in occupied:
                c += 1
            colspan = int(cell.get("colspan", 1))
            rowspan = int(cell.get("rowspan", 1))
            content = _normalize(_collect_inline(cell))
            grid[(r, c)] = content
            for dc in range(1, colspan):
                grid[(r, c + dc)] = _COLSPAN_MARKER
            for dr in range(1, rowspan):
                for dc in range(colspan):
                    occupied.add((r + dr, c + dc))
                    grid[(r + dr, c + dc)] = _ROWSPAN_MARKER
            c += colspan

    if not grid:
        return None

    num_rows = max(r for r, _ in grid) + 1
    num_cols = max(c for _, c in grid) + 1
    headers = [grid.get((0, c), "") for c in range(num_cols)]
    rows = [[grid.get((r, c), "") for c in range(num_cols)] for r in range(1, num_rows)]
    return Table(headers=headers, rows=rows)


_COLSPAN_MARKER = "\x00<"  # sentinel stored in Table IR for a colspan continuation cell
_ROWSPAN_MARKER = "\x00^"  # sentinel stored in Table IR for a rowspan continuation cell


def _is_complex_table(element: ET.Element) -> bool:
    """Return True if the table has Confluence-specific attributes that
    cannot be round-tripped through the simple Table IR (class, style,
    colgroup, etc.).  Tables with colspan/rowspan are handled via span markers.
    """
    if element.get("class") or element.get("style"):
        return True
    for child in element:
        if _local(child.tag) == "colgroup":
            return True
    return False


def _blocks_from_elements(elements: list[ET.Element]) -> list:
    from .blocks import Heading, LayoutMacro, Paragraph, RawBlock, Table

    _XHTML_BLOCK_TYPES = [LayoutMacro, Heading, Paragraph, Table, RawBlock]

    blocks = []
    for element in elements:
        # Transparent macro wrappers: recurse into their children
        if _is_macro(element.tag):
            local = _local(element.tag)
            if local == "rich-text-body":
                blocks.extend(_blocks_from_elements(list(element)))
                continue
            if local == "structured-macro":
                name = element.get(f"{{{_AC_NS}}}name", "")
                if name in _TRANSPARENT_LAYOUT_MACROS:
                    blocks.extend(_blocks_from_elements(list(element)))
                    continue

        block = None
        for cls in _XHTML_BLOCK_TYPES:
            block = cls.from_xhtml(element)
            if block is not None:
                break

        if block is not None:
            blocks.append(block)
        else:
            # Transparent non-macro container (div, body, etc.) → recurse
            blocks.extend(_blocks_from_elements(list(element)))

    return blocks


def _md_blocks_from_lines(lines: list[str]) -> list:
    from .blocks import Heading, LayoutMacro, Paragraph, RawBlock, Table

    _MD_BLOCK_TYPES = [LayoutMacro, RawBlock, Heading, Table, Paragraph]

    blocks = []
    i = 0
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        for block_cls in _MD_BLOCK_TYPES:
            result = block_cls.from_markdown(lines, i)
            if result is not None:
                block, i = result
                blocks.append(block)
                break
        else:
            i += 1

    return blocks


# ===========================================================================
# Markdown parsing
# ===========================================================================

_ATX_HEADING = re.compile(r"^(#{1,6})\s+(.*)")
_SETEXT_EQ = re.compile(r"^=+\s*$")
_SETEXT_DASH = re.compile(r"^-{2,}\s*$")


def _md_is_sep_row(line: str) -> bool:
    s = line.strip()
    return bool(s) and "-" in s and all(c in "|-: \t" for c in s)


def _md_parse_row(line: str) -> list[str]:
    result = []
    for cell in line.strip().strip("|").split("|"):
        s = cell.strip()
        if s == "<":
            result.append(_COLSPAN_MARKER)
        elif s == "^":
            result.append(_ROWSPAN_MARKER)
        elif s.startswith("\\<"):
            result.append(_encode_inline_xml("<" + s[2:]))
        elif s.startswith("\\^"):
            result.append(_encode_inline_xml("^" + s[2:]))
        else:
            result.append(_encode_inline_xml(s))
    return result


def _md_parse_table(lines: list[str]) -> "Table | None":
    from .blocks import Table  # noqa: F401 — only needed for type check at runtime

    sep_idx: int | None = next(
        (i for i, ln in enumerate(lines) if _md_is_sep_row(ln)), None
    )
    if sep_idx is None or sep_idx == 0:
        return None
    headers = _md_parse_row(lines[sep_idx - 1])
    rows = [_md_parse_row(ln) for ln in lines[sep_idx + 1 :] if ln.strip()]

    from .blocks import Table

    return Table(headers=headers, rows=rows)

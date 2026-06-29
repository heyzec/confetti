from __future__ import annotations

import html.entities
import re
from typing import override
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from html import escape

# ===========================================================================
# Namespace constants
# ===========================================================================

_AC_NS = "http://atlassian.com/ac"
_RI_NS = "http://atlassian.com/ri"
_MACRO_NS = {_AC_NS, _RI_NS}

ET.register_namespace("ac", _AC_NS)
ET.register_namespace("ri", _RI_NS)

# Transparent layout macros (block-level, content traversed but wrapper is
# preserved via LayoutMacro — see below).  easy-heading-free only appears as
# an inline element inside <p>, so it never hits _xhtml_traverse's block path.
_TRANSPARENT_LAYOUT_MACROS = {"easy-heading-free"}

# Sentinels for inline raw XML fragments embedded in text strings
_RAW_OPEN = "\x02"
_RAW_CLOSE = "\x03"

# ===========================================================================
# Inline Markdown ↔ XHTML
# ===========================================================================

_INLINE_MD_PATTERNS = [
    (re.compile(r"\[([^\]]*)\]\(([^)]*)\)"), "link"),
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

# Characters we re-encode as named HTML entities when emitting XHTML
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
            result.append(escape(text[pos:]))
            break

        if best_start > pos:
            result.append(escape(text[pos:best_start]))

        inner = escape(best_m.group(1))
        if best_name == "link":
            result.append(f'<a href="{escape(best_m.group(2))}">{inner}</a>')
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


_SENTINEL_RE = re.compile(
    re.escape(_RAW_OPEN) + r"(.*?)" + re.escape(_RAW_CLOSE), re.DOTALL
)


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


# ===========================================================================
# XHTML parsing helpers
# ===========================================================================

_XML_PREDEFINED = {"lt", "gt", "amp", "apos", "quot"}
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_CELL_TAGS = {"td", "th"}
_LIST_TAGS = {"ul", "ol"}

# Mapping from namespace URI to prefix for serialization
_NS_TO_PREFIX = {_AC_NS: "ac", _RI_NS: "ri"}


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
        # Un-escape XML entities ET may have introduced in element text
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


def _xhtml_parse_table(element: ET.Element) -> Table | None:
    """Parse a simple (no Confluence attributes) table into the Table IR."""

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
    first_cells = get_cells(trs[0])
    if not first_cells:
        return None

    headers = [_normalize(_collect_inline(c)) for c in first_cells]
    rows: list[list[str]] = [
        [_normalize(_collect_inline(c)) for c in get_cells(tr)]
        for tr in trs[1:]
        if get_cells(tr)
    ]
    return Table(headers=headers, rows=rows)


_SUPPORTED_INLINE_LOCALS = frozenset(
    {
        "br",
        "time",
        "a",
        "strong",
        "b",
        "em",
        "i",
        "s",
        "del",
        "code",
    }
)


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


def _is_complex_table(element: ET.Element) -> bool:
    """Return True if the table has Confluence-specific attributes that
    cannot be round-tripped through the simple Table IR (class, style,
    colgroup, colspan, rowspan, etc.).
    """
    # tag = element.tag if "}" not in element.tag else element.tag.split("}")[1] # ???
    # Table-level attributes
    if element.get("class") or element.get("style"):
        return True
    # Presence of colgroup child
    for child in element:
        if _local(child.tag) == "colgroup":
            return True
    # Cell-level colspan / rowspan
    for desc in element.iter():
        if _local(desc.tag) in _CELL_TAGS:
            if desc.get("colspan") or desc.get("rowspan"):
                return True
    return False


def _xhtml_traverse(element: ET.Element, blocks: list[Block]) -> None:
    if _is_macro(element.tag):
        local = _local(element.tag)
        if local == "structured-macro":
            name = element.get(f"{{{_AC_NS}}}name", "")
            if name == "numberedheadings":
                # Preserve the wrapper and traverse its rich-text-body children
                open_xml = _serialize_open_tag(element)
                close_xml = f"</{_et_tag_to_qname(element.tag)}>"
                inner_blocks: list[Block] = []
                for child in element:
                    if _local(child.tag) == "rich-text-body":
                        open_xml += _serialize_open_tag(child)
                        close_xml = f"</{_et_tag_to_qname(child.tag)}>" + close_xml
                        for grandchild in child:
                            _xhtml_traverse(grandchild, inner_blocks)
                    else:
                        _xhtml_traverse(child, inner_blocks)
                blocks.append(
                    LayoutMacro(
                        open_xml=open_xml, close_xml=close_xml, blocks=inner_blocks
                    )
                )
            elif name in _TRANSPARENT_LAYOUT_MACROS:
                for child in element:
                    _xhtml_traverse(child, blocks)
            else:
                blocks.append(RawBlock(xml=_serialize_element(element)))
        elif local == "rich-text-body":
            for child in element:
                _xhtml_traverse(child, blocks)
        else:
            blocks.append(RawBlock(xml=_serialize_element(element)))
        return

    local = _local(element.tag)

    if local in _HEADING_TAGS:
        if element.attrib or not _inline_is_simple(element):
            blocks.append(RawBlock(xml=_serialize_element(element)))
            return
        text = _normalize(_collect_inline(element))
        if text:
            blocks.append(Heading(level=int(local[1]), text=text))
        return

    if local == "p":
        if element.attrib or not _inline_is_simple(element):
            blocks.append(RawBlock(xml=_serialize_element(element)))
            return
        text = _normalize(_collect_inline(element))
        if text:
            blocks.append(Paragraph(text=text))
        elif list(element):
            blocks.append(RawBlock(xml=_serialize_element(element)))
        return

    if local == "table":
        # Complex Confluence tables preserved verbatim; simple tables use Table IR
        if _is_complex_table(element):
            blocks.append(RawBlock(xml=_serialize_element(element)))
        else:
            table = _xhtml_parse_table(element)
            if table:
                blocks.append(table)
        return

    if local in _LIST_TAGS:
        blocks.append(RawBlock(xml=_serialize_element(element)))
        return

    for child in element:
        _xhtml_traverse(child, blocks)


# ===========================================================================
# Markdown parsing
# ===========================================================================

_ATX_HEADING = re.compile(r"^(#{1,6})\s+(.*)")
_SETEXT_EQ = re.compile(r"^=+\s*$")
_SETEXT_DASH = re.compile(r"^-{2,}\s*$")

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


def _md_is_sep_row(line: str) -> bool:
    s = line.strip()
    return bool(s) and "-" in s and all(c in "|-: \t" for c in s)


def _md_parse_row(line: str) -> list[str]:
    return [_encode_inline_xml(c.strip()) for c in line.strip().strip("|").split("|")]


def _md_parse_table(lines: list[str]) -> Table | None:
    sep_idx: int | None = next(
        (i for i, ln in enumerate(lines) if _md_is_sep_row(ln)), None
    )
    if sep_idx is None or sep_idx == 0:
        return None
    headers = _md_parse_row(lines[sep_idx - 1])
    rows = [_md_parse_row(ln) for ln in lines[sep_idx + 1 :] if ln.strip()]
    return Table(headers=headers, rows=rows)


# ===========================================================================
# IR types
# ===========================================================================


class Block(ABC):
    @abstractmethod
    def to_markdown(self) -> str: ...

    @abstractmethod
    def to_xhtml(self) -> str: ...


@dataclass
class Paragraph(Block):
    text: str

    @override
    def to_markdown(self) -> str:
        return _render_for_markdown(self.text)

    @override
    def to_xhtml(self) -> str:
        return f"<p>{_render_for_xhtml(self.text)}</p>"


@dataclass
class Heading(Block):
    level: int
    text: str

    @override
    def to_markdown(self) -> str:
        return f"{'#' * self.level} {_render_for_markdown(self.text)}"

    @override
    def to_xhtml(self) -> str:
        return f"<h{self.level}>{_render_for_xhtml(self.text)}</h{self.level}>"


@dataclass
class Table(Block):
    headers: list[str]
    rows: list[list[str]]

    @override
    def to_markdown(self) -> str:
        ncols = max(len(self.headers), max((len(r) for r in self.rows), default=0))
        if ncols == 0:
            return ""

        def pad(row: list[str]) -> list[str]:
            return row + [""] * (ncols - len(row))

        def esc(text: str) -> str:
            clean = _render_for_markdown(text)
            return clean.replace("|", "\\|").replace("\n", " ").replace("\r", "")

        header_line = "| " + " | ".join(esc(h) for h in pad(self.headers)) + " |"
        sep_line = "| " + " | ".join("---" for _ in range(ncols)) + " |"
        data_lines = [
            "| " + " | ".join(esc(c) for c in pad(row)) + " |" for row in self.rows
        ]
        return "\n".join([header_line, sep_line, *data_lines])

    @override
    def to_xhtml(self) -> str:
        lines = ["<table>"]
        if self.headers:
            lines.append("  <tr>")
            for h in self.headers:
                lines.append(f"    <th>{_render_for_xhtml(h)}</th>")
            lines.append("  </tr>")
        for row in self.rows:
            lines.append("  <tr>")
            for cell in row:
                lines.append(f"    <td>{_render_for_xhtml(cell)}</td>")
            lines.append("  </tr>")
        lines.append("</table>")
        return "\n".join(lines)


@dataclass
class RawBlock(Block):
    """An opaque XML block preserved verbatim."""

    xml: str

    @override
    def to_markdown(self) -> str:
        return f"<!-- ac:macro\n{self.xml}\n-->"

    @override
    def to_xhtml(self) -> str:
        return self.xml


@dataclass
class LayoutMacro(Block):
    """A layout wrapper macro (e.g. numberedheadings) whose open/close XML is
    preserved verbatim while its inner blocks remain editable in Markdown.

    Markdown representation:
        <!-- ac:layout-open
        {open_xml}
        -->

        {inner blocks}

        <!-- ac:layout-close
        {close_xml}
        -->
    """

    open_xml: str
    close_xml: str
    blocks: list[Block]

    @override
    def to_markdown(self) -> str:
        inner = "\n\n".join(b.to_markdown() for b in self.blocks)
        return (
            f"<!-- ac:layout-open\n{self.open_xml}\n-->"
            f"\n\n{inner}\n\n"
            f"<!-- ac:layout-close\n{self.close_xml}\n-->"
        )

    @override
    def to_xhtml(self) -> str:
        return (
            self.open_xml + "".join(b.to_xhtml() for b in self.blocks) + self.close_xml
        )


@dataclass
class Document:
    blocks: list[Block] = field(default_factory=list)

    @classmethod
    def from_xhtml(cls, xhtml: str) -> Document:
        xhtml = _replace_html_entities(xhtml)
        ns = f'xmlns:ac="{_AC_NS}" xmlns:ri="{_RI_NS}"'
        try:
            root = ET.fromstring(f"<root {ns}>{xhtml}</root>")
        except ET.ParseError as exc:
            raise ValueError(f"Failed to parse XHTML: {exc}") from exc
        blocks: list[Block] = []
        _xhtml_traverse(root, blocks)
        return cls(blocks=blocks)

    @classmethod
    def from_markdown(cls, markdown: str) -> Document:
        lines = markdown.splitlines()
        blocks: list[Block] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if not stripped:
                i += 1
                continue

            # Layout macro wrapper open
            if stripped == "<!-- ac:layout-open":
                open_lines: list[str] = []
                i += 1
                while i < len(lines) and lines[i].rstrip() != "-->":
                    open_lines.append(lines[i])
                    i += 1
                i += 1  # skip '-->'
                open_xml = "\n".join(open_lines)

                # Collect inner lines until <!-- ac:layout-close
                inner_lines: list[str] = []
                while i < len(lines) and lines[i].strip() != "<!-- ac:layout-close":
                    inner_lines.append(lines[i])
                    i += 1

                # Skip '<!-- ac:layout-close'
                i += 1
                close_lines: list[str] = []
                while i < len(lines) and lines[i].rstrip() != "-->":
                    close_lines.append(lines[i])
                    i += 1
                i += 1  # skip '-->'
                close_xml = "\n".join(close_lines)

                inner_doc = Document.from_markdown("\n".join(inner_lines))
                blocks.append(
                    LayoutMacro(
                        open_xml=open_xml, close_xml=close_xml, blocks=inner_doc.blocks
                    )
                )
                continue

            # Preserved macro block
            if stripped == "<!-- ac:macro":
                xml_lines: list[str] = []
                i += 1
                while i < len(lines) and lines[i].rstrip() != "-->":
                    xml_lines.append(lines[i])
                    i += 1
                i += 1  # skip '-->'
                blocks.append(RawBlock(xml="\n".join(xml_lines)))
                continue

            m = _ATX_HEADING.match(line)
            if m:
                blocks.append(
                    Heading(
                        level=len(m.group(1)),
                        text=_encode_inline_xml(m.group(2).strip()),
                    )
                )
                i += 1
                continue

            if i + 1 < len(lines):
                nxt = lines[i + 1].strip()
                if _SETEXT_EQ.match(nxt):
                    blocks.append(Heading(level=1, text=_encode_inline_xml(stripped)))
                    i += 2
                    continue
                if _SETEXT_DASH.match(nxt):
                    blocks.append(Heading(level=2, text=_encode_inline_xml(stripped)))
                    i += 2
                    continue

            if "|" in stripped:
                table_lines: list[str] = []
                while i < len(lines) and "|" in lines[i]:
                    table_lines.append(lines[i])
                    i += 1
                table = _md_parse_table(table_lines)
                if table:
                    blocks.append(table)
                else:
                    for tl in table_lines:
                        if tl.strip():
                            blocks.append(
                                Paragraph(text=_encode_inline_xml(tl.strip()))
                            )
                continue

            para_lines: list[str] = []
            while i < len(lines):
                cur = lines[i]
                cur_s = cur.strip()
                if not cur_s or _ATX_HEADING.match(cur) or "|" in cur_s:
                    break
                if cur_s in (
                    "<!-- ac:macro",
                    "<!-- ac:layout-open",
                    "<!-- ac:layout-close",
                ):
                    break
                para_lines.append(cur_s)
                i += 1
            if para_lines:
                text = _encode_inline_xml(" ".join(para_lines))
                blocks.append(Paragraph(text=text))

        return cls(blocks=blocks)

    def to_markdown(self) -> str:
        return "\n\n".join(b.to_markdown() for b in self.blocks)

    def to_xhtml(self) -> str:
        return "".join(b.to_xhtml() for b in self.blocks)

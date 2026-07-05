from __future__ import annotations

import html.entities
import re
import xml.etree.ElementTree as ET

from ..constants import AC_NS, MACRO_NS, RAW_CLOSE, RAW_OPEN, RI_NS, SENTINEL_RE

# ===========================================================================
# Namespace / XML constants
# ===========================================================================


ET.register_namespace("ac", AC_NS)
ET.register_namespace("ri", RI_NS)

_NS_TO_PREFIX = {AC_NS: "ac", RI_NS: "ri"}

_XML_PREDEFINED = {"lt", "gt", "amp", "apos", "quot"}
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_CELL_TAGS = {"td", "th"}
_LIST_TAGS = {"ul", "ol"}


def normalize(text: str) -> str:
    """Collapse ASCII whitespace, but preserve non-breaking spaces (\u00a0)."""
    return re.sub(r"[ \t\n\r\f\v]+", " ", text).strip(" \t\n\r\f\v")


def _xml_escape(s: str) -> str:
    """Escape for XML text/attribute content — encodes &, <, >, " but NOT ' (valid in text nodes)."""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _re_encode_entities(text: str) -> str:
    UNICODE_TO_ENTITY = {
        "\u00a0": "&nbsp;",
        "\u2192": "&rarr;",
        "\u2190": "&larr;",
        "\u2194": "&harr;",
        "\u21d2": "&rArr;",
        "\u2013": "&ndash;",
        "\u2014": "&mdash;",
    }
    for ch, ent in UNICODE_TO_ENTITY.items():
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


def replace_html_entities(text: str) -> str:
    def replace(m: re.Match[str]) -> str:
        name = m.group(1)
        if name in _XML_PREDEFINED:
            return m.group(0)
        cp = html.entities.name2codepoint.get(name)
        return chr(cp) if cp else m.group(0)

    return re.sub(r"&([a-zA-Z][a-zA-Z0-9]*);", replace, text)


def is_local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def is_macro(tag: str) -> bool:
    ns = tag.split("}")[0][1:] if "}" in tag else ""
    return ns in MACRO_NS


def et_tag_to_qname(tag: str) -> str:
    """Convert ET Clark-notation tag '{uri}local' to 'prefix:local'."""
    if "}" in tag:
        uri, local = tag[1:].split("}", 1)
        prefix = _NS_TO_PREFIX.get(uri, "")
        return f"{prefix}:{local}" if prefix else local
    return tag


def serialize_open_tag(element: ET.Element) -> str:
    """Serialize just the opening tag of an element (no children, no tail)."""
    tag_str = et_tag_to_qname(element.tag)
    parts = [f"<{tag_str}"]
    for k, v in element.attrib.items():
        k_str = et_tag_to_qname(k)
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
    xml = xml.replace(f' xmlns:ac="{AC_NS}"', "")
    xml = xml.replace(f' xmlns:ri="{RI_NS}"', "")
    xml = _restore_cdata(xml)
    xml = _re_encode_entities_in_text(xml)
    return xml


# ===========================================================================
# Inline Markdown ↔ XHTML
# ===========================================================================


_INLINE_MD_PATTERNS = [
    (re.compile(r"\\(.)"), "escape"),
    (re.compile(r"\[([^\]]*)\]\(([^)]*)\)"), "link"),
    (re.compile(r"\*\*\*(.+?)\*\*\*", re.DOTALL), "strong_em"),
    (re.compile(r"___(.+?)___", re.DOTALL), "strong_em"),
    (re.compile(r"\*\*(.+?)\*\*", re.DOTALL), "strong"),
    (re.compile(r"__(.+?)__", re.DOTALL), "strong"),
    (re.compile(r"~~(.+?)~~", re.DOTALL), "s"),
    (re.compile(r"`([^`\n]+)`"), "code"),
    (re.compile(r"\*([^*\n]+)\*"), "em"),
    (re.compile(r"_([^_\n]+)_"), "em"),
    (re.compile(r"📅\s*(\d{4}-\d{2}-\d{2})"), "date"),
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


# suspicious function
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
            result.append(_xml_escape(text[pos:]))
            break

        if best_start > pos:
            result.append(_xml_escape(text[pos:best_start]))

        inner = _xml_escape(best_m.group(1))
        if best_name == "link":
            result.append(f'<a href="{_xml_escape(best_m.group(2))}">{inner}</a>')
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
        elif best_name == "escape":
            result.append(_xml_escape(best_m.group(1)))
        elif best_name == "date":
            result.append(f'<time datetime="{best_m.group(1)}" />')

        pos = best_m.end()

    return "".join(result)


def render_for_xhtml(text: str) -> str:
    """Convert inline Markdown + sentinel-wrapped raw XML to XHTML.
    Also re-encodes non-breaking spaces and arrow characters as HTML entities.
    """
    if RAW_OPEN not in text:
        return _re_encode_entities(_render_inline_md(text))

    raw_fragments: list[str] = []

    def _extract(m: re.Match[str]) -> str:
        raw_fragments.append(m.group(1))
        return f"\x01{len(raw_fragments) - 1}\x01"

    placeholder_text = SENTINEL_RE.sub(_extract, text)
    rendered = _render_inline_md(placeholder_text)
    for i, raw in enumerate(raw_fragments):
        rendered = rendered.replace(f"\x01{i}\x01", raw)
    return _re_encode_entities(rendered)


def render_for_markdown(text: str) -> str:
    """Strip sentinels from text for Markdown output; raw XML becomes inline HTML."""
    return text.replace(RAW_OPEN, "").replace(RAW_CLOSE, "")


def _inline_text(element: ET.Element) -> str:
    """Inline-Markdown representation of a child element (without its tail)."""
    if is_macro(element.tag):
        return f"{RAW_OPEN}{_serialize_element(element)}{RAW_CLOSE}"

    local = is_local(element.tag)
    if local == "br":
        return " "
    if local == "time":
        dt = element.get("datetime", "")
        return f"📅 {dt}" if dt else ""
    if local == "a":
        href = element.get("href", "")
        inner = collect_inline(element)
        return f"[{inner}]({href})" if href else inner
    if local in _XHTML_INLINE_TAGS:
        pre, post = _XHTML_INLINE_TAGS[local]
        inner = collect_inline(element)
        return f"{pre}{inner}{post}" if inner else ""

    return collect_inline(element)


def collect_inline(element: ET.Element) -> str:
    """Collect all inline-Markdown text from within an element."""
    parts: list[str] = []
    if element.text:
        parts.append((element.text))
    for child in element:
        parts.append(_inline_text(child))
        if child.tail:
            parts.append((child.tail))

    output = "".join(parts)
    # _ = escape_md_text(output)  # turn out this isn't covered in tests
    return output


# ===========================================================================
# XHTML traversal
# ===========================================================================

# Transparent layout macros: content traversed, wrapper preserved via LayoutMacro.
_TRANSPARENT_LAYOUT_MACROS = {"easy-heading-free"}

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


def inline_is_simple(element: ET.Element) -> bool:
    """Return True if every descendant (non-macro) element is a supported inline tag."""
    for child in element.iter():
        if child is element:
            continue
        if is_macro(child.tag):
            continue
        local = is_local(child.tag)
        if local not in _SUPPORTED_INLINE_LOCALS:
            return False
        if local == "a" and set(child.attrib.keys()) - {"href"}:
            return False
        if local not in ("a", "br", "time") and child.attrib:
            return False
    return True


_BLOCK_CONTENT_TAGS = frozenset(
    {
        "p",
        "div",
        "ul",
        "ol",
        "table",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "pre",
        "blockquote",
    }
)


def _blocks_from_elements(elements: list[ET.Element]) -> list:
    from ..blocks import (
        CodeBlock,
        Heading,
        LayoutMacro,
        List,
        Paragraph,
        RawBlock,
        Table,
        TaskList,
    )

    _XHTML_BLOCK_TYPES = [
        LayoutMacro,
        CodeBlock,
        TaskList,
        Heading,
        Paragraph,
        Table,
        List,
        RawBlock,
    ]

    blocks = []
    for element in elements:
        # Transparent macro wrappers: recurse into their children
        if is_macro(element.tag):
            local = is_local(element.tag)
            if local == "rich-text-body":
                blocks.extend(_blocks_from_elements(list(element)))
                continue
            if local == "structured-macro":
                sv = element.get(f"{{{AC_NS}}}schema-version", "1")
                assert sv == "1", f"unexpected ac:schema-version {sv!r}"
                name = element.get(f"{{{AC_NS}}}name", "")
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

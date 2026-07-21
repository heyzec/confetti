from __future__ import annotations

import html.entities
import re
import xml.etree.ElementTree as ET

from ..constants import AC_NS, MACRO_NS, RI_NS

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


# def normalize(text: str) -> str:
#     assert isinstance(text, str), f"Expected str, got {type(text)}"
#     """Collapse ASCII whitespace, but preserve non-breaking spaces (\u00a0)."""
#     return re.sub(r"[ \t\n\r\f\v]+", " ", text).strip(" \t\n\r\f\v")


def xml_escape(s: str) -> str:
    """Escape for XML text/attribute content — encodes &, <, >, " but NOT ' (valid in text nodes)."""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


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

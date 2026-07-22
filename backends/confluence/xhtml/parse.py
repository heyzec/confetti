import re
import xml.etree.ElementTree as ET

from ..blocks import (
    Block,
    CodeBlock,
    Heading,
    LayoutMacro,
    List,
    Paragraph,
    RawBlock,
    Table,
    TaskList,
)
from ..blocks.code import Code
from ..blocks.date import Date
from ..blocks.link import Link
from ..blocks.raw_inline import RawInline
from ..blocks.styled_text import StyledText
from ..blocks.task_list import TaskListItem
from ..blocks.text import Text
from ..constants import AC_NS, RI_NS
from ..document import Document
from ..xhtml import (
    et_tag_to_qname,
    is_local,
    is_macro,
    replace_html_entities,
    serialize_open_tag,
)
from ..xhtml.table import xhtml_parse_table

from ..xhtml import _HEADING_TAGS, _LIST_TAGS, inline_is_simple, is_local, is_macro

# Transparent layout macros: content traversed, wrapper preserved via LayoutMacro.
_TRANSPARENT_LAYOUT_MACROS = {"easy-heading-free"}


def serialize_element(element: ET.Element) -> str:
    """Serialize an ET element to an XML string, excluding its tail and
    namespace declarations.  Re-encodes HTML entities and restores CDATA
    sections stripped by ElementTree.
    """

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

    saved_tail = element.tail
    element.tail = None
    xml = ET.tostring(element, encoding="unicode")
    element.tail = saved_tail
    xml = xml.replace(f' xmlns:ac="{AC_NS}"', "")
    xml = xml.replace(f' xmlns:ri="{RI_NS}"', "")
    xml = _restore_cdata(xml)
    xml = _re_encode_entities_in_text(xml)
    return xml


def parse_layout_macro(element: ET.Element) -> LayoutMacro | None:
    if not is_macro(element.tag):
        return None
    if is_local(element.tag) != "structured-macro":
        return None
    if element.get(f"{{{AC_NS}}}name", "") != "numberedheadings":
        return None
    open_xml = serialize_open_tag(element)
    close_xml = f"</{et_tag_to_qname(element.tag)}>"
    inner_blocks: list[Block] = []
    for child in element:
        if is_local(child.tag) == "rich-text-body":
            open_xml += serialize_open_tag(child)
            close_xml = f"</{et_tag_to_qname(child.tag)}>" + close_xml
            inner_blocks.extend(_blocks_from_elements(list(child)))
        else:
            inner_blocks.extend(_blocks_from_elements([child]))
    return LayoutMacro(open_xml=open_xml, close_xml=close_xml, blocks=inner_blocks)


def parse_code_block(element: ET.Element) -> CodeBlock | None:
    if not is_macro(element.tag) or is_local(element.tag) != "structured-macro":
        return None
    if element.get(f"{{{AC_NS}}}name", "") != "code":
        return None

    macro_id = element.get(f"{{{AC_NS}}}macro-id", "")
    params: list[tuple[str, str]] = []
    body = ""

    for child in element:
        local = is_local(child.tag)
        if local == "parameter":
            name = child.get(f"{{{AC_NS}}}name", "")
            params.append((name, child.text or ""))
        elif local == "plain-text-body":
            body = child.text or ""

    return CodeBlock(macro_id=macro_id, params=params, body=body)


def parse_task_list(element: ET.Element) -> TaskList | None:
    from .parse import collect_inline

    _BLOCK_LOCALS = {
        "p",
        "ul",
        "ol",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "pre",
        "table",
    }

    if not is_macro(element.tag) or is_local(element.tag) != "task-list":
        return None

    tasks: list[TaskListItem] = []
    for task_el in element:
        if is_local(task_el.tag) != "task":
            continue
        task_id = 0
        done = False
        body = None
        for child in task_el:
            loc = is_local(child.tag)
            if loc == "task-id":
                task_id = int(child.text or "0")
            elif loc == "task-status":
                if child.text == "complete":
                    done = True
                elif child.text == "incomplete":
                    done = False
                else:
                    assert False, f"Unexpected task status: {child.text!r}"
            elif loc == "task-body":
                # children = list(child)
                body = collect_inline(child)
        assert body is not None, "Task body is missing"
        tasks.append(TaskListItem(task_id=task_id, done=done, body=body))
    return TaskList(tasks=tasks)


def parse_heading(element: ET.Element) -> Heading | None:
    if is_macro(element.tag):
        return None
    local = is_local(element.tag)
    if local not in _HEADING_TAGS:
        return None
    if element.attrib or not inline_is_simple(element):
        return None
    blocks = collect_inline(element)
    assert blocks
    return Heading(level=int(local[1]), body=blocks)


def collect_inline(element: ET.Element) -> list[Block]:
    children = []
    if element.text:
        children.append(Text(re.sub(r"[ \t\n\r\f\v]+", " ", element.text)))
    for child in element:
        children.append(parse_inline(child))
        if child.tail:
            children.append(Text(re.sub(r"[ \t\n\r\f\v]+", " ", child.tail)))
    return children


def parse_inline(element: ET.Element) -> Block:
    children = collect_inline(element)
    if element.tag == "em":
        return StyledText(kind="italic", body=children)
    if element.tag == "strong":
        return StyledText(kind="bold", body=children)
    if element.tag == "code":
        assert element.text is not None, "Code element should contain text"
        return Code(code=element.text)
    if element.tag == "a":
        url = element.get("href", "")
        assert url, "Anchor tag missing href attribute"
        return Link(
            url=url,
            display_text=collect_inline(element),
        )
    if element.tag == "s":
        return StyledText(kind="strikethrough", body=children)
    elif element.tag == "br":
        return Text(text="\n")
    if element.tag == "code":
        assert len(children) == 1 and isinstance(
            children[0], Text
        ), "Code element should contain only text"
        return Code(code=children[0].text)

    if element.tag == "time":
        dt_fmt = element.get("datetime")
        assert dt_fmt
        return Date.parse(dt_fmt)

    saved_tail = element.tail
    element.tail = None
    xml = ET.tostring(element, encoding="unicode")
    element.tail = saved_tail
    return RawInline(xml=xml)


def parse_paragraph(element: ET.Element) -> Paragraph | None:
    if is_macro(element.tag):
        return None
    if is_local(element.tag) != "p":
        return None
    return Paragraph(body=collect_inline(element))


def parse_table(element: ET.Element) -> Table | None:
    if is_macro(element.tag) or is_local(element.tag) != "table":
        return None
    return xhtml_parse_table(element)


def parse_list(element: ET.Element) -> List | None:
    local = is_local(element.tag)
    if local not in ("ul", "ol") or is_macro(element.tag):
        return None

    items: list[list[Block]] = []
    for child in element:
        if is_local(child.tag) != "li":
            return None
        if not inline_is_simple(child):
            return None
        items.append(collect_inline(child))

    return List(tag=local, items=items)


def parse_raw_block(element: ET.Element) -> RawBlock | None:
    local = is_local(element.tag)

    if is_macro(element.tag):
        return RawBlock(xml=serialize_element(element))

    if local in _LIST_TAGS:
        return RawBlock(xml=serialize_element(element))

    # Any table Table.from_xhtml couldn't handle (truly complex or unrepresentable cells)
    if local == "table":
        return RawBlock(xml=serialize_element(element))

    if local in _HEADING_TAGS and (element.attrib or not inline_is_simple(element)):
        return RawBlock(xml=serialize_element(element))

    if local == "p":
        if element.attrib or not inline_is_simple(element):
            return RawBlock(xml=serialize_element(element))
        assert False, "uncovered code"
        # if list(element) and not normalize(collect_inline(element)):
        #     return RawBlock(xml=_serialize_element(element))

    return None


def parse_element(element: ET.Element) -> Block | None:
    parsers = [
        parse_layout_macro,
        parse_code_block,
        parse_task_list,
        parse_heading,
        parse_paragraph,
        parse_table,
        parse_list,
        parse_raw_block,
    ]
    for parser in parsers:
        block = parser(element)
        if block is not None:
            return block
    return None


def _blocks_from_elements(elements: list[ET.Element]) -> list:
    blocks = []
    for element in elements:
        block = parse_element(element)
        if block is not None:
            blocks.append(block)
        else:
            # Maybe this element is just a container (div, body, etc.)
            # Ignore this container, recurse into its children
            blocks.extend(_blocks_from_elements(list(element)))

    return blocks


def parse_xhtml(xhtml: str) -> Document:
    xhtml = replace_html_entities(xhtml)
    ns = f'xmlns:ac="{AC_NS}" xmlns:ri="{RI_NS}"'
    try:
        root = ET.fromstring(f"<root {ns}>{xhtml}</root>")
    except ET.ParseError as exc:
        raise ValueError(f"Failed to parse XHTML: {exc}") from exc
    return Document(blocks=_blocks_from_elements(list(root)))

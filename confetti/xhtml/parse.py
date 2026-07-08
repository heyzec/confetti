import xml.etree.ElementTree as ET

from confetti.blocks import (
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
from confetti.constants import AC_NS, RI_NS
from confetti.document import Document
from confetti.xhtml import (
    _serialize_element,
    et_tag_to_qname,
    is_local,
    is_macro,
    replace_html_entities,
    serialize_open_tag,
)
from confetti.xhtml.table import xhtml_parse_table

from ..xhtml import (
    _HEADING_TAGS,
    _LIST_TAGS,
    collect_inline,
    inline_is_simple,
    is_local,
    is_macro,
    normalize,
)

# Transparent layout macros: content traversed, wrapper preserved via LayoutMacro.
_TRANSPARENT_LAYOUT_MACROS = {"easy-heading-free"}


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

    tasks: list[tuple[int, str, str]] = []
    for task_el in element:
        if is_local(task_el.tag) != "task":
            continue
        task_id = 0
        status = "incomplete"
        body_md = ""
        for child in task_el:
            loc = is_local(child.tag)
            if loc == "task-id":
                task_id = int(child.text or "0")
            elif loc == "task-status":
                status = child.text or "incomplete"
            elif loc == "task-body":
                children = list(child)
                has_block = any(
                    is_local(c.tag) in _BLOCK_LOCALS
                    for c in children
                    if not is_macro(c.tag)
                )
                has_direct_text = bool(child.text and child.text.strip())
                if has_block and not has_direct_text:
                    blocks = _blocks_from_elements(children)
                    body_md = (
                        "\n".join(b.to_markdown() for b in blocks) if blocks else ""
                    )
                elif inline_is_simple(child):
                    body_md = normalize(collect_inline(child))
                else:
                    return None  # unsupported body → fall back to RawBlock
        tasks.append((task_id, status, body_md))

    return TaskList(tasks=tasks)


def parse_heading(element: ET.Element) -> Heading | None:
    if is_macro(element.tag):
        return None
    local = is_local(element.tag)
    if local not in _HEADING_TAGS:
        return None
    if element.attrib or not inline_is_simple(element):
        return None
    text = normalize(collect_inline(element))
    return Heading(level=int(local[1]), text=text) if text else None


def parse_paragraph(element: ET.Element) -> Paragraph | None:
    if is_macro(element.tag):
        return None
    if is_local(element.tag) != "p":
        return None
    if element.attrib or not inline_is_simple(element):
        return None
    text = normalize(collect_inline(element))
    return Paragraph(text=text) if text else None


def parse_table(element: ET.Element) -> Table | None:
    if is_macro(element.tag) or is_local(element.tag) != "table":
        return None
    return xhtml_parse_table(element)


def parse_list(element: ET.Element) -> List | None:
    local = is_local(element.tag)
    if local not in ("ul", "ol") or is_macro(element.tag):
        return None

    items: list[str] = []
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
        return RawBlock(xml=_serialize_element(element))

    if local in _LIST_TAGS:
        return RawBlock(xml=_serialize_element(element))

    # Any table Table.from_xhtml couldn't handle (truly complex or unrepresentable cells)
    if local == "table":
        return RawBlock(xml=_serialize_element(element))

    if local in _HEADING_TAGS and (element.attrib or not inline_is_simple(element)):
        return RawBlock(xml=_serialize_element(element))

    if local == "p":
        if element.attrib or not inline_is_simple(element):
            return RawBlock(xml=_serialize_element(element))
        if list(element) and not normalize(collect_inline(element)):
            return RawBlock(xml=_serialize_element(element))

    return None


def _blocks_from_elements(elements: list[ET.Element]) -> list:
    constructors = [
        parse_layout_macro,
        parse_code_block,
        parse_task_list,
        parse_heading,
        parse_paragraph,
        parse_table,
        parse_list,
        parse_raw_block,
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
        for constructor in constructors:
            block = constructor(element)
            if block is not None:
                break

        if block is not None:
            blocks.append(block)
        else:
            # Transparent non-macro container (div, body, etc.) → recurse
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

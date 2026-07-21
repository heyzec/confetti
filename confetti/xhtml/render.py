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
from ..blocks.text import Text
from ..document import Document
from ..xhtml import xml_escape

from ..xhtml.table import render_table_xhtml


def render_code_block(block: CodeBlock) -> str:
    parts = [
        f'<ac:structured-macro ac:name="code"'
        f' ac:schema-version="1"'
        f' ac:macro-id="{block.macro_id}">'
    ]
    for name, value in block.params:
        parts.append(f'<ac:parameter ac:name="{name}">{value}</ac:parameter>')
    parts.append(f"<ac:plain-text-body><![CDATA[{block.body}]]></ac:plain-text-body>")
    parts.append("</ac:structured-macro>")
    return "".join(parts)


def render_inline(block: Block) -> str:
    if isinstance(block, Text):
        return xml_escape(block.text)
    if isinstance(block, StyledText):
        contents = "".join([render_inline(child) for child in block.body])
        if block.kind == "bold":
            return f"<strong>{contents}</strong>"
        if block.kind == "italic":
            return f"<em>{contents}</em>"
        if block.kind == "strikethrough":
            return f"<s>{contents}</s>"
        assert False, f"Unsupported StyledText kind: {block.kind}"
    if isinstance(block, Code):
        return f"<code>{block.code}</code>"
    if isinstance(block, Link):
        contents = "".join([render_inline(child) for child in block.display_text])
        return f'<a href="{block.url}">{contents}</a>'
    if isinstance(block, Date):
        return f'<time datetime="{block.format()}" />'
    if isinstance(block, RawInline):
        return block.xml

    assert False, f"Unsupported inline block type: {type(block).__name__}"


def render_paragraph(block: Paragraph) -> str:
    inner = "".join(render_inline(child) for child in block.body)
    return f"<p>{inner}</p>"


def render_heading(block: Heading) -> str:
    inner = "".join(render_inline(child) for child in block.body)
    return f"<h{block.level}>{inner}</h{block.level}>"


def render_list(block: List) -> str:
    fragments = []
    for item in block.items:
        rendered = "".join(render_inline(child) for child in item)
        fragments.append(f"<li>{rendered}</li>")
    return f"<{block.tag}>" + "".join(fragments) + f"</{block.tag}>"


def render_table(block: Table) -> str:
    return render_table_xhtml(block)


def render_layout_macro(block: LayoutMacro) -> str:
    return (
        block.open_xml
        + "".join(render_xhtml_for_block(b) for b in block.blocks)
        + block.close_xml
    )


def render_raw_block(block: RawBlock) -> str:
    return block.xml


def render_task_list(block: TaskList) -> str:
    parts = ["<ac:task-list>"]
    for task_item in block.tasks:
        parts.append(
            f"\n<ac:task>"
            f"\n<ac:task-id>{task_item.task_id}</ac:task-id>"
            f"\n<ac:task-status>{'incomplete' if task_item.done else 'incomplete'}</ac:task-status>"
            f"\n<ac:task-body>{''.join(render_inline(b) for b in task_item.body)}</ac:task-body>"
            f"\n</ac:task>"
        )
    parts.append("\n</ac:task-list>")
    return "".join(parts)


def render_xhtml_for_block(block: Block) -> str:
    dispatchers = {
        CodeBlock: render_code_block,
        Heading: render_heading,
        Paragraph: render_paragraph,
        List: render_list,
        Table: render_table,
        LayoutMacro: render_layout_macro,
        RawBlock: render_raw_block,
        TaskList: render_task_list,
    }
    t = type(block)
    if t not in dispatchers:
        assert False, f"Unsupported block type: {t.__name__}"
    return dispatchers[t](block)


def render_xhtml(doc: Document) -> str:
    fragments = []
    for block in doc.blocks:
        fragments.append(render_xhtml_for_block(block))
    return "".join(fragments)

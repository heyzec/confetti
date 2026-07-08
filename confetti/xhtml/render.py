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
from confetti.document import Document
from confetti.markdown.parse import parse_markdown
from confetti.xhtml import render_for_xhtml

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


def render_heading(block: Heading) -> str:
    return f"<h{block.level}>{render_for_xhtml(block.text)}</h{block.level}>"


def render_paragraph(block: Paragraph) -> str:
    return f"<p>{render_for_xhtml(block.text)}</p>"


def render_list(block: List) -> str:
    inner = "".join(f"<li>{render_for_xhtml(item)}</li>" for item in block.items)
    return f"<{block.tag}>{inner}</{block.tag}>"


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
    for task_id, status, body_md in block.tasks:
        body_xhtml = render_xhtml(parse_markdown(body_md))
        parts.append(
            f"\n<ac:task>"
            f"\n<ac:task-id>{task_id}</ac:task-id>"
            f"\n<ac:task-status>{status}</ac:task-status>"
            f"\n<ac:task-body>{body_xhtml}</ac:task-body>"
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

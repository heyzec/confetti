import json

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
from confetti.blocks.code import Code
from confetti.blocks.date import Date
from confetti.blocks.link import Link
from confetti.blocks.raw_inline import RawInline
from confetti.blocks.styled_text import StyledText
from confetti.blocks.text import Text
from confetti.document import Document
from confetti.markdown import escape_md_text

from ..markdown.table import render_table_markdown


def render_code_block(block: CodeBlock) -> str:
    extra_params = [(k, v) for k, v in block.params if k != "language"]
    meta: dict = {}
    if block.macro_id:
        meta["macro-id"] = block.macro_id
    if extra_params:
        meta["params"] = extra_params
    lang = block._language()
    fence_open = f"```{lang}" if lang else "```"
    fence = f"{fence_open}\n{block.body}\n```"
    if not meta:
        return fence  # no metadata → bare fence, no comment header needed
    meta_str = json.dumps(meta, separators=(", ", ": "))
    return f"<!-- confetti:code {meta_str} -->\n{fence}"


def render_inline(block: Block) -> str:
    if isinstance(block, Text):
        return escape_md_text(block.text)
    if isinstance(block, StyledText):
        contents = "".join([render_inline(child) for child in block.body])
        if block.kind == "bold":
            return f"**{contents}**"
        if block.kind == "italic":
            return f"*{contents}*"
        if block.kind == "strikethrough":
            return f"~~{contents}~~"
        assert False, f"Unsupported styled text kind: {block.kind}"
    if isinstance(block, Link):
        contents = "".join([render_inline(child) for child in block.display_text])
        return f"[{contents}]({block.url})"
    if isinstance(block, Code):
        return f"`{block.code}`"
    if isinstance(block, Date):
        return f"📅 {block.format()}"

    if isinstance(block, RawInline):
        return block.xml  # raw XML is preserved verbatim in inline context
    assert False, f"Unsupported inline block type: {type(block).__name__}"


def render_paragraph(block: Paragraph) -> str:
    line = "".join(render_inline(child) for child in block.body)
    return line.strip()


def render_heading(block: Heading) -> str:
    subline = "".join(render_inline(child) for child in block.body)
    return f"{'#' * block.level} " + subline


def render_list(block: List) -> str:
    lines = []
    for n, item in enumerate(block.items, 1):
        content = "".join(render_inline(b) for b in item)
        if block.tag == "ol":
            lines.append(f"{n}. {content}")
        else:
            lines.append(f"- {content}")
    return "\n".join(lines)


def render_table(block: Table) -> str:
    return render_table_markdown(block)


def render_layout_macro(block: LayoutMacro) -> str:
    inner = "\n\n".join(render_markdown_for_block(b) for b in block.blocks)
    return (
        f"<!-- confetti:layout-open\n{block.open_xml}\n-->"
        f"\n\n{inner}\n\n"
        f"<!-- confetti:layout-close\n{block.close_xml}\n-->"
    )


def render_raw_block(block: RawBlock) -> str:
    return f"<!-- confetti:raw\n{block.xml}\n-->"


def render_task_list(block: TaskList) -> str:
    lines = []
    for task_item in block.tasks:
        check = "x" if task_item.done else " "
        rendered = "".join(render_inline(b) for b in task_item.body)
        lines.append(f"- [{check}] {rendered}")
    return "\n".join(lines)


def render_markdown_for_block(block: Block) -> str:
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


def render_markdown(doc: Document) -> str:
    lines = []
    for block in doc.blocks:
        lines.append(render_markdown_for_block(block))
    return "\n\n".join(lines)

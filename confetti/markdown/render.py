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
from confetti.document import Document
from confetti.xhtml import render_for_markdown

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


def render_heading(block: Heading) -> str:
    return f"{'#' * block.level} {render_for_markdown(block.text)}"


def render_paragraph(block: Paragraph) -> str:
    return render_for_markdown(block.text)


def render_list(block: List) -> str:
    if block.tag == "ol":
        return "\n".join(f"{n}. {item}" for n, item in enumerate(block.items, 1))
    return "\n".join(f"- {item}" for item in block.items)


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
    for _task_id, status, body_md in block.tasks:
        check = "x" if status == "complete" else " "
        body_lines = body_md.splitlines()
        first = body_lines[0] if body_lines else ""
        rest = ["    " + l for l in body_lines[1:]]
        lines.append(f"- [{check}] {first}")
        lines.extend(rest)
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

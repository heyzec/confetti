from __future__ import annotations

import json
import re

from ..blocks import (
    Block,
    CodeBlock,
    ExpandBlock,
    Heading,
    LayoutMacro,
    List,
    Paragraph,
    RawBlock,
    TaskList,
)
from ..blocks.code import Code
from ..blocks.date import Date
from ..blocks.link import Link
from ..blocks.raw_inline import RawInline
from ..blocks.styled_text import StyledText
from ..blocks.task_list import TaskListItem
from ..blocks.text import Text
from ..document import Document
from .constants import ATX_HEADING, SETEXT_DASH, SETEXT_EQ
from .table import parse_table

# List specific constant required by parse_paragraph
_UL_ITEM = re.compile(r"^[-*]\s+(.+)")
_OL_ITEM = re.compile(r"^\d+\.\s+(.+)")


def parse_layout_macro(lines: list[str], i: int) -> tuple[LayoutMacro, int] | None:
    if lines[i].strip() != "<!-- confetti:layout-open":
        return None
    open_lines: list[str] = []
    i += 1
    while i < len(lines) and lines[i].rstrip() != "-->":
        open_lines.append(lines[i])
        i += 1
    i += 1  # skip '-->'
    open_xml = "\n".join(open_lines)

    inner_lines: list[str] = []
    while i < len(lines) and lines[i].strip() != "<!-- confetti:layout-close":
        inner_lines.append(lines[i])
        i += 1
    i += 1  # skip '<!-- confetti:layout-close'

    close_lines: list[str] = []
    while i < len(lines) and lines[i].rstrip() != "-->":
        close_lines.append(lines[i])
        i += 1
    i += 1  # skip '-->'
    close_xml = "\n".join(close_lines)

    inner_blocks = md_blocks_from_lines(inner_lines)
    return LayoutMacro(open_xml=open_xml, close_xml=close_xml, blocks=inner_blocks), i


def parse_code_block(lines: list[str], i: int) -> tuple[CodeBlock, int] | None:
    line = lines[i].strip()

    if line.startswith("<!-- confetti:code ") and line.endswith(" -->"):
        meta_str = line[len("<!-- confetti:code ") : -len(" -->")]
        try:
            meta = json.loads(meta_str)
        except json.JSONDecodeError:
            return None
        macro_id = meta.get("macro-id", "")
        params: list[tuple[str, str]] = [tuple(p) for p in meta.get("params", [])]
        i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines) or not lines[i].strip().startswith("```"):
            return None
        lang = lines[i].strip()[3:]
        if lang:
            params = [("language", lang)] + params
        i += 1
    elif line.startswith("```"):
        macro_id = ""
        lang = line[3:]
        params = [("language", lang)] if lang else []
        i += 1
    else:
        return None

    body_lines: list[str] = []
    while i < len(lines) and lines[i].strip() != "```":
        body_lines.append(lines[i])
        i += 1
    i += 1  # skip closing ```

    body = "\n".join(body_lines)
    return CodeBlock(macro_id=macro_id, params=params, body=body), i


def parse_task_list(lines: list[str], i: int) -> tuple[TaskList, int] | None:
    _TASK_GFM = re.compile(r"^[-*]\s+\[([ x])\]\s*(.*)")
    _CONTINUATION = re.compile(r"^ {2,}(.+)")

    if not _TASK_GFM.match(lines[i]):
        return None

    tasks: list[TaskListItem] = []
    auto_id = 1
    while i < len(lines):
        m = _TASK_GFM.match(lines[i])
        if not m:
            break
        check, body = m.group(1), m.group(2).strip()
        i += 1
        cont: list[str] = []
        while i < len(lines) and _CONTINUATION.match(lines[i]):
            cont.append(_CONTINUATION.match(lines[i]).group(1))  # type: ignore[union-attr]
            i += 1
        if cont:
            body = (body + "\n" if body else "") + "\n".join(cont)
        done = check != " "
        tasks.append(TaskListItem(task_id=auto_id, done=done, body=parse_inline(body)))
        auto_id += 1
    if not tasks:
        return None
    return TaskList(tasks=tasks), i


def parse_raw_block(lines: list[str], i: int) -> tuple[RawBlock, int] | None:
    if lines[i].strip() != "<!-- confetti:raw":
        return None
    xml_lines: list[str] = []
    i += 1
    while i < len(lines) and lines[i].rstrip() != "-->":
        xml_lines.append(lines[i])
        i += 1
    i += 1  # skip '-->'
    return RawBlock(xml="\n".join(xml_lines)), i


_DETAILS_OPEN = re.compile(r'^<details(?:\s+data-macro-id="([^"]*)")?>')
_SUMMARY = re.compile(r"^<summary>(.*)</summary>$")


def parse_expand(lines: list[str], i: int) -> tuple[ExpandBlock, int] | None:
    m = _DETAILS_OPEN.match(lines[i].strip())
    if not m:
        return None
    macro_id = m.group(1) or ""
    i += 1
    title = ""
    if i < len(lines):
        sm = _SUMMARY.match(lines[i].strip())
        if sm:
            title = sm.group(1)
            i += 1
    inner_lines: list[str] = []
    while i < len(lines) and lines[i].strip() != "</details>":
        inner_lines.append(lines[i])
        i += 1
    i += 1  # skip '</details>'
    inner_blocks = md_blocks_from_lines(inner_lines)
    return ExpandBlock(macro_id=macro_id, title=title, blocks=inner_blocks), i


def parse_list(lines: list[str], i: int) -> tuple[List, int] | None:
    ul_m = _UL_ITEM.match(lines[i])
    ol_m = _OL_ITEM.match(lines[i])
    pat, tag = (_UL_ITEM, "ul") if ul_m else (_OL_ITEM, "ol") if ol_m else (None, "")
    if not pat:
        return None

    items: list[list[Block]] = []
    while i < len(lines):
        m = pat.match(lines[i])
        if not m:
            break
        items.append(parse_inline(m.group(1)))
        i += 1

    return List(tag=tag, items=items), i


def parse_heading(lines: list[str], i: int) -> tuple[Heading, int] | None:
    line = lines[i]
    m = ATX_HEADING.match(line)
    if m:
        return (
            Heading(level=len(m.group(1)), body=parse_inline(m.group(2).strip())),
            i + 1,
        )
    stripped = line.strip()
    if stripped and i + 1 < len(lines):
        nxt = lines[i + 1].strip()
        if SETEXT_EQ.match(nxt):
            return Heading(level=1, body=parse_inline(stripped)), i + 2
        if SETEXT_DASH.match(nxt):
            return Heading(level=2, body=parse_inline(stripped)), i + 2
    return None


def parse_paragraph(lines: list[str], i: int) -> tuple[Paragraph, int] | None:
    para_lines: list[str] = []
    while i < len(lines):
        cur_s = lines[i].strip()
        if not cur_s or ATX_HEADING.match(lines[i]) or "|" in cur_s:
            break
        if cur_s in (
            "<!-- confetti:raw",
            "<!-- confetti:layout-open",
            "<!-- confetti:layout-close",
        ):
            break
        if cur_s.startswith("<details") or cur_s == "</details>":
            break
        if (
            cur_s.startswith("```")
            or cur_s.startswith("- ")
            or cur_s.startswith("* ")
            or _OL_ITEM.match(cur_s)
        ):
            break
        para_lines.append(cur_s)
        i += 1
    if para_lines:
        body = []
        for line in para_lines:
            temp = parse_inline(line)
            body.extend(temp)
        return Paragraph(body=body), i
    return None


def parse_styled_text(lines: list[str], i: int) -> tuple[Paragraph, int] | None:
    print("Parsing styled text starting at line", i)
    # This is a placeholder for parsing styled text if needed.
    # Currently, it behaves the same as parse_paragraph.
    return parse_paragraph(lines, i)


_INLINE_MD_PATTERNS = [
    (re.compile(r"\\(?P<inner>.)"), "escape"),
    (re.compile(r"\[(?P<inner>[^\]]*)\]\((?P<url>[^)]*)\)"), "link"),
    (re.compile(r"\*\*\*(?P<inner>.+?)\*\*\*", re.DOTALL), "strong_em"),
    (re.compile(r"___(?P<inner>.+?)___", re.DOTALL), "strong_em"),
    (re.compile(r"\*\*(?P<inner>.+?)\*\*", re.DOTALL), "strong"),
    (re.compile(r"__(?P<inner>.+?)__", re.DOTALL), "strong"),
    (re.compile(r"~~(?P<inner>.+?)~~", re.DOTALL), "s"),
    (re.compile(r"`(?P<inner>[^`\n]+)`"), "code"),
    (re.compile(r"\*(?P<inner>[^*\n]+)\*"), "em"),
    (re.compile(r"_(?P<inner>[^_\n]+)_"), "em"),
    (re.compile(r"📅\s*(?P<inner>\d{4}-\d{2}-\d{2})"), "date"),
    (re.compile(r"<([^>]+)( [^>]+)?>(?P<inner>.+)</\1>"), "raw_inline"),
    (re.compile(r"(?P<inner>)<([^>]+)( [^>]+)?/>"), "raw_inline"),
]


def parse_inline(text: str) -> list[Block]:
    """Convert inline Markdown markers in a plain string to XHTML tags."""
    result: list[Block] = []
    pos = 0
    while pos < len(text):
        best_m, best_name, best_start = None, None, len(text)
        for pat, name in _INLINE_MD_PATTERNS:
            m = pat.search(text, pos)
            if m and m.start() < best_start:
                best_m, best_name, best_start = m, name, m.start()

        # print(
        #     f"Best match {best_name} at position {best_start} with match: {best_m.group(0) if best_m else None}"
        # )

        if best_m is None:
            # print("Here is the text to append as Text:", text[pos:])
            result.append(Text(text=text[pos:]))
            break

        if best_start > pos:
            # print("Here is the text to append as Text:", text[pos:best_start])
            result.append(Text(text=text[pos:best_start]))

        inner_text = best_m.group("inner")
        if best_name == "link":
            result.append(
                Link(url=best_m.group("url"), display_text=parse_inline(inner_text))
            )
        elif best_name == "strong_em":
            # Commonmark: <em><strong>...</strong></em> is always preferred to <strong><em>...</em></strong>
            result.append(
                StyledText(
                    kind="italic",
                    body=[StyledText(kind="bold", body=parse_inline(inner_text))],
                )
            )
        elif best_name == "strong":
            result.append(StyledText(kind="bold", body=parse_inline(inner_text)))
        elif best_name == "s":
            result.append(
                StyledText(kind="strikethrough", body=parse_inline(inner_text))
            )
        elif best_name == "code":
            result.append(Code(code=inner_text))
        elif best_name == "em":
            result.append(StyledText(kind="italic", body=parse_inline(inner_text)))
        elif best_name == "escape":
            result.append(Text(text=inner_text))
        elif best_name == "date":
            dt_fmt = best_m.group(1)
            result.append(Date.parse(dt_fmt))
        elif best_name == "raw_inline":
            result.append(RawInline(xml=best_m.group(0)))

        pos = best_m.end()

    return result


# To deprecate (avoid use by parse_layout_macro)
def md_blocks_from_lines(lines: list[str]) -> list:
    parsers = [
        parse_layout_macro,
        parse_expand,
        parse_code_block,
        parse_task_list,
        parse_raw_block,
        parse_list,
        parse_heading,
        parse_table,
        parse_paragraph,
    ]

    blocks = []
    i = 0
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        for parser in parsers:
            result = parser(lines, i)
            if result is not None:
                block, i = result
                blocks.append(block)
                break
        else:
            i += 1

    return blocks


def parse_markdown(markdown: str) -> Document:
    lines = markdown.splitlines()
    blocks = md_blocks_from_lines(lines)
    return Document(blocks=blocks)

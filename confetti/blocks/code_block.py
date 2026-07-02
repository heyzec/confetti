from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import override

from .block import Block


@dataclass
class CodeBlock(Block):
    """A Confluence code macro rendered as a fenced code block.

    Markdown representation:
        <!-- ac:code {"macro-id": "...", "schema-version": "1", "params": [["language", "sql"], ...]} -->
        ```language
        code content
        ```
    """

    macro_id: str
    schema_version: str
    params: list[tuple[str, str]]
    body: str

    def _language(self) -> str:
        for k, v in self.params:
            if k == "language":
                return v
        return ""

    @classmethod
    def from_xhtml(cls, element: ET.Element) -> CodeBlock | None:
        from ..helpers import _AC_NS, _is_macro, _local

        if not _is_macro(element.tag) or _local(element.tag) != "structured-macro":
            return None
        if element.get(f"{{{_AC_NS}}}name", "") != "code":
            return None

        macro_id = element.get(f"{{{_AC_NS}}}macro-id", "")
        schema_version = element.get(f"{{{_AC_NS}}}schema-version", "1")
        params: list[tuple[str, str]] = []
        body = ""

        for child in element:
            local = _local(child.tag)
            if local == "parameter":
                name = child.get(f"{{{_AC_NS}}}name", "")
                params.append((name, child.text or ""))
            elif local == "plain-text-body":
                body = child.text or ""

        return cls(macro_id=macro_id, schema_version=schema_version, params=params, body=body)

    @classmethod
    def from_markdown(cls, lines: list[str], i: int) -> tuple[CodeBlock, int] | None:
        line = lines[i].strip()
        if not (line.startswith("<!-- ac:code ") and line.endswith(" -->")):
            return None
        meta_str = line[len("<!-- ac:code "):-len(" -->")]
        try:
            meta = json.loads(meta_str)
        except json.JSONDecodeError:
            return None

        macro_id = meta.get("macro-id", "")
        schema_version = meta.get("schema-version", "1")
        params = [tuple(p) for p in meta.get("params", [])]

        i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines) or not lines[i].strip().startswith("```"):
            return None

        # skip the opening fence line
        i += 1
        body_lines: list[str] = []
        while i < len(lines) and lines[i].strip() != "```":
            body_lines.append(lines[i])
            i += 1
        i += 1  # skip closing ```

        body = "\n".join(body_lines)
        return cls(macro_id=macro_id, schema_version=schema_version, params=params, body=body), i

    @override
    def to_markdown(self) -> str:
        meta = {"macro-id": self.macro_id, "schema-version": self.schema_version, "params": self.params}
        meta_str = json.dumps(meta, separators=(", ", ": "))
        lang = self._language()
        fence_open = f"```{lang}" if lang else "```"
        return f"<!-- ac:code {meta_str} -->\n{fence_open}\n{self.body}\n```"

    @override
    def to_xhtml(self) -> str:
        from ..helpers import _AC_NS

        ac = f"{{{_AC_NS}}}"
        parts = [
            f'<ac:structured-macro ac:name="code"'
            f' ac:schema-version="{self.schema_version}"'
            f' ac:macro-id="{self.macro_id}">'
        ]
        for name, value in self.params:
            parts.append(f'<ac:parameter ac:name="{name}">{value}</ac:parameter>')
        parts.append(f"<ac:plain-text-body><![CDATA[{self.body}]]></ac:plain-text-body>")
        parts.append("</ac:structured-macro>")
        return "".join(parts)

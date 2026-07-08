from __future__ import annotations

import json
from dataclasses import dataclass
from typing import override

from .block import Block


@dataclass
class CodeBlock(Block):
    """A Confluence code macro rendered as a fenced code block.

    Markdown representation:
        <!-- confetti:code {"macro-id": "...", "params": [["title", "q"], ...]} -->
        ```language
        code content
        ```
    Language is stored in the fence line, not in params.
    """

    macro_id: str
    params: list[tuple[str, str]]
    body: str

    def _language(self) -> str:
        for k, v in self.params:
            if k == "language":
                return v
        return ""

    # @classmethod
    # def from_xhtml(cls, element: ET.Element) -> CodeBlock | None:
    #     ...

    # @classmethod
    # def from_markdown(cls, lines: list[str], i: int) -> tuple[CodeBlock, int] | None:
    #     ...

    @override
    def to_markdown(self) -> str:
        extra_params = [(k, v) for k, v in self.params if k != "language"]
        meta: dict = {}
        if self.macro_id:
            meta["macro-id"] = self.macro_id
        if extra_params:
            meta["params"] = extra_params
        lang = self._language()
        fence_open = f"```{lang}" if lang else "```"
        fence = f"{fence_open}\n{self.body}\n```"
        if not meta:
            return fence  # no metadata → bare fence, no comment header needed
        meta_str = json.dumps(meta, separators=(", ", ": "))
        return f"<!-- confetti:code {meta_str} -->\n{fence}"

    @override
    def to_xhtml(self) -> str:
        parts = [
            f'<ac:structured-macro ac:name="code"'
            f' ac:schema-version="1"'
            f' ac:macro-id="{self.macro_id}">'
        ]
        for name, value in self.params:
            parts.append(f'<ac:parameter ac:name="{name}">{value}</ac:parameter>')
        parts.append(
            f"<ac:plain-text-body><![CDATA[{self.body}]]></ac:plain-text-body>"
        )
        parts.append("</ac:structured-macro>")
        return "".join(parts)

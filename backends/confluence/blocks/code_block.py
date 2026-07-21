from __future__ import annotations

from dataclasses import dataclass

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

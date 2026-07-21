import re


# try moving to to render.py
def escape_md_text(s: str) -> str:
    """Escape characters in a plain text node that would be misread as Markdown."""
    return re.sub(r"([_\\])", r"\\\1", s)

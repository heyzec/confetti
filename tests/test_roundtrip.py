"""Round-trip and reverse-direction tests: Markdown → XHTML and XHTML → MD → XHTML."""

from confetti import (
    ir_to_xhtml,
    ir_to_markdown,
    markdown_to_ir,
    markdown_to_xhtml,
    xhtml_to_ir,
    xhtml_to_markdown,
)
from confetti.ir import Heading, Paragraph, Table


# ---------------------------------------------------------------------------
# Markdown → IR
# ---------------------------------------------------------------------------


class TestMarkdownToIR:
    def test_atx_h1(self):
        doc = markdown_to_ir("# Hello")
        assert len(doc.blocks) == 1
        b = doc.blocks[0]
        assert isinstance(b, Heading)
        assert b.level == 1
        assert b.text == "Hello"

    def test_atx_h3(self):
        doc = markdown_to_ir("### Deep")
        b = doc.blocks[0]
        assert isinstance(b, Heading)
        assert b.level == 3

    def test_setext_h1(self):
        doc = markdown_to_ir("Title\n=====")
        assert isinstance(doc.blocks[0], Heading)
        assert doc.blocks[0].level == 1

    def test_setext_h2(self):
        doc = markdown_to_ir("Subtitle\n--------")
        assert isinstance(doc.blocks[0], Heading)
        assert doc.blocks[0].level == 2

    def test_paragraph(self):
        doc = markdown_to_ir("Just some text.")
        assert len(doc.blocks) == 1
        assert isinstance(doc.blocks[0], Paragraph)
        assert doc.blocks[0].text == "Just some text."

    def test_multiline_paragraph_joined(self):
        doc = markdown_to_ir("Line one\nLine two")
        assert len(doc.blocks) == 1
        assert "Line one" in doc.blocks[0].text
        assert "Line two" in doc.blocks[0].text

    def test_two_paragraphs(self):
        doc = markdown_to_ir("First\n\nSecond")
        assert len(doc.blocks) == 2

    def test_table(self):
        md = "| Col1 | Col2 |\n|------|------|\n| a | b |"
        doc = markdown_to_ir(md)
        assert len(doc.blocks) == 1
        b = doc.blocks[0]
        assert isinstance(b, Table)
        assert b.headers == ["Col1", "Col2"]
        assert b.rows == [["a", "b"]]

    def test_table_with_aligned_separator(self):
        md = "| A | B |\n| :--- | ---: |\n| 1 | 2 |"
        doc = markdown_to_ir(md)
        assert isinstance(doc.blocks[0], Table)
        assert doc.blocks[0].headers == ["A", "B"]

    def test_mixed_blocks(self):
        md = "# Heading\n\nParagraph.\n\n## Sub\n\nMore."
        doc = markdown_to_ir(md)
        types = [type(b).__name__ for b in doc.blocks]
        assert types == ["Heading", "Paragraph", "Heading", "Paragraph"]


# ---------------------------------------------------------------------------
# IR → XHTML
# ---------------------------------------------------------------------------


class TestIRToXHTML:
    def test_heading(self):
        from converter.ir import Document

        doc = Document(blocks=[Heading(level=1, text="Hi")])
        assert ir_to_xhtml(doc) == "<h1>Hi</h1>"

    def test_paragraph(self):
        from converter.ir import Document

        doc = Document(blocks=[Paragraph(text="Hello")])
        assert ir_to_xhtml(doc) == "<p>Hello</p>"

    def test_paragraph_escaping(self):
        from converter.ir import Document

        doc = Document(blocks=[Paragraph(text="a < b & c > d")])
        xhtml = ir_to_xhtml(doc)
        assert "&lt;" in xhtml
        assert "&amp;" in xhtml
        assert "&gt;" in xhtml

    def test_table(self):
        from converter.ir import Document

        doc = Document(blocks=[Table(headers=["A", "B"], rows=[["1", "2"]])])
        xhtml = ir_to_xhtml(doc)
        assert "<table>" in xhtml
        assert "<th>A</th>" in xhtml
        assert "<th>B</th>" in xhtml
        assert "<td>1</td>" in xhtml
        assert "<td>2</td>" in xhtml
        assert "</table>" in xhtml


# ---------------------------------------------------------------------------
# Markdown → XHTML (full pipeline)
# ---------------------------------------------------------------------------


class TestMarkdownToXHTML:
    def test_heading(self):
        assert "<h1>Hello</h1>" in markdown_to_xhtml("# Hello")

    def test_h2(self):
        assert "<h2>Section</h2>" in markdown_to_xhtml("## Section")

    def test_paragraph(self):
        assert "<p>Text here.</p>" in markdown_to_xhtml("Text here.")

    def test_table(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        xhtml = markdown_to_xhtml(md)
        assert "<table>" in xhtml
        assert "<th>A</th>" in xhtml
        assert "<td>1</td>" in xhtml

    def test_html_escaping_in_output(self):
        md = "a < b"
        xhtml = markdown_to_xhtml(md)
        assert "<p>" in xhtml
        assert "&lt;" in xhtml


# ---------------------------------------------------------------------------
# XHTML → Markdown → IR → XHTML round-trip
# ---------------------------------------------------------------------------


class TestRoundTrip:
    def _roundtrip(self, xhtml: str) -> str:
        md = xhtml_to_markdown(xhtml)
        ir = markdown_to_ir(md)
        return ir_to_xhtml(ir)

    def test_strong_roundtrip(self):
        xhtml = "<p>Hello <strong>bold</strong> world</p>"
        assert "<strong>bold</strong>" in self._roundtrip(xhtml)

    def test_emphasis_roundtrip(self):
        xhtml = "<p>Hello <em>italic</em> world</p>"
        assert "<em>italic</em>" in self._roundtrip(xhtml)

    def test_strikethrough_roundtrip(self):
        xhtml = "<p><s>removed</s></p>"
        assert "<s>removed</s>" in self._roundtrip(xhtml)

    def test_code_roundtrip(self):
        xhtml = "<p>Call <code>foo()</code></p>"
        assert "<code>foo()</code>" in self._roundtrip(xhtml)

    def test_link_roundtrip(self):
        xhtml = '<p>See <a href="https://example.com">link</a></p>'
        result = self._roundtrip(xhtml)
        assert 'href="https://example.com"' in result
        assert ">link<" in result

    def test_heading_preserved(self):
        assert "<h1>My Heading</h1>" in self._roundtrip("<h1>My Heading</h1>")

    def test_paragraph_preserved(self):
        assert "<p>Hello world</p>" in self._roundtrip("<p>Hello world</p>")

    def test_table_structure_preserved(self):
        xhtml = """
        <table>
          <tr><th>Name</th><th>Score</th></tr>
          <tr><td>Alice</td><td>95</td></tr>
          <tr><td>Bob</td><td>87</td></tr>
        </table>
        """
        result = self._roundtrip(xhtml)
        assert "<th>Name</th>" in result
        assert "<th>Score</th>" in result
        assert "<td>Alice</td>" in result
        assert "<td>95</td>" in result

    def test_mixed_document_structure(self):
        xhtml = """
        <h1>Title</h1>
        <p>Intro.</p>
        <h2>Section</h2>
        <table>
          <tr><th>A</th><th>B</th></tr>
          <tr><td>1</td><td>2</td></tr>
        </table>
        """
        md = xhtml_to_markdown(xhtml)
        assert "# Title" in md
        assert "## Section" in md
        assert "| A | B |" in md

        result = self._roundtrip(xhtml)
        assert "<h1>" in result
        assert "<h2>" in result
        assert "<table>" in result

    def test_macro_preserved_in_roundtrip(self):
        # ac:structured-macro is preserved through the round-trip
        xhtml = """
        <p>Keep</p>
        <ac:structured-macro ac:name="code">
          <ac:plain-text-body><![CDATA[secret_code_here]]></ac:plain-text-body>
        </ac:structured-macro>
        <p>Me</p>
        """
        result = self._roundtrip(xhtml)
        assert "Keep" in result
        assert "Me" in result
        assert "ac:structured-macro" in result

    def test_block_count_preserved(self):
        xhtml = "<h1>A</h1><p>B</p><h2>C</h2>"
        ir_original = xhtml_to_ir(xhtml)
        md = ir_to_markdown(ir_original)
        ir_roundtrip = markdown_to_ir(md)
        assert len(ir_original.blocks) == len(ir_roundtrip.blocks)

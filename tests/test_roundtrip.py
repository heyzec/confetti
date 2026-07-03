"""Round-trip and reverse-direction tests: Markdown → XHTML and XHTML → MD → XHTML."""

import unittest

from confetti import (
    ir_to_xhtml,
    ir_to_markdown,
    markdown_to_ir,
    markdown_to_xhtml,
    xhtml_to_ir,
    xhtml_to_markdown,
)
from confetti.blocks import Heading, Paragraph, Table
from confetti.document import Document


# ---------------------------------------------------------------------------
# Markdown → IR
# ---------------------------------------------------------------------------


class TestMarkdownToIR(unittest.TestCase):
    def test_atx_h1(self):
        doc = markdown_to_ir("# Hello")
        self.assertEqual(len(doc.blocks), 1)
        b = doc.blocks[0]
        self.assertIsInstance(b, Heading)
        self.assertEqual(b.level, 1)
        self.assertEqual(b.text, "Hello")

    def test_atx_h3(self):
        doc = markdown_to_ir("### Deep")
        b = doc.blocks[0]
        self.assertIsInstance(b, Heading)
        self.assertEqual(b.level, 3)

    def test_setext_h1(self):
        doc = markdown_to_ir("Title\n=====")
        self.assertIsInstance(doc.blocks[0], Heading)
        self.assertEqual(doc.blocks[0].level, 1)

    def test_setext_h2(self):
        doc = markdown_to_ir("Subtitle\n--------")
        self.assertIsInstance(doc.blocks[0], Heading)
        self.assertEqual(doc.blocks[0].level, 2)

    def test_paragraph(self):
        doc = markdown_to_ir("Just some text.")
        self.assertEqual(len(doc.blocks), 1)
        self.assertIsInstance(doc.blocks[0], Paragraph)
        self.assertEqual(doc.blocks[0].text, "Just some text.")

    def test_multiline_paragraph_joined(self):
        doc = markdown_to_ir("Line one\nLine two")
        self.assertEqual(len(doc.blocks), 1)
        self.assertIn("Line one", doc.blocks[0].text)
        self.assertIn("Line two", doc.blocks[0].text)

    def test_two_paragraphs(self):
        doc = markdown_to_ir("First\n\nSecond")
        self.assertEqual(len(doc.blocks), 2)

    def test_table(self):
        md = "| Col1 | Col2 |\n|------|------|\n| a | b |"
        doc = markdown_to_ir(md)
        self.assertEqual(len(doc.blocks), 1)
        b = doc.blocks[0]
        self.assertIsInstance(b, Table)
        self.assertEqual(b.headers, ["Col1", "Col2"])
        self.assertEqual(b.rows, [["a", "b"]])

    def test_table_with_aligned_separator(self):
        md = "| A | B |\n| :--- | ---: |\n| 1 | 2 |"
        doc = markdown_to_ir(md)
        self.assertIsInstance(doc.blocks[0], Table)
        self.assertEqual(doc.blocks[0].headers, ["A", "B"])

    def test_mixed_blocks(self):
        md = "# Heading\n\nParagraph.\n\n## Sub\n\nMore."
        doc = markdown_to_ir(md)
        types = [type(b).__name__ for b in doc.blocks]
        self.assertEqual(types, ["Heading", "Paragraph", "Heading", "Paragraph"])


# ---------------------------------------------------------------------------
# IR → XHTML
# ---------------------------------------------------------------------------


class TestIRToXHTML(unittest.TestCase):
    def test_heading(self):
        from confetti.document import Document
        doc = Document(blocks=[Heading(level=1, text="Hi")])
        self.assertEqual(ir_to_xhtml(doc), "<h1>Hi</h1>")

    def test_paragraph(self):
        from confetti.document import Document
        doc = Document(blocks=[Paragraph(text="Hello")])
        self.assertEqual(ir_to_xhtml(doc), "<p>Hello</p>")

    def test_paragraph_escaping(self):
        from confetti.document import Document
        doc = Document(blocks=[Paragraph(text="a < b & c > d")])
        xhtml = ir_to_xhtml(doc)
        self.assertIn("&lt;", xhtml)
        self.assertIn("&amp;", xhtml)
        self.assertIn("&gt;", xhtml)

    def test_table(self):
        from confetti.document import Document
        doc = Document(blocks=[Table(headers=["A", "B"], rows=[["1", "2"]])])
        xhtml = ir_to_xhtml(doc)
        self.assertIn("<table>", xhtml)
        self.assertIn("<th>A</th>", xhtml)
        self.assertIn("<th>B</th>", xhtml)
        self.assertIn("<td>1</td>", xhtml)
        self.assertIn("<td>2</td>", xhtml)
        self.assertIn("</table>", xhtml)


# ---------------------------------------------------------------------------
# Markdown → XHTML (full pipeline)
# ---------------------------------------------------------------------------


class TestMarkdownToXHTML(unittest.TestCase):
    def test_heading(self):
        self.assertIn("<h1>Hello</h1>", markdown_to_xhtml("# Hello"))

    def test_h2(self):
        self.assertIn("<h2>Section</h2>", markdown_to_xhtml("## Section"))

    def test_paragraph(self):
        self.assertIn("<p>Text here.</p>", markdown_to_xhtml("Text here."))

    def test_table(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        xhtml = markdown_to_xhtml(md)
        self.assertIn("<table>", xhtml)
        self.assertIn("<th>A</th>", xhtml)
        self.assertIn("<td>1</td>", xhtml)

    def test_html_escaping_in_output(self):
        xhtml = markdown_to_xhtml("a < b")
        self.assertIn("<p>", xhtml)
        self.assertIn("&lt;", xhtml)


# ---------------------------------------------------------------------------
# XHTML → Markdown → IR → XHTML round-trip
# ---------------------------------------------------------------------------


class TestRoundTrip(unittest.TestCase):
    def _roundtrip(self, xhtml: str) -> str:
        md = xhtml_to_markdown(xhtml)
        ir = markdown_to_ir(md)
        return ir_to_xhtml(ir)

    def test_strong_roundtrip(self):
        xhtml = "<p>Hello <strong>bold</strong> world</p>"
        self.assertIn("<strong>bold</strong>", self._roundtrip(xhtml))

    def test_emphasis_roundtrip(self):
        xhtml = "<p>Hello <em>italic</em> world</p>"
        self.assertIn("<em>italic</em>", self._roundtrip(xhtml))

    def test_strikethrough_roundtrip(self):
        xhtml = "<p><s>removed</s></p>"
        self.assertIn("<s>removed</s>", self._roundtrip(xhtml))

    def test_code_roundtrip(self):
        xhtml = "<p>Call <code>foo()</code></p>"
        self.assertIn("<code>foo()</code>", self._roundtrip(xhtml))

    def test_link_roundtrip(self):
        xhtml = '<p>See <a href="https://example.com">link</a></p>'
        result = self._roundtrip(xhtml)
        self.assertIn('href="https://example.com"', result)
        self.assertIn(">link<", result)

    def test_heading_preserved(self):
        self.assertIn("<h1>My Heading</h1>", self._roundtrip("<h1>My Heading</h1>"))

    def test_paragraph_preserved(self):
        self.assertIn("<p>Hello world</p>", self._roundtrip("<p>Hello world</p>"))

    def test_table_structure_preserved(self):
        xhtml = """
        <table>
          <tr><th>Name</th><th>Score</th></tr>
          <tr><td>Alice</td><td>95</td></tr>
          <tr><td>Bob</td><td>87</td></tr>
        </table>
        """
        result = self._roundtrip(xhtml)
        self.assertIn("<th>Name</th>", result)
        self.assertIn("<th>Score</th>", result)
        self.assertIn("<td>Alice</td>", result)
        self.assertIn("<td>95</td>", result)

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
        self.assertIn("# Title", md)
        self.assertIn("## Section", md)
        self.assertIn("| A | B |", md)

        result = self._roundtrip(xhtml)
        self.assertIn("<h1>", result)
        self.assertIn("<h2>", result)
        self.assertIn("<table>", result)

    def test_macro_preserved_in_roundtrip(self):
        xhtml = """
        <p>Keep</p>
        <ac:structured-macro ac:name="code">
          <ac:plain-text-body><![CDATA[secret_code_here]]></ac:plain-text-body>
        </ac:structured-macro>
        <p>Me</p>
        """
        result = self._roundtrip(xhtml)
        self.assertIn("Keep", result)
        self.assertIn("Me", result)
        self.assertIn("ac:structured-macro", result)

    def test_block_count_preserved(self):
        xhtml = "<h1>A</h1><p>B</p><h2>C</h2>"
        ir_original = xhtml_to_ir(xhtml)
        md = ir_to_markdown(ir_original)
        ir_roundtrip = markdown_to_ir(md)
        self.assertEqual(len(ir_original.blocks), len(ir_roundtrip.blocks))

    def test_escaped_asterisk_not_bullet(self):
        md = r"\* Without the backslash, this would be a bullet in an unordered list."
        xhtml = ir_to_xhtml(markdown_to_ir(md))
        self.assertIn("* Without", xhtml)
        self.assertNotIn("<ul>", xhtml)
        self.assertNotIn("<li>", xhtml)

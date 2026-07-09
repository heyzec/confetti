"""Round-trip and reverse-direction tests: Markdown → XHTML and XHTML → MD → XHTML."""

import unittest

from confetti import xhtml_to_markdown
from confetti.convert import parse_markdown
from confetti.markdown.render import render_markdown
from confetti.xhtml.parse import parse_xhtml
from confetti.xhtml.render import render_xhtml

# ---------------------------------------------------------------------------
# XHTML → Markdown → IR → XHTML round-trip
# ---------------------------------------------------------------------------


class TestRoundTrip(unittest.TestCase):
    def _roundtrip(self, xhtml: str) -> str:
        md = xhtml_to_markdown(xhtml)
        ir = parse_markdown(md)
        return render_xhtml(ir)

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
        self.assertIn("<th>Name<br /></th>", result)
        self.assertIn("<th>Score<br /></th>", result)
        self.assertIn("<td>Alice<br /></td>", result)
        self.assertIn("<td>95<br /></td>", result)

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
        self.assertIn("| A", md)
        self.assertIn("| B", md)

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
        ir_original = parse_xhtml(xhtml)
        md = render_markdown(ir_original)
        ir_roundtrip = parse_markdown(md)
        self.assertEqual(len(ir_original.blocks), len(ir_roundtrip.blocks))

    def test_escaped_asterisk_not_bullet(self):
        md = r"\* Without the backslash, this would be a bullet in an unordered list."
        xhtml = render_xhtml(parse_markdown(md))
        self.assertIn("* Without", xhtml)
        self.assertNotIn("<ul>", xhtml)
        self.assertNotIn("<li>", xhtml)

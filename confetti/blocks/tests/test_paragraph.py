import unittest

from confetti.blocks import Link, Paragraph, StyledText, Text
from confetti.convert import (
    markdown_to_xhtml,
    parse_markdown,
    parse_xhtml,
    xhtml_to_markdown,
)
from confetti.document import Document
from confetti.xhtml.render import render_xhtml


class TestParagraphMarkdown(unittest.TestCase):
    def test_parse_simple(self):
        md = "Hello world"
        doc = parse_markdown(md)
        self.assertEqual(len(doc.blocks), 1)
        actual = doc.blocks[0]
        expected = Paragraph(body=[Text(text="Hello world")])
        self.assertEqual(actual, expected)

    # We now return two separate Text blocks
    # def test_parse_multiline_joined(self):
    #     md = "Line one\nLine two"
    #     doc = parse_markdown(md)
    #     self.assertEqual(len(doc.blocks), 1)
    #     actual = doc.blocks[0]
    #     expected = Paragraph(body=[Text(text="Line one Line two")])
    #     self.assertEqual(actual, expected)

    def test_parse_two_paragraphs(self):
        md = "Line one\n\nLine two"
        doc = parse_markdown(md)
        self.assertEqual(len(doc.blocks), 2)
        actual1 = doc.blocks[0]
        actual2 = doc.blocks[1]
        expected1 = Paragraph(body=[Text(text="Line one")])
        expected2 = Paragraph(body=[Text(text="Line two")])
        self.assertEqual(actual1, expected1)
        self.assertEqual(actual2, expected2)


class TestParagraphXHTML(unittest.TestCase):
    def test_parse_simple(self):
        xhtml = "<p>Hello world</p>"
        doc = parse_xhtml(xhtml)
        self.assertEqual(len(doc.blocks), 1)
        actual = doc.blocks[0]
        expected = Paragraph(body=[Text(text="Hello world")])
        self.assertEqual(actual, expected)

    def test_parse_with_bold(self):
        xhtml = "<p>Hello <strong>bold</strong> world</p>"
        doc = parse_xhtml(xhtml)
        self.assertEqual(len(doc.blocks), 1)
        actual = doc.blocks[0]
        expected = Paragraph(
            body=[
                Text(text="Hello "),
                StyledText(kind="bold", body=[Text(text="bold")]),
                Text(text=" world"),
            ]
        )
        self.assertEqual(actual, expected)

    def test_parse_with_link(self):
        xhtml = '<p>See <a href="https://example.com">link</a></p>'
        doc = parse_xhtml(xhtml)
        self.assertEqual(len(doc.blocks), 1)
        actual = doc.blocks[0]
        expected = Paragraph(
            body=[
                Text(text="See "),
                Link(url="https://example.com", display_text=[Text(text="link")]),
            ]
        )
        self.assertEqual(actual, expected)

    def test_render_escaping(self):
        doc = Document(blocks=[Paragraph(body=[Text(text="a < b & c > d")])])
        xhtml = render_xhtml(doc)
        self.assertIn("&lt;", xhtml)
        self.assertIn("&amp;", xhtml)
        self.assertIn("&gt;", xhtml)


class TestParagraphEquivalence(unittest.TestCase):
    """
    Tests conversion both from Markdown to XHTML and vice versa.

    Note: Equivalance implies round-trip.
    """

    def _check_equivalence(self, md: str, xhtml: str):
        with self.subTest(i="xhtml_to_markdown"):
            self.assertEqual(md, xhtml_to_markdown(xhtml))
        with self.subTest(i="markdown_to_xhtml"):
            self.assertEqual(xhtml, markdown_to_xhtml(md))

    def test_simple(self):
        self._check_equivalence("Hello world", "<p>Hello world</p>")

    def test_bold(self):
        self._check_equivalence(
            "Hello **bold** world",
            "<p>Hello <strong>bold</strong> world</p>",
        )

    def test_italic(self):
        self._check_equivalence(
            "Hello *italic* world",
            "<p>Hello <em>italic</em> world</p>",
        )

    def test_strikethrough(self):
        self._check_equivalence(
            "Old: ~~removed~~ text",
            "<p>Old: <s>removed</s> text</p>",
        )

    def test_code(self):
        self._check_equivalence(
            "Call `foo()` here",
            "<p>Call <code>foo()</code> here</p>",
        )

    def test_link(self):
        self._check_equivalence(
            "See [link](https://example.com) here",
            '<p>See <a href="https://example.com">link</a> here</p>',
        )

    def test_bold_link(self):
        self._check_equivalence(
            "I love supporting the **[EFF](https://eff.org)**.",
            (
                '<p>I love supporting the <strong><a href="https://eff.org">EFF</a></strong>.</p>'
            ),
        )

    def test_italic_link(self):
        self._check_equivalence(
            "This is the *[Markdown Guide](https://www.markdownguide.org)*.",
            '<p>This is the <em><a href="https://www.markdownguide.org">Markdown Guide</a></em>.</p>',
        )

    def test_code_link(self):
        self._check_equivalence(
            "See the section on [`code`](##code).",
            '<p>See the section on <a href="##code"><code>code</code></a>.</p>',
        )

    def test_escape_underscore(self):
        self._check_equivalence("foo\\_bar", "<p>foo_bar</p>")

    def test_escape_backslash(self):
        self._check_equivalence("C:\\\\path\\\\file", "<p>C:\\path\\file</p>")

    def test_escape_underscore_in_url(self):
        # Check that underscores in URLs are not escaped, since they are valid in URLs.
        self._check_equivalence(
            "[label](https://example.com/foo_bar)",
            '<p><a href="https://example.com/foo_bar">label</a></p>',
        )

    def test_date(self):
        self._check_equivalence(
            "📅 2026-04-28",
            '<p><time datetime="2026-04-28" /></p>',
        )


class TestParagraphConvert(unittest.TestCase):
    def test_multiple_paragraphs_separated(self):
        result = xhtml_to_markdown("<p>First</p><p>Second</p>")
        self.assertIn("First", result)
        self.assertIn("Second", result)
        self.assertLess(result.index("First"), result.index("Second"))

    def test_whitespace_normalized(self):
        self.assertEqual(xhtml_to_markdown("<p>  Hello   world  </p>"), "Hello world")

    def test_inline_macro_preserved(self):
        xhtml = (
            "<p>Hello "
            '<ac:structured-macro ac:name="status">'
            '<ac:parameter ac:name="title">P1</ac:parameter>'
            "</ac:structured-macro>"
            " world</p>"
        )
        result = xhtml_to_markdown(xhtml)
        self.assertIn("Hello", result)
        self.assertIn("world", result)
        self.assertIn("ac:structured-macro", result)

    def test_inline_comment_marker_skipped(self):
        xhtml = (
            "<p>Text "
            '<ac:inline-comment-marker ac:ref="abc">annotated</ac:inline-comment-marker>'
            " more</p>"
        )
        result = xhtml_to_markdown(xhtml)
        self.assertIn("Text", result)
        self.assertIn("more", result)

    def test_nbsp_entity(self):
        result = xhtml_to_markdown("<p>Hello&nbsp;world</p>")
        self.assertIn("Hello", result)
        self.assertIn("world", result)

    def test_bold_underscore(self):
        self.assertEqual(
            markdown_to_xhtml("I just love __bold text__."),
            "<p>I just love <strong>bold text</strong>.</p>",
        )

    def test_italic_underscore(self):
        self.assertEqual(
            markdown_to_xhtml("Italicized text is the _cat's meow_."),
            "<p>Italicized text is the <em>cat's meow</em>.</p>",
        )

    def test_bold_italic_underscore(self):
        self.assertEqual(
            markdown_to_xhtml("This is ___really important___."),
            "<p>This is <em><strong>really important</strong></em>.</p>",
        )


class TestParagraphRoundtrip(unittest.TestCase):
    def test_nested_style(self):
        expected = "<p><em><strong>really important</strong></em></p>"
        intermediate = xhtml_to_markdown(expected)
        actual = markdown_to_xhtml(intermediate)
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()

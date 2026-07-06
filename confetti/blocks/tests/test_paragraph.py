import unittest

from confetti.blocks import Paragraph
from confetti.convert import (
    markdown_to_xhtml,
    parse_markdown,
    parse_xhtml,
    xhtml_to_markdown,
)


class TestParagraphMarkdown(unittest.TestCase):
    def test_parse_simple(self):
        md = "Hello world"
        doc = parse_markdown(md)
        self.assertEqual(len(doc.blocks), 1)
        actual = doc.blocks[0]
        expected = Paragraph(text="Hello world")
        self.assertEqual(actual, expected)

    def test_parse_multiline_joined(self):
        md = "Line one\nLine two"
        doc = parse_markdown(md)
        self.assertEqual(len(doc.blocks), 1)
        actual = doc.blocks[0]
        expected = Paragraph(text="Line one Line two")
        self.assertEqual(actual, expected)

    def test_parse_two_paragraphs(self):
        md = "Line one\n\nLine two"
        doc = parse_markdown(md)
        self.assertEqual(len(doc.blocks), 2)
        actual1 = doc.blocks[0]
        actual2 = doc.blocks[1]
        expected1 = Paragraph(text="Line one")
        expected2 = Paragraph(text="Line two")
        self.assertEqual(actual1, expected1)
        self.assertEqual(actual2, expected2)


class TestParagraphXHTML(unittest.TestCase):
    def test_parse_simple(self):
        xhtml = "<p>Hello world</p>"
        doc = parse_xhtml(xhtml)
        self.assertEqual(len(doc.blocks), 1)
        actual = doc.blocks[0]
        expected = Paragraph(text="Hello world")
        self.assertEqual(actual, expected)

    def test_parse_with_bold(self):
        xhtml = "<p>Hello <strong>bold</strong> world</p>"
        doc = parse_xhtml(xhtml)
        self.assertEqual(len(doc.blocks), 1)
        actual = doc.blocks[0]
        expected = Paragraph(text="Hello **bold** world")
        self.assertEqual(actual, expected)

    def test_parse_with_link(self):
        xhtml = '<p>See <a href="https://example.com">link</a></p>'
        doc = parse_xhtml(xhtml)
        self.assertEqual(len(doc.blocks), 1)
        actual = doc.blocks[0]
        expected = Paragraph(text="See [link](https://example.com)")
        self.assertEqual(actual, expected)


class TestParagraphConvert(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(xhtml_to_markdown("<p>Hello world</p>"), "Hello world")

    def test_with_strong(self):
        self.assertEqual(
            xhtml_to_markdown("<p>Hello <strong>bold</strong> world</p>"),
            "Hello **bold** world",
        )

    def test_with_emphasis(self):
        self.assertEqual(
            xhtml_to_markdown("<p>Hello <em>italic</em> world</p>"),
            "Hello *italic* world",
        )

    def test_with_anchor(self):
        self.assertEqual(
            xhtml_to_markdown('<p>See <a href="https://example.com">link</a> here</p>'),
            "See [link](https://example.com) here",
        )

    def test_with_strikethrough(self):
        self.assertEqual(
            xhtml_to_markdown("<p>Old: <s>removed</s> text</p>"),
            "Old: ~~removed~~ text",
        )

    def test_with_code(self):
        self.assertEqual(
            xhtml_to_markdown("<p>Call <code>foo()</code> here</p>"),
            "Call `foo()` here",
        )

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

    def test_time_to_emoji(self):
        self.assertEqual(
            xhtml_to_markdown('<p><time datetime="2026-04-28" /></p>'),
            "📅 2026-04-28",
        )

    def test_emoji_to_time(self):
        self.assertEqual(
            markdown_to_xhtml("📅 2026-04-28"),
            '<p><time datetime="2026-04-28" /></p>',
        )

    def test_bold_link(self):
        self.assertEqual(
            xhtml_to_markdown(
                '<p>I love supporting the <strong><a href="https://eff.org">EFF</a></strong>.</p>'
            ),
            "I love supporting the **[EFF](https://eff.org)**.",
        )

    def test_italic_link(self):
        self.assertEqual(
            xhtml_to_markdown(
                '<p>This is the <em><a href="https://www.markdownguide.org">Markdown Guide</a></em>.</p>'
            ),
            "This is the *[Markdown Guide](https://www.markdownguide.org)*.",
        )

    def test_code_link(self):
        self.assertEqual(
            xhtml_to_markdown(
                '<p>See the section on <a href="##code"><code>code</code></a>.</p>'
            ),
            "See the section on [`code`](##code).",
        )

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
    def test_paragraph(self):
        self.assertEqual(
            xhtml_to_markdown("<p>I really like using Markdown.</p>"),
            "I really like using Markdown.",
        )
        self.assertEqual(
            markdown_to_xhtml("I really like using Markdown."),
            "<p>I really like using Markdown.</p>",
        )

    def test_bold(self):
        self.assertEqual(
            xhtml_to_markdown("<p>I just love <strong>bold text</strong>.</p>"),
            "I just love **bold text**.",
        )
        self.assertEqual(
            markdown_to_xhtml("I just love **bold text**."),
            "<p>I just love <strong>bold text</strong>.</p>",
        )

    def test_italic(self):
        self.assertEqual(
            xhtml_to_markdown("<p>Italicized text is the <em>cat's meow</em>.</p>"),
            "Italicized text is the *cat's meow*.",
        )
        self.assertEqual(
            markdown_to_xhtml("Italicized text is the *cat's meow*."),
            "<p>Italicized text is the <em>cat's meow</em>.</p>",
        )

    def test_strikethrough(self):
        self.assertEqual(
            xhtml_to_markdown(
                "<p><s>The world is flat.</s> We now know that the world is round.</p>"
            ),
            "~~The world is flat.~~ We now know that the world is round.",
        )
        self.assertEqual(
            markdown_to_xhtml(
                "~~The world is flat.~~ We now know that the world is round."
            ),
            "<p><s>The world is flat.</s> We now know that the world is round.</p>",
        )

    def test_inline_code(self):
        self.assertEqual(
            xhtml_to_markdown("<p>At the command prompt, type <code>nano</code>.</p>"),
            "At the command prompt, type `nano`.",
        )
        self.assertEqual(
            markdown_to_xhtml("At the command prompt, type `nano`."),
            "<p>At the command prompt, type <code>nano</code>.</p>",
        )

    def test_link(self):
        self.assertEqual(
            xhtml_to_markdown(
                '<p>My favorite search engine is <a href="https://duckduckgo.com">Duck Duck Go</a>.</p>'
            ),
            "My favorite search engine is [Duck Duck Go](https://duckduckgo.com).",
        )
        self.assertEqual(
            markdown_to_xhtml(
                "My favorite search engine is [Duck Duck Go](https://duckduckgo.com)."
            ),
            '<p>My favorite search engine is <a href="https://duckduckgo.com">Duck Duck Go</a>.</p>',
        )

    def test_time_roundtrip(self):
        md = xhtml_to_markdown('<p>Due: <time datetime="2025-12-31" /></p>')
        self.assertEqual(md, "Due: 📅 2025-12-31")
        self.assertEqual(
            markdown_to_xhtml(md),
            '<p>Due: <time datetime="2025-12-31" /></p>',
        )


if __name__ == "__main__":
    unittest.main()

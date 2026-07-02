import unittest

from confetti import xhtml_to_markdown
from confetti.document import Document


# Tests corresponding to "Paragraphs", "Emphasis", "Links", "Strikethrough",
# and "Code" sections of example.md
class TestInlineExamples(unittest.TestCase):
    # --- Paragraphs ---

    def test_paragraph(self):
        self.assertEqual(
            xhtml_to_markdown("<p>I really like using Markdown.</p>"),
            "I really like using Markdown.",
        )
        self.assertEqual(
            Document.from_markdown("I really like using Markdown.").to_xhtml(),
            "<p>I really like using Markdown.</p>",
        )

    # --- Bold ---

    def test_bold(self):
        self.assertEqual(
            xhtml_to_markdown("<p>I just love <strong>bold text</strong>.</p>"),
            "I just love **bold text**.",
        )
        self.assertEqual(
            Document.from_markdown("I just love **bold text**.").to_xhtml(),
            "<p>I just love <strong>bold text</strong>.</p>",
        )

    # --- Italic ---

    def test_italic(self):
        self.assertEqual(
            xhtml_to_markdown("<p>Italicized text is the <em>cat's meow</em>.</p>"),
            "Italicized text is the *cat's meow*.",
        )
        self.assertEqual(
            Document.from_markdown("Italicized text is the *cat's meow*.").to_xhtml(),
            "<p>Italicized text is the <em>cat's meow</em>.</p>",
        )

    # --- Strikethrough ---

    def test_strikethrough(self):
        self.assertEqual(
            xhtml_to_markdown("<p><s>The world is flat.</s> We now know that the world is round.</p>"),
            "~~The world is flat.~~ We now know that the world is round.",
        )
        self.assertEqual(
            Document.from_markdown("~~The world is flat.~~ We now know that the world is round.").to_xhtml(),
            "<p><s>The world is flat.</s> We now know that the world is round.</p>",
        )

    # --- Inline code ---

    def test_inline_code(self):
        self.assertEqual(
            xhtml_to_markdown("<p>At the command prompt, type <code>nano</code>.</p>"),
            "At the command prompt, type `nano`.",
        )
        self.assertEqual(
            Document.from_markdown("At the command prompt, type `nano`.").to_xhtml(),
            "<p>At the command prompt, type <code>nano</code>.</p>",
        )

    # --- Links ---

    def test_link(self):
        self.assertEqual(
            xhtml_to_markdown('<p>My favorite search engine is <a href="https://duckduckgo.com">Duck Duck Go</a>.</p>'),
            "My favorite search engine is [Duck Duck Go](https://duckduckgo.com).",
        )
        self.assertEqual(
            Document.from_markdown("My favorite search engine is [Duck Duck Go](https://duckduckgo.com).").to_xhtml(),
            '<p>My favorite search engine is <a href="https://duckduckgo.com">Duck Duck Go</a>.</p>',
        )

    def test_bold_link(self):
        # from_xhtml only: **[EFF](https://eff.org)**
        self.assertEqual(
            xhtml_to_markdown('<p>I love supporting the <strong><a href="https://eff.org">EFF</a></strong>.</p>'),
            "I love supporting the **[EFF](https://eff.org)**.",
        )

    def test_italic_link(self):
        # from_xhtml only: *[Markdown Guide](url)*
        self.assertEqual(
            xhtml_to_markdown('<p>This is the <em><a href="https://www.markdownguide.org">Markdown Guide</a></em>.</p>'),
            "This is the *[Markdown Guide](https://www.markdownguide.org)*.",
        )

    def test_code_link(self):
        # from_xhtml only: [`code`](url)
        self.assertEqual(
            xhtml_to_markdown('<p>See the section on <a href="##code"><code>code</code></a>.</p>'),
            "See the section on [`code`](##code).",
        )


class TestParagraphs(unittest.TestCase):
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

    # --- Dates ---

    def test_time_to_emoji(self):
        self.assertEqual(
            xhtml_to_markdown('<p><time datetime="2026-04-28" /></p>'),
            "📅 2026-04-28",
        )

    def test_emoji_to_time(self):
        self.assertEqual(
            Document.from_markdown("📅 2026-04-28").to_xhtml(),
            '<p><time datetime="2026-04-28" /></p>',
        )

    def test_time_roundtrip(self):
        md = xhtml_to_markdown('<p>Due: <time datetime="2025-12-31" /></p>')
        self.assertEqual(md, "Due: 📅 2025-12-31")
        self.assertEqual(
            Document.from_markdown(md).to_xhtml(),
            '<p>Due: <time datetime="2025-12-31" /></p>',
        )


if __name__ == "__main__":
    unittest.main()

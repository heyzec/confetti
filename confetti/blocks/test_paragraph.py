import unittest

from confetti import xhtml_to_markdown


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


if __name__ == "__main__":
    unittest.main()

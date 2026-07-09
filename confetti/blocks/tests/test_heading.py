import unittest

from confetti.blocks import Heading
from confetti.blocks.text import Text
from confetti.convert import (
    parse_markdown,
    parse_xhtml,
    render_xhtml,
    xhtml_to_markdown,
)
from confetti.markdown.render import render_heading as md_render_heading
from confetti.xhtml.render import render_heading as xhtml_render_heading


class TestHeadingMarkdown(unittest.TestCase):
    def test_parse_atx(self):
        for level in range(1, 7):
            md = "#" * level + " Hello World"
            doc = parse_markdown(md)
            actual = doc.blocks[0]
            expected = Heading(level=level, body=[Text(text="Hello World")])
            self.assertEqual(expected, actual)

    def test_render_atx(self):
        for level in range(1, 7):
            block = Heading(level=level, body=[Text(text="Hello World")])
            actual = md_render_heading(block)
            expected = "#" * level + " Hello World"
            self.assertEqual(expected, actual)

    def test_parse_setext_h1(self):
        doc = parse_markdown("Title\n=====")
        actual = doc.blocks[0]
        expected = Heading(level=1, body=[Text(text="Title")])
        self.assertEqual(expected, actual)

    def test_parse_setext_h2(self):
        doc = parse_markdown("Subtitle\n--------")
        actual = doc.blocks[0]
        expected = Heading(level=2, body=[Text(text="Subtitle")])
        self.assertEqual(expected, actual)


class TestHeadingXHTML(unittest.TestCase):
    def test_parse(self):
        for level in range(1, 7):
            xhtml = f"<h{level}>Hello World</h{level}>"
            doc = parse_xhtml(xhtml)
            actual = doc.blocks[0]
            expected = Heading(level=level, body=[Text(text="Hello World")])
            self.assertEqual(expected, actual)

    def test_render(self):
        for level in range(1, 7):
            block = Heading(level=level, body=[Text(text="Hello World")])
            actual = xhtml_render_heading(block)
            expected = f"<h{level}>Hello World</h{level}>"
            self.assertEqual(expected, actual)


class TestHeadingConvert(unittest.TestCase):
    def test_heading_with_inline_elements(self):
        xhtml = '<h2>API <ac:inline-comment-marker ac:ref="x">Design</ac:inline-comment-marker></h2>'
        result = xhtml_to_markdown(xhtml)
        self.assertTrue(result.startswith("## API"))
        self.assertIn("ac:inline-comment-marker", result)
        self.assertIn("Design", result)

    def test_setext_h1(self):
        doc = parse_markdown("Showcase headings 2\n================")
        self.assertEqual(render_xhtml(doc), "<h1>Showcase headings 2</h1>")

    def test_setext_h2(self):
        doc = parse_markdown("Headling level 2\n----------------")
        self.assertEqual(render_xhtml(doc), "<h2>Headling level 2</h2>")


if __name__ == "__main__":
    unittest.main()

import unittest

from confetti.blocks import Heading
from confetti.convert import (
    markdown_to_xhtml,
    parse_markdown,
    parse_xhtml,
    render_xhtml,
    xhtml_to_markdown,
)


# Tests corresponding to the "Headings" section of example.md
class TestHeadingsExamples(unittest.TestCase):
    def test_atx_h1(self):
        self.assertEqual(xhtml_to_markdown("<h1>Heading 1</h1>"), "# Heading 1")
        self.assertEqual(markdown_to_xhtml("# Heading 1"), "<h1>Heading 1</h1>")

    def test_atx_h2(self):
        self.assertEqual(xhtml_to_markdown("<h2>Heading 2</h2>"), "## Heading 2")
        self.assertEqual(markdown_to_xhtml("## Heading 2"), "<h2>Heading 2</h2>")

    def test_atx_h3(self):
        self.assertEqual(xhtml_to_markdown("<h3>Heading 3</h3>"), "### Heading 3")
        self.assertEqual(markdown_to_xhtml("### Heading 3"), "<h3>Heading 3</h3>")

    def test_atx_h4(self):
        self.assertEqual(xhtml_to_markdown("<h4>Heading 4</h4>"), "#### Heading 4")
        self.assertEqual(markdown_to_xhtml("#### Heading 4"), "<h4>Heading 4</h4>")

    def test_atx_h5(self):
        self.assertEqual(xhtml_to_markdown("<h5>Heading 5</h5>"), "##### Heading 5")
        self.assertEqual(markdown_to_xhtml("##### Heading 5"), "<h5>Heading 5</h5>")

    def test_atx_h6(self):
        self.assertEqual(xhtml_to_markdown("<h6>Heading 6</h6>"), "###### Heading 6")
        self.assertEqual(markdown_to_xhtml("###### Heading 6"), "<h6>Heading 6</h6>")

    def test_setext_h1(self):
        # Setext-style === parses as h1; normalises to ATX on output
        doc = parse_markdown("Showcase headings 2\n================")
        self.assertEqual(render_xhtml(doc), "<h1>Showcase headings 2</h1>")

    def test_setext_h2(self):
        # Setext-style --- parses as h2; normalises to ATX on output
        doc = parse_markdown("Headling level 2\n----------------")
        self.assertEqual(render_xhtml(doc), "<h2>Headling level 2</h2>")


class TestHeadings(unittest.TestCase):
    def test_h1(self):
        self.assertEqual(xhtml_to_markdown("<h1>Hello World</h1>"), "# Hello World")

    def test_h2(self):
        self.assertEqual(xhtml_to_markdown("<h2>Sub Heading</h2>"), "## Sub Heading")

    def test_h3(self):
        self.assertEqual(xhtml_to_markdown("<h3>Deep</h3>"), "### Deep")

    def test_h6(self):
        self.assertEqual(xhtml_to_markdown("<h6>Deepest</h6>"), "###### Deepest")

    def test_heading_ir_structure(self):
        doc = parse_xhtml("<h2>Title</h2>")
        self.assertEqual(len(doc.blocks), 1)
        b = doc.blocks[0]
        assert isinstance(b, Heading)
        self.assertEqual(b.level, 2)
        self.assertEqual(b.text, "Title")

    def test_heading_with_inline_elements(self):
        # ac:inline-comment-marker is preserved as raw inline XML for round-trip fidelity
        xhtml = '<h2>API <ac:inline-comment-marker ac:ref="x">Design</ac:inline-comment-marker></h2>'
        result = xhtml_to_markdown(xhtml)
        self.assertTrue(result.startswith("## API"))
        self.assertIn("ac:inline-comment-marker", result)
        self.assertIn("Design", result)


if __name__ == "__main__":
    unittest.main()

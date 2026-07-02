import unittest

from confetti import xhtml_to_ir, xhtml_to_markdown
from confetti.blocks import Heading
from confetti.document import Document


# Tests corresponding to the "Headings" section of example.md
class TestHeadingsExamples(unittest.TestCase):
    def test_atx_h1(self):
        self.assertEqual(xhtml_to_markdown("<h1>Heading 1</h1>"), "# Heading 1")
        self.assertEqual(Document.from_markdown("# Heading 1").to_xhtml(), "<h1>Heading 1</h1>")

    def test_atx_h2(self):
        self.assertEqual(xhtml_to_markdown("<h2>Heading 2</h2>"), "## Heading 2")
        self.assertEqual(Document.from_markdown("## Heading 2").to_xhtml(), "<h2>Heading 2</h2>")

    def test_atx_h3(self):
        self.assertEqual(xhtml_to_markdown("<h3>Heading 3</h3>"), "### Heading 3")
        self.assertEqual(Document.from_markdown("### Heading 3").to_xhtml(), "<h3>Heading 3</h3>")

    def test_atx_h4(self):
        self.assertEqual(xhtml_to_markdown("<h4>Heading 4</h4>"), "#### Heading 4")
        self.assertEqual(Document.from_markdown("#### Heading 4").to_xhtml(), "<h4>Heading 4</h4>")

    def test_atx_h5(self):
        self.assertEqual(xhtml_to_markdown("<h5>Heading 5</h5>"), "##### Heading 5")
        self.assertEqual(Document.from_markdown("##### Heading 5").to_xhtml(), "<h5>Heading 5</h5>")

    def test_atx_h6(self):
        self.assertEqual(xhtml_to_markdown("<h6>Heading 6</h6>"), "###### Heading 6")
        self.assertEqual(Document.from_markdown("###### Heading 6").to_xhtml(), "<h6>Heading 6</h6>")

    def test_setext_h1(self):
        # Setext-style === parses as h1; normalises to ATX on output
        doc = Document.from_markdown("Showcase headings 2\n================")
        self.assertEqual(doc.to_xhtml(), "<h1>Showcase headings 2</h1>")

    def test_setext_h2(self):
        # Setext-style --- parses as h2; normalises to ATX on output
        doc = Document.from_markdown("Headling level 2\n----------------")
        self.assertEqual(doc.to_xhtml(), "<h2>Headling level 2</h2>")


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
        doc = xhtml_to_ir("<h2>Title</h2>")
        self.assertEqual(len(doc.blocks), 1)
        b = doc.blocks[0]
        self.assertIsInstance(b, Heading)
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

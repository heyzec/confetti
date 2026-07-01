import unittest

from confetti import xhtml_to_ir, xhtml_to_markdown
from confetti.blocks import Heading


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

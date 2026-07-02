import unittest

from confetti import xhtml_to_markdown
from confetti.blocks import List
from confetti.document import Document


class TestList(unittest.TestCase):
    def test_ul_from_xhtml(self):
        result = xhtml_to_markdown("<ul><li>Alpha</li><li>Beta</li></ul>")
        self.assertIn("- Alpha", result)
        self.assertIn("- Beta", result)

    def test_ol_from_xhtml(self):
        result = xhtml_to_markdown("<ol><li>First</li><li>Second</li></ol>")
        self.assertIn("1. First", result)
        self.assertIn("2. Second", result)

    def test_ul_from_markdown(self):
        doc = Document.from_markdown("- Alpha\n- Beta\n")
        self.assertEqual(len(doc.blocks), 1)
        self.assertIsInstance(doc.blocks[0], List)
        self.assertEqual(doc.blocks[0].tag, "ul")
        self.assertEqual(doc.blocks[0].items, ["Alpha", "Beta"])

    def test_ol_from_markdown(self):
        doc = Document.from_markdown("1. First\n2. Second\n")
        self.assertEqual(len(doc.blocks), 1)
        self.assertIsInstance(doc.blocks[0], List)
        self.assertEqual(doc.blocks[0].tag, "ol")

    def test_roundtrip_ul(self):
        xhtml = "<ul><li>Alpha</li><li>Beta</li></ul>"
        self.assertEqual(Document.from_markdown(Document.from_xhtml(xhtml).to_markdown()).to_xhtml(), xhtml)

    def test_roundtrip_ol(self):
        xhtml = "<ol><li>First</li><li>Second</li></ol>"
        self.assertEqual(Document.from_markdown(Document.from_xhtml(xhtml).to_markdown()).to_xhtml(), xhtml)

    def test_complex_list_falls_back_to_raw(self):
        from confetti.blocks import RawBlock
        xhtml = "<ul><li><p>nested</p><p>block</p></li></ul>"
        doc = Document.from_xhtml(xhtml)
        self.assertIsInstance(doc.blocks[0], RawBlock)


if __name__ == "__main__":
    unittest.main()

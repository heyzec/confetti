import unittest

from confetti import xhtml_to_markdown
from confetti.blocks import List, RawBlock
from confetti.convert import markdown_to_xhtml, parse_markdown, parse_xhtml


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
        doc = parse_markdown("- Alpha\n- Beta\n")
        self.assertEqual(len(doc.blocks), 1)
        assert isinstance(doc.blocks[0], List)
        self.assertEqual(doc.blocks[0].tag, "ul")
        self.assertEqual(doc.blocks[0].items, ["Alpha", "Beta"])

    def test_ol_from_markdown(self):
        doc = parse_markdown("1. First\n2. Second\n")
        self.assertEqual(len(doc.blocks), 1)
        assert isinstance(doc.blocks[0], List)
        self.assertEqual(doc.blocks[0].tag, "ol")

    def test_roundtrip_ul(self):
        xhtml = "<ul><li>Alpha</li><li>Beta</li></ul>"
        self.assertEqual(
            markdown_to_xhtml(xhtml_to_markdown(xhtml)),
            xhtml,
        )

    def test_roundtrip_ol(self):
        xhtml = "<ol><li>First</li><li>Second</li></ol>"
        self.assertEqual(
            markdown_to_xhtml(xhtml_to_markdown(xhtml)),
            xhtml,
        )

    def test_paragraph_not_swallowed_by_adjacent_ol(self):
        md = "Intro\n1. First\n2. Second\n"
        doc = parse_markdown(md)
        self.assertEqual(len(doc.blocks), 2)
        self.assertIsInstance(doc.blocks[1], List)

    def test_paragraph_not_swallowed_by_adjacent_ul(self):
        md = "Intro\n- Alpha\n- Beta\n"
        doc = parse_markdown(md)
        self.assertEqual(len(doc.blocks), 2)
        self.assertIsInstance(doc.blocks[1], List)

    def test_complex_list_falls_back_to_raw(self):
        xhtml = "<ul><li><p>nested</p><p>block</p></li></ul>"
        doc = parse_xhtml(xhtml)
        self.assertIsInstance(doc.blocks[0], RawBlock)


if __name__ == "__main__":
    unittest.main()

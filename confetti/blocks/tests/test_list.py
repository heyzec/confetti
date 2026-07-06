import unittest

from confetti.blocks import List, Paragraph, RawBlock
from confetti.convert import (
    markdown_to_xhtml,
    parse_markdown,
    parse_xhtml,
    xhtml_to_markdown,
)


class TestListMarkdown(unittest.TestCase):
    def test_parse_ul(self):
        md = "- Alpha\n- Beta\n"
        doc = parse_markdown(md)
        self.assertEqual(len(doc.blocks), 1)
        actual = doc.blocks[0]
        expected = List(tag="ul", items=["Alpha", "Beta"])
        self.assertEqual(actual, expected)

    def test_parse_ol(self):
        md = "1. First\n2. Second\n"
        doc = parse_markdown(md)
        self.assertEqual(len(doc.blocks), 1)
        actual = doc.blocks[0]
        expected = List(tag="ol", items=["First", "Second"])
        self.assertEqual(actual, expected)


class TestListXHTML(unittest.TestCase):
    def test_parse_ul(self):
        xhtml = "<ul><li>Alpha</li><li>Beta</li></ul>"
        doc = parse_xhtml(xhtml)
        b = doc.blocks[0]
        assert isinstance(b, List)
        self.assertEqual(b.tag, "ul")
        self.assertEqual(b.items, ["Alpha", "Beta"])

    def test_parse_ol(self):
        xhtml = "<ol><li>First</li><li>Second</li></ol>"
        doc = parse_xhtml(xhtml)
        b = doc.blocks[0]
        assert isinstance(b, List)
        self.assertEqual(b.tag, "ol")
        self.assertEqual(b.items, ["First", "Second"])


class TestListConvert(unittest.TestCase):
    def test_paragraph_not_swallowed_by_adjacent_list(self):
        md = "Intro\n1. First\n2. Second\n"
        doc = parse_markdown(md)
        self.assertEqual(len(doc.blocks), 2)
        actual1 = doc.blocks[0]
        actual2 = doc.blocks[1]
        expected1 = Paragraph(text="Intro")
        expected2 = List(tag="ol", items=["First", "Second"])
        self.assertEqual(actual1, expected1)
        self.assertEqual(actual2, expected2)

    def test_parse_xhtml_complex_list_fallback(self):
        xhtml = "<ul><li><p>nested</p><p>block</p></li></ul>"
        doc = parse_xhtml(xhtml)
        self.assertIsInstance(doc.blocks[0], RawBlock)

    def test_ul_from_xhtml(self):
        result = xhtml_to_markdown("<ul><li>Alpha</li><li>Beta</li></ul>")
        self.assertIn("- Alpha", result)
        self.assertIn("- Beta", result)

    def test_ol_from_xhtml(self):
        result = xhtml_to_markdown("<ol><li>First</li><li>Second</li></ol>")
        self.assertIn("1. First", result)
        self.assertIn("2. Second", result)


class TestListRoundtrip(unittest.TestCase):
    def test_roundtrip_ul(self):
        xhtml = "<ul><li>Alpha</li><li>Beta</li></ul>"
        self.assertEqual(markdown_to_xhtml(xhtml_to_markdown(xhtml)), xhtml)

    def test_roundtrip_ol(self):
        xhtml = "<ol><li>First</li><li>Second</li></ol>"
        self.assertEqual(markdown_to_xhtml(xhtml_to_markdown(xhtml)), xhtml)


if __name__ == "__main__":
    unittest.main()

import unittest

from confetti.blocks import Paragraph
from confetti.blocks.code import Code
from confetti.markdown.parse import parse_markdown


class TestCodeBlockMarkdown(unittest.TestCase):
    def test_parse_bare_no_lang(self):
        md = "`Hello World`"
        doc = parse_markdown(md)
        actual = doc.blocks[0]
        expected = Paragraph(body=[Code(code="Hello World")])
        self.assertEqual(actual, expected)

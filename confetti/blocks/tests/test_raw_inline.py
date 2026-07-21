import unittest

from confetti import markdown_to_xhtml, xhtml_to_markdown

from ...blocks import Paragraph
from ...blocks.raw_inline import RawInline
from ...markdown.parse import parse_markdown


class TestRawInlineMarkdown(unittest.TestCase):
    def test_parse_html_p(self):
        md = "<p>Hello world</p>"
        doc = parse_markdown(md)
        actual = doc.blocks[0]
        expected = Paragraph(body=[RawInline(xml=md)])
        self.assertEqual(actual, expected)

    def test_parse_html_with_attr(self):
        md = """<span style="display: none;">hi</span>"""
        doc = parse_markdown(md)
        actual = doc.blocks[0]
        expected = Paragraph(body=[RawInline(xml=md)])
        self.assertEqual(actual, expected)

    def test_parse_html_self_closing(self):
        md = """<meta/>"""
        doc = parse_markdown(md)
        actual = doc.blocks[0]
        expected = Paragraph(body=[RawInline(xml=md)])
        self.assertEqual(actual, expected)


class TestRawInlineRoundtrip(unittest.TestCase):
    def test_span(self):
        expected = "<p>Hello world</p>"
        intermediate = markdown_to_xhtml(expected)
        actual = xhtml_to_markdown(intermediate)
        self.assertEqual(actual, expected)

    def test_confluence_comment(self):
        expected = """<ac:inline-comment-marker xmlns:ac="http://atlassian.com/ac" ac:ref="12345678-abcd-1234-abcd-1234567890ab">This is suspicious</ac:inline-comment-marker>"""
        intermediate = markdown_to_xhtml(expected)
        actual = xhtml_to_markdown(intermediate)
        self.assertEqual(actual, expected)

    def test_confluence_status_macro(self):
        expected = """<ac:structured-macro xmlns:ac="http://atlassian.com/ac" ac:name="status" ac:schema-version="1" ac:macro-id="12345678-abcd-1234-abcd-1234567890ab"><ac:parameter ac:name="colour">Blue</ac:parameter><ac:parameter ac:name="title">My Title</ac:parameter></ac:structured-macro>"""
        intermediate = markdown_to_xhtml(expected)
        actual = xhtml_to_markdown(intermediate)
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()

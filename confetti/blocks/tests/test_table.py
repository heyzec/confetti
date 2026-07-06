from __future__ import annotations

import unittest

from confetti.blocks import Table
from confetti.convert import (
    markdown_to_xhtml,
    parse_markdown,
    parse_xhtml,
    render_xhtml,
    xhtml_to_markdown,
)


class TestTableMarkdown(unittest.TestCase):
    def test_parse_simple(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        doc = parse_markdown(md)
        actual = doc.blocks[0]
        expected = Table(headers=["A", "B"], rows=[["1", "2"]])
        self.assertEqual(actual, expected)

    def test_parse_multiple_rows(self):
        md = "| Name | Score |\n|---|---|\n| Alice | 95 |\n| Bob | 87 |"
        doc = parse_markdown(md)
        actual = doc.blocks[0]
        expected = Table(
            headers=["Name", "Score"], rows=[["Alice", "95"], ["Bob", "87"]]
        )
        self.assertEqual(actual, expected)


class TestTableXHTML(unittest.TestCase):
    def test_table_ir_structure(self):
        xhtml = "<table>" "<tr><th>A</th></tr>" "<tr><td>1</td></tr>" "</table>"
        doc = parse_xhtml(xhtml)
        actual = doc.blocks[0]
        expected = Table(headers=["A"], rows=[["1"]])
        self.assertEqual(actual, expected)

    def test_table_ir_multiple_columns(self):
        xhtml = (
            "<table>"
            "<tr><th>Name</th><th>Score</th></tr>"
            "<tr><td>Alice</td><td>95</td></tr>"
            "</table>"
        )
        doc = parse_xhtml(xhtml)
        actual = doc.blocks[0]
        expected = Table(headers=["Name", "Score"], rows=[["Alice", "95"]])
        self.assertEqual(actual, expected)


class TestTableConvert(unittest.TestCase):
    def test_basic_table_from_markdown(self):
        md = "| Syntax | Description |\n| --- | --- |\n| Header | Title |\n| Paragraph | Text |"
        xhtml = markdown_to_xhtml(md)
        self.assertIn("<table>", xhtml)
        self.assertIn("<th>Syntax</th>", xhtml)
        self.assertIn("<td>Header</td>", xhtml)

    def test_simple_th_headers(self):
        xhtml = """
        <table>
          <tr><th>Name</th><th>Value</th></tr>
          <tr><td>Alice</td><td>1</td></tr>
          <tr><td>Bob</td><td>2</td></tr>
        </table>
        """
        result = xhtml_to_markdown(xhtml)
        self.assertIn("| Name | Value |", result)
        self.assertIn("| --- | --- |", result)
        self.assertIn("| Alice | 1 |", result)
        self.assertIn("| Bob | 2 |", result)

    def test_table_with_tbody(self):
        xhtml = """
        <table>
          <tbody>
            <tr><th>A</th><th>B</th></tr>
            <tr><td>1</td><td>2</td></tr>
          </tbody>
        </table>
        """
        result = xhtml_to_markdown(xhtml)
        self.assertIn("| A | B |", result)
        self.assertIn("| 1 | 2 |", result)

    def test_table_with_colgroup(self):
        xhtml = """
        <table>
          <colgroup><col /><col /></colgroup>
          <tbody>
            <tr><th>X</th><th>Y</th></tr>
            <tr><td>a</td><td>b</td></tr>
          </tbody>
        </table>
        """
        result = xhtml_to_markdown(xhtml)
        self.assertIn("<!-- confetti:table ", result)
        self.assertIn("| X | Y |", result)
        self.assertIn("| a | b |", result)

    def test_pipe_escaped_in_cell(self):
        xhtml = """
        <table>
          <tr><th>Key</th><th>Value</th></tr>
          <tr><td>a|b</td><td>c</td></tr>
        </table>
        """
        self.assertIn("a\\|b", xhtml_to_markdown(xhtml))

    def test_uneven_rows_padded(self):
        xhtml = """
        <table>
          <tr><th>A</th><th>B</th><th>C</th></tr>
          <tr><td>1</td><td>2</td></tr>
        </table>
        """
        result = xhtml_to_markdown(xhtml)
        lines = [ln for ln in result.splitlines() if ln.strip()]
        self.assertGreaterEqual(lines[2].count("|"), 4)

    def test_cell_with_div_wrapper(self):
        xhtml = """
        <table>
          <tr><th>Col</th></tr>
          <tr><td><div class="content-wrapper"><p>cell text</p></div></td></tr>
        </table>
        """
        self.assertIn("cell text", xhtml_to_markdown(xhtml))

    def test_colspan_produces_span_marker(self):
        xhtml = '<table><tr><th colspan="2">AB</th><th>C</th></tr><tr><td>D</td><td>E</td><td>F</td></tr></table>'
        result = xhtml_to_markdown(xhtml)
        self.assertIn("| AB | < | C |", result)
        self.assertIn("| D | E | F |", result)

    def test_rowspan_produces_span_marker(self):
        xhtml = '<table><tr><th>A</th><th>B</th></tr><tr><td rowspan="2">X</td><td>Y</td></tr><tr><td>Z</td></tr></table>'
        result = xhtml_to_markdown(xhtml)
        self.assertIn("| X | Y |", result)
        self.assertIn("| ^ | Z |", result)


class TestTableRoundtrip(unittest.TestCase):
    def test_colspan_roundtrip(self):
        xhtml = '<table><tr><th colspan="2">AB</th><th>C</th></tr><tr><td>D</td><td>E</td><td>F</td></tr></table>'
        self.assertEqual(
            markdown_to_xhtml(xhtml_to_markdown(xhtml)),
            render_xhtml(parse_xhtml(xhtml)),
        )

    def test_rowspan_roundtrip(self):
        xhtml = '<table><tr><th>A</th><th>B</th></tr><tr><td rowspan="2">X</td><td>Y</td></tr><tr><td>Z</td></tr></table>'
        self.assertEqual(
            markdown_to_xhtml(xhtml_to_markdown(xhtml)),
            render_xhtml(parse_xhtml(xhtml)),
        )

    def test_colspan_rowspan_combined_roundtrip(self):
        xhtml = (
            "<table>"
            '<tr><th colspan="2">AB</th><th>C</th></tr>'
            '<tr><td rowspan="2">X</td><td>Y</td><td>Y2</td></tr>'
            "<tr><td>Z</td><td>Z2</td></tr>"
            "</table>"
        )
        self.assertEqual(
            markdown_to_xhtml(xhtml_to_markdown(xhtml)),
            render_xhtml(parse_xhtml(xhtml)),
        )

    def test_literal_lt_escaped(self):
        xhtml = "<table><tr><th>Key</th></tr><tr><td>&lt;</td></tr></table>"
        md = xhtml_to_markdown(xhtml)
        self.assertNotIn("| < |", md)
        self.assertIn("\\<", md)
        self.assertEqual(
            markdown_to_xhtml(md),
            render_xhtml(parse_xhtml(xhtml)),
        )


if __name__ == "__main__":
    unittest.main()

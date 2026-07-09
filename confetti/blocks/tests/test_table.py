from __future__ import annotations

import unittest

from confetti.blocks import Merge, Table, Text
from confetti.convert import (
    markdown_to_xhtml,
    parse_markdown,
    parse_xhtml,
    render_xhtml,
    xhtml_to_markdown,
)
from confetti.document import Document


def _unpad(md: str) -> str:
    """Strip cell padding from a pipe table for easier assertions."""
    lines = []
    for line in md.splitlines():
        if "|" in line:
            line = "|".join(c.strip() for c in line.split("|"))
        lines.append(line)
    return "\n".join(lines)


class TestTableMarkdown(unittest.TestCase):
    def test_parse_simple(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        doc = parse_markdown(md)
        actual = doc.blocks[0]
        expected = Table(
            cells=[
                [[Text(text="A")], [Text(text="B")]],  # Row 1
                [[Text(text="1")], [Text(text="2")]],  # Row 2
            ]
        )
        self.assertEqual(actual, expected)

    def test_parse_multiple_rows(self):
        md = "| Name | Score |\n|---|---|\n| Alice | 95 |\n| Bob | 87 |"
        doc = parse_markdown(md)
        actual = doc.blocks[0]
        expected = Table(
            cells=[
                [[Text(text="Name")], [Text(text="Score")]],  # Row 1
                [[Text(text="Alice")], [Text(text="95")]],  # Row 2
                [[Text(text="Bob")], [Text(text="87")]],  # Row 3
            ]
        )
        self.assertEqual(actual, expected)

    def test_parse_colspan_marker(self):
        md = "| AB | < | C |\n|---|---|---|\n| D | E | F |"
        doc = parse_markdown(md)
        actual = doc.blocks[0]
        assert isinstance(actual, Table)
        self.assertEqual(actual.merges, [Merge(row=0, col=0, rowspan=1, colspan=2)])
        self.assertIsNone(actual.cells[0][1])

    def test_parse_rowspan_marker(self):
        md = "| A | B |\n|---|---|\n| X | Y |\n| ^ | Z |"
        doc = parse_markdown(md)
        actual = doc.blocks[0]
        assert isinstance(actual, Table)
        self.assertEqual(actual.merges, [Merge(row=1, col=0, rowspan=2, colspan=1)])
        self.assertIsNone(actual.cells[2][0])

    def test_parse_escaped_lt_not_a_marker(self):
        md = "| Key |\n|---|\n| \\< |"
        doc = parse_markdown(md)
        block = doc.blocks[0]
        assert isinstance(block, Table)
        actual = block.cells[1][0]
        expected = [Text(text="<")]
        self.assertEqual(actual, expected)

    def test_parse_escaped_caret_not_a_marker(self):
        md = "| Key |\n|---|\n| \\^ |"
        doc = parse_markdown(md)
        block = doc.blocks[0]
        assert isinstance(block, Table)
        actual = block.cells[1][0]
        expected = [Text(text="^")]
        self.assertEqual(actual, expected)

    # def test_table_with_aligned_separator(self):
    #     md = "| A | B |\n| :--- | ---: |\n| 1 | 2 |"
    #     doc = parse_markdown(md)
    #     b = doc.blocks[0]
    #     assert isinstance(b, Table)
    #     self.assertEqual(b.cells[0], ["A", "B"])


class TestTableXHTML(unittest.TestCase):
    def test_parse_simple(self):
        xhtml = "<table><tr><th>A</th></tr><tr><td>1</td></tr></table>"
        doc = parse_xhtml(xhtml)
        actual = doc.blocks[0]
        expected = Table(cells=[[[Text(text="A")]], [[Text(text="1")]]])
        self.assertEqual(actual, expected)

    def test_parse_multiple_columns(self):
        xhtml = (
            "<table>"
            "<tr><th>Name</th><th>Score</th></tr>"
            "<tr><td>Alice</td><td>95</td></tr>"
            "</table>"
        )
        doc = parse_xhtml(xhtml)
        actual = doc.blocks[0]
        expected = Table(
            cells=[
                [[Text(text="Name")], [Text(text="Score")]],  # Row 1
                [[Text(text="Alice")], [Text(text="95")]],  # Row 2
            ]
        )
        self.assertEqual(actual, expected)

    def test_parse_colspan(self):
        xhtml = '<table><tr><th colspan="2">AB</th><th>C</th></tr><tr><td>D</td><td>E</td><td>F</td></tr></table>'
        doc = parse_xhtml(xhtml)
        actual = doc.blocks[0]
        expected = Table(
            cells=[
                [[Text(text="AB")], None, [Text(text="C")]],
                [[Text(text="D")], [Text(text="E")], [Text(text="F")]],
            ],
            merges=[Merge(row=0, col=0, rowspan=1, colspan=2)],
        )
        self.assertEqual(actual, expected)

    def test_parse_rowspan(self):
        xhtml = '<table><tr><th>A</th><th>B</th></tr><tr><td rowspan="2">X</td><td>Y</td></tr><tr><td>Z</td></tr></table>'
        doc = parse_xhtml(xhtml)
        actual = doc.blocks[0]

        expected = Table(
            cells=[
                [[Text(text="A")], [Text(text="B")]],  # Row 1
                [[Text(text="X")], [Text(text="Y")]],  # Row 2
                [None, [Text(text="Z")]],  # Row 3
            ],
            merges=[Merge(row=1, col=0, rowspan=2, colspan=1)],
        )
        self.assertEqual(actual, expected)

    def test_render_simple(self):
        doc = Document(
            blocks=[
                Table(
                    cells=[
                        [[Text(text="A")], [Text(text="B")]],
                        [[Text(text="1")], [Text(text="2")]],
                    ]
                )
            ]
        )
        xhtml = render_xhtml(doc)
        self.assertIn("<table>", xhtml)
        self.assertIn("<th>A<br /></th>", xhtml)
        self.assertIn("<th>B<br /></th>", xhtml)
        self.assertIn("<td>1<br /></td>", xhtml)
        self.assertIn("<td>2<br /></td>", xhtml)
        self.assertIn("</table>", xhtml)


class TestTableConvert(unittest.TestCase):
    def test_basic_table_from_markdown(self):
        md = "| Syntax | Description |\n| --- | --- |\n| Header | Title |\n| Paragraph | Text |"
        xhtml = markdown_to_xhtml(md)
        self.assertIn("<table>", xhtml)
        self.assertIn("<th>Syntax<br /></th>", xhtml)
        self.assertIn("<td>Header<br /></td>", xhtml)

    def test_simple_th_headers(self):
        xhtml = """
        <table>
          <tr><th>Name</th><th>Value</th></tr>
          <tr><td>Alice</td><td>1</td></tr>
          <tr><td>Bob</td><td>2</td></tr>
        </table>
        """
        result = _unpad(xhtml_to_markdown(xhtml))
        self.assertIn("|Name|Value|", result)
        # self.assertIn("|--- | --- |", result)
        self.assertIn("|Alice|1|", result)
        self.assertIn("|Bob|2|", result)

    def test_table_with_tbody(self):
        xhtml = """
        <table>
          <tbody>
            <tr><th>A</th><th>B</th></tr>
            <tr><td>1</td><td>2</td></tr>
          </tbody>
        </table>
        """
        result = _unpad(xhtml_to_markdown(xhtml))
        self.assertIn("|A|B|", result)
        self.assertIn("|1|2|", result)

    def test_pipe_escaped_in_cell(self):
        xhtml = """
        <table>
          <tr><th>Key</th><th>Value</th></tr>
          <tr><td>a|b</td><td>c</td></tr>
        </table>
        """
        self.assertIn("a\\|b", xhtml_to_markdown(xhtml))

    def test_colspan_produces_lt_marker(self):
        xhtml = '<table><tr><th colspan="2">AB</th><th>C</th></tr><tr><td>D</td><td>E</td><td>F</td></tr></table>'
        result = _unpad(xhtml_to_markdown(xhtml))
        self.assertIn("|AB|<|C|", result)
        self.assertIn("|D|E|F|", result)

    def test_rowspan_produces_caret_marker(self):
        xhtml = '<table><tr><th>A</th><th>B</th></tr><tr><td rowspan="2">X</td><td>Y</td></tr><tr><td>Z</td></tr></table>'
        result = _unpad(xhtml_to_markdown(xhtml))
        self.assertIn("|X|Y|", result)
        self.assertIn("|^|Z|", result)

    def test_literal_lt_escaped_in_cell(self):
        xhtml = "<table><tr><th>Key</th></tr><tr><td>&lt;</td></tr></table>"
        md = xhtml_to_markdown(xhtml)
        self.assertIn("\\<", md)

    def test_literal_caret_escaped_in_cell(self):
        xhtml = "<table><tr><th>Key</th></tr><tr><td>^</td></tr></table>"
        md = xhtml_to_markdown(xhtml)
        self.assertNotIn("|^|", md)
        self.assertIn("\\^", md)


class TestTableRoundtrip(unittest.TestCase):
    def test_simple(self):
        xhtml = (
            "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"
        )
        self.assertEqual(
            markdown_to_xhtml(xhtml_to_markdown(xhtml)),
            render_xhtml(parse_xhtml(xhtml)),
        )

    def test_colspan(self):
        xhtml = '<table><tr><th colspan="2">AB</th><th>C</th></tr><tr><td>D</td><td>E</td><td>F</td></tr></table>'
        self.assertEqual(
            markdown_to_xhtml(xhtml_to_markdown(xhtml)),
            render_xhtml(parse_xhtml(xhtml)),
        )

    def test_rowspan(self):
        xhtml = '<table><tr><th>A</th><th>B</th></tr><tr><td rowspan="2">X</td><td>Y</td></tr><tr><td>Z</td></tr></table>'
        self.assertEqual(
            markdown_to_xhtml(xhtml_to_markdown(xhtml)),
            render_xhtml(parse_xhtml(xhtml)),
        )

    def test_colspan_rowspan_combined(self):
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

    def test_literal_lt_roundtrip(self):
        xhtml = "<table><tr><th>Key</th></tr><tr><td>&lt;</td></tr></table>"
        self.assertEqual(
            markdown_to_xhtml(xhtml_to_markdown(xhtml)),
            render_xhtml(parse_xhtml(xhtml)),
        )

    def test_literal_caret_roundtrip(self):
        xhtml = "<table><tr><th>Key</th></tr><tr><td>^</td></tr></table>"
        self.assertEqual(
            markdown_to_xhtml(xhtml_to_markdown(xhtml)),
            render_xhtml(parse_xhtml(xhtml)),
        )


if __name__ == "__main__":
    unittest.main()

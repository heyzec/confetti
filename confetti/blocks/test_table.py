import unittest

from confetti import xhtml_to_ir, xhtml_to_markdown
from confetti.blocks import Table
from confetti.document import Document


# Tests corresponding to "Tables" and "Custom Syntax: Tables with Span Markers"
# sections of example.md
class TestTableExamples(unittest.TestCase):
    # --- Basic pipe table (example.md "Tables" section) ---

    def test_basic_table(self):
        # from_markdown: pipe table parses and round-trips to valid XHTML
        md = "| Syntax | Description |\n| --- | --- |\n| Header | Title |\n| Paragraph | Text |"
        xhtml = Document.from_markdown(md).to_xhtml()
        self.assertIn("<table>", xhtml)
        self.assertIn("<th>Syntax</th>", xhtml)
        self.assertIn("<td>Header</td>", xhtml)

    # --- Colspan "<" marker (example.md "Tables with Span Markers") ---

    def test_colspan_produces_span_marker(self):
        # from_xhtml → to_markdown: colspan="2" cell produces "<" in the next column
        xhtml = "<table><tr><th colspan=\"2\">AB</th><th>C</th></tr><tr><td>D</td><td>E</td><td>F</td></tr></table>"
        result = xhtml_to_markdown(xhtml)
        self.assertIn("| AB | < | C |", result)
        self.assertIn("| D | E | F |", result)

    def test_colspan_roundtrip(self):
        xhtml = "<table><tr><th colspan=\"2\">AB</th><th>C</th></tr><tr><td>D</td><td>E</td><td>F</td></tr></table>"
        self.assertEqual(
            Document.from_markdown(Document.from_xhtml(xhtml).to_markdown()).to_xhtml(),
            Document.from_xhtml(xhtml).to_xhtml(),
        )

    # --- Rowspan "^" marker (example.md "Tables with Span Markers") ---

    def test_rowspan_produces_span_marker(self):
        # from_xhtml → to_markdown: rowspan="2" cell produces "^" in the row below
        xhtml = "<table><tr><th>A</th><th>B</th></tr><tr><td rowspan=\"2\">X</td><td>Y</td></tr><tr><td>Z</td></tr></table>"
        result = xhtml_to_markdown(xhtml)
        self.assertIn("| X | Y |", result)
        self.assertIn("| ^ | Z |", result)

    def test_rowspan_roundtrip(self):
        xhtml = "<table><tr><th>A</th><th>B</th></tr><tr><td rowspan=\"2\">X</td><td>Y</td></tr><tr><td>Z</td></tr></table>"
        self.assertEqual(
            Document.from_markdown(Document.from_xhtml(xhtml).to_markdown()).to_xhtml(),
            Document.from_xhtml(xhtml).to_xhtml(),
        )

    # --- Combined colspan + rowspan ---

    def test_colspan_rowspan_combined_roundtrip(self):
        xhtml = (
            "<table>"
            "<tr><th colspan=\"2\">AB</th><th>C</th></tr>"
            "<tr><td rowspan=\"2\">X</td><td>Y</td><td>Y2</td></tr>"
            "<tr><td>Z</td><td>Z2</td></tr>"
            "</table>"
        )
        self.assertEqual(
            Document.from_markdown(Document.from_xhtml(xhtml).to_markdown()).to_xhtml(),
            Document.from_xhtml(xhtml).to_xhtml(),
        )

    # --- Literal "<" in cell content must be escaped as "\<" ---

    def test_literal_lt_escaped(self):
        # from_xhtml → to_markdown: &lt; in cell becomes \< (not a span marker)
        xhtml = "<table><tr><th>Key</th></tr><tr><td>&lt;</td></tr></table>"
        md = xhtml_to_markdown(xhtml)
        self.assertNotIn("| < |", md)
        self.assertIn("\\<", md)
        # full roundtrip correct
        self.assertEqual(
            Document.from_markdown(md).to_xhtml(),
            Document.from_xhtml(xhtml).to_xhtml(),
        )


class TestTables(unittest.TestCase):
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
        self.assertIn("<!-- ac:macro", result)
        self.assertIn("X", result)
        self.assertIn("a", result)

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

    def test_table_ir_structure(self):
        doc = xhtml_to_ir("<table><tr><th>A</th></tr><tr><td>1</td></tr></table>")
        self.assertEqual(len(doc.blocks), 1)
        b = doc.blocks[0]
        self.assertIsInstance(b, Table)
        self.assertEqual(b.headers, ["A"])
        self.assertEqual(b.rows, [["1"]])

    def test_cell_with_div_wrapper(self):
        xhtml = """
        <table>
          <tr><th>Col</th></tr>
          <tr><td><div class="content-wrapper"><p>cell text</p></div></td></tr>
        </table>
        """
        self.assertIn("cell text", xhtml_to_markdown(xhtml))


if __name__ == "__main__":
    unittest.main()

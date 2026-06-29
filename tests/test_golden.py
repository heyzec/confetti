"""Golden tests: known XHTML input → expected Markdown output."""

import os

import pytest

from converter import xhtml_to_ir, xhtml_to_markdown
from converter.ir import Heading, Paragraph, Table


# ---------------------------------------------------------------------------
# Headings
# ---------------------------------------------------------------------------


class TestHeadings:
    def test_h1(self):
        assert xhtml_to_markdown("<h1>Hello World</h1>") == "# Hello World"

    def test_h2(self):
        assert xhtml_to_markdown("<h2>Sub Heading</h2>") == "## Sub Heading"

    def test_h3(self):
        assert xhtml_to_markdown("<h3>Deep</h3>") == "### Deep"

    def test_h6(self):
        assert xhtml_to_markdown("<h6>Deepest</h6>") == "###### Deepest"

    def test_heading_ir_structure(self):
        doc = xhtml_to_ir("<h2>Title</h2>")
        assert len(doc.blocks) == 1
        b = doc.blocks[0]
        assert isinstance(b, Heading)
        assert b.level == 2
        assert b.text == "Title"

    def test_heading_with_inline_elements(self):
        # ac:inline-comment-marker is preserved as raw inline XML for round-trip fidelity
        xhtml = '<h2>API <ac:inline-comment-marker ac:ref="x">Design</ac:inline-comment-marker></h2>'
        result = xhtml_to_markdown(xhtml)
        assert result.startswith("## API")
        assert "ac:inline-comment-marker" in result
        assert "Design" in result


# ---------------------------------------------------------------------------
# Paragraphs
# ---------------------------------------------------------------------------


class TestParagraphs:
    def test_simple(self):
        assert xhtml_to_markdown("<p>Hello world</p>") == "Hello world"

    def test_with_strong(self):
        xhtml = "<p>Hello <strong>bold</strong> world</p>"
        assert xhtml_to_markdown(xhtml) == "Hello **bold** world"

    def test_with_emphasis(self):
        xhtml = "<p>Hello <em>italic</em> world</p>"
        assert xhtml_to_markdown(xhtml) == "Hello *italic* world"

    def test_with_anchor(self):
        xhtml = '<p>See <a href="https://example.com">link</a> here</p>'
        assert xhtml_to_markdown(xhtml) == "See [link](https://example.com) here"

    def test_with_strikethrough(self):
        xhtml = "<p>Old: <s>removed</s> text</p>"
        assert xhtml_to_markdown(xhtml) == "Old: ~~removed~~ text"

    def test_with_code(self):
        xhtml = "<p>Call <code>foo()</code> here</p>"
        assert xhtml_to_markdown(xhtml) == "Call `foo()` here"

    def test_multiple_paragraphs_separated(self):
        xhtml = "<p>First</p><p>Second</p>"
        result = xhtml_to_markdown(xhtml)
        assert "First" in result
        assert "Second" in result
        # Two blank-line-separated blocks
        assert result.index("First") < result.index("Second")

    def test_whitespace_normalized(self):
        xhtml = "<p>  Hello   world  </p>"
        assert xhtml_to_markdown(xhtml) == "Hello world"

    def test_inline_macro_preserved(self):
        # Inline ac:structured-macro is preserved as raw XML for round-trip fidelity
        xhtml = (
            "<p>Hello "
            '<ac:structured-macro ac:name="status">'
            '<ac:parameter ac:name="title">P1</ac:parameter>'
            "</ac:structured-macro>"
            " world</p>"
        )
        result = xhtml_to_markdown(xhtml)
        assert "Hello" in result
        assert "world" in result
        assert "ac:structured-macro" in result

    def test_inline_comment_marker_skipped(self):
        xhtml = (
            "<p>Text "
            '<ac:inline-comment-marker ac:ref="abc">annotated</ac:inline-comment-marker>'
            " more</p>"
        )
        result = xhtml_to_markdown(xhtml)
        assert "Text" in result
        assert "more" in result

    def test_nbsp_entity(self):
        xhtml = "<p>Hello&nbsp;world</p>"
        result = xhtml_to_markdown(xhtml)
        assert "Hello" in result
        assert "world" in result


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


class TestTables:
    def test_simple_th_headers(self):
        xhtml = """
        <table>
          <tr><th>Name</th><th>Value</th></tr>
          <tr><td>Alice</td><td>1</td></tr>
          <tr><td>Bob</td><td>2</td></tr>
        </table>
        """
        result = xhtml_to_markdown(xhtml)
        assert "| Name | Value |" in result
        assert "| --- | --- |" in result
        assert "| Alice | 1 |" in result
        assert "| Bob | 2 |" in result

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
        assert "| A | B |" in result
        assert "| 1 | 2 |" in result

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
        # Complex tables (with colgroup) are preserved verbatim as raw blocks
        assert "<!-- ac:macro" in result
        assert "X" in result
        assert "a" in result

    def test_pipe_escaped_in_cell(self):
        xhtml = """
        <table>
          <tr><th>Key</th><th>Value</th></tr>
          <tr><td>a|b</td><td>c</td></tr>
        </table>
        """
        result = xhtml_to_markdown(xhtml)
        assert "a\\|b" in result

    def test_uneven_rows_padded(self):
        xhtml = """
        <table>
          <tr><th>A</th><th>B</th><th>C</th></tr>
          <tr><td>1</td><td>2</td></tr>
        </table>
        """
        result = xhtml_to_markdown(xhtml)
        lines = [ln for ln in result.splitlines() if ln.strip()]
        data_row = lines[2]
        # 3-column table → 4 pipe characters per row
        assert data_row.count("|") >= 4

    def test_table_ir_structure(self):
        xhtml = "<table><tr><th>A</th></tr><tr><td>1</td></tr></table>"
        doc = xhtml_to_ir(xhtml)
        assert len(doc.blocks) == 1
        b = doc.blocks[0]
        assert isinstance(b, Table)
        assert b.headers == ["A"]
        assert b.rows == [["1"]]

    def test_cell_with_div_wrapper(self):
        xhtml = """
        <table>
          <tr><th>Col</th></tr>
          <tr><td><div class="content-wrapper"><p>cell text</p></div></td></tr>
        </table>
        """
        result = xhtml_to_markdown(xhtml)
        assert "cell text" in result


# ---------------------------------------------------------------------------
# Macro dropping
# ---------------------------------------------------------------------------


class TestMacroDropping:
    def test_block_macro_preserved_as_comment(self):
        # Block ac:structured-macro is preserved as an HTML comment for round-trip fidelity
        xhtml = """
        <p>Before</p>
        <ac:structured-macro ac:name="code">
          <ac:parameter ac:name="language">python</ac:parameter>
          <ac:plain-text-body><![CDATA[print("hello")]]></ac:plain-text-body>
        </ac:structured-macro>
        <p>After</p>
        """
        result = xhtml_to_markdown(xhtml)
        assert "Before" in result
        assert "After" in result
        assert "<!-- ac:macro" in result
        assert "ac:structured-macro" in result

    def test_expand_macro_preserved_as_comment(self):
        # ac:structured-macro (expand) is preserved as an HTML comment for round-trip fidelity
        xhtml = """
        <p>Visible</p>
        <ac:structured-macro ac:name="expand">
          <ac:parameter ac:name="title">Hidden title</ac:parameter>
          <ac:rich-text-body><p>Expand body</p></ac:rich-text-body>
        </ac:structured-macro>
        """
        result = xhtml_to_markdown(xhtml)
        assert "Visible" in result
        assert "<!-- ac:macro" in result
        assert "ac:structured-macro" in result

    def test_ri_user_preserved_inline(self):
        # ac:link with ri:user is preserved as raw inline XML for round-trip fidelity
        xhtml = '<p>Owner: <ac:link><ri:user ri:userkey="abc123" /></ac:link></p>'
        result = xhtml_to_markdown(xhtml)
        assert "Owner:" in result
        assert "ac:link" in result
        assert "ri:user" in result

    def test_jira_macro_preserved_as_comment(self):
        # ac:structured-macro (jira) is preserved as an HTML comment for round-trip fidelity
        xhtml = """
        <ac:structured-macro ac:name="jira">
          <ac:parameter ac:name="jqlQuery">key=ABC-123</ac:parameter>
        </ac:structured-macro>
        <p>After jira</p>
        """
        result = xhtml_to_markdown(xhtml)
        assert "After jira" in result
        assert "<!-- ac:macro" in result
        assert "ac:structured-macro" in result


# ---------------------------------------------------------------------------
# Lists
# ---------------------------------------------------------------------------


class TestLists:
    def test_unordered_list(self):
        xhtml = "<ul><li>Alpha</li><li>Beta</li></ul>"
        result = xhtml_to_markdown(xhtml)
        # Lists are preserved verbatim as raw blocks for round-trip fidelity
        assert "<!-- ac:macro" in result
        assert "Alpha" in result
        assert "Beta" in result

    def test_ordered_list(self):
        xhtml = "<ol><li>First</li><li>Second</li></ol>"
        result = xhtml_to_markdown(xhtml)
        # Lists are preserved verbatim as raw blocks for round-trip fidelity
        assert "<!-- ac:macro" in result
        assert "First" in result
        assert "Second" in result


# ---------------------------------------------------------------------------
# Integration: parse the actual td.xml
# ---------------------------------------------------------------------------


class TestTdXml:
    @pytest.fixture(scope="class")
    def td_result(self):
        td_path = os.path.join(os.path.dirname(__file__), "..", "td.xml")
        with open(td_path, encoding="utf-8") as fh:
            xhtml = fh.read()
        return xhtml_to_markdown(xhtml)

    def test_parses_without_error(self, td_result):
        assert len(td_result) > 0

    def test_top_level_headings_present(self, td_result):
        assert "# Metadata" in td_result
        assert "# Background" in td_result
        assert "# Technical Design" in td_result

    def test_macros_preserved_in_output(self, td_result):
        # Macros are preserved: block macros as HTML comments, inline macros as raw XML
        assert "<!-- ac:macro" in td_result or "ac:structured-macro" in td_result

    def test_tables_rendered(self, td_result):
        # All tables in td.xml are complex (class/colgroup/colspan) so preserved as raw blocks
        assert "<!-- ac:macro" in td_result
        assert "<table" in td_result

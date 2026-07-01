"""Golden tests for the full parse/render pipeline."""

import os
import unittest

from confetti import xhtml_to_markdown


# ---------------------------------------------------------------------------
# Macro dropping
# ---------------------------------------------------------------------------


class TestMacroDropping(unittest.TestCase):
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
        self.assertIn("Before", result)
        self.assertIn("After", result)
        self.assertIn("<!-- ac:macro", result)
        self.assertIn("ac:structured-macro", result)

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
        self.assertIn("Visible", result)
        self.assertIn("<!-- ac:macro", result)
        self.assertIn("ac:structured-macro", result)

    def test_ri_user_preserved_inline(self):
        # ac:link with ri:user is preserved as raw inline XML for round-trip fidelity
        xhtml = '<p>Owner: <ac:link><ri:user ri:userkey="abc123" /></ac:link></p>'
        result = xhtml_to_markdown(xhtml)
        self.assertIn("Owner:", result)
        self.assertIn("ac:link", result)
        self.assertIn("ri:user", result)

    def test_jira_macro_preserved_as_comment(self):
        # ac:structured-macro (jira) is preserved as an HTML comment for round-trip fidelity
        xhtml = """
        <ac:structured-macro ac:name="jira">
          <ac:parameter ac:name="jqlQuery">key=ABC-123</ac:parameter>
        </ac:structured-macro>
        <p>After jira</p>
        """
        result = xhtml_to_markdown(xhtml)
        self.assertIn("After jira", result)
        self.assertIn("<!-- ac:macro", result)
        self.assertIn("ac:structured-macro", result)


# ---------------------------------------------------------------------------
# Integration: parse the actual td.xml
# ---------------------------------------------------------------------------


class TestTdXml(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        td_path = os.path.join(os.path.dirname(__file__), "..", "td.xml")
        with open(td_path, encoding="utf-8") as fh:
            xhtml = fh.read()
        cls.td_result = xhtml_to_markdown(xhtml)

    def test_parses_without_error(self):
        self.assertGreater(len(self.td_result), 0)

    def test_top_level_headings_present(self):
        self.assertIn("# Metadata", self.td_result)
        self.assertIn("# Background", self.td_result)
        self.assertIn("# Technical Design", self.td_result)

    def test_macros_preserved_in_output(self):
        # Macros are preserved: block macros as HTML comments, inline macros as raw XML
        self.assertTrue(
            "<!-- ac:macro" in self.td_result or "ac:structured-macro" in self.td_result
        )

    def test_tables_rendered(self):
        # All tables in td.xml are complex (class/colgroup/colspan) so preserved as raw blocks
        self.assertIn("<!-- ac:macro", self.td_result)
        self.assertIn("<table", self.td_result)

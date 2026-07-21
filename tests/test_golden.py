"""Golden tests for the full parse/render pipeline."""

import os
import unittest

from backends.confluence import xhtml_to_markdown

# ---------------------------------------------------------------------------
# Macro dropping
# ---------------------------------------------------------------------------


class TestMacroDropping(unittest.TestCase):
    def test_code_macro_rendered_as_fenced_block(self):
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
        self.assertIn("```python", result)
        self.assertIn('print("hello")', result)

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
        self.assertIn("<!-- confetti:raw", result)
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
        self.assertIn("<!-- confetti:raw", result)
        self.assertIn("ac:structured-macro", result)

import unittest

from confetti.blocks import CodeBlock
from confetti.convert import (
    markdown_to_xhtml,
    parse_markdown,
    parse_xhtml,
    render_xhtml,
    xhtml_to_markdown,
)


class TestCodeBlockMarkdown(unittest.TestCase):
    def test_parse_bare_no_lang(self):
        md = "```\nhello\n```"
        doc = parse_markdown(md)
        actual = doc.blocks[0]
        expected = CodeBlock(params=[], body="hello", macro_id="")
        self.assertEqual(actual, expected)

    def test_parse_bare_with_lang(self):
        md = "```python\nprint(1)\n```"
        doc = parse_markdown(md)
        actual = doc.blocks[0]
        expected = CodeBlock(
            params=[("language", "python")], body="print(1)", macro_id=""
        )
        self.assertEqual(actual, expected)


class TestCodeBlockXHTML(unittest.TestCase):
    def test_parse_basic(self):
        xhtml = '<ac:structured-macro ac:name="code" ac:schema-version="1" ac:macro-id="abc"><ac:parameter ac:name="language">python</ac:parameter><ac:plain-text-body><![CDATA[print("hi")]]></ac:plain-text-body></ac:structured-macro>'
        doc = parse_xhtml(xhtml)
        actual = doc.blocks[0]
        expected = CodeBlock(
            params=[("language", "python")], body='print("hi")', macro_id="abc"
        )
        self.assertEqual(actual, expected)

    def test_parse_extra_params_preserved(self):
        xhtml = '<ac:structured-macro ac:name="code" ac:schema-version="1" ac:macro-id="p1"><ac:parameter ac:name="title">My Title</ac:parameter><ac:parameter ac:name="linenumbers">true</ac:parameter><ac:parameter ac:name="collapse">true</ac:parameter><ac:plain-text-body><![CDATA[x = 1]]></ac:plain-text-body></ac:structured-macro>'
        doc = parse_xhtml(xhtml)
        actual = doc.blocks[0]
        expected = CodeBlock(
            params=[
                ("title", "My Title"),
                ("linenumbers", "true"),
                ("collapse", "true"),
            ],
            body="x = 1",
            macro_id="p1",
        )
        self.assertEqual(actual, expected)


class TestCodeBlockConvert(unittest.TestCase):
    def test_to_markdown_with_language(self):
        xhtml = '<ac:structured-macro ac:name="code" ac:schema-version="1" ac:macro-id="abc"><ac:parameter ac:name="language">sql</ac:parameter><ac:plain-text-body><![CDATA[SELECT 1]]></ac:plain-text-body></ac:structured-macro>'
        md = xhtml_to_markdown(xhtml)
        self.assertIn("<!-- confetti:code ", md)
        self.assertIn('"macro-id": "abc"', md)
        self.assertIn("```sql", md)
        self.assertIn("SELECT 1", md)

    def test_to_markdown_no_language(self):
        xhtml = '<ac:structured-macro ac:name="code" ac:schema-version="1" ac:macro-id="xyz"><ac:plain-text-body><![CDATA[hello]]></ac:plain-text-body></ac:structured-macro>'
        md = xhtml_to_markdown(xhtml)
        self.assertIn("```\n", md)

    def test_bare_fence_to_xhtml(self):
        md = "```sql\nSELECT 1\n```"
        xhtml = markdown_to_xhtml(md)
        self.assertIn('ac:name="code"', xhtml)
        self.assertIn('ac:name="language"', xhtml)
        self.assertIn("SELECT 1", xhtml)


class TestCodeBlockRoundtrip(unittest.TestCase):
    def test_bare_fence_roundtrips_to_markdown(self):
        md = "```python\nprint(1)\n```"
        doc = parse_markdown(md)
        self.assertEqual(doc.blocks[0].to_markdown(), md)

    def test_roundtrip_with_language(self):
        xhtml = '<ac:structured-macro ac:name="code" ac:schema-version="1" ac:macro-id="r1"><ac:parameter ac:name="language">sql</ac:parameter><ac:parameter ac:name="title">q</ac:parameter><ac:parameter ac:name="linenumbers">true</ac:parameter><ac:plain-text-body><![CDATA[SELECT 1]]></ac:plain-text-body></ac:structured-macro>'
        md = xhtml_to_markdown(xhtml)
        self.assertEqual(markdown_to_xhtml(md), render_xhtml(parse_xhtml(xhtml)))

    def test_roundtrip_no_params(self):
        xhtml = '<ac:structured-macro ac:name="code" ac:schema-version="1" ac:macro-id="r2"><ac:plain-text-body><![CDATA[hello world]]></ac:plain-text-body></ac:structured-macro>'
        md = xhtml_to_markdown(xhtml)
        self.assertEqual(markdown_to_xhtml(md), render_xhtml(parse_xhtml(xhtml)))

    def test_multiline_body(self):
        xhtml = '<ac:structured-macro ac:name="code" ac:schema-version="1" ac:macro-id="m1"><ac:parameter ac:name="language">python</ac:parameter><ac:plain-text-body><![CDATA[def f():\n    return 1]]></ac:plain-text-body></ac:structured-macro>'
        md = xhtml_to_markdown(xhtml)
        self.assertIn("def f():", md)
        self.assertIn("    return 1", md)
        self.assertEqual(markdown_to_xhtml(md), render_xhtml(parse_xhtml(xhtml)))


if __name__ == "__main__":
    unittest.main()

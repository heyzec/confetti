import unittest

from confetti import xhtml_to_ir, xhtml_to_markdown
from confetti.document import Document
from confetti.blocks import CodeBlock


class TestCodeBlock(unittest.TestCase):
    def test_basic_parse(self):
        xhtml = '<ac:structured-macro ac:name="code" ac:schema-version="1" ac:macro-id="abc"><ac:parameter ac:name="language">python</ac:parameter><ac:plain-text-body><![CDATA[print("hi")]]></ac:plain-text-body></ac:structured-macro>'
        doc = xhtml_to_ir(xhtml)
        self.assertEqual(len(doc.blocks), 1)
        b = doc.blocks[0]
        self.assertIsInstance(b, CodeBlock)
        self.assertEqual(b.macro_id, "abc")
        self.assertEqual(b.params, [("language", "python")])
        self.assertEqual(b.body, 'print("hi")')

    def test_to_markdown_with_language(self):
        xhtml = '<ac:structured-macro ac:name="code" ac:schema-version="1" ac:macro-id="abc"><ac:parameter ac:name="language">sql</ac:parameter><ac:plain-text-body><![CDATA[SELECT 1]]></ac:plain-text-body></ac:structured-macro>'
        md = xhtml_to_markdown(xhtml)
        self.assertIn("<!-- confetti:code ", md)
        self.assertIn('"macro-id": "abc"', md)
        self.assertIn("```sql", md)
        self.assertIn("SELECT 1", md)
        self.assertIn("```", md)

    def test_to_markdown_no_language(self):
        xhtml = '<ac:structured-macro ac:name="code" ac:schema-version="1" ac:macro-id="xyz"><ac:plain-text-body><![CDATA[hello]]></ac:plain-text-body></ac:structured-macro>'
        md = xhtml_to_markdown(xhtml)
        self.assertIn("```\n", md)

    def test_extra_params_preserved(self):
        xhtml = '<ac:structured-macro ac:name="code" ac:schema-version="1" ac:macro-id="p1"><ac:parameter ac:name="title">My Title</ac:parameter><ac:parameter ac:name="linenumbers">true</ac:parameter><ac:parameter ac:name="collapse">true</ac:parameter><ac:plain-text-body><![CDATA[x = 1]]></ac:plain-text-body></ac:structured-macro>'
        doc = xhtml_to_ir(xhtml)
        b = doc.blocks[0]
        self.assertIsInstance(b, CodeBlock)
        self.assertEqual(b.params, [("title", "My Title"), ("linenumbers", "true"), ("collapse", "true")])

    def test_roundtrip_with_language(self):
        xhtml = '<ac:structured-macro ac:name="code" ac:schema-version="1" ac:macro-id="r1"><ac:parameter ac:name="language">sql</ac:parameter><ac:parameter ac:name="title">q</ac:parameter><ac:parameter ac:name="linenumbers">true</ac:parameter><ac:plain-text-body><![CDATA[SELECT 1]]></ac:plain-text-body></ac:structured-macro>'
        md = Document.from_xhtml(xhtml).to_markdown()
        self.assertEqual(Document.from_markdown(md).to_xhtml(), Document.from_xhtml(xhtml).to_xhtml())

    def test_roundtrip_no_params(self):
        xhtml = '<ac:structured-macro ac:name="code" ac:schema-version="1" ac:macro-id="r2"><ac:plain-text-body><![CDATA[hello world]]></ac:plain-text-body></ac:structured-macro>'
        md = Document.from_xhtml(xhtml).to_markdown()
        self.assertEqual(Document.from_markdown(md).to_xhtml(), Document.from_xhtml(xhtml).to_xhtml())

    def test_multiline_body(self):
        xhtml = '<ac:structured-macro ac:name="code" ac:schema-version="1" ac:macro-id="m1"><ac:parameter ac:name="language">python</ac:parameter><ac:plain-text-body><![CDATA[def f():\n    return 1]]></ac:plain-text-body></ac:structured-macro>'
        md = Document.from_xhtml(xhtml).to_markdown()
        self.assertIn("def f():", md)
        self.assertIn("    return 1", md)
        self.assertEqual(Document.from_markdown(md).to_xhtml(), Document.from_xhtml(xhtml).to_xhtml())


if __name__ == "__main__":
    unittest.main()

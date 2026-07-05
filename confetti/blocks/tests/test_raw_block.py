import unittest

from confetti.blocks import RawBlock
from confetti.convert import markdown_to_xhtml, parse_xhtml, xhtml_to_markdown


class TestRawBlock(unittest.TestCase):
    def test_complex_list_preserved_as_raw(self):
        xhtml = "<ul><li><p>a</p><p>b</p></li></ul>"
        doc = parse_xhtml(xhtml)
        self.assertIsInstance(doc.blocks[0], RawBlock)

    def test_roundtrip_via_confetti_raw(self):
        xhtml = "<ul><li><p>a</p><p>b</p></li></ul>"
        md = xhtml_to_markdown(xhtml)
        self.assertIn("<!-- confetti:raw", md)
        self.assertEqual(markdown_to_xhtml(md), xhtml)


if __name__ == "__main__":
    unittest.main()

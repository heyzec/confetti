import unittest

from confetti import xhtml_to_markdown
from confetti.blocks import RawBlock
from confetti.document import Document


class TestRawBlock(unittest.TestCase):
    def test_complex_list_preserved_as_raw(self):
        xhtml = "<ul><li><p>a</p><p>b</p></li></ul>"
        doc = Document.from_xhtml(xhtml)
        self.assertIsInstance(doc.blocks[0], RawBlock)

    def test_roundtrip_via_confetti_raw(self):
        xhtml = "<ul><li><p>a</p><p>b</p></li></ul>"
        md = Document.from_xhtml(xhtml).to_markdown()
        self.assertIn("<!-- confetti:raw", md)
        self.assertEqual(Document.from_markdown(md).to_xhtml(), xhtml)


if __name__ == "__main__":
    unittest.main()

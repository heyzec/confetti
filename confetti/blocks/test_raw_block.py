import unittest

from confetti import xhtml_to_markdown


class TestLists(unittest.TestCase):
    def test_unordered_list(self):
        result = xhtml_to_markdown("<ul><li>Alpha</li><li>Beta</li></ul>")
        self.assertIn("<!-- confetti:raw", result)
        self.assertIn("Alpha", result)
        self.assertIn("Beta", result)

    def test_ordered_list(self):
        result = xhtml_to_markdown("<ol><li>First</li><li>Second</li></ol>")
        self.assertIn("<!-- confetti:raw", result)
        self.assertIn("First", result)
        self.assertIn("Second", result)


if __name__ == "__main__":
    unittest.main()

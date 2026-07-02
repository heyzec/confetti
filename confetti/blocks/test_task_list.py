import unittest

from confetti import xhtml_to_ir, xhtml_to_markdown
from confetti.document import Document
from confetti.blocks import RawBlock, TaskList


class TestTaskList(unittest.TestCase):
    def _xhtml(self, tasks_xml: str) -> str:
        return f"<ac:task-list>{tasks_xml}</ac:task-list>"

    def _task(self, tid: int, status: str, body: str) -> str:
        return f"\n<ac:task>\n<ac:task-id>{tid}</ac:task-id>\n<ac:task-status>{status}</ac:task-status>\n<ac:task-body>{body}</ac:task-body>\n</ac:task>"

    def test_basic_parse(self):
        xhtml = self._xhtml(self._task(1, "incomplete", "do something"))
        doc = xhtml_to_ir(xhtml)
        self.assertEqual(len(doc.blocks), 1)
        b = doc.blocks[0]
        self.assertIsInstance(b, TaskList)
        self.assertEqual(b.tasks, [(1, "incomplete", "do something")])

    def test_complete_status(self):
        xhtml = self._xhtml(self._task(5, "complete", "done"))
        doc = xhtml_to_ir(xhtml)
        b = doc.blocks[0]
        self.assertIsInstance(b, TaskList)
        self.assertEqual(b.tasks[0][1], "complete")

    def test_to_markdown_incomplete(self):
        xhtml = self._xhtml(self._task(1, "incomplete", "do something"))
        md = xhtml_to_markdown(xhtml)
        self.assertNotIn("<!--", md)
        self.assertIn("- [ ] do something", md)

    def test_to_markdown_complete(self):
        xhtml = self._xhtml(self._task(2, "complete", "done task"))
        md = xhtml_to_markdown(xhtml)
        self.assertNotIn("<!--", md)
        self.assertIn("- [x] done task", md)

    def test_multiple_tasks(self):
        xhtml = self._xhtml(
            self._task(3, "incomplete", "first") + self._task(4, "complete", "second")
        )
        md = xhtml_to_markdown(xhtml)
        self.assertIn("- [ ] first", md)
        self.assertIn("- [x] second", md)

    def test_roundtrip_simple(self):
        xhtml = self._xhtml(self._task(1, "incomplete", "apply for permissions"))
        self.assertEqual(
            Document.from_markdown(Document.from_xhtml(xhtml).to_markdown()).to_xhtml(),
            Document.from_xhtml(xhtml).to_xhtml(),
        )

    def test_roundtrip_complete(self):
        xhtml = self._xhtml(self._task(1, "complete", "reviewed"))
        self.assertEqual(
            Document.from_markdown(Document.from_xhtml(xhtml).to_markdown()).to_xhtml(),
            Document.from_xhtml(xhtml).to_xhtml(),
        )

    def test_roundtrip_with_inline_code(self):
        xhtml = self._xhtml(self._task(1, "incomplete", "merge <code>master</code> branch"))
        self.assertEqual(
            Document.from_markdown(Document.from_xhtml(xhtml).to_markdown()).to_xhtml(),
            Document.from_xhtml(xhtml).to_xhtml(),
        )

    def test_roundtrip_with_link(self):
        xhtml = self._xhtml(
            self._task(1, "incomplete", 'configure <a href="https://example.com">WSA Gateway</a>')
        )
        self.assertEqual(
            Document.from_markdown(Document.from_xhtml(xhtml).to_markdown()).to_xhtml(),
            Document.from_xhtml(xhtml).to_xhtml(),
        )

    def test_complex_body_falls_back_to_rawblock(self):
        # span with style attribute is not simple inline → RawBlock
        xhtml = self._xhtml(
            self._task(5, "incomplete", '<span style="color: rgb(51,51,51);">styled</span>')
        )
        doc = xhtml_to_ir(xhtml)
        self.assertIsInstance(doc.blocks[0], RawBlock)

    def test_body_with_ul_falls_back_to_rawblock(self):
        xhtml = self._xhtml(
            self._task(99, "complete", "text<ul><li>item</li></ul>")
        )
        doc = xhtml_to_ir(xhtml)
        self.assertIsInstance(doc.blocks[0], RawBlock)


if __name__ == "__main__":
    unittest.main()

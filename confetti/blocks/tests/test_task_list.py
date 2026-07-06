import unittest

from confetti.blocks import RawBlock, TaskList
from confetti.convert import (
    markdown_to_xhtml,
    parse_markdown,
    parse_xhtml,
    render_xhtml,
    xhtml_to_markdown,
)


class TestTaskListMarkdown(unittest.TestCase):
    def test_parse_incomplete(self):
        md = "- [ ] do something"
        doc = parse_markdown(md)
        b = doc.blocks[0]
        assert isinstance(b, TaskList)
        self.assertEqual(b.tasks, [(1, "incomplete", "do something")])

    def test_parse_complete(self):
        md = "- [x] done task"
        doc = parse_markdown(md)
        b = doc.blocks[0]
        assert isinstance(b, TaskList)
        self.assertEqual(b.tasks, [(1, "complete", "done task")])

    def test_parse_multiple(self):
        md = "- [ ] first\n- [x] second"
        doc = parse_markdown(md)
        b = doc.blocks[0]
        assert isinstance(b, TaskList)
        self.assertEqual(len(b.tasks), 2)
        self.assertEqual(b.tasks[0], (1, "incomplete", "first"))
        self.assertEqual(b.tasks[1], (2, "complete", "second"))


class TestTaskListXHTML(unittest.TestCase):
    def _wrap_task_list(self, tasks_xml: str) -> str:
        return f"<ac:task-list>{tasks_xml}</ac:task-list>"

    def _wrap_task(self, tid: int, status: str, body: str) -> str:
        return f"\n<ac:task>\n<ac:task-id>{tid}</ac:task-id>\n<ac:task-status>{status}</ac:task-status>\n<ac:task-body>{body}</ac:task-body>\n</ac:task>"

    def test_basic_parse(self):
        xhtml = self._wrap_task_list(self._wrap_task(1, "incomplete", "do something"))
        doc = parse_xhtml(xhtml)
        self.assertEqual(len(doc.blocks), 1)
        actual = doc.blocks[0]
        expected = TaskList(tasks=[(1, "incomplete", "do something")])
        self.assertEqual(actual, expected)

    def test_parse_complete_status(self):
        xhtml = self._wrap_task_list(self._wrap_task(5, "complete", "done"))
        doc = parse_xhtml(xhtml)
        self.assertEqual(len(doc.blocks), 1)
        actual = doc.blocks[0]
        expected = TaskList(tasks=[(5, "complete", "done")])
        self.assertEqual(actual, expected)

    def test_complex_body_falls_back_to_rawblock(self):
        xhtml = self._wrap_task_list(
            self._wrap_task(
                5, "incomplete", '<span style="color: rgb(51,51,51);">styled</span>'
            )
        )
        doc = parse_xhtml(xhtml)
        self.assertEqual(len(doc.blocks), 1)
        self.assertIsInstance(doc.blocks[0], RawBlock)

    def test_body_with_ul_falls_back_to_rawblock(self):
        xhtml = self._wrap_task_list(
            self._wrap_task(99, "complete", "text<ul><li>item</li></ul>")
        )
        doc = parse_xhtml(xhtml)
        self.assertEqual(len(doc.blocks), 1)
        self.assertIsInstance(doc.blocks[0], RawBlock)


class TestTaskListConvert(unittest.TestCase):
    def _xhtml(self, tasks_xml: str) -> str:
        return f"<ac:task-list>{tasks_xml}</ac:task-list>"

    def _task(self, tid: int, status: str, body: str) -> str:
        return f"\n<ac:task>\n<ac:task-id>{tid}</ac:task-id>\n<ac:task-status>{status}</ac:task-status>\n<ac:task-body>{body}</ac:task-body>\n</ac:task>"

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


class TestTaskListRoundtrip(unittest.TestCase):
    def _xhtml(self, tasks_xml: str) -> str:
        return f"<ac:task-list>{tasks_xml}</ac:task-list>"

    def _task(self, tid: int, status: str, body: str) -> str:
        return f"\n<ac:task>\n<ac:task-id>{tid}</ac:task-id>\n<ac:task-status>{status}</ac:task-status>\n<ac:task-body>{body}</ac:task-body>\n</ac:task>"

    def test_roundtrip_simple(self):
        xhtml = self._xhtml(self._task(1, "incomplete", "apply for permissions"))
        self.assertEqual(
            markdown_to_xhtml(xhtml_to_markdown(xhtml)),
            render_xhtml(parse_xhtml(xhtml)),
        )

    def test_roundtrip_complete(self):
        xhtml = self._xhtml(self._task(1, "complete", "reviewed"))
        self.assertEqual(
            markdown_to_xhtml(xhtml_to_markdown(xhtml)),
            render_xhtml(parse_xhtml(xhtml)),
        )

    def test_roundtrip_with_inline_code(self):
        xhtml = self._xhtml(
            self._task(1, "incomplete", "merge <code>master</code> branch")
        )
        self.assertEqual(
            markdown_to_xhtml(xhtml_to_markdown(xhtml)),
            render_xhtml(parse_xhtml(xhtml)),
        )

    def test_roundtrip_with_link(self):
        xhtml = self._xhtml(
            self._task(
                1,
                "incomplete",
                'configure <a href="https://example.com">WSA Gateway</a>',
            )
        )
        self.assertEqual(
            markdown_to_xhtml(xhtml_to_markdown(xhtml)),
            render_xhtml(parse_xhtml(xhtml)),
        )


if __name__ == "__main__":
    unittest.main()

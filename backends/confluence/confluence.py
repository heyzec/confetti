import argparse
import datetime
import sys
import zoneinfo
from dataclasses import dataclass
from typing import Any, Generator, override

from dulwich.notes import Notes
from dulwich.objects import Blob, Commit, Tree
from dulwich.repo import MemoryRepo, Repo

import cicero

from .client import ConfluenceClient, PageVersion
from .convert import markdown_to_xhtml, xhtml_to_markdown

DOCUMENT_NAME = "document.md"

global_client: ConfluenceClient


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _write(path: str, content: str) -> None:
    if not content.endswith("\n"):
        content += "\n"
    if path == "-":
        sys.stdout.write(content)
    else:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        print(f"Written to {path}", file=sys.stderr)


def cmd_to_md(args: argparse.Namespace) -> None:
    xhtml = _read(args.input)
    md = xhtml_to_markdown(xhtml)
    _write(args.output, md)


def cmd_to_xhtml(args: argparse.Namespace) -> None:
    md = _read(args.input)
    xhtml = markdown_to_xhtml(md)
    _write(args.output, xhtml)


@dataclass
class ConfluenceRevision(cicero.BaseRevision):
    page_id: int
    version: PageVersion

    @override
    def id(self):
        return str(self.version.number)

    @override
    def gen_branch_name(self) -> str:
        return f"unexpected-{self.page_id}-{self.version.number}"

    @override
    def prepare_commit(self, repo: Repo | MemoryRepo, parent: bytes | None = None):
        xhtml = global_client.read_page(str(self.page_id), self.version.number)
        md_temp = xhtml_to_markdown(xhtml)
        xhtml_temp = markdown_to_xhtml(md_temp)
        md = xhtml_to_markdown(xhtml_temp)
        md = md.strip()

        blob = Blob.from_string(md.encode())
        tree = Tree()
        tree.add(DOCUMENT_NAME.encode(), 0o100644, blob.id)
        repo.object_store.add_object(blob)
        repo.object_store.add_object(tree)

        message = f"{self.version.message}\n"
        email: str = str(self.version.by_username)
        actor: str = f"{email} <{email}>"

        commit = Commit()
        commit.tree = tree.id
        commit.parents = (
            [parent] if parent else []
        )  # pyright: ignore[reportAttributeAccessIssue] ignore covariance issue
        commit.author = commit.committer = actor.encode()

        assert self.version.when.endswith("+08:00")
        t = datetime.datetime.fromisoformat(
            self.version.when.replace("Z", "+00:00")
        ).timestamp()
        dt = datetime.datetime.fromtimestamp(t, zoneinfo.ZoneInfo("Asia/Singapore"))
        dt = datetime.datetime(dt.year, dt.month, dt.day)  # zero out hour, minute, etc
        dt = dt.astimezone(
            datetime.timezone.utc
        )  # prepare for getting timestamp in UTC
        commit.author_time = commit.commit_time = int(dt.timestamp())

        commit.author_timezone = commit.commit_timezone = 8 * 3600
        commit.message = message.encode()
        repo.object_store.add_object(commit)

        note = Notes(repo.object_store, repo.refs).get_note(commit.id)
        if note:
            assert note.decode() == str(
                self.version.number
            ), f"ID of PR for commit {commit.id} has changed! from_note={note.decode()} vs from_pr={self.version.number}"

        Notes(repo.object_store, repo.refs).set_note(
            commit.id, f"{self.version.number}".encode()
        )

        return commit


@dataclass
class ConfluenceConfig(cicero.BaseConfig):
    page_id: int = 0

    @override
    def generate_url_slug(self) -> str:
        return f"confluence-{self.page_id}"

    @override
    @classmethod
    def from_url_slug(cls, slug: str):
        _, page_id = slug.split("-", 1)
        return ConfluenceConfig(
            page_id=int(page_id),
        )


class Confluence(cicero.Base):
    feature_branches_prepared: bool = False

    def __init__(self, client: ConfluenceClient):
        self.client = client
        super().__init__()  # Not ideal, calling parse should be library's job
        global global_client
        global_client = client  # hack

    def cmd_download(self, args: argparse.Namespace) -> None:
        xhtml = self.client.read_page(args.page)

        if args.file.endswith(".md"):
            content = xhtml_to_markdown(xhtml)
        else:
            content = xhtml

        _write(args.file, content)

    def cmd_upload(self, args: argparse.Namespace) -> None:
        raw = _read(args.file)
        if args.file.endswith(".md"):
            xhtml = markdown_to_xhtml(raw)
        else:
            xhtml = raw

        page_id = self.client._resolve_page_id(args.page)
        page = self.client.get_metadata(page_id)
        title = page["title"]
        new_version = self.client.update_page(args.page, title, xhtml)

        print(
            f"Updated '{title}' (page {page_id}) -> version {new_version}",
            file=sys.stderr,
        )

    @override
    def get_repo_path(self, args):
        return "temp"

    @override
    def stream_revisions(self, scenario) -> Generator[ConfluenceRevision]:
        if scenario == "feature":
            return
        versions = self.client.list_versions(self.args.page_id)
        for version in versions:
            yield ConfluenceRevision(
                page_id=self.args.page_id,
                version=version,
            )

    @override
    def on_push(self, src, dst, commit, forced, local):
        def get_pr_id(ref: str) -> int | None:
            branchname = ref.split("/")[-1]
            if branchname.isdigit():
                return int(branchname)
            if "_" in branchname:
                if not branchname.split("_")[-1].isdigit():
                    return None
                return int(branchname.split("_")[-1])
            return None

        pr_id = get_pr_id(dst) or get_pr_id(src)
        if pr_id:
            raise NotImplementedError("Confluence versions are immutable")
        else:
            # Create new PR
            if dst not in ("refs/heads/new"):
                self.send(
                    "error",
                    dst,
                    "updates are only accepted by pushing to refs/heads/new",
                )
                return
            self.log(
                f"Creating PR from commit {commit.id.decode()}: {commit.message.decode().strip()}"
            )
            tree_id = commit.tree
            tree = local.get_object(tree_id)
            assert isinstance(tree, Tree)

            entries = list(tree.items())
            assert len(entries) == 1

            name, _mode, sha = entries[0]
            assert name == DOCUMENT_NAME.encode()
            blob = local[sha]
            assert isinstance(blob, Blob)

            md = blob.data.decode()
            xhtml = markdown_to_xhtml(md)
            md_temp = xhtml_to_markdown(xhtml)
            xhtml_temp = markdown_to_xhtml(md_temp)
            md = xhtml_to_markdown(xhtml_temp)
            md = md.strip()

            self.client.update_page(
                str(self.args.page_id),
                "Updated from git",
                xhtml,
                message=commit.message.strip().decode(),
            )
            self.log(
                f"Updated Confluence page {self.args.page_id} from commit {commit.id.strip().decode()}"
            )
            assert src == "refs/heads/main"
            local.refs["refs/remotes/origin/main".encode()] = commit.id

    @override
    def parse(
        self, subparsers: cicero.SupportsAddParser
    ) -> Generator[ConfluenceConfig | None, Any, None]:
        # xhtml-to-md
        p1 = subparsers.add_parser("to-md", help="Convert Confluence XHTML -> Markdown")
        p1.add_argument(
            "input", metavar="FILE", help="XHTML input file (or - for stdin)"
        )
        p1.add_argument(
            "-o",
            "--output",
            metavar="FILE",
            default="-",
            help="Output file (default: stdout)",
        )
        p1.set_defaults(func=cmd_to_md)

        # md-to-xhtml
        p2 = subparsers.add_parser("to-xhtml", help="Convert Markdown -> XHTML")
        p2.add_argument(
            "input", metavar="FILE", help="Markdown input file (or - for stdin)"
        )
        p2.add_argument(
            "-o",
            "--output",
            metavar="FILE",
            default="-",
            help="Output file (default: stdout)",
        )
        p2.set_defaults(func=cmd_to_xhtml)

        # download
        p3 = subparsers.add_parser(
            "download", help="Download a Confluence page to a file"
        )
        p3.add_argument(
            "--page",
            "-p",
            required=True,
            metavar="ID_OR_URL",
            help="Confluence page ID or URL",
        )
        p3.add_argument(
            "file",
            metavar="FILE",
            help="Output file (.md triggers Markdown conversion)",
        )
        p3.set_defaults(func=self.cmd_download)

        # upload
        p4 = subparsers.add_parser("upload", help="Upload XHTML to a Confluence page")
        p4.add_argument(
            "--page",
            "-p",
            required=True,
            metavar="ID_OR_URL",
            help="Confluence page ID or URL",
        )
        p4.add_argument("file", metavar="FILE", help="XHTML file to upload")
        p4.set_defaults(func=self.cmd_upload)

        clone_parser = yield
        assert isinstance(clone_parser, argparse.ArgumentParser)
        clone_parser.add_argument("url", help="Confluence page URL")

        args = yield
        assert isinstance(args, argparse.Namespace)
        page_id = self.client._resolve_page_id(args.url)

        yield ConfluenceConfig(
            page_id=page_id,
        )


Confluence.setT(ConfluenceConfig)

from __future__ import annotations

import abc
import argparse
import logging
import os
import sys
from dataclasses import dataclass
from typing import Any, Generator, Literal, Protocol, final

from dulwich.notes import Notes
from dulwich.objects import Commit, Tree
from dulwich.porcelain import reset
from dulwich.repo import MemoryRepo, Repo

DEBUGFILE = os.path.expanduser("~/cicero.log")

DEBUG_MODE: bool = False


# TODO: Wrong abstraction, it is both a context and a repo config
@dataclass
class BaseConfig(abc.ABC):
    command: str | None = None
    is_helper: bool = False

    def setup(self):
        pass

    @abc.abstractmethod
    def generate_url_slug(self) -> str:
        """
        Generates a URL suffix used as the repository remote URL, e.g. "cicero://<slug>"
        """
        ...

    @classmethod
    @abc.abstractmethod
    def from_url_slug(cls, slug: str) -> BaseConfig:
        """
        Initializes the configuration from a URL suffix, e.g. "cicero://<slug>"
        """
        ...

    def __post_init__(self):
        self.setup()


class BaseRevision(abc.ABC):
    @abc.abstractmethod
    def id(self) -> str: ...

    @abc.abstractmethod
    def prepare_commit(
        self, repo: Repo | MemoryRepo, parent: bytes | None = None
    ) -> Commit: ...

    @abc.abstractmethod
    def gen_branch_name(self) -> str: ...


class SupportsAddParser(Protocol):
    def add_parser(self, *args, **kwargs) -> argparse.ArgumentParser: ...


class Base[T: BaseConfig, U: BaseRevision](abc.ABC):
    args: T  # to remove, for transition only

    feature_branches_prepared: bool = False

    classT: type[T]

    @classmethod
    def setT(cls, t: type[T]):
        cls.classT = t

    def __init__(self):
        parser = argparse.ArgumentParser()  # unable to show help...
        script_name = os.path.basename(sys.argv[0])
        if script_name == "git-remote-cicero":
            parser.add_argument("remote")
            parser.add_argument("url")
            args = parser.parse_args()

            ctx = self.classT.from_url_slug(args.url)
            ctx.is_helper = True
        else:
            subparsers = parser.add_subparsers(dest="command", required=True)
            g = self.parse(subparsers)
            clone_parser = subparsers.add_parser("clone", help="Clone a repo")
            next(g)
            g.send(clone_parser)
            args = parser.parse_args()
            if args.command != "clone":
                args.func(args)
                exit(0)

            args.is_helper = False
            ctx = g.send(args)
            assert isinstance(ctx, self.classT)

            # ctx = self.parse()
            ctx.is_helper = False
            ctx.command = args.command if hasattr(args, "command") else None

        self.args = ctx

    @abc.abstractmethod
    def stream_revisions(
        self, scenario: Literal["main", "feature"]
    ) -> Generator[U, Any, None]: ...

    def log(self, *args: str, end: str = "\n"):
        print(*args, file=sys.stderr, end=end)
        sys.stderr.flush()

    def debug(*args: object):
        with open(DEBUGFILE, "a") as f:
            print(*args, file=f)

    def send(self, *args: str):
        """Respond with output to git when called as helper"""
        output = " ".join(args)
        print(output)
        self.debug(f"< {output}")
        sys.stdout.flush()

    def progress(self, template: str):
        def f(progress: str | int, done: bool = False):
            output = "\r" + template.format(str(progress))
            if done:
                output += ", done.\n"
            self.log(output, end="")

        return f

    def prepare_main_branch(self, repo: Repo | MemoryRepo, args: T):
        publish_requests: list[BaseRevision] = []

        def iter_pr():
            for pr in self.stream_revisions("main"):
                publish_requests.append(pr)
                yield pr.id()

        def iter_commits():
            try:
                commit = repo.get_object(repo.refs[b"refs/heads/main"])
            except KeyError:
                return

            while commit:
                assert isinstance(commit, Commit)
                message = commit.message.decode()
                title = message.split("\n\n")[0] if "\n\n" in message else message
                description = message.split("\n\n")[1] if "\n\n" in message else None
                try:
                    # There is a bug here, we are introducing bad object into git object store
                    note = Notes(repo.object_store, repo.refs).get_note(commit.id)
                    yield note.decode() if note else None
                except KeyError:
                    self.log(f"Key error for {commit.id.decode()}")
                    yield None

                if not commit.parents:
                    break
                commit = repo.get_object(commit.parents[0])

        def find_ancestor(iterable1, iterable2):
            i = 0
            d1, d2 = {}, {}
            iterator1 = iterable1()
            iterator2 = iterable2()
            while True:
                try:
                    e1 = next(iterator1)
                except StopIteration:
                    return None, i
                try:
                    e2 = next(iterator2)
                except StopIteration:
                    return i, None
                d1[e1] = i
                d2[e2] = i
                if e1 in d2:
                    return i, d2[e1]
                if e2 in d1:
                    return d1[e2], i
                i += 1

        idx_commits, idx_pr = find_ancestor(iter_commits, iter_pr)
        logging.debug(f"find_ancestor: {idx_commits}, {idx_pr}")
        if idx_pr is None:
            raise Exception(
                "No common ancestor found between local main branch and remote publish requests. Are you sure root commit is generated with latest version of Cicero?"
            )

        if idx_commits is None:
            # Repo not initialized, create root node and transform into fast-forward case
            publish_requests = list(self.stream_revisions("main"))
            pr_meta = publish_requests[-1]

            commit_gen = pr_meta.prepare_commit(repo, None)

            repo.refs[b"refs/heads/main"] = commit_gen.id
            parent = commit_gen.id
            n_ahead, n_behind = 0, len(publish_requests) - 1
            hashes = []  # placeholder
        else:
            n_ahead, n_behind = idx_commits, idx_pr
            hashes = []
            commit = repo.get_object(repo.refs[b"refs/heads/main"])
            for i in range(n_ahead):
                assert isinstance(commit, Commit)
                hashes.append(commit.id)
                commit = repo.get_object(commit.parents[0])
            parent = commit.id

        if n_behind == 0:
            repo.refs.set_symbolic_ref(b"HEAD", b"refs/heads/main")
            return

        self.log(f"Applying {n_behind} new publish requests to main branch...")
        progress_download = self.progress("remote: Downloading publish requests: {}")
        i = 0

        while n_behind > 0:
            progress_download(i)
            pr_meta = publish_requests[n_behind - 1]
            commit_gen = pr_meta.prepare_commit(
                repo, parent
            )  # try not to pollute local repo

            if n_ahead == 0:
                if not isinstance(pr_meta.id(), str) or 'bound method' in repr(pr_meta.id()):
                    assert False
                Notes(repo.object_store, repo.refs).set_note(
                    commit_gen.id, f"{pr_meta.id()}".encode()
                )
                repo.refs[b"refs/heads/main"] = commit_gen.id
                parent = commit_gen.id
            else:
                commit_local = repo.get_object(hashes[n_ahead - 1])
                assert isinstance(commit_local, Commit)
                if commit_local.id != commit_gen.id:
                    message = "Cannot fast-forward main branch, please rebase first"
                    message += (
                        f'\nFor commit "{commit_local.message.decode().strip()}":'
                    )
                    hints = []
                    # Generate debugging hints
                    attrs = [
                        "message",
                        # "tree",
                        "author",
                        "committer",
                        "author_time",
                        "commit_time",
                        "author_timezone",
                        "commit_timezone",
                        "parents",
                    ]
                    for attr in attrs:
                        val_local = getattr(commit_local, attr)
                        val_gen = getattr(commit_gen, attr)
                        if val_local != val_gen:
                            # TODO: Also show what is the commit for debug
                            hints.append(
                                f"mismatch in attribute {attr}: {val_local} (local) vs {val_gen} (generated)"
                            )
                    if not hints:
                        assert commit_local.tree != commit_gen.tree
                        for (name1, mode1, sha1), (name2, mode2, sha2) in zip(
                            repo.get_object(commit_local.tree).items(),
                            repo.get_object(commit_gen.tree).items(),
                            strict=True,
                        ):
                            if name1 != name2 or mode1 != mode2 or sha1 != sha2:
                                c1 = repo.get_object(sha1).data.decode()
                                c2 = repo.get_object(sha2).data.decode()
                                self.log(f"C1>>>\n{c1}\n<<<C1")
                                self.log(f"C2>>>\n{c2}\n<<<C2")

                                hints.append(
                                    f"mismatch in tree entry: {name1} {mode1} {sha1.decode()} (local) vs {name2} {mode2} {sha2.decode()} (generated)"
                                )
                    message += "".join(f"\n- {hint}" for hint in hints)
                    raise Exception(message)

                # Otherwise, they are actually same commit, add note
                if not isinstance(pr_meta.id(), str) or 'bound method' in repr(pr_meta.id()):
                    assert False
                Notes(repo.object_store, repo.refs).set_note(
                    commit_gen.id, f"{pr_meta.id()}".encode()
                )
                parent = commit_gen.id
                n_ahead -= 1
            n_behind -= 1
            i += 1
        progress_download(i, done=True)

        repo.refs.set_symbolic_ref(b"HEAD", b"refs/heads/main")

    def prepare_feature_branches(self, repo: Repo | MemoryRepo, args: T):
        if self.feature_branches_prepared:
            return

        prs = self.stream_revisions("feature")
        for i, pr_meta in enumerate(prs):
            repo.refs.set_symbolic_ref(b"HEAD", b"refs/heads/main")
            commit = pr_meta.prepare_commit(repo, repo.head())
            branch_name = pr_meta.gen_branch_name()

            # Hack: poor code practice
            if isinstance(repo, MemoryRepo):
                repo.refs[f"refs/heads/{branch_name}".encode()] = commit.id
            else:
                repo.refs[f"refs/remotes/origin/{branch_name}".encode()] = commit.id

    @abc.abstractmethod
    def get_repo_path(self, args: T) -> str:
        """Override this method to specify the path where the repository should be cloned to."""
        ...

    @abc.abstractmethod
    def parse(
        self, subparsers: SupportsAddParser
    ) -> Generator[T | None, Any, None]: ...

    @abc.abstractmethod
    def on_push(
        self, src: str, dst: str, commit: Commit, forced: bool, local: Repo
    ): ...  # we need to get rid of Repo

    def handle_list(self, local: Repo, remote: MemoryRepo, arg: str | None):
        if arg == "for-push":
            # After deterministic commit generation, no need for special handling
            pass

        for ref, sha in remote.refs.as_dict().items():
            self.send(sha.decode(), ref.decode())

        self.send("@refs/heads/main HEAD")

    def handle_fetch(self, local: Repo, remote: MemoryRepo, shas: list[str]):
        visited = set()  # git store is large, caching can save seconds

        def recurse(sha: bytes, depth=0):
            if sha in visited:
                # log(str(depth), depth * " ", sha.decode(), "already visited")
                return
            visited.add(sha)
            if isinstance(sha, str):
                raise TypeError("sha must be bytes")

            depth += 1

            obj = remote.get_object(sha)
            local.object_store.add_object(obj)
            if isinstance(obj, Commit):
                commit = obj
                # log(str(depth), depth * " ", obj.id.decode(), "new visit: Commit")
                recurse(commit.tree, depth)
                for parent in obj.parents:
                    recurse(parent, depth)
            elif isinstance(obj, Tree):
                # log(str(depth), depth * " ", obj.id.decode(), "new visit: Tree")
                tree = obj
                for name, mode, sha in tree.items():
                    child = remote.get_object(sha)
                    recurse(child.id, depth)

        def handle_one(sha: str):
            recurse(sha.encode())

        for sha in shas:
            handle_one(sha)

        n = len(remote.refs.as_dict()) - 2
        if n > 0:
            self.log(
                f"remote: There are {n} open PRs, run `git branch --all` to find them."
            )

    def handle_push(self, local: Repo, remote: MemoryRepo, push_args: list[str]):
        # TODO: move to config_centre
        # Enforce author and commiter format
        cfg = local.get_config_stack()
        user_name = cfg.get("user", "name")
        user_email = cfg.get("user", "email")
        if user_name != user_email:
            raise Exception(
                "user.name and user.email in git config must be the same to proceed."
            )

        def handle_one(arg: str):
            force = False
            if arg[0] == "+":
                force = True
                arg = arg[1:]
            src, dst = arg.split(":")

            if src == "HEAD":
                self.send("error", dst, "please push from a specific branch")
                return

            if local.refs[b"refs/heads/main"] != remote.refs[b"refs/heads/main"]:
                self.send(
                    "error", dst, "local main branch is not up to date with remote"
                )
                return

            # These checks no longer needed after we adverstise feature branch as main
            # One concern to take note is prevent pushing to PR that overrides change
            # if force:
            #     send("error", dst, "force pushes are not supported")
            #     return
            # # Second layer check: In theory, if "list" tells git client that branch contains latest of remote main, it will reject
            # if repo.refs[b'refs/heads/main'] not in get_reachable_commits(repo.object_store, [repo.refs[src.encode()]]):
            #     send("error", dst, "PR is not based on latest main branch")
            #     return

            commit_id = local.refs[src.encode()]
            commit = local.get_object(commit_id)
            assert isinstance(commit, Commit)

            self.on_push(src, dst, commit, force, local)

        first = True
        for arg in push_args:
            if first:
                first = False
            handle_one(arg)

    def serve(self, local: Repo, remote: MemoryRepo, namespace_id: T):
        self.debug("============Serving============")

        while True:
            line = sys.stdin.readline()
            line = line.strip()
            if not line:
                break

            self.debug(f"> {line}")
            cmd = line.split(maxsplit=1)[0]

            if cmd == "capabilities":
                self.send("list")
                self.send("push")
                self.send("fetch")
                self.send()

            elif cmd == "list":
                arg = None
                if " " in line:
                    arg = line.split(" ", 1)[1]
                self.handle_list(local, remote, arg)
                self.send()

            elif cmd == "fetch":
                batch = [line] + list(iter(lambda: sys.stdin.readline().strip(), ""))
                shas = [line.split()[1] for line in batch]
                self.handle_fetch(local, remote, shas)
                self.send()

            elif cmd == "push":
                batch = [line] + list(iter(lambda: sys.stdin.readline().strip(), ""))
                args = [line.split()[1] for line in batch]
                self.handle_push(local, remote, args)
                self.send()

            else:
                raise Exception(f"Unknown command: {cmd}")

    @final
    def post_clone(self, local: Repo):
        cid = local.refs[b"refs/heads/main"]
        local.refs[b"refs/remotes/origin/main"] = local.refs[b"refs/heads/main"]
        reset(local, mode="hard", treeish=cid)

        config = local.get_config()

        # Add remote with fetch string
        section = (b"remote", b"origin")
        config.set(section, "url", f"cicero://{self.args.generate_url_slug()}")
        config.set(section, "fetch", "+refs/heads/*:refs/remotes/origin/*")
        config.set(section, "fetch", "refs/notes/commits:refs/notes/commits")

        # Set main upstream
        section = (b"branch", b"main")
        config.set(section, "remote", "origin")
        config.set(section, "merge", "refs/heads/main")

        # Don't warn when pushing to open PR
        section = (b"push",)
        config.set(section, "default", "upstream")

        section = (b"core",)
        config.set(section, "hooksPath", "../../hooks")

        with open(local.path + "/.git/config", "wb") as f:
            config.write_to_path()

    @final
    def main(self):
        args = self.args
        if args.is_helper:
            # Invoked via git
            repo_path = os.getcwd()
            local = Repo(repo_path)

            remote = MemoryRepo()
            for sha in local.object_store:
                remote.object_store.add_object(local.object_store[sha])
            if b"refs/notes/commits" in local.refs:
                remote.refs[b"refs/notes/commits"] = local.refs[b"refs/notes/commits"]

            try:
                remote.refs[b"refs/heads/main"] = local.refs[b"refs/heads/main"]
            except KeyError:
                pass
            try:
                remote.refs[b"HEAD"] = remote.refs[b"HEAD"]
            except KeyError:
                pass

            self.prepare_main_branch(remote, args)
            self.prepare_feature_branches(remote, args)
            self.serve(local, remote, args)
        elif args.command == "clone":
            # Invoked for "cloning" the repo
            repo_path = self.get_repo_path(args)
            if os.path.exists(repo_path):
                self.log(
                    f"fatal: destination path '{repo_path}' already exists and is not an empty directory."
                )
                if not DEBUG_MODE:
                    sys.exit(1)
                os.system(f"rm -rf {repo_path}")

            self.log(f"Cloning into '{repo_path}'...")
            os.makedirs(repo_path)
            local = Repo.init(repo_path)

            self.prepare_main_branch(local, args)
            self.prepare_feature_branches(local, args)
            self.post_clone(local)
        else:
            raise Exception(f"Unknown command: {args.command}")

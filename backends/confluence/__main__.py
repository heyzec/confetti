#!/usr/bin/env python3
import argparse
import os
import sys

from backends.confluence.client import ConfluenceClient
from backends.confluence.convert import markdown_to_xhtml, xhtml_to_markdown

try:
    import dotenv
except ImportError:
    dotenv = None  # type: ignore[assignment]


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


def cmd_download(args: argparse.Namespace) -> None:
    xhtml = client.read_page(args.page)

    if args.file.endswith(".md"):
        content = xhtml_to_markdown(xhtml)
    else:
        content = xhtml

    _write(args.file, content)


def cmd_upload(args: argparse.Namespace) -> None:
    raw = _read(args.file)
    if args.file.endswith(".md"):
        xhtml = markdown_to_xhtml(raw)
    else:
        xhtml = raw

    page_id = client._resolve_page_id(args.page)
    page = client.get_metadata(page_id)
    title = page["title"]
    new_version = client.update_page(args.page, title, xhtml)

    print(
        f"Updated '{title}' (page {page_id}) → version {new_version}", file=sys.stderr
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m converter",
        description="Bidirectional Confluence XHTML ↔ Markdown converter.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # xhtml-to-md
    p1 = sub.add_parser("to-md", help="Convert Confluence XHTML → Markdown")
    p1.add_argument("input", metavar="FILE", help="XHTML input file (or - for stdin)")
    p1.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        default="-",
        help="Output file (default: stdout)",
    )
    p1.set_defaults(func=cmd_to_md)

    # md-to-xhtml
    p2 = sub.add_parser("to-xhtml", help="Convert Markdown → XHTML")
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
    p3 = sub.add_parser("download", help="Download a Confluence page to a file")
    p3.add_argument(
        "--page",
        "-p",
        required=True,
        metavar="ID_OR_URL",
        help="Confluence page ID or URL",
    )
    p3.add_argument(
        "file", metavar="FILE", help="Output file (.md triggers Markdown conversion)"
    )
    p3.set_defaults(func=cmd_download)

    # upload
    p4 = sub.add_parser("upload", help="Upload XHTML to a Confluence page")
    p4.add_argument(
        "--page",
        "-p",
        required=True,
        metavar="ID_OR_URL",
        help="Confluence page ID or URL",
    )
    p4.add_argument("file", metavar="FILE", help="XHTML file to upload")
    p4.set_defaults(func=cmd_upload)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    token = os.environ.get("CONFLUENCE_TOKEN")
    if not token:
        raise ValueError("CONFLUENCE_TOKEN environment variable not set")
    base_url = os.environ.get("CONFLUENCE_URL", "https://confluence.shopee.io").rstrip(
        "/"
    )
    global client
    client = ConfluenceClient(base_url=base_url, token=token)

    args.func(args)


if __name__ == "__main__":
    if dotenv is not None:
        dotenv.load_dotenv()
    main()

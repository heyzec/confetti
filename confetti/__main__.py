#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

try:
    import dotenv
except ImportError:
    dotenv = None  # type: ignore[assignment]

from .convert import xhtml_to_ir, markdown_to_ir, ir_to_markdown, ir_to_xhtml


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


def _resolve_page_id(value: str, auth_headers: dict) -> str:
    """Accept a numeric page ID or a Confluence page URL; return the numeric ID."""
    if value.isdigit():
        return value
    req = urllib.request.Request(value, headers=auth_headers)
    try:
        with urllib.request.urlopen(req) as resp:
            final_url = resp.url
    except urllib.error.HTTPError as exc:
        raise ValueError(f"Could not resolve page URL: {exc.code} {exc.reason}") from exc
    parsed = urllib.parse.urlparse(final_url)
    parts = parsed.path.split("/")
    if len(parts) < 4 or parts[1] != "display":
        raise ValueError(f"Could not extract page from resolved URL: {final_url}")
    space_key = parts[2]
    title = urllib.parse.unquote_plus(parts[3])
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    api_url = (
        f"{base_url}/rest/api/content"
        f"?spaceKey={urllib.parse.quote(space_key)}"
        f"&title={urllib.parse.quote(title)}"
    )
    api_req = urllib.request.Request(api_url, headers=auth_headers)
    try:
        with urllib.request.urlopen(api_req) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise ValueError(f"Could not look up page by title: {exc.code} {exc.reason}") from exc
    results = data.get("results", [])
    if not results:
        raise ValueError(f"No page found for space={space_key!r} title={title!r}")
    return results[0]["id"]


def cmd_to_md(args: argparse.Namespace) -> None:
    xhtml = _read(args.input)
    md = ir_to_markdown(xhtml_to_ir(xhtml))
    _write(args.output, md)


def cmd_to_xhtml(args: argparse.Namespace) -> None:
    md = _read(args.input)
    xhtml = ir_to_xhtml(markdown_to_ir(md))
    _write(args.output, xhtml)


def cmd_download(args: argparse.Namespace) -> None:
    token = os.environ.get("CONFLUENCE_TOKEN")
    if not token:
        raise ValueError("CONFLUENCE_TOKEN environment variable not set")

    base_url = os.environ.get("CONFLUENCE_URL", "https://confluence.shopee.io").rstrip("/")
    auth_headers = {"Authorization": f"Bearer {token}"}
    page_id = _resolve_page_id(args.page, auth_headers)

    get_url = f"{base_url}/rest/api/content/{page_id}?expand=body.storage"
    req = urllib.request.Request(get_url, headers=auth_headers)
    try:
        with urllib.request.urlopen(req) as resp:
            page = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise ValueError(f"GET page {page_id} failed: {exc.code} {exc.reason}") from exc

    xhtml = page["body"]["storage"]["value"]

    if args.file.endswith(".md"):
        content = ir_to_markdown(xhtml_to_ir(xhtml))
    else:
        content = xhtml

    _write(args.file, content)


def cmd_upload(args: argparse.Namespace) -> None:
    token = os.environ.get("CONFLUENCE_TOKEN")
    if not token:
        raise ValueError("CONFLUENCE_TOKEN environment variable not set")

    base_url = os.environ.get("CONFLUENCE_URL", "https://confluence.shopee.io").rstrip("/")
    auth_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    page_id = _resolve_page_id(args.page, auth_headers)

    get_url = f"{base_url}/rest/api/content/{page_id}"
    req = urllib.request.Request(get_url, headers=auth_headers)
    try:
        with urllib.request.urlopen(req) as resp:
            page = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise ValueError(f"GET page {page_id} failed: {exc.code} {exc.reason}") from exc

    current_version = page["version"]["number"]
    title = page["title"]

    raw = _read(args.file)
    if args.file.endswith(".md"):
        xhtml = ir_to_xhtml(markdown_to_ir(raw))
    else:
        xhtml = raw

    put_url = f"{base_url}/rest/api/content/{page_id}?expand=body.storage"
    body = json.dumps({
        "version": {"number": current_version + 1},
        "type": "page",
        "title": title,
        "body": {"storage": {"value": xhtml, "representation": "storage"}},
    }).encode()
    req = urllib.request.Request(put_url, data=body, headers=auth_headers, method="PUT")
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        raise ValueError(f"PUT page {page_id} failed: {exc.code} {exc.reason}\n{detail}") from exc

    new_version = result["version"]["number"]
    print(f"Updated '{title}' (page {page_id}) → version {new_version}", file=sys.stderr)


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
    p3.add_argument("--page", "-p", required=True, metavar="ID_OR_URL", help="Confluence page ID or URL")
    p3.add_argument("file", metavar="FILE", help="Output file (.md triggers Markdown conversion)")
    p3.set_defaults(func=cmd_download)

    # upload
    p4 = sub.add_parser("upload", help="Upload XHTML to a Confluence page")
    p4.add_argument("--page", "-p", required=True, metavar="ID_OR_URL", help="Confluence page ID or URL")
    p4.add_argument("file", metavar="FILE", help="XHTML file to upload")
    p4.set_defaults(func=cmd_upload)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if dotenv is not None:
        dotenv.load_dotenv()
    main()

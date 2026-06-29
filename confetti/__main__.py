#!/usr/bin/env python3
import argparse
import sys

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


def cmd_to_md(args: argparse.Namespace) -> None:
    xhtml = _read(args.input)
    md = ir_to_markdown(xhtml_to_ir(xhtml))
    _write(args.output, md)


def cmd_to_xhtml(args: argparse.Namespace) -> None:
    md = _read(args.input)
    xhtml = ir_to_xhtml(markdown_to_ir(md))
    _write(args.output, xhtml)


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
    main()

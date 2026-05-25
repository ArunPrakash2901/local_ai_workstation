#!/usr/bin/env python3
"""Small workstation command bridge for Product Development Lane."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import audit_product_development_lane as audit_tool  # noqa: E402
import build_product_packet as build_tool  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ws product-dev",
        description="Product Development Lane non-executing artifact commands.",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("help", help="Show Product Development Lane help")

    audit = sub.add_parser("audit", help="Audit Product Development Lane artifacts")
    audit.add_argument("--root", default="product_development_lane")

    build = sub.add_parser("build-packet", help="Build product-development artifacts from a READY Discovery queue")
    build.add_argument("--queue", required=True)
    build.add_argument("--output", default="product_development_lane")
    return parser


def render_help() -> str:
    return """Product Development Lane commands
=================================

ws product-dev build-packet --queue <discovery_queue>
  Build non-executing product-development artifacts from a READY Discovery queue.

ws product-dev audit
  Audit Product Development Lane structure and generated artifacts.

ws product-dev help
  Show this help.

Safety boundary:
- no worker prompt execution
- no branch creation or checkout
- no commit, push, or merge
- no model/provider/API/browser calls
"""


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in {None, "help"}:
        print(render_help())
        return 0
    if args.command == "audit":
        result = audit_tool.audit_product_development_lane(Path(args.root))
        print(audit_tool.render_audit(result, Path(args.root)))
        return 0 if result.ok else 1
    if args.command == "build-packet":
        return build_tool.main(["--queue", args.queue, "--output", args.output])
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())


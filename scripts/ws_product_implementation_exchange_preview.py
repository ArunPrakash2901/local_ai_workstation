#!/usr/bin/env python3
"""Deterministic no-write Product Lane implementation exchange preview CLI."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_implementation_exchange_preview import render_implementation_exchange_preview


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview Product Lane implementation exchange handoff (dry-run)."
    )
    parser.add_argument("--product", dest="product_id", help="Existing product id slug.")
    parser.add_argument("--target", help="Exchange target (e.g., codex_cli, gemini_cli).")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run exchange preview without writing files.",
    )
    parser.add_argument(
        "--root",
        default=os.environ.get("WS_HOME", str(Path(__file__).resolve().parents[1])),
        help="Workstation root. Defaults to WS_HOME or script parent root.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()

    if not args.dry_run:
        print("ERROR: --dry-run is required. Exchange preview is currently dry-run only.", file=sys.stderr)
        return 2

    if not args.product_id or not str(args.product_id).strip():
        print("ERROR: --product <product_id> is required.", file=sys.stderr)
        return 2

    if not args.target or not str(args.target).strip():
        print("ERROR: --target <target> is required.", file=sys.stderr)
        return 2

    try:
        report = render_implementation_exchange_preview(
            root, str(args.product_id).strip(), str(args.target).strip()
        )
        print(report.rstrip())
        return 0

    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

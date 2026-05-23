#!/usr/bin/env python3
"""Deterministic no-write Product Lane implementation plan gate CLI."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_implementation_plan import (
    load_implementation_plan_inputs,
    render_implementation_plan_preview,
    write_implementation_plan,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deterministic Product Lane implementation planning gate."
    )
    parser.add_argument("--product", dest="product_id", help="Existing product id slug.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview implementation planning gate without writing files.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Write deterministic implementation planning artifact.",
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

    if not args.product_id or not str(args.product_id).strip():
        print("ERROR: --product <product_id> is required.", file=sys.stderr)
        return 2

    if args.dry_run and args.confirm:
        print("ERROR: --dry-run and --confirm are mutually exclusive.", file=sys.stderr)
        return 2

    if not args.dry_run and not args.confirm:
        print("ERROR: exactly one of --dry-run or --confirm is required.", file=sys.stderr)
        return 2

    try:
        if args.dry_run:
            payload = load_implementation_plan_inputs(root, str(args.product_id).strip())
            output = render_implementation_plan_preview(payload)
            print(output.rstrip())
        else:
            output = write_implementation_plan(root, str(args.product_id).strip(), confirm=True)
            print(output)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except PermissionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except FileExistsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

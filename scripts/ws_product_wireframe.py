#!/usr/bin/env python3
"""Preview deterministic Product Lane wireframes (dry-run only)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_wireframe import load_wireframe_inputs, render_wireframe_preview


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Preview deterministic Product Lane wireframes from product.yaml, "
            "scope_lock.md, and approved prd.md (Phase 2 Slice 4 dry-run only)."
        )
    )
    parser.add_argument(
        "--product",
        dest="product_id",
        help="Existing product id slug.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Required in Phase 2 Slice 4. Write-mode is not implemented.",
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
        print(
            "Write-mode product-wireframe is not implemented in Phase 2 Slice 4. Use --dry-run.",
            file=sys.stderr,
        )
        return 2

    if not args.product_id or not str(args.product_id).strip():
        print("ERROR: --product <product_id> is required.", file=sys.stderr)
        return 2

    try:
        payload = load_wireframe_inputs(root, str(args.product_id).strip())
        output = render_wireframe_preview(
            payload["product_record"],
            payload["scope_lock_text"],
            payload["prd_text"],
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(output.rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

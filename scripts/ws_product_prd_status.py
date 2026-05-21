#!/usr/bin/env python3
"""Show PURE_READ Product Lane PRD status."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_prd_status import get_prd_status, render_prd_status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show Product Lane PRD artifact status (PURE_READ, no writes)."
    )
    parser.add_argument(
        "--product",
        dest="product_id",
        required=True,
        help="Existing product id slug.",
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

    try:
        status_record = get_prd_status(root, str(args.product_id).strip())
        output = render_prd_status(status_record)
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


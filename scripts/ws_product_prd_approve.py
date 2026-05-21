#!/usr/bin/env python3
"""Approve deterministic Product Lane PRD (guarded write)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_prd_approval import approve_prd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Approve deterministic Product Lane PRD metadata after a PASS review. "
            "Writes approval artifact and updates product.yaml."
        )
    )
    parser.add_argument(
        "--product",
        dest="product_id",
        required=True,
        help="Existing product id slug.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required for write-mode PRD approval.",
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

    if not args.confirm:
        print(
            "ERROR: ws product-prd-approve requires --confirm for writes.\n"
            "Run ws product-prd-review --product <product_id> --dry-run and proceed only on PASS.",
            file=sys.stderr,
        )
        return 2

    try:
        result = approve_prd(root, str(args.product_id).strip(), confirm=True)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except FileExistsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    except PermissionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print("PRD APPROVED")
    print(f"Product: {result['product_id']}")
    print(f"Main state: {result['state_before']} -> {result['state_after']}")
    print(f"PRD status: {result['prd_status']}")
    print(f"Reviewed at: {result['prd_reviewed_at']}")
    print(f"Approved at: {result['prd_approved_at']}")
    print("Files written:")
    print(f"- {result['approval_path']}")
    print(f"- {result['product_file']}")
    if result["action_log_updated"]:
        print(f"Action log updated: {result['action_log_path']}")
    else:
        print("Action log updated: skipped (action_log.md not found)")
    print("Models/providers/agents used: no")
    print("Next suggested command: future ws product-wireframe --dry-run or ws product-tech-plan --dry-run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

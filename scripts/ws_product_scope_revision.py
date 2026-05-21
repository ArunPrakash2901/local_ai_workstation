#!/usr/bin/env python3
"""Deterministic Product Lane scope revision preview CLI."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_scope_revision import (
    confirm_scope_revision,
    load_scope_revision_inputs,
    render_revised_scope_preview,
    render_scope_revision_dry_run,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Preview deterministic Product Lane scope revision output from scope_lock.md "
            "and confirmed scope change decisions (dry-run only in this slice)."
        )
    )
    parser.add_argument("--product", dest="product_id", help="Existing product id slug.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deterministic scope revision output without writing files.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Write a versioned revised scope lock and update active scope metadata.",
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

    if args.dry_run == args.confirm:
        print("ERROR: specify exactly one of --dry-run or --confirm.", file=sys.stderr)
        return 2

    if not args.product_id or not str(args.product_id).strip():
        print("ERROR: --product <product_id> is required.", file=sys.stderr)
        return 2

    try:
        if args.dry_run:
            payload = load_scope_revision_inputs(root, str(args.product_id).strip())
            preview = render_revised_scope_preview(
                payload["product_record"],
                payload["scope_lock_text"],
                payload["changes"],
            )
            output = render_scope_revision_dry_run(payload["product_record"], preview)
        else:
            result = confirm_scope_revision(root, str(args.product_id).strip(), confirm=True)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        print(output.rstrip())
        return 0

    print("SCOPE REVISION RECORDED")
    print("=======================")
    print("")
    print(f"Product: {result['product_id']}")
    print(f"State: {result['state_before']} -> {result['state_after']}")
    print(f"active_scope_lock: {result['active_scope_lock']}")
    print(f"active_scope_lock_hash: {result['active_scope_lock_hash']}")
    print(f"active_scope_revision: {result['active_scope_revision']}")
    print(f"scope_change_pending: {result['scope_change_pending']}")
    print(f"prd_status: {result.get('prd_status') or 'UNSET'}")
    print("")
    print("Stale artifacts:")
    stale_artifacts = list(result.get("stale_artifacts", []))
    if stale_artifacts:
        for artifact_name in stale_artifacts:
            print(f"- {artifact_name}")
    else:
        print("- none")
    print("")
    print("Files written:")
    for path in result.get("files_written", []):
        print(f"- {path}")
    print("")
    print("Safety:")
    print("- No models/providers/agents used.")
    print("- Original scope_lock.md remains unchanged.")
    print("- prd.md remains stale until a future PRD regeneration flow runs.")
    print("")
    print("Next suggested command:")
    print("- Future ws product-prd --dry-run or future PRD regeneration flow")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

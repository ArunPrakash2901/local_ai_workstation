#!/usr/bin/env python3
"""Deterministic Product Lane scope change preview/confirm CLI."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_scope_change import (
    confirm_scope_change,
    compute_scope_change_impact,
    load_scope_change_inputs,
    parse_scope_change_text,
    render_scope_change_dry_run,
    validate_scope_change_request,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or record deterministic Product Lane scope change intent from product metadata "
            "and an operator-authored change file."
        )
    )
    parser.add_argument("--product", dest="product_id", help="Existing product id slug.")
    parser.add_argument(
        "--file",
        dest="change_file",
        help="Operator-authored scope change request file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deterministic scope change impact without writing files.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Record scope change decision and update product metadata.",
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

    if not args.change_file or not str(args.change_file).strip():
        print("ERROR: --file <change_file> is required.", file=sys.stderr)
        return 2

    try:
        change_path = Path(args.change_file).expanduser()
        if not change_path.is_absolute():
            change_path = (root / change_path).resolve()
        else:
            change_path = change_path.resolve()
        if not change_path.is_file():
            raise FileNotFoundError(f"change file not found: {change_path}")

        if args.dry_run:
            payload = load_scope_change_inputs(root, str(args.product_id).strip())
            change = validate_scope_change_request(parse_scope_change_text(change_path.read_text(encoding="utf-8")))
            impact = compute_scope_change_impact(payload["product_record"], change, payload["paths"])
            output = render_scope_change_dry_run(payload["product_record"], change, impact)
        else:
            result = confirm_scope_change(root, str(args.product_id).strip(), change_path, confirm=True)
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

    print("SCOPE CHANGE DECISION RECORDED")
    print("==============================")
    print("")
    print(f"Product: {result['product_id']}")
    print(f"Change ID: {result['change_id']}")
    print(f"Field: {result['field']}")
    print(f"State: {result['state_before']} -> {result['state_after']}")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

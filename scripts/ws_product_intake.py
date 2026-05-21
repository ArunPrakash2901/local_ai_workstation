#!/usr/bin/env python3
"""Product Lane Phase 1 intake workflow.

Slice 1:
- --dry-run preview (no writes)

Slice 2:
- --confirm intake start (guarded write)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_intake_questions import (
    get_supported_product_types,
    render_intake_preview,
    validate_question_bank,
)
from product_intake_artifacts import start_intake
from product_registry import get_product_status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview or start Product Lane intake workflow."
    )
    parser.add_argument(
        "--product",
        dest="product_id",
        help="Optional existing product id. Uses product_type from product.yaml.",
    )
    parser.add_argument(
        "--type",
        dest="product_type",
        choices=get_supported_product_types(),
        help="Optional product type when no product_id is provided.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="No-write preview mode.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Start intake and write templates for an existing product.",
    )
    parser.add_argument(
        "--root",
        default=os.environ.get("WS_HOME", str(Path(__file__).resolve().parents[1])),
        help="Workstation root. Defaults to WS_HOME or script parent root.",
    )
    return parser.parse_args()


def _resolve_record_or_type(args: argparse.Namespace, root: Path) -> dict[str, object] | str:
    if not args.product_id and not args.product_type:
        raise ValueError("usage requires either --product <product_id> or --type <product_type>")

    if args.product_id:
        record = get_product_status(root, args.product_id)
        record_type = str(record.get("product_type", "")).strip()
        if not record_type:
            raise ValueError(f"product {args.product_id!r} has no product_type")
        if args.product_type and args.product_type != record_type:
            raise ValueError(
                f"--type {args.product_type!r} does not match product {args.product_id!r} "
                f"type {record_type!r}"
            )
        return record

    return str(args.product_type)


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()

    if args.dry_run and args.confirm:
        print("ERROR: choose either --dry-run or --confirm, not both.", file=sys.stderr)
        return 2

    if not args.dry_run and not args.confirm:
        print(
            "ERROR: specify a mode: --dry-run (preview) or --confirm (start intake).",
            file=sys.stderr,
        )
        return 2

    validation_errors = validate_question_bank()
    if validation_errors:
        print("ERROR: static question bank validation failed:", file=sys.stderr)
        for error in validation_errors:
            print(f"- {error}", file=sys.stderr)
        return 3

    if args.dry_run:
        try:
            payload = _resolve_record_or_type(args, root)
            output = render_intake_preview(payload)
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

    if not args.product_id:
        print(
            "ERROR: --confirm requires --product <product_id>.\n"
            "Use --dry-run with --type for preview-only flows.",
            file=sys.stderr,
        )
        return 2

    if not args.product_id.strip():
        print("ERROR: --product must be non-empty", file=sys.stderr)
        return 2

    try:
        record = get_product_status(root, args.product_id)
        if args.product_type and args.product_type != record.get("product_type"):
            raise ValueError(
                f"--type {args.product_type!r} does not match product {args.product_id!r} "
                f"type {record.get('product_type')!r}"
            )
        result = start_intake(record, root, confirm=True, overwrite=False)
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

    print("INTAKE STARTED")
    print(f"Product: {result['product_id']}")
    print(f"State: {result['state_before']} -> {result['state_after']}")
    print(f"Open questions: {result['open_question_count']}")
    print("Files written:")
    for item in result["files_written"]:
        print(f"- {item}")
    if result["action_log_updated"]:
        print(f"Action log updated: {result['action_log_path']}")
    else:
        print("Action log updated: skipped (action_log.md not found)")
    print("Models/providers/agents used: no")
    print("Next step: answer intake questions and import with ws product-answer-import --confirm.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

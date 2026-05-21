#!/usr/bin/env python3
"""Import operator-provided Product Lane intake answers (guarded write)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from product_answer_import import import_answers
from product_registry import get_product_status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import Product Lane intake answers from a local file and classify "
            "INTAKE_STARTED -> SCOPE_READY or CLARIFICATION_NEEDED."
        )
    )
    parser.add_argument(
        "--product",
        dest="product_id",
        required=True,
        help="Existing product id slug.",
    )
    parser.add_argument(
        "--file",
        dest="answers_file",
        required=True,
        help="Path to answers text file using 'question_id: answer text' lines.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required for write-mode import.",
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
            "ERROR: ws product-answer-import requires --confirm for writes.\n"
            "This command imports operator-provided answers and updates product state.",
            file=sys.stderr,
        )
        return 2

    answers_path = Path(args.answers_file).expanduser().resolve()
    if not answers_path.is_file():
        print(f"ERROR: answers file not found: {answers_path}", file=sys.stderr)
        return 1

    try:
        answers_text = answers_path.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"ERROR: could not read answers file: {exc}", file=sys.stderr)
        return 2

    try:
        product_record = get_product_status(root, args.product_id)
        result = import_answers(
            product_record,
            root,
            answers_text,
            confirm=True,
            overwrite=False,
        )
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

    print("ANSWERS IMPORTED")
    print(f"Product: {result['product_id']}")
    print(f"State: {result['state_before']} -> {result['state_after']}")
    print(f"Open questions: {result['open_question_count']}")
    print("Unresolved required/blocking/privacy:")
    print(f"- required: {len(result['unresolved_required'])}")
    print(f"- blocking: {len(result['unresolved_blocking'])}")
    print(f"- privacy: {len(result['unresolved_privacy'])}")
    if result["unresolved_all"]:
        print("Unresolved question IDs:")
        for question_id in result["unresolved_all"]:
            print(f"- {question_id}")
    print("Files written:")
    print(f"- {result['answers_path']}")
    print(f"- {result['product_file']}")
    if result["action_log_updated"]:
        print(f"Action log updated: {result['action_log_path']}")
    else:
        print("Action log updated: skipped (action_log.md not found)")
    print("Models/providers/agents used: no")
    if result["state_after"] == "SCOPE_READY":
        print("Next suggested command: ws product-scope --product <product_id> --dry-run")
    else:
        print("Next suggested step: update unresolved answers and re-import.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

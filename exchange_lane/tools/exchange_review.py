#!/usr/bin/env python3
"""Exchange Lane operator review queue tools."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import exchange_packet  # noqa: E402
import exchange_import_result  # noqa: E402
import exchange_validate_result  # noqa: E402
import exchange_loop_decision  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from workstation_ids import check_path_length  # noqa: E402

DEFAULT_ROOT = Path(__file__).resolve().parents[1]

REVIEW_SCOPES = {
    "summary": "VALIDATED_FOR_SUMMARY",
    "repair": "VALIDATED_FOR_REPAIR_LOOP",
    "patch-proposal": "VALIDATED_FOR_PATCH_PROPOSAL",
    "test-run": "VALIDATED_FOR_TEST_RUN",
}


class ExchangeReviewError(Exception):
    """Operator-facing exchange review error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ExchangeReviewError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ExchangeReviewError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ExchangeReviewError(f"JSON root must be an object: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    length_check = check_path_length(path)
    if length_check["status"] == "fail":
        raise ExchangeReviewError(f"refusing to write overlong path: {length_check['message']} -> {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def iter_json(root: Path, folder: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    folder_path = root / folder
    if not folder_path.exists():
        return records
    for path in sorted(folder_path.glob("*.json")):
        try:
            data = load_json(path)
        except ExchangeReviewError:
            continue
        data["_path"] = str(path)
        records.append(data)
    return records


def review_list(root: Path) -> list[dict[str, Any]]:
    root = root.resolve()
    results = iter_json(root, "result_packets")
    validations = {v.get("result_id"): v for v in iter_json(root, "result_validations")}
    decisions = {d.get("result_id"): d for d in iter_json(root, "loop_decisions")}

    review_items = []
    for res in results:
        rid = res.get("result_id")
        status = res.get("result_status")
        val = validations.get(rid, {})
        v_status = val.get("validation_status", "PENDING")
        dec = decisions.get(rid, {})
        d_val = dec.get("decision", "PENDING")

        needs_attention = False
        action = "none"

        if status == "IMPORTED_PENDING_REVIEW":
            needs_attention = True
            action = "validate or review result"
        elif v_status == "VALIDATION_BLOCKED":
            needs_attention = True
            action = "inspect validation block"
        elif d_val == "BLOCKED_NEEDS_OPERATOR":
            needs_attention = True
            action = "manual decision required"
        elif d_val == "COMPLETED_PENDING_DAILY_REVIEW":
            needs_attention = True
            action = "daily review/checkpoint"
        elif status == "READY_FOR_OPERATOR_REVIEW":
            needs_attention = True
            action = "review promoted result"

        if needs_attention:
            item = {
                "result_id": rid,
                "result_status": status,
                "trusted": res.get("trusted", False),
                "validation_id": val.get("validation_id"),
                "validation_status": v_status,
                "loop_decision_id": dec.get("loop_decision_id"),
                "loop_decision": d_val,
                "adapter": res.get("adapter_id"),
                "dispatch_plan_id": res.get("source_dispatch_plan_id"),
                "created_at": res.get("imported_at"),
                "recommended_action": action,
            }
            review_items.append(item)

    return review_items


def review_result(root: Path, result_id: str) -> dict[str, Any]:
    root = root.resolve()
    res_path = exchange_import_result.result_packet_path(root, result_id)
    res = load_json(res_path)

    rid = res.get("result_id")
    validations = {v.get("result_id"): v for v in iter_json(root, "result_validations")}
    decisions = {d.get("result_id"): d for d in iter_json(root, "loop_decisions")}

    val = validations.get(rid, {})
    dec = decisions.get(rid, {})

    artifacts = res.get("output_artifacts", {})

    view = {
        "result_id": rid,
        "result_status": res.get("result_status"),
        "lineage": {
            "source_packet": res.get("source_packet"),
            "dispatch_plan": res.get("source_dispatch_plan"),
            "session": res.get("source_session_id"),
            "assignment": res.get("source_assignment_id"),
        },
        "adapter": res.get("adapter_id"),
        "artifacts": {
            "capture_manifest": res.get("source_capture_manifest"),
            "stdout": artifacts.get("raw_output"),
            "stderr": artifacts.get("operator_report"),  # stderr is often in operator report or raw
        },
        "validation": {
            "status": val.get("validation_status", "PENDING"),
            "id": val.get("validation_id"),
        },
        "loop_decision": {
            "decision": dec.get("decision", "PENDING"),
            "id": dec.get("loop_decision_id"),
            "reasons": dec.get("decision_reasons", []),
        },
        "blockers": res.get("blockers", []),
        "safety": {
            "model_called": res.get("model_or_provider_called"),
            "app_modified": res.get("app_source_modified"),
        },
        "next_action": "review-accept or review-reject",
    }
    return view


def review_accept(root: Path, result_id: str, scope: str) -> Path:
    if scope not in REVIEW_SCOPES:
        raise ExchangeReviewError(f"invalid scope: {scope}. Allowed: {list(REVIEW_SCOPES.keys())}")

    root = root.resolve()
    res_path = exchange_import_result.result_packet_path(root, result_id)
    res = load_json(res_path)

    if res.get("result_status") == "REJECTED_BY_POLICY":
        raise ExchangeReviewError("cannot accept a rejected result")

    validations = {v.get("result_id"): v for v in iter_json(root, "result_validations")}
    val = validations.get(result_id, {})
    v_status = val.get("validation_status")

    if v_status == "VALIDATION_BLOCKED" and scope not in ("summary", "repair"):
        raise ExchangeReviewError(
            f"refusing to promote BLOCKED result to {scope}; only 'summary' or 'repair' allowed for blocked results"
        )

    res["result_status"] = f"ACCEPTED_FOR_{scope.upper().replace('-', '_')}"
    res["review_scope"] = scope
    res["promotion_status"] = REVIEW_SCOPES[scope]
    res["reviewed_by"] = "operator"
    res["reviewed_at"] = utc_now()
    res["human_review_required"] = False

    write_json(res_path, res)
    return res_path


def review_reject(root: Path, result_id: str, reason: str) -> Path:
    if not reason.strip():
        raise ExchangeReviewError("reject requires a reason")

    root = root.resolve()
    res_path = exchange_import_result.result_packet_path(root, result_id)
    res = load_json(res_path)

    res["result_status"] = "REJECTED_BY_POLICY"
    res["rejection_reason"] = reason
    res["reviewed_by"] = "operator"
    res["reviewed_at"] = utc_now()
    res["human_review_required"] = False

    write_json(res_path, res)
    return res_path


def review_checkpoint(root: Path) -> Path:
    root = root.resolve()
    results = iter_json(root, "result_packets")
    validations = iter_json(root, "result_validations")
    decisions = iter_json(root, "loop_decisions")

    status_counts = Counter(str(r.get("result_status")) for r in results)
    decision_counts = Counter(str(d.get("decision")) for d in decisions)

    now = utc_now()
    stamp = now.replace(":", "").replace("-", "").split(".")[0].replace("T", "_")
    report_id = f"review_checkpoint_{stamp}"
    report_dir = root / "review_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{report_id}.md"

    lines = [
        f"# Exchange Review Checkpoint: {now}",
        "",
        "## Summary",
        f"- Total Results: {len(results)}",
        f"- Total Validations: {len(validations)}",
        f"- Total Decisions: {len(decisions)}",
        "",
        "## Review Statuses",
    ]
    for status in sorted(status_counts):
        lines.append(f"- {status}: {status_counts[status]}")

    lines.extend([
        "",
        "## Loop Decisions",
    ])
    for dec in sorted(decision_counts):
        lines.append(f"- {dec}: {decision_counts[dec]}")

    lines.extend([
        "",
        "## Next Safe Action",
        "- command: ws workstation status",
        "- reason: check global readiness baseline.",
    ])

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def cmd_review_list(args: argparse.Namespace) -> int:
    items = review_list(Path(args.root))
    if not items:
        print("review queue empty")
        return 0
    print("exchange review queue:")
    for item in items:
        print(
            f"- {item['result_id']} | status={item['result_status']} | decision={item['loop_decision']} | action={item['recommended_action']}"
        )
    return 0


def cmd_review_result(args: argparse.Namespace) -> int:
    view = review_result(Path(args.root), args.result_id)
    print(json.dumps(view, indent=2, sort_keys=True))
    return 0


def cmd_review_accept(args: argparse.Namespace) -> int:
    if not args.confirm:
        raise ExchangeReviewError("review-accept requires --confirm")
    path = review_accept(Path(args.root), args.result_id, args.scope)
    print(f"result accepted and promoted: {path}")
    return 0


def cmd_review_reject(args: argparse.Namespace) -> int:
    if not args.confirm:
        raise ExchangeReviewError("review-reject requires --confirm")
    path = review_reject(Path(args.root), args.result_id, args.reason)
    print(f"result rejected: {path}")
    return 0


def cmd_review_checkpoint(args: argparse.Namespace) -> int:
    path = review_checkpoint(Path(args.root))
    print(f"review checkpoint report written: {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Exchange Lane operator review queue tools.")
    sub = parser.add_subparsers(dest="command")

    help_parser = sub.add_parser("help", help="Show command help.")
    help_parser.set_defaults(func=lambda _args: (print(parser.format_help()), 0)[1])

    list_cmd = sub.add_parser("review-list", help="List items needing operator attention.")
    list_cmd.add_argument("--root", default=str(DEFAULT_ROOT))
    list_cmd.set_defaults(func=cmd_review_list)

    res_cmd = sub.add_parser("review-result", help="concise operator review view for one result.")
    res_cmd.add_argument("--result-id", required=True)
    res_cmd.add_argument("--root", default=str(DEFAULT_ROOT))
    res_cmd.set_defaults(func=cmd_review_result)

    accept = sub.add_parser("review-accept", help="Record operator acceptance for a bounded scope.")
    accept.add_argument("--result-id", required=True)
    accept.add_argument("--scope", required=True, choices=sorted(REVIEW_SCOPES.keys()))
    accept.add_argument("--confirm", action="store_true")
    accept.add_argument("--root", default=str(DEFAULT_ROOT))
    accept.set_defaults(func=cmd_review_accept)

    reject = sub.add_parser("review-reject", help="Record operator rejection.")
    reject.add_argument("--result-id", required=True)
    reject.add_argument("--reason", required=True)
    reject.add_argument("--confirm", action="store_true")
    reject.add_argument("--root", default=str(DEFAULT_ROOT))
    reject.set_defaults(func=cmd_review_reject)

    checkpoint = sub.add_parser("review-checkpoint", help="Generate a review summary report.")
    checkpoint.add_argument("--root", default=str(DEFAULT_ROOT))
    checkpoint.set_defaults(func=cmd_review_checkpoint)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        print(parser.format_help())
        return 0
    func = getattr(args, "func", None)
    if func is None:
        print(parser.format_help())
        return 0
    try:
        return int(func(args))
    except (ExchangeReviewError, exchange_import_result.ImportResultError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

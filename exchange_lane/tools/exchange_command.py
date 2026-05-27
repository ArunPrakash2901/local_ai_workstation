#!/usr/bin/env python3
"""Exchange Lane command surface (non-executing)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import audit_exchange_lane  # noqa: E402
import exchange_dispatch_plan  # noqa: E402
import exchange_fake_dispatch  # noqa: E402
import exchange_import_result  # noqa: E402
import exchange_loop_decision  # noqa: E402
import exchange_packet  # noqa: E402
import exchange_real_dispatch  # noqa: E402
import exchange_review  # noqa: E402
import exchange_validate_result  # noqa: E402


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = DEFAULT_ROOT.parents[0]

ROUTING_TARGETS = ["codex_cli", "gemini_cli", "ollama_local", "powershell_manual", "wsl_manual"]


def cmd_help(_args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    print(parser.format_help())
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    return audit_exchange_lane.main(["--root", args.root])


def cmd_packet_list(args: argparse.Namespace) -> int:
    return exchange_packet.main(["packet-list", "--root", args.root])


def cmd_packet_status(args: argparse.Namespace) -> int:
    return exchange_packet.main(
        ["packet-status", "--root", args.root, "--packet-id", args.packet_id]
    )


def cmd_adapter_list(_args: argparse.Namespace) -> int:
    adapters = list(ROUTING_TARGETS)
    runtime_profiles = REPO_ROOT / "runtime_lane" / "adapters"
    if runtime_profiles.exists():
        for path in sorted(runtime_profiles.glob("*_profile.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            adapter_id = data.get("adapter_id")
            if isinstance(adapter_id, str) and adapter_id and adapter_id not in adapters:
                adapters.append(adapter_id)
    print("exchange routing targets:")
    for item in adapters:
        print(f"- {item}")
    return 0


def cmd_approve_planning(args: argparse.Namespace) -> int:
    return exchange_packet.main(
        [
            "approve-planning",
            "--root",
            args.root,
            "--packet-id",
            args.packet_id,
            "--note",
            args.note,
        ]
    )


def cmd_dispatch_plan(args: argparse.Namespace) -> int:
    argv = [
        "plan",
        "--root",
        args.root,
        "--runtime-root",
        str(REPO_ROOT / "runtime_lane"),
        "--packet-id",
        args.packet_id,
        "--session-id",
        args.session_id,
        "--assignment-id",
        args.assignment_id,
    ]
    if args.write_report:
        argv.append("--write-report")
    if args.mark_dispatch_planned:
        argv.append("--mark-dispatch-planned")
    return exchange_dispatch_plan.main(argv)


def cmd_dispatch_plan_list(args: argparse.Namespace) -> int:
    return exchange_dispatch_plan.main(["plan-list", "--root", args.root])


def cmd_dispatch_plan_status(args: argparse.Namespace) -> int:
    return exchange_dispatch_plan.main(
        ["plan-status", "--root", args.root, "--dispatch-plan-id", args.dispatch_plan_id]
    )


def cmd_fake_dispatch(args: argparse.Namespace) -> int:
    argv = ["fake-dispatch", "--root", args.root, "--dispatch-plan-id", args.dispatch_plan_id]
    if args.confirm:
        argv.append("--confirm")
    return exchange_fake_dispatch.main(argv)


def cmd_real_dispatch(args: argparse.Namespace) -> int:
    argv = [
        "dispatch",
        "--root",
        args.root,
        "--runtime-root",
        str(REPO_ROOT / "runtime_lane"),
        "--dispatch-plan-id",
        args.dispatch_plan_id,
    ]
    if args.dry_run:
        argv.append("--dry-run")
    if args.confirm:
        argv.append("--confirm")
    return exchange_real_dispatch.main(argv)


def cmd_import_result(args: argparse.Namespace) -> int:
    argv = ["import-result", "--root", args.root, "--capture-manifest", args.capture_manifest]
    if args.confirm:
        argv.append("--confirm")
    return exchange_import_result.main(argv)


def result_packets(root: Path) -> list[dict[str, object]]:
    packets: list[dict[str, object]] = []
    for path in sorted((root / "result_packets").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data["_path"] = str(path)
            packets.append(data)
    return packets


def cmd_result_list(args: argparse.Namespace) -> int:
    results = result_packets(Path(args.root))
    if not results:
        print("no result packets")
        return 0
    print("result packets:")
    for result in results:
        print(
            f"- {result.get('result_id', '')} | packet={result.get('source_packet_id', '')} | "
            f"dispatch_plan={result.get('source_dispatch_plan_id', '')} | status={result.get('result_status', '')} | "
            f"trusted={result.get('trusted', '')}"
        )
    return 0


def cmd_result_status(args: argparse.Namespace) -> int:
    try:
        result_id = exchange_import_result.require_id(args.result_id, "result_id")
    except exchange_import_result.ImportResultError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    path = exchange_import_result.result_packet_path(Path(args.root), result_id)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"error: result packet not found: {result_id}", file=sys.stderr)
        return 1
    print(json.dumps(data, indent=2, sort_keys=True))
    return 0


def cmd_validate_result(args: argparse.Namespace) -> int:
    return exchange_validate_result.main(
        ["validate-result", "--root", args.root, "--result-id", args.result_id]
    )


def cmd_validation_status(args: argparse.Namespace) -> int:
    return exchange_validate_result.main(
        ["validation-status", "--root", args.root, "--validation-id", args.validation_id]
    )


def cmd_decide_loop(args: argparse.Namespace) -> int:
    return exchange_loop_decision.main(
        ["decide", "--root", args.root, "--validation-id", args.validation_id]
    )


def cmd_loop_status(args: argparse.Namespace) -> int:
    return exchange_loop_decision.main(["loop-status", "--root", args.root])


def cmd_repair_plan(args: argparse.Namespace) -> int:
    return exchange_loop_decision.main(
        ["repair-plan", "--root", args.root, "--loop-decision-id", args.loop_decision_id]
    )


def cmd_review_list(args: argparse.Namespace) -> int:
    return exchange_review.main(["review-list", "--root", args.root])


def cmd_review_result(args: argparse.Namespace) -> int:
    return exchange_review.main(["review-result", "--root", args.root, "--result-id", args.result_id])


def cmd_review_accept(args: argparse.Namespace) -> int:
    argv = ["review-accept", "--root", args.root, "--result-id", args.result_id, "--scope", args.scope]
    if args.confirm:
        argv.append("--confirm")
    return exchange_review.main(argv)


def cmd_review_reject(args: argparse.Namespace) -> int:
    argv = ["review-reject", "--root", args.root, "--result-id", args.result_id, "--reason", args.reason]
    if args.confirm:
        argv.append("--confirm")
    return exchange_review.main(argv)


def cmd_review_checkpoint(args: argparse.Namespace) -> int:
    return exchange_review.main(["review-checkpoint", "--root", args.root])


def cmd_status(args: argparse.Namespace) -> int:
    root = Path(args.root)
    packets = exchange_packet.list_packets(root)
    dispatch_plans = exchange_dispatch_plan.list_plans(root)
    status_counts = Counter(str(p.get("packet_status", "UNKNOWN")) for p in packets)
    dispatch_plan_counts = Counter(str(p.get("planned_status", "UNKNOWN")) for p in dispatch_plans)
    blocked = [p for p in packets if p.get("packet_status") == "BLOCKED"]
    result_packets = list((root / "result_packets").glob("*.json"))

    print("Exchange Lane Status")
    print("====================")
    print(f"root: {root}")
    print(f"packet_count: {len(packets)}")
    for key in sorted(status_counts):
        print(f"- {key}: {status_counts[key]}")
    print(f"dispatch_plan_count: {len(dispatch_plans)}")
    for key in sorted(dispatch_plan_counts):
        print(f"- dispatch_plan {key}: {dispatch_plan_counts[key]}")
    print(f"result_packet_count: {len(result_packets)}")
    print(f"blocked_packet_count: {len(blocked)}")
    print(f"known_adapter_count: {len(ROUTING_TARGETS)}")
    if blocked:
        print("blocked packets:")
        for pkt in blocked:
            print(f"- {pkt.get('packet_id', '')}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Exchange Lane command interface (non-executing).")
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("help", help="Show Exchange Lane help.")
    sub.add_parser("audit", help="Audit Exchange Lane metadata.")
    sub.add_parser("status", help="Show packet and result summary.")
    sub.add_parser("packet-list", help="List packets.")
    packet_status = sub.add_parser("packet-status", help="Show one packet.")
    packet_status.add_argument("--packet-id", required=True)
    approve_planning = sub.add_parser("approve-planning", help="Approve one packet for dispatch planning.")
    approve_planning.add_argument("--packet-id", required=True)
    approve_planning.add_argument("--note", required=True)
    dispatch_plan = sub.add_parser("dispatch-plan", help="Create dispatch planning metadata only.")
    dispatch_plan.add_argument("--packet-id", required=True)
    dispatch_plan.add_argument("--session-id", required=True)
    dispatch_plan.add_argument("--assignment-id", required=True)
    dispatch_plan.add_argument("--write-report", action="store_true")
    dispatch_plan.add_argument("--mark-dispatch-planned", action="store_true")
    dispatch_plan_list = sub.add_parser("dispatch-plan-list", help="List dispatch plan artifacts.")
    dispatch_plan_status = sub.add_parser("dispatch-plan-status", help="Show one dispatch plan artifact.")
    dispatch_plan_status.add_argument("--dispatch-plan-id", required=True)
    fake_dispatch = sub.add_parser("fake-dispatch", help="Write fake dispatch result capture artifacts.")
    fake_dispatch.add_argument("--dispatch-plan-id", required=True)
    fake_dispatch.add_argument("--confirm", action="store_true")
    real_dispatch = sub.add_parser("real-dispatch", help="Dry-run or execute guarded CLI dispatch.")
    real_dispatch.add_argument("--dispatch-plan-id", required=True)
    real_dispatch.add_argument("--dry-run", action="store_true")
    real_dispatch.add_argument("--confirm", action="store_true")
    import_result = sub.add_parser("import-result", help="Import a result capture as an untrusted result packet.")
    import_result.add_argument("--capture-manifest", required=True)
    import_result.add_argument("--confirm", action="store_true")
    sub.add_parser("result-list", help="List result packets.")
    result_status = sub.add_parser("result-status", help="Show one result packet.")
    result_status.add_argument("--result-id", required=True)
    validate_result = sub.add_parser("validate-result", help="Validate an imported result packet.")
    validate_result.add_argument("--result-id", required=True)
    validation_status = sub.add_parser("validation-status", help="Show one result validation record.")
    validation_status.add_argument("--validation-id", required=True)
    decide_loop = sub.add_parser("decide-loop", help="Create a loop decision from a validation record.")
    decide_loop.add_argument("--validation-id", required=True)
    sub.add_parser("loop-status", help="Summarize validations and loop decisions.")
    repair_plan = sub.add_parser("repair-plan", help="Create metadata-only repair packet when repair is allowed.")
    repair_plan.add_argument("--loop-decision-id", required=True)
    sub.add_parser("adapter-list", help="List routing adapters.")

    sub.add_parser("review-list", help="List Exchange items needing operator attention.")

    review_result_cmd = sub.add_parser("review-result", help="Show concise operator review view for one result.")
    review_result_cmd.add_argument("--result-id", required=True)

    review_accept = sub.add_parser("review-accept", help="Record operator acceptance for a bounded scope.")
    review_accept.add_argument("--result-id", required=True)
    review_accept.add_argument("--scope", required=True, choices=["summary", "repair", "patch-proposal", "test-run"])
    review_accept.add_argument("--confirm", action="store_true")

    review_reject = sub.add_parser("review-reject", help="Record operator rejection.")
    review_reject.add_argument("--result-id", required=True)
    review_reject.add_argument("--reason", required=True)
    review_reject.add_argument("--confirm", action="store_true")

    sub.add_parser("review-checkpoint", help="Generate a review summary report.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command or "help"
    if command == "help":
        return cmd_help(args, parser)
    if command == "audit":
        return cmd_audit(args)
    if command == "status":
        return cmd_status(args)
    if command == "packet-list":
        return cmd_packet_list(args)
    if command == "packet-status":
        return cmd_packet_status(args)
    if command == "approve-planning":
        return cmd_approve_planning(args)
    if command == "dispatch-plan":
        return cmd_dispatch_plan(args)
    if command == "dispatch-plan-list":
        return cmd_dispatch_plan_list(args)
    if command == "dispatch-plan-status":
        return cmd_dispatch_plan_status(args)
    if command == "fake-dispatch":
        return cmd_fake_dispatch(args)
    if command == "real-dispatch":
        return cmd_real_dispatch(args)
    if command == "import-result":
        return cmd_import_result(args)
    if command == "result-list":
        return cmd_result_list(args)
    if command == "result-status":
        return cmd_result_status(args)
    if command == "validate-result":
        return cmd_validate_result(args)
    if command == "validation-status":
        return cmd_validation_status(args)
    if command == "decide-loop":
        return cmd_decide_loop(args)
    if command == "loop-status":
        return cmd_loop_status(args)
    if command == "repair-plan":
        return cmd_repair_plan(args)
    if command == "adapter-list":
        return cmd_adapter_list(args)
    if command == "review-list":
        return cmd_review_list(args)
    if command == "review-result":
        return cmd_review_result(args)
    if command == "review-accept":
        return cmd_review_accept(args)
    if command == "review-reject":
        return cmd_review_reject(args)
    if command == "review-checkpoint":
        return cmd_review_checkpoint(args)

    print(parser.format_help())
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

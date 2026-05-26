#!/usr/bin/env python3
"""Exchange Lane fake dispatch capture writer.

This tool simulates adapter output from an approved dispatch plan without running
any real CLI, model, provider, browser, terminal, or git operation.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import exchange_dispatch_plan  # noqa: E402
import exchange_packet  # noqa: E402


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class FakeDispatchError(Exception):
    """Operator-facing fake dispatch error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def require_id(value: str, label: str) -> str:
    if not value or not ID_RE.fullmatch(value):
        raise FakeDispatchError(f"{label} must use letters, numbers, '.', '_' or '-' and cannot be empty")
    return value


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FakeDispatchError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise FakeDispatchError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise FakeDispatchError(f"JSON root must be an object: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_raw_output(packet_id: str, dispatch_plan_id: str, target_adapter: str) -> str:
    return "\n".join(
        [
            "# Fake Dispatch Output",
            "",
            f"- packet_id: `{packet_id}`",
            f"- dispatch_plan_id: `{dispatch_plan_id}`",
            f"- target_adapter: `{target_adapter}`",
            "- fake_execution: `true`",
            "- real_cli_execution: `false`",
            "",
            "This is deterministic fake output for the MVP dispatch/import loop.",
            "No Codex, Gemini, Ollama, browser, terminal, provider, worker prompt, or git operation ran.",
            "",
        ]
    )


def render_validation() -> str:
    return "\n".join(
        [
            "# Fake Dispatch Validation",
            "",
            "- validation_status: `FAKE_NOT_EXECUTED`",
            "- trusted: `false`",
            "- human_review_required: `true`",
            "- files_created: `[]`",
            "- files_modified: `[]`",
            "- commands_run: `[]`",
            "- tests_run: `[]`",
            "",
            "This validation summary only proves the fake capture format.",
            "It does not prove implementation correctness.",
            "",
        ]
    )


def render_operator_report(packet_id: str, dispatch_plan_id: str) -> str:
    return "\n".join(
        [
            "# Fake Dispatch Operator Report",
            "",
            f"- packet_id: `{packet_id}`",
            f"- dispatch_plan_id: `{dispatch_plan_id}`",
            "- result_trusted: `false`",
            "- human_review_required: `true`",
            "",
            "No real CLI, model, provider, browser, terminal, worker prompt, branch, commit, push, or merge occurred.",
            "Importing this capture will create an untrusted Exchange result packet for review only.",
            "",
        ]
    )


def fake_dispatch(root: Path, dispatch_plan_id: str) -> Path:
    root = root.resolve()
    dispatch_plan_id = require_id(dispatch_plan_id, "dispatch_plan_id")
    plan_path = exchange_dispatch_plan.dispatch_plan_path(root, dispatch_plan_id)
    plan = load_json(plan_path)
    if plan.get("planned_status") != "PLANNED_NOT_DISPATCHED":
        raise FakeDispatchError("fake-dispatch requires planned_status PLANNED_NOT_DISPATCHED")

    packet_id = require_id(str(plan.get("packet_id", "")), "packet_id")
    packet_path = Path(str(plan.get("packet_path", "")))
    if not packet_path.is_file():
        packet_path = exchange_packet.packet_path(root, packet_id)
    if not packet_path.is_file():
        raise FakeDispatchError(f"linked exchange packet missing: {packet_id}")

    source_artifact_path = str(plan.get("source_artifact_path", ""))
    source_artifact_exists = bool(source_artifact_path and Path(source_artifact_path).exists())
    target_adapter = str(plan.get("target_adapter", ""))
    capture_dir = root / "outbox" / packet_id / dispatch_plan_id
    capture_manifest_path = capture_dir / "capture_manifest.json"
    if capture_manifest_path.exists():
        raise FakeDispatchError(f"capture already exists: {capture_manifest_path}")

    raw_output_path = capture_dir / "raw_output.md"
    parsed_result_path = capture_dir / "parsed_result.json"
    validation_path = capture_dir / "validation.md"
    operator_report_path = capture_dir / "operator_report.md"

    parsed_result = {
        "result_summary": "Fake dispatch result for MVP loop validation; no worker prompt was executed.",
        "files_created": [],
        "files_modified": [],
        "commands_run": [],
        "tests_run": [],
        "validation_status": "FAKE_NOT_EXECUTED",
        "blockers": [],
        "human_review_required": True,
        "trusted": False,
    }
    capture_id = f"{packet_id}__{dispatch_plan_id}__fake_capture"
    manifest = {
        "capture_id": capture_id,
        "packet_id": packet_id,
        "dispatch_plan_id": dispatch_plan_id,
        "source_dispatch_plan": str(plan_path.resolve()),
        "source_packet": str(packet_path.resolve()),
        "target_adapter": target_adapter,
        "fake_execution": True,
        "real_cli_execution": False,
        "created_at": utc_now(),
        "raw_output_path": str(raw_output_path.resolve()),
        "parsed_result_path": str(parsed_result_path.resolve()),
        "validation_path": str(validation_path.resolve()),
        "operator_report_path": str(operator_report_path.resolve()),
        "execution_occurred": False,
        "model_or_provider_called": False,
        "terminal_started": False,
        "branch_created": False,
        "commit_performed": False,
        "push_performed": False,
        "merge_performed": False,
        "app_source_modified": False,
        "import_status": "NOT_IMPORTED",
        "generated_by": "exchange_fake_dispatch.py",
        "source_artifact_path": source_artifact_path,
        "source_artifact_exists": source_artifact_exists,
    }

    capture_dir.mkdir(parents=True, exist_ok=True)
    raw_output_path.write_text(render_raw_output(packet_id, dispatch_plan_id, target_adapter), encoding="utf-8")
    write_json(parsed_result_path, parsed_result)
    validation_path.write_text(render_validation(), encoding="utf-8")
    operator_report_path.write_text(render_operator_report(packet_id, dispatch_plan_id), encoding="utf-8")
    write_json(capture_manifest_path, manifest)
    return capture_manifest_path


def cmd_fake_dispatch(args: argparse.Namespace) -> int:
    if not args.confirm:
        raise FakeDispatchError("fake-dispatch requires --confirm")
    manifest_path = fake_dispatch(Path(args.root), args.dispatch_plan_id)
    print(f"fake dispatch capture written: {manifest_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Exchange fake dispatch capture writer.")
    sub = parser.add_subparsers(dest="command")

    help_parser = sub.add_parser("help", help="Show command help.")
    help_parser.set_defaults(func=lambda _args: (print(parser.format_help()), 0)[1])

    fake = sub.add_parser("fake-dispatch", help="Write fake dispatch result capture artifacts.")
    fake.add_argument("--dispatch-plan-id", required=True)
    fake.add_argument("--root", default=str(DEFAULT_ROOT))
    fake.add_argument("--confirm", action="store_true")
    fake.set_defaults(func=cmd_fake_dispatch)
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
    except (FakeDispatchError, exchange_dispatch_plan.DispatchPlanError, exchange_packet.ExchangePacketError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

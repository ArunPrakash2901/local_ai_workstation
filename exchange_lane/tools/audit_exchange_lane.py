#!/usr/bin/env python3
"""Audit Exchange Lane metadata without execution."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from pathlib import PureWindowsPath
from typing import Any

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import exchange_packet  # noqa: E402
import exchange_dispatch_plan  # noqa: E402


RESULT_STATUSES = {
    "DRAFT",
    "IMPORTED_PENDING_REVIEW",
    "IMPORTED_PENDING_VALIDATION",
    "ACCEPTED_BY_HUMAN",
    "REJECTED_BY_HUMAN",
    "BLOCKED",
    "ARCHIVED",
}

VALIDATION_STATUSES = {
    "VALIDATION_PASSED",
    "VALIDATION_FAILED",
    "VALIDATION_WARNING",
    "VALIDATION_BLOCKED",
    "VALIDATION_INCOMPLETE",
}

LOOP_DECISIONS = {
    "AUTO_CONTINUE",
    "AUTO_REPAIR_ONCE",
    "AUTO_REPAIR_RETRY_AVAILABLE",
    "BLOCKED_NEEDS_OPERATOR",
    "BLOCKED_QUOTA_OR_AUTH",
    "BLOCKED_PERMISSION_PROMPT",
    "BLOCKED_FORBIDDEN_ACTION",
    "BLOCKED_VALIDATION_FAILED",
    "COMPLETED_PENDING_DAILY_REVIEW",
    "READY_FOR_FINAL_HUMAN_REVIEW",
}

KNOWN_ADAPTERS = {
    "codex_cli",
    "gemini_cli",
    "ollama_local",
    "powershell_manual",
    "wsl_manual",
    "manual",
    "unknown",
}

REQUIRED_FOLDERS = (
    "contracts",
    "dispatch_plan_reports",
    "dispatch_plans",
    "packets",
    "result_packets",
    "result_validations",
    "loop_decisions",
    "repair_packets",
    "loop_reports",
    "outbox",
    "adapter_commands",
    "routing",
    "manifests",
    "reports",
    "tools",
    "examples",
)

REQUIRED_CONTRACTS = (
    "dispatch_plan_contract.md",
    "exchange_packet_contract.md",
    "result_packet_contract.md",
    "result_capture_contract.md",
    "result_validation_contract.md",
    "loop_decision_contract.md",
    "real_dispatch_contract.md",
    "routing_policy.md",
    "adapter_routing_contract.md",
)

DISPATCH_PLAN_REQUIRED_FIELDS = (
    "dispatch_plan_id",
    "packet_id",
    "packet_path",
    "packet_checksum",
    "source_artifact_path",
    "source_artifact_checksum",
    "target_adapter",
    "target_session_id",
    "target_assignment_id",
    "runtime_session_path",
    "runtime_assignment_path",
    "planned_status",
    "generated_at",
    "generated_by",
    "compatibility_status",
    "compatibility_notes",
    "quota_notes",
    "approval_notes",
    "operator_notes",
    "execution_allowed",
    "commit_allowed",
    "push_allowed",
    "merge_allowed",
    "blocked_reasons",
    "next_operator_action",
)


class AuditResult:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def load_json(path: Path, result: AuditResult) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        result.error(f"invalid JSON: {path}: {exc}")
        return None
    if not isinstance(data, dict):
        result.error(f"JSON root must be object: {path}")
        return None
    return data


def iter_string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for child in value.values():
            strings.extend(iter_string_values(child))
        return strings
    if isinstance(value, list):
        strings: list[str] = []
        for child in value:
            strings.extend(iter_string_values(child))
        return strings
    return []


def existing_file(path_text: str) -> bool:
    path = Path(path_text)
    if path.is_file():
        return True
    win_path = PureWindowsPath(path_text)
    if win_path.drive:
        mapped = Path("/mnt") / win_path.drive.rstrip(":").lower() / Path(*win_path.parts[1:])
        return mapped.is_file()
    return False


def readable_file(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_file():
        return path
    win_path = PureWindowsPath(path_text)
    if win_path.drive:
        mapped = Path("/mnt") / win_path.drive.rstrip(":").lower() / Path(*win_path.parts[1:])
        if mapped.is_file():
            return mapped
    return path


def audit_exchange_lane(root: Path) -> AuditResult:
    result = AuditResult()
    runtime_root = root.parent / "runtime_lane"
    for folder in REQUIRED_FOLDERS:
        if not (root / folder).is_dir():
            result.error(f"missing folder: {root / folder}")
    for contract in REQUIRED_CONTRACTS:
        if not (root / "contracts" / contract).is_file():
            result.error(f"missing contract: {contract}")
    for tool_name in (
        "exchange_fake_dispatch.py",
        "exchange_import_result.py",
        "exchange_validate_result.py",
        "exchange_loop_decision.py",
        "exchange_real_dispatch.py",
    ):
        if not (root / "tools" / tool_name).is_file():
            result.error(f"missing tool: {tool_name}")

    for adapter_id in ("codex_cli", "gemini_cli"):
        command_config_path = root / "adapter_commands" / f"{adapter_id}_command.json"
        data = load_json(command_config_path, result) if command_config_path.is_file() else None
        if data is None:
            result.error(f"missing adapter command config: {command_config_path}")
            continue
        if data.get("adapter_id") != adapter_id:
            result.error(f"{command_config_path}: adapter_id must be {adapter_id}")
        for field in (
            "enabled",
            "executable",
            "base_args",
            "input_mode",
            "prompt_argument_strategy",
            "cwd_policy",
            "timeout_seconds",
            "requires_human_cli_auth",
            "uses_subscription_quota",
            "notes",
            "forbidden_args",
            "allowed_environment_keys",
        ):
            if field not in data:
                result.error(f"{command_config_path}: missing command config field {field}")
        if data.get("enabled") is not False:
            result.warn(f"{command_config_path}: adapter command config is enabled; deliberate operator review required")
        if data.get("shell") is True:
            result.error(f"{command_config_path}: shell=True is forbidden")
        base_args = data.get("base_args", [])
        forbidden_args = data.get("forbidden_args", [])
        if not isinstance(base_args, list) or not all(isinstance(item, str) for item in base_args):
            result.error(f"{command_config_path}: base_args must be a list of strings")
            base_args = []
        if not isinstance(forbidden_args, list) or not all(isinstance(item, str) for item in forbidden_args):
            result.error(f"{command_config_path}: forbidden_args must be a list of strings")
            forbidden_args = []
        executable_name = Path(str(data.get("executable", ""))).name.lower()
        if executable_name in {"cmd", "cmd.exe", "powershell", "powershell.exe", "pwsh", "pwsh.exe", "bash", "bash.exe", "sh", "sh.exe", "wsl", "wsl.exe"}:
            result.error(f"{command_config_path}: executable must not be a shell launcher")
        for arg in base_args:
            for forbidden in forbidden_args:
                if forbidden and forbidden in arg:
                    result.error(f"{command_config_path}: base_args contains forbidden arg {forbidden}")

    for path in sorted((root / "packets").glob("*.json")):
        data = load_json(path, result)
        if data is None:
            continue
        status = data.get("packet_status")
        if status not in exchange_packet.PACKET_STATUSES:
            result.error(f"{path}: invalid packet_status {status!r}")
        source_path = str(data.get("source_artifact_path", ""))
        if status in {"DRAFT", "READY_FOR_REVIEW", "APPROVED_FOR_DISPATCH_PLANNING", "DISPATCH_PLANNED", "BLOCKED"}:
            if not source_path:
                result.error(f"{path}: missing source_artifact_path")
            elif not Path(source_path).exists() and not existing_file(source_path):
                result.error(f"{path}: source_artifact_path missing: {source_path}")
        if source_path and (Path(source_path).is_file() or existing_file(source_path)):
            checksum = str(data.get("source_artifact_checksum", ""))
            if len(checksum) != 64:
                result.error(f"{path}: missing/invalid source_artifact_checksum for file artifact")
        target_adapter = str(data.get("target_adapter", ""))
        if target_adapter not in KNOWN_ADAPTERS and not (Path(__file__).resolve().parents[2] / "runtime_lane" / "adapters" / f"{target_adapter}_profile.json").exists():
            result.warn(f"{path}: unknown target_adapter {target_adapter!r}")
        for field in ("execution_allowed", "commit_allowed", "push_allowed", "merge_allowed"):
            if data.get(field) not in {False, None}:
                result.error(f"{path}: unsafe field {field}={data.get(field)!r}")
        for field in ("execution_occurred", "branch_created", "commit_performed", "push_performed", "merge_performed"):
            if data.get(field) not in {False, None}:
                result.error(f"{path}: packet claims forbidden action {field}={data.get(field)!r}")
        if status == "DISPATCH_PLANNED":
            plan_id = str(data.get("dispatch_plan_id", ""))
            plan_path = str(data.get("dispatch_plan_path", ""))
            if not plan_id and not plan_path:
                result.error(f"{path}: DISPATCH_PLANNED requires dispatch_plan_id or dispatch_plan_path")
            if plan_id and not (root / "dispatch_plans" / f"{plan_id}.json").is_file():
                result.error(f"{path}: referenced dispatch plan missing: {plan_id}")
            if plan_path and not existing_file(plan_path):
                result.error(f"{path}: referenced dispatch_plan_path missing: {plan_path}")

    imported_capture_ids: dict[str, Path] = {}
    for path in sorted((root / "result_packets").glob("*.json")):
        data = load_json(path, result)
        if data is None:
            continue
        status = data.get("result_status")
        if status not in RESULT_STATUSES:
            result.error(f"{path}: invalid result_status {status!r}")
        if status == "IMPORTED_PENDING_REVIEW":
            if data.get("trusted") is not False:
                result.error(f"{path}: imported result packets must have trusted false")
            if data.get("human_review_required") is not True:
                result.error(f"{path}: imported result packets must require human review")
        if data.get("real_cli_execution") is True and data.get("trusted") is not False:
            result.error(f"{path}: imported real CLI results must remain trusted false by default")
        capture_id = str(data.get("capture_id", ""))
        if capture_id:
            if capture_id in imported_capture_ids:
                result.error(f"{path}: duplicate import for capture_id {capture_id}")
            imported_capture_ids[capture_id] = path
        for field in (
            "execution_occurred",
            "model_or_provider_called",
            "terminal_started",
            "branch_created",
            "commit_performed",
            "push_performed",
            "merge_performed",
            "app_source_modified",
        ):
            value = data.get(field)
            if value not in {False, True, None}:
                result.error(f"{path}: invalid boolean field {field}={value!r}")
        for artifact_key in ("raw_output", "parsed_result", "validation", "operator_report"):
            artifact_path = str(data.get("output_artifacts", {}).get(artifact_key, "")) if isinstance(data.get("output_artifacts"), dict) else ""
            if artifact_path and not existing_file(artifact_path):
                result.error(f"{path}: imported output artifact missing: {artifact_path}")

    for path in sorted((root / "outbox").glob("**/capture_manifest.json")):
        data = load_json(path, result)
        if data is None:
            continue
        for field in (
            "capture_id",
            "packet_id",
            "dispatch_plan_id",
            "source_dispatch_plan",
            "source_packet",
            "target_adapter",
            "fake_execution",
            "real_cli_execution",
            "raw_output_path",
            "parsed_result_path",
            "validation_path",
            "operator_report_path",
            "import_status",
        ):
            if field not in data:
                result.error(f"{path}: missing capture field {field}")
        for artifact_field in ("raw_output_path", "parsed_result_path", "validation_path", "operator_report_path"):
            artifact_path = str(data.get(artifact_field, ""))
            if not artifact_path or not existing_file(artifact_path):
                result.error(f"{path}: capture artifact missing: {artifact_path}")
        if data.get("fake_execution") is True:
            if data.get("real_cli_execution") is not False:
                result.error(f"{path}: fake capture must have real_cli_execution false")
            for field in (
                "execution_occurred",
                "model_or_provider_called",
                "terminal_started",
                "branch_created",
                "commit_performed",
                "push_performed",
                "merge_performed",
                "app_source_modified",
            ):
                if data.get(field) is not False:
                    result.error(f"{path}: fake capture field {field} must be false")
        if data.get("real_cli_execution") is True:
            command_manifest_path = str(data.get("command_manifest_path", ""))
            if not command_manifest_path or not existing_file(command_manifest_path):
                result.error(f"{path}: real capture command_manifest_path missing: {command_manifest_path}")
            if data.get("fake_execution") is not False:
                result.error(f"{path}: real capture must have fake_execution false")
            if data.get("terminal_started") is not False:
                result.error(f"{path}: real capture must not claim terminal_started")
            for field in ("branch_created", "commit_performed", "push_performed", "merge_performed"):
                if data.get(field) is not False:
                    result.error(f"{path}: real capture field {field} must be false")
            if "return_code" not in data and "timed_out" not in data:
                result.error(f"{path}: real capture must include return_code or timed_out")
            if data.get("timed_out") not in {False, True, None}:
                result.error(f"{path}: real capture timed_out must be boolean")
            if command_manifest_path and existing_file(command_manifest_path):
                command_manifest = load_json(readable_file(command_manifest_path), result)
                if command_manifest is not None:
                    if command_manifest.get("shell") is not False:
                        result.error(f"{command_manifest_path}: command manifest shell must be false")
        import_status = str(data.get("import_status", ""))
        if import_status not in {"NOT_IMPORTED", "IMPORTED"}:
            result.error(f"{path}: invalid import_status {import_status!r}")
        capture_id = str(data.get("capture_id", ""))
        if import_status == "IMPORTED" and capture_id and capture_id not in imported_capture_ids:
            result.error(f"{path}: capture import_status IMPORTED but no result packet references capture_id {capture_id}")

    validation_ids: dict[str, Path] = {}
    for path in sorted((root / "result_validations").glob("*.json")):
        data = load_json(path, result)
        if data is None:
            continue
        for field in (
            "validation_id",
            "result_id",
            "result_packet_path",
            "source_packet_id",
            "dispatch_plan_id",
            "capture_manifest_path",
            "parsed_result_path",
            "raw_output_path",
            "validation_source_path",
            "operator_report_path",
            "created_at",
            "validation_status",
            "validation_checks",
            "safety_flags",
            "expected_outputs_check",
            "forbidden_actions_check",
            "file_change_check",
            "command_check",
            "test_result_check",
            "blocker_check",
            "retry_eligibility",
            "human_escalation_required",
            "recommended_loop_decision",
            "reasons",
            "generated_by",
        ):
            if field not in data:
                result.error(f"{path}: missing validation field {field}")
        validation_id = str(data.get("validation_id", ""))
        if validation_id:
            validation_ids[validation_id] = path
        status = str(data.get("validation_status", ""))
        if status not in VALIDATION_STATUSES:
            result.error(f"{path}: invalid validation_status {status!r}")
        decision = str(data.get("recommended_loop_decision", ""))
        if decision not in LOOP_DECISIONS:
            result.error(f"{path}: invalid recommended_loop_decision {decision!r}")
        result_id = str(data.get("result_id", ""))
        if result_id and not (root / "result_packets" / f"{result_id}.json").is_file():
            result.error(f"{path}: referenced result packet missing: {result_id}")
        result_packet_path = str(data.get("result_packet_path", ""))
        if result_packet_path and not existing_file(result_packet_path):
            result.error(f"{path}: result_packet_path missing: {result_packet_path}")
        for artifact_field in (
            "capture_manifest_path",
            "parsed_result_path",
            "raw_output_path",
            "validation_source_path",
            "operator_report_path",
        ):
            artifact_path = str(data.get(artifact_field, ""))
            if artifact_path and not existing_file(artifact_path):
                result.error(f"{path}: validation artifact reference missing: {artifact_path}")
        if data.get("human_escalation_required") not in {False, True}:
            result.error(f"{path}: human_escalation_required must be boolean")
        safety_flags = data.get("safety_flags", {})
        if not isinstance(safety_flags, dict):
            result.error(f"{path}: safety_flags must be object")
            safety_flags = {}
        validation_forbidden_flags = [
            "terminal_started",
            "branch_created",
            "commit_performed",
            "push_performed",
            "merge_performed",
            "app_source_modified",
        ]
        if safety_flags.get("fake_execution") is True:
            validation_forbidden_flags.extend(["execution_occurred", "model_or_provider_called"])
        unsafe_flags = [flag for flag in validation_forbidden_flags if safety_flags.get(flag) is True]
        if status == "VALIDATION_PASSED" and unsafe_flags:
            result.error(f"{path}: VALIDATION_PASSED cannot carry unsafe source flags: {unsafe_flags}")
        for field in (
            "execution_occurred",
            "terminal_started",
            "model_or_provider_called",
            "dispatch_occurred",
            "packet_dispatched",
            "branch_created",
            "commit_performed",
            "push_performed",
            "merge_performed",
        ):
            if data.get(field) not in {False, None}:
                result.error(f"{path}: validation record claims forbidden action {field}={data.get(field)!r}")

    loop_decision_ids: dict[str, Path] = {}
    for path in sorted((root / "loop_decisions").glob("*.json")):
        data = load_json(path, result)
        if data is None:
            continue
        for field in (
            "loop_decision_id",
            "result_id",
            "validation_id",
            "source_packet_id",
            "dispatch_plan_id",
            "decision",
            "decision_reasons",
            "retry_count",
            "retry_budget",
            "next_action",
            "auto_continue_allowed",
            "auto_repair_allowed",
            "human_escalation_required",
            "followup_packet_planned",
            "followup_packet_path",
            "runtime_assignment_update_planned",
            "safety_notes",
            "created_at",
            "generated_by",
        ):
            if field not in data:
                result.error(f"{path}: missing loop decision field {field}")
        loop_decision_id = str(data.get("loop_decision_id", ""))
        if loop_decision_id:
            loop_decision_ids[loop_decision_id] = path
        decision = str(data.get("decision", ""))
        if decision not in LOOP_DECISIONS:
            result.error(f"{path}: invalid loop decision {decision!r}")
        validation_id = str(data.get("validation_id", ""))
        if validation_id and validation_id not in validation_ids and not (root / "result_validations" / f"{validation_id}.json").is_file():
            result.error(f"{path}: referenced validation record missing: {validation_id}")
        for field in ("auto_continue_allowed", "auto_repair_allowed", "human_escalation_required"):
            if data.get(field) not in {False, True}:
                result.error(f"{path}: {field} must be boolean")
        for field in (
            "dispatch_occurred",
            "packet_dispatched",
            "execution_occurred",
            "model_or_provider_called",
            "terminal_started",
            "branch_created",
            "commit_performed",
            "push_performed",
            "merge_performed",
        ):
            if data.get(field) not in {False, None}:
                result.error(f"{path}: loop decision claims forbidden action {field}={data.get(field)!r}")

    for path in sorted((root / "repair_packets").glob("*.json")):
        data = load_json(path, result)
        if data is None:
            continue
        for field in (
            "repair_packet_id",
            "loop_decision_id",
            "result_id",
            "validation_id",
            "source_packet_id",
            "dispatch_plan_id",
            "validation_failure_reason",
            "bounded_repair_objective",
            "allowed_target_adapter",
            "execution_allowed",
            "dispatch_allowed",
            "branch_creation_allowed",
            "commit_allowed",
            "push_allowed",
            "merge_allowed",
            "created_at",
            "generated_by",
        ):
            if field not in data:
                result.error(f"{path}: missing repair packet field {field}")
        loop_decision_id = str(data.get("loop_decision_id", ""))
        if loop_decision_id and loop_decision_id not in loop_decision_ids and not (root / "loop_decisions" / f"{loop_decision_id}.json").is_file():
            result.error(f"{path}: referenced loop decision missing: {loop_decision_id}")
        validation_id = str(data.get("validation_id", ""))
        if validation_id and validation_id not in validation_ids and not (root / "result_validations" / f"{validation_id}.json").is_file():
            result.error(f"{path}: referenced validation record missing: {validation_id}")
        result_id = str(data.get("result_id", ""))
        if result_id and not (root / "result_packets" / f"{result_id}.json").is_file():
            result.error(f"{path}: referenced result packet missing: {result_id}")
        for field in (
            "execution_allowed",
            "dispatch_allowed",
            "branch_creation_allowed",
            "commit_allowed",
            "push_allowed",
            "merge_allowed",
        ):
            if data.get(field) is not False:
                result.error(f"{path}: repair packet field {field} must be false")

    for path in sorted((root / "dispatch_plans").glob("*.json")):
        data = load_json(path, result)
        if data is None:
            continue
        for field in DISPATCH_PLAN_REQUIRED_FIELDS:
            if field not in data:
                result.error(f"{path}: missing dispatch plan field {field}")
        status = str(data.get("planned_status", ""))
        if status not in exchange_dispatch_plan.PLANNED_STATUSES:
            result.error(f"{path}: invalid planned_status {status!r}")
        compatibility_status = str(data.get("compatibility_status", ""))
        if compatibility_status not in {"PASS", "BLOCKED"}:
            result.error(f"{path}: invalid compatibility_status {compatibility_status!r}")

        packet_path = str(data.get("packet_path", ""))
        if not packet_path or not existing_file(packet_path):
            result.error(f"{path}: referenced packet_path missing: {packet_path}")

        session_path = str(data.get("runtime_session_path", ""))
        if status != "BLOCKED_NO_SESSION":
            if not session_path or not existing_file(session_path):
                result.error(f"{path}: runtime_session_path missing for planned_status {status}")

        assignment_path = str(data.get("runtime_assignment_path", ""))
        if status not in {"BLOCKED_ASSIGNMENT_MISSING", "BLOCKED_NO_SESSION"}:
            if not assignment_path or not existing_file(assignment_path):
                result.error(f"{path}: runtime_assignment_path missing for planned_status {status}")

        for field in ("execution_allowed", "commit_allowed", "push_allowed", "merge_allowed"):
            if data.get(field) is not False:
                result.error(f"{path}: dispatch plan field {field} must be false")
        for field in (
            "execution_occurred",
            "session_started",
            "terminal_started",
            "cli_executed",
            "model_invoked",
            "browser_automated",
            "branch_created",
            "commit_performed",
            "push_performed",
            "merge_performed",
        ):
            if data.get(field) not in {False, None}:
                result.error(f"{path}: dispatch plan claims forbidden action {field}={data.get(field)!r}")

        blocked_reasons = data.get("blocked_reasons", [])
        if status == "PLANNED_NOT_DISPATCHED" and blocked_reasons:
            result.error(f"{path}: PLANNED_NOT_DISPATCHED must not carry blocked_reasons")
        if status != "PLANNED_NOT_DISPATCHED" and compatibility_status != "BLOCKED":
            result.error(f"{path}: blocked dispatch plans must report compatibility_status=BLOCKED")

        string_fields = []
        for field in (
            "compatibility_notes",
            "approval_notes",
            "quota_notes",
            "operator_notes",
            "blocked_reasons",
            "next_operator_action",
        ):
            string_fields.extend(iter_string_values(data.get(field)))
        normalized_text = " | ".join(text.casefold() for text in string_fields)
        forbidden_claims = (
            "terminal started",
            "session started",
            "cli executed",
            "model invoked",
            "browser automated",
            "branch created",
            "commit performed",
            "push performed",
            "merge performed",
            "ran codex",
            "ran gemini",
            "ran ollama",
        )
        for phrase in forbidden_claims:
            if phrase in normalized_text:
                result.error(f"{path}: dispatch plan text must not claim forbidden action: {phrase}")

        if runtime_root.exists():
            if session_path and Path(session_path).is_file() and not str(Path(session_path).resolve()).startswith(str(runtime_root.resolve())):
                result.error(f"{path}: runtime_session_path escapes runtime_lane: {session_path}")
            if assignment_path and Path(assignment_path).is_file() and not str(Path(assignment_path).resolve()).startswith(str(runtime_root.resolve())):
                result.error(f"{path}: runtime_assignment_path escapes runtime_lane: {assignment_path}")
    return result


def render_audit(result: AuditResult, root: Path) -> str:
    lines = [
        "Exchange Lane Audit",
        "===================",
        f"root: {root}",
        "scope: metadata inspection only; no dispatch/execution/model/terminal actions.",
        "",
        f"Warnings: {len(result.warnings)}",
    ]
    lines.extend(f"- WARNING {w}" for w in result.warnings)
    lines.append(f"Errors: {len(result.errors)}")
    lines.extend(f"- ERROR {e}" for e in result.errors)
    lines.append("")
    lines.append("Result: PASS" if result.ok else "Result: FAIL")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit Exchange Lane metadata.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    result = audit_exchange_lane(root)
    print(render_audit(result, root))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

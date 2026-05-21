#!/usr/bin/env python3
"""No-write validation for the ws command safety manifest and TUI policy."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any


os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "registry" / "ws_command_safety.yaml"
MATRIX_PATH = ROOT / "WS_COMMAND_SAFETY_MATRIX.md"
TUI_APP_PATH = ROOT / "tui" / "app.py"
MIN_COMMAND_COUNT = 121

REQUIRED_TOP_LEVEL = {"version", "default_policy", "safety_classes", "commands"}
REQUIRED_COMMAND_FIELDS = {
    "safety_class",
    "description",
    "writes_local_files",
    "writes_project_files",
    "invokes_agent_or_model",
    "external_provider_or_cloud",
    "read_only_strict",
    "read_only_with_local_reports",
    "safe_dry_run",
    "tui_exposure",
    "confirmation",
    "operator_label",
    "warning_label",
    "evidence",
    "confidence",
    "notes",
}
BOOLEAN_FIELDS = {
    "writes_local_files",
    "writes_project_files",
    "invokes_agent_or_model",
    "external_provider_or_cloud",
    "read_only_strict",
    "read_only_with_local_reports",
    "safe_dry_run",
}
SAFETY_CLASSES = {
    "PURE_READ",
    "LOCAL_REPORT_WRITE",
    "DRY_RUN_ONLY",
    "GUARDED_WRITE",
    "AGENT_RUN",
    "PROVIDER_CALL",
    "DESTRUCTIVE",
    "UNKNOWN",
}
TUI_EXPOSURES = {"visible", "visible_with_label", "disabled", "hidden", "admin_only"}
VISIBLE_TUI_EXPOSURES = {"visible", "visible_with_label"}
CONFIRMATIONS = {
    "none",
    "light",
    "explicit",
    "typed",
    "branch",
    "dirty_worktree",
    "provider",
    "destructive",
    "required",
}
CONFIDENCES = {"high", "medium", "low"}
KNOWN_COMMANDS = {
    "ws ready",
    "ws agent-hygiene",
    "ws feature-status",
    "ws stronghold-status",
    "ws handoff-status",
    "ws product-list",
    "ws product-status",
    "ws product-new",
    "ws product-help",
    "ws product-intake --confirm",
    "ws product-answer-import",
    "ws product-scope --dry-run",
    "ws product-scope-change --dry-run",
    "ws product-scope-change --confirm",
    "ws product-scope-revision --dry-run",
    "ws product-scope-revision --confirm",
    "ws product-lock-scope",
    "ws product-prd --dry-run",
    "ws product-prd --confirm",
    "ws product-prd-review --dry-run",
    "ws product-prd-approve",
    "ws product-prd-status",
    "ws product-wireframe --dry-run",
    "ws build --dry-run",
    "ws agent-run --dry-run",
    "ws review",
    "ws stuck",
}
KNOWN_CLASSIFICATIONS = {
    "ws ready": "LOCAL_REPORT_WRITE",
    "ws feature-status": "PURE_READ",
    "ws stronghold-status": "PURE_READ",
    "ws handoff-status": "PURE_READ",
    "ws product-list": "PURE_READ",
    "ws product-status": "PURE_READ",
    "ws product-new": "GUARDED_WRITE",
    "ws product-help": "PURE_READ",
    "ws product-intake --confirm": "GUARDED_WRITE",
    "ws product-answer-import": "GUARDED_WRITE",
    "ws product-scope --dry-run": "DRY_RUN_ONLY",
    "ws product-scope-change --dry-run": "DRY_RUN_ONLY",
    "ws product-scope-change --confirm": "GUARDED_WRITE",
    "ws product-scope-revision --dry-run": "DRY_RUN_ONLY",
    "ws product-scope-revision --confirm": "GUARDED_WRITE",
    "ws product-lock-scope": "GUARDED_WRITE",
    "ws product-prd --dry-run": "DRY_RUN_ONLY",
    "ws product-prd --confirm": "GUARDED_WRITE",
    "ws product-prd-review --dry-run": "DRY_RUN_ONLY",
    "ws product-prd-approve": "GUARDED_WRITE",
    "ws product-prd-status": "PURE_READ",
    "ws product-wireframe --dry-run": "DRY_RUN_ONLY",
    "ws build --dry-run": "DRY_RUN_ONLY",
    "ws agent-run --dry-run": "DRY_RUN_ONLY",
    "ws review": "UNKNOWN",
    "ws stuck": "UNKNOWN",
}


class ValidationReport:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.tui_import_used = False
        self.tui_import_skipped_reason: str | None = None

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def load_yaml_like(path: Path, report: ValidationReport) -> dict[str, Any] | None:
    if not path.is_file():
        report.error(f"manifest not found: {path}")
        return None

    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as json_exc:
        try:
            import yaml  # type: ignore
        except ImportError:
            report.error(
                "manifest is not JSON-compatible YAML and PyYAML is unavailable: "
                f"{json_exc}"
            )
            return None
        try:
            data = yaml.safe_load(raw)
        except Exception as yaml_exc:
            report.error(f"manifest YAML parse failed: {yaml_exc}")
            return None

    if not isinstance(data, dict):
        report.error("manifest root must be a mapping")
        return None
    return data


def matrix_commands(report: ValidationReport) -> set[str]:
    if not MATRIX_PATH.is_file():
        report.warn(f"safety matrix not found for cross-check: {MATRIX_PATH}")
        return set()

    lines = MATRIX_PATH.read_text(encoding="utf-8").splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.startswith("## 5. Command Safety Matrix"))
        end = next(i for i, line in enumerate(lines) if line.startswith("## 6. TUI Exposure Policy"))
    except StopIteration:
        report.warn("could not locate command matrix section for cross-check")
        return set()

    commands: set[str] = set()
    for line in lines[start:end]:
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip()[1:-1].split("|")]
        if len(cells) != 14:
            report.warn(f"skipping matrix row with unexpected column count: {line[:120]}")
            continue
        commands.add(cells[0].strip("`"))
    return commands


def validate_top_level(data: dict[str, Any], report: ValidationReport) -> dict[str, Any]:
    missing = REQUIRED_TOP_LEVEL - set(data)
    if missing:
        report.error(f"missing top-level fields: {', '.join(sorted(missing))}")

    if data.get("version") != 1:
        report.error(f"version must be 1, found {data.get('version')!r}")

    if not isinstance(data.get("default_policy"), dict):
        report.error("default_policy must be a mapping")

    safety_classes = data.get("safety_classes")
    if not isinstance(safety_classes, dict):
        report.error("safety_classes must be a mapping")
    else:
        missing_classes = SAFETY_CLASSES - set(safety_classes)
        if missing_classes:
            report.error(f"safety_classes missing definitions: {', '.join(sorted(missing_classes))}")

    commands = data.get("commands")
    if not isinstance(commands, dict):
        report.error("commands must be a mapping")
        return {}
    return commands


def require_string(entry: dict[str, Any], field: str, command: str, report: ValidationReport) -> None:
    if not isinstance(entry.get(field), str):
        report.error(f"{command}: {field} must be a string")


def validate_command_entry(command: str, entry: Any, report: ValidationReport) -> None:
    if not isinstance(command, str) or not command:
        report.error(f"command keys must be non-empty strings: {command!r}")
        return
    if not isinstance(entry, dict):
        report.error(f"{command}: command entry must be a mapping")
        return

    missing = REQUIRED_COMMAND_FIELDS - set(entry)
    if missing:
        report.error(f"{command}: missing fields: {', '.join(sorted(missing))}")
        return

    for field in BOOLEAN_FIELDS:
        if not isinstance(entry.get(field), bool):
            report.error(f"{command}: {field} must be a boolean")

    for field in ("description", "operator_label", "warning_label", "notes"):
        require_string(entry, field, command, report)

    evidence = entry.get("evidence")
    if not isinstance(evidence, list) or not all(isinstance(item, str) for item in evidence):
        report.error(f"{command}: evidence must be a list of strings")

    safety_class = entry.get("safety_class")
    tui_exposure = entry.get("tui_exposure")
    confirmation = entry.get("confirmation")
    confidence = entry.get("confidence")

    if safety_class not in SAFETY_CLASSES:
        report.error(f"{command}: invalid safety_class {safety_class!r}")
    if tui_exposure not in TUI_EXPOSURES:
        report.error(f"{command}: invalid tui_exposure {tui_exposure!r}")
    if confirmation not in CONFIRMATIONS:
        report.error(f"{command}: invalid confirmation {confirmation!r}")
    if confidence not in CONFIDENCES:
        report.error(f"{command}: invalid confidence {confidence!r}")

    if safety_class == "UNKNOWN":
        if tui_exposure != "hidden":
            report.error(f"{command}: UNKNOWN commands must be hidden")
        if confirmation != "required":
            report.error(f"{command}: UNKNOWN commands must require required confirmation")

    if safety_class == "DESTRUCTIVE":
        if tui_exposure in VISIBLE_TUI_EXPOSURES:
            report.error(f"{command}: DESTRUCTIVE commands must not be visible by default")
        if confirmation != "destructive":
            report.error(f"{command}: DESTRUCTIVE commands must require destructive confirmation")

    if safety_class == "PROVIDER_CALL":
        if tui_exposure in VISIBLE_TUI_EXPOSURES:
            report.error(f"{command}: PROVIDER_CALL commands must not be visible by default")
        if confirmation != "provider":
            report.error(f"{command}: PROVIDER_CALL commands must require provider confirmation")

    if safety_class == "PURE_READ":
        if entry.get("writes_local_files"):
            report.error(f"{command}: PURE_READ must not write local files")
        if entry.get("writes_project_files"):
            report.error(f"{command}: PURE_READ must not write project files")

    if entry.get("writes_project_files") and entry.get("read_only_strict"):
        report.error(f"{command}: project-writing commands must not be read_only_strict")

    if entry.get("external_provider_or_cloud") and entry.get("read_only_strict"):
        report.error(f"{command}: provider/cloud commands must not be read_only_strict")

    if safety_class == "LOCAL_REPORT_WRITE":
        warning = str(entry.get("warning_label", "")).lower()
        if not entry.get("writes_local_files"):
            report.error(f"{command}: LOCAL_REPORT_WRITE should write local files")
        if "local" not in warning or ("report" not in warning and "status" not in warning):
            report.error(
                f"{command}: LOCAL_REPORT_WRITE warning_label must explain local report/status writes"
            )

        tui_dispatch_policy = entry.get("tui_dispatch_policy")
        tui_dispatch_allowed = entry.get("tui_dispatch_allowed")
        report_write_scope = entry.get("report_write_scope")

        valid_policies = {"safe_local_report", "preview_only", "hidden_local_report", "system_only", "learning_only"}
        if tui_dispatch_policy not in valid_policies:
            report.error(f"{command}: LOCAL_REPORT_WRITE has invalid or missing tui_dispatch_policy: {tui_dispatch_policy}")

        if not isinstance(tui_dispatch_allowed, bool):
            report.error(f"{command}: LOCAL_REPORT_WRITE has missing or non-boolean tui_dispatch_allowed: {tui_dispatch_allowed}")

        if not isinstance(report_write_scope, str) or not report_write_scope:
            report.error(f"{command}: LOCAL_REPORT_WRITE has missing or invalid report_write_scope: {report_write_scope}")


def validate_known_commands(commands: dict[str, Any], report: ValidationReport) -> None:
    for command in sorted(KNOWN_COMMANDS):
        if command not in commands:
            report.error(f"expected command missing: {command}")

    for command, expected_class in sorted(KNOWN_CLASSIFICATIONS.items()):
        entry = commands.get(command)
        if not isinstance(entry, dict):
            continue
        actual = entry.get("safety_class")
        if actual != expected_class:
            report.error(f"{command}: expected {expected_class}, found {actual}")


def validate_matrix_crosscheck(commands: dict[str, Any], report: ValidationReport) -> None:
    matrix = matrix_commands(report)
    if not matrix:
        return
    manifest_commands = set(commands)
    missing = matrix - manifest_commands
    extra = manifest_commands - matrix
    if missing:
        report.error(f"manifest missing matrix commands: {', '.join(sorted(missing))}")
    if extra:
        unbacked_extra = []
        source_backed_extra = []
        for command in sorted(extra):
            entry = commands.get(command, {})
            evidence = " ".join(str(item).lower() for item in entry.get("evidence", []))
            if command.startswith("ws ") and "scripts/ws" in evidence:
                source_backed_extra.append(command)
            else:
                unbacked_extra.append(command)
        if source_backed_extra:
            report.warn(
                "manifest has source-backed commands not present in matrix: "
                f"{', '.join(source_backed_extra)}"
            )
        if unbacked_extra:
            report.error(
                "manifest has commands not present in matrix or source-backed drift evidence: "
                f"{', '.join(unbacked_extra)}"
            )


def import_tui_app(report: ValidationReport) -> Any | None:
    if not TUI_APP_PATH.is_file():
        report.warn(f"TUI app not found; helper validation skipped: {TUI_APP_PATH}")
        report.tui_import_skipped_reason = "tui app missing"
        return None

    try:
        spec = importlib.util.spec_from_file_location("ws_tui_app_validation", TUI_APP_PATH)
        if spec is None or spec.loader is None:
            raise RuntimeError("could not create import spec")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    except Exception as exc:
        report.warn(f"TUI helper import skipped: {exc}")
        report.tui_import_skipped_reason = str(exc)
        return None

    report.tui_import_used = True
    return module


def validate_tui_helpers(commands: dict[str, Any], report: ValidationReport) -> None:
    app = import_tui_app(report)
    if app is None:
        return

    app.COMMAND_SAFETY_MANIFEST_PATH = MANIFEST_PATH
    app._COMMAND_SAFETY_MANIFEST = None

    manifest = app.load_command_safety_manifest()
    if not manifest.loaded:
        report.error(f"TUI helper failed to load manifest: {manifest.warning}")
        return

    helper_checks = [
        ("ws review", "READ_ONLY_WITH_LOCAL_REPORTS", False, "UNKNOWN must be hidden"),
        ("ws stuck", "SAFE_DRY_RUN", False, "UNKNOWN must be hidden"),
        ("ws agent-run", "READ_ONLY_WITH_LOCAL_REPORTS", False, "PROVIDER_CALL hidden by default"),
        ("ws cleanup-apply --apply", "SAFE_DRY_RUN", False, "DESTRUCTIVE hidden by default"),
        ("ws ready", "READ_ONLY_WITH_LOCAL_REPORTS", True, "LOCAL_REPORT_WRITE visible with label"),
        ("ws ready", "READ_ONLY_STRICT", False, "LOCAL_REPORT_WRITE disabled in strict read-only"),
        ("ws product-prd --dry-run", "SAFE_DRY_RUN", False, "DRY_RUN_ONLY preview remains hidden by default"),
        ("ws product-scope-change --dry-run", "READ_ONLY_WITH_LOCAL_REPORTS", False, "DRY_RUN_ONLY preview remains hidden by default"),
        ("ws product-scope-change --dry-run", "SAFE_DRY_RUN", False, "DRY_RUN_ONLY preview remains hidden by default"),
        ("ws product-scope-change --confirm", "READ_ONLY_WITH_LOCAL_REPORTS", False, "GUARDED_WRITE remains hidden in read-only mode"),
        ("ws product-scope-change --confirm", "SAFE_DRY_RUN", False, "GUARDED_WRITE remains hidden by default"),
        ("ws product-scope-revision --dry-run", "READ_ONLY_WITH_LOCAL_REPORTS", False, "DRY_RUN_ONLY preview remains hidden by default"),
        ("ws product-scope-revision --dry-run", "SAFE_DRY_RUN", False, "DRY_RUN_ONLY preview remains hidden by default"),
        ("ws product-scope-revision --confirm", "READ_ONLY_WITH_LOCAL_REPORTS", False, "GUARDED_WRITE remains hidden in read-only mode"),
        ("ws product-scope-revision --confirm", "SAFE_DRY_RUN", False, "GUARDED_WRITE remains hidden by default"),
        ("ws product-prd --confirm", "READ_ONLY_WITH_LOCAL_REPORTS", False, "GUARDED_WRITE remains hidden in read-only mode"),
        ("ws product-prd --confirm", "SAFE_DRY_RUN", False, "GUARDED_WRITE remains hidden by default"),
        ("ws product-prd-approve", "READ_ONLY_WITH_LOCAL_REPORTS", False, "GUARDED_WRITE remains hidden in read-only mode"),
        ("ws product-prd-approve", "SAFE_DRY_RUN", False, "GUARDED_WRITE remains hidden by default"),
        ("ws product-prd-status", "READ_ONLY_WITH_LOCAL_REPORTS", True, "PURE_READ status command visible in read-only mode"),
        ("ws product-prd-status", "SAFE_DRY_RUN", True, "PURE_READ status command visible in safe dry-run mode"),
        ("ws product-wireframe --dry-run", "READ_ONLY_WITH_LOCAL_REPORTS", False, "DRY_RUN_ONLY preview remains hidden by default"),
        ("ws product-wireframe --dry-run", "SAFE_DRY_RUN", False, "DRY_RUN_ONLY preview remains hidden by default"),
        ("ws learning-run --session --dry-run", "SAFE_DRY_RUN", True, "dry-run action visible"),
        ("ws not-a-command", "SAFE_DRY_RUN", False, "missing command hidden"),
    ]
    for command, mode, expected, reason in helper_checks:
        actual = app.is_command_visible(command, mode)
        if actual is not expected:
            report.error(f"TUI helper mismatch for {command} in {mode}: expected {expected}, got {actual} ({reason})")

    for command, entry in commands.items():
        safety_class = entry.get("safety_class")
        if safety_class in {"UNKNOWN", "PROVIDER_CALL", "DESTRUCTIVE"}:
            if app.is_command_visible(command, "READ_ONLY_WITH_LOCAL_REPORTS"):
                report.error(f"TUI helper exposes {safety_class} command in READ_ONLY_WITH_LOCAL_REPORTS: {command}")

    missing = app.get_command_safety("ws not-a-command")
    if missing.safety_class != "UNKNOWN" or missing.tui_exposure != "hidden":
        report.error("TUI helper missing-command fallback must be UNKNOWN/hidden")

    ready = app.get_command_safety("ws ready")
    if ready.tui_exposure != "visible_with_label" or not ready.warning_label:
        report.error("TUI helper should label ws ready as visible_with_label with a warning")


def print_summary(commands: dict[str, Any], report: ValidationReport) -> None:
    safety_counts = Counter(
        entry.get("safety_class", "INVALID")
        for entry in commands.values()
        if isinstance(entry, dict)
    )
    exposure_counts = Counter(
        entry.get("tui_exposure", "INVALID")
        for entry in commands.values()
        if isinstance(entry, dict)
    )

    print("WS Command Safety Validation")
    print("============================")
    print(f"Manifest: {MANIFEST_PATH}")
    print(f"Total command entries: {len(commands)}")
    print(f"TUI helper import used: {'yes' if report.tui_import_used else 'no'}")
    if report.tui_import_skipped_reason:
        print(f"TUI helper import skipped reason: {report.tui_import_skipped_reason}")
    print("")
    print("Counts by safety class:")
    for name in sorted(safety_counts):
        print(f"- {name}: {safety_counts[name]}")
    print("")
    print("Counts by TUI exposure:")
    for name in sorted(exposure_counts):
        print(f"- {name}: {exposure_counts[name]}")
    print("")
    print(f"Warnings: {len(report.warnings)}")
    for warning in report.warnings:
        print(f"- WARN: {warning}")
    print("")
    print(f"Errors: {len(report.errors)}")
    for error in report.errors:
        print(f"- ERROR: {error}")
    print("")
    print(f"Result: {'FAIL' if report.errors else 'PASS'}")


def main() -> int:
    report = ValidationReport()
    data = load_yaml_like(MANIFEST_PATH, report)
    commands: dict[str, Any] = {}
    if data is not None:
        commands = validate_top_level(data, report)
        if len(commands) < MIN_COMMAND_COUNT:
            report.error(
                f"expected at least {MIN_COMMAND_COUNT} command entries, found {len(commands)}"
            )
        for command, entry in commands.items():
            validate_command_entry(command, entry, report)
        validate_known_commands(commands, report)
        validate_matrix_crosscheck(commands, report)
        validate_tui_helpers(commands, report)

    print_summary(commands, report)
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

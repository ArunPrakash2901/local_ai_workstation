#!/usr/bin/env python3
"""No-write regression test for TUI command visibility metadata."""

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
TUI_APP_PATH = ROOT / "tui" / "app.py"
VISIBLE_EXPOSURES = {"visible", "visible_with_label"}
NON_VISIBLE_EXPOSURES = {"disabled", "hidden", "admin_only"}
DEFAULT_MODES = ("READ_ONLY_WITH_LOCAL_REPORTS", "SAFE_DRY_RUN")


class VisibilityReport:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.notes: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def note(self, message: str) -> None:
        self.notes.append(message)


def load_manifest(report: VisibilityReport) -> dict[str, Any]:
    if not MANIFEST_PATH.is_file():
        report.error(f"manifest not found: {MANIFEST_PATH}")
        return {}
    raw = MANIFEST_PATH.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as json_exc:
        try:
            import yaml
            data = yaml.safe_load(raw)
        except ImportError:
            report.error(f"manifest is not JSON-compatible YAML and PyYAML is unavailable: {json_exc}")
            return {}
        except Exception as exc:
            report.error(f"manifest YAML parse failed: {exc}")
            return {}
    commands = data.get("commands")
    if not isinstance(commands, dict):
        report.error("manifest commands must be a mapping")
        return {}
    return commands


def import_tui_app(report: VisibilityReport) -> Any | None:
    try:
        spec = importlib.util.spec_from_file_location("ws_tui_visibility_app", TUI_APP_PATH)
        if spec is None or spec.loader is None:
            raise RuntimeError("could not create import spec")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    except Exception as exc:
        report.error(f"could not import TUI helper module: {exc}")
        return None

    module.COMMAND_SAFETY_MANIFEST_PATH = MANIFEST_PATH
    module._COMMAND_SAFETY_MANIFEST = None
    manifest = module.load_command_safety_manifest()
    if not manifest.loaded:
        report.error(f"TUI helper failed to load manifest: {manifest.warning}")
        return None
    return module


def is_visible(app: Any, command: str, mode: str) -> bool:
    return bool(app.is_command_visible(command, mode))


def expect(condition: bool, report: VisibilityReport, message: str) -> None:
    if not condition:
        report.error(message)


def validate_class_rules(commands: dict[str, Any], app: Any, report: VisibilityReport) -> None:
    for command, entry in commands.items():
        safety_class = entry.get("safety_class")
        exposure = entry.get("tui_exposure")
        warning = str(entry.get("warning_label", ""))

        visible_default = any(is_visible(app, command, mode) for mode in DEFAULT_MODES)
        visible_safe_dry_run = is_visible(app, command, "SAFE_DRY_RUN")
        visible_read_only = is_visible(app, command, "READ_ONLY_WITH_LOCAL_REPORTS")
        visible_strict = is_visible(app, command, "READ_ONLY_STRICT")

        if safety_class == "UNKNOWN":
            expect(exposure == "hidden", report, f"{command}: UNKNOWN must have hidden exposure")
            expect(not visible_default, report, f"{command}: UNKNOWN is visible by default")

        if safety_class == "DESTRUCTIVE":
            expect(exposure == "hidden", report, f"{command}: DESTRUCTIVE must be hidden")
            expect(not visible_default, report, f"{command}: DESTRUCTIVE is visible by default")

        if safety_class == "PROVIDER_CALL":
            expect(exposure in {"hidden", "disabled", "admin_only"}, report, f"{command}: PROVIDER_CALL exposure is unsafe: {exposure}")
            expect(not visible_default, report, f"{command}: PROVIDER_CALL is visible by default")

        if safety_class == "GUARDED_WRITE":
            expect(exposure in NON_VISIBLE_EXPOSURES, report, f"{command}: GUARDED_WRITE should be hidden/disabled/admin_only")
            expect(not visible_default, report, f"{command}: GUARDED_WRITE is visible by default")

        if safety_class == "AGENT_RUN":
            if exposure in VISIBLE_EXPOSURES:
                expect(entry.get("safe_dry_run") is True, report, f"{command}: visible AGENT_RUN must be explicitly safe_dry_run")
            else:
                expect(exposure in NON_VISIBLE_EXPOSURES, report, f"{command}: AGENT_RUN has unexpected exposure {exposure}")
            expect(not visible_read_only, report, f"{command}: AGENT_RUN visible in READ_ONLY_WITH_LOCAL_REPORTS")

        if safety_class == "PURE_READ":
            if exposure in VISIBLE_EXPOSURES:
                expect(visible_read_only, report, f"{command}: visible PURE_READ not visible in READ_ONLY_WITH_LOCAL_REPORTS")
            else:
                expect(not visible_default, report, f"{command}: hidden PURE_READ is visible by helper")

        if safety_class == "LOCAL_REPORT_WRITE":
            expect(entry.get("writes_local_files") is True, report, f"{command}: LOCAL_REPORT_WRITE must write local files")
            expect(warning, report, f"{command}: LOCAL_REPORT_WRITE must carry warning_label")
            expect(not visible_strict, report, f"{command}: LOCAL_REPORT_WRITE visible in READ_ONLY_STRICT")
            if exposure in VISIBLE_EXPOSURES:
                expect(exposure == "visible_with_label", report, f"{command}: LOCAL_REPORT_WRITE should be visible_with_label")
                expect(visible_read_only, report, f"{command}: visible LOCAL_REPORT_WRITE not visible in READ_ONLY_WITH_LOCAL_REPORTS")
            else:
                expect(not visible_default, report, f"{command}: hidden LOCAL_REPORT_WRITE is visible by helper")

        if safety_class == "DRY_RUN_ONLY":
            expect(not visible_strict, report, f"{command}: DRY_RUN_ONLY visible in READ_ONLY_STRICT")
            if exposure in VISIBLE_EXPOSURES:
                expect(visible_safe_dry_run, report, f"{command}: visible DRY_RUN_ONLY not visible in SAFE_DRY_RUN")
            else:
                expect(not visible_default, report, f"{command}: hidden DRY_RUN_ONLY is visible by helper")

        if entry.get("external_provider_or_cloud"):
            expect(not visible_default, report, f"{command}: external provider/cloud command visible by default")


def validate_known_commands(commands: dict[str, Any], app: Any, report: VisibilityReport) -> None:
    known = {
        "ws review": ("UNKNOWN", "hidden"),
        "ws stuck": ("UNKNOWN", "hidden"),
        "ws ready": ("LOCAL_REPORT_WRITE", "visible_with_label"),
        "ws product-new": ("GUARDED_WRITE", "hidden"),
        "ws product-intake --confirm": ("GUARDED_WRITE", "hidden"),
        "ws product-answer-import": ("GUARDED_WRITE", "hidden"),
        "ws product-scope --dry-run": ("DRY_RUN_ONLY", "hidden"),
        "ws product-scope-change --dry-run": ("DRY_RUN_ONLY", "hidden"),
        "ws product-scope-change --confirm": ("GUARDED_WRITE", "hidden"),
        "ws product-scope-revision --dry-run": ("DRY_RUN_ONLY", "hidden"),
        "ws product-scope-revision --confirm": ("GUARDED_WRITE", "hidden"),
        "ws product-lock-scope": ("GUARDED_WRITE", "hidden"),
        "ws product-prd --dry-run": ("DRY_RUN_ONLY", "hidden"),
        "ws product-prd --confirm": ("GUARDED_WRITE", "hidden"),
        "ws product-prd-review --dry-run": ("DRY_RUN_ONLY", "hidden"),
        "ws product-prd-approve": ("GUARDED_WRITE", "hidden"),
        "ws product-prd-status": ("PURE_READ", "visible"),
        "ws product-wireframe --dry-run": ("DRY_RUN_ONLY", "hidden"),
        "ws product-list": ("PURE_READ", "visible"),
        "ws product-status": ("PURE_READ", "visible"),
        "ws product-help": ("PURE_READ", "visible"),
        "ws feature-status": ("PURE_READ", "visible"),
        "ws stronghold-status": ("PURE_READ", "visible"),
        "ws handoff-status": ("PURE_READ", "visible"),
        "ws build --dry-run": ("DRY_RUN_ONLY", None),
        "ws agent-run --dry-run": ("DRY_RUN_ONLY", None),
    }

    for command, (expected_class, expected_exposure) in known.items():
        entry = commands.get(command)
        expect(isinstance(entry, dict), report, f"{command}: missing from manifest")
        if not isinstance(entry, dict):
            continue
        expect(entry.get("safety_class") == expected_class, report, f"{command}: expected {expected_class}, got {entry.get('safety_class')}")
        if expected_exposure:
            expect(entry.get("tui_exposure") == expected_exposure, report, f"{command}: expected exposure {expected_exposure}, got {entry.get('tui_exposure')}")

    expect(not is_visible(app, "ws review", "SAFE_DRY_RUN"), report, "ws review should be hidden")
    expect(not is_visible(app, "ws stuck", "SAFE_DRY_RUN"), report, "ws stuck should be hidden")

    ready = app.get_command_safety("ws ready")
    expect(ready.safety_class == "LOCAL_REPORT_WRITE", report, "ws ready helper class should be LOCAL_REPORT_WRITE")
    expect(ready.tui_exposure == "visible_with_label", report, "ws ready helper exposure should be visible_with_label")
    expect(bool(ready.warning_label), report, "ws ready helper should have warning label")

    product_new = app.get_command_safety("ws product-new")
    expect(product_new.safety_class == "GUARDED_WRITE", report, "ws product-new helper class should be GUARDED_WRITE")
    expect(not is_visible(app, "ws product-new", "READ_ONLY_WITH_LOCAL_REPORTS"), report, "ws product-new should not be visible")
    expect(not is_visible(app, "ws product-new", "SAFE_DRY_RUN"), report, "ws product-new should not be visible")

    product_intake_confirm = app.get_command_safety("ws product-intake --confirm")
    expect(
        product_intake_confirm.safety_class == "GUARDED_WRITE",
        report,
        "ws product-intake --confirm helper class should be GUARDED_WRITE",
    )
    expect(
        not is_visible(app, "ws product-intake --confirm", "READ_ONLY_WITH_LOCAL_REPORTS"),
        report,
        "ws product-intake --confirm should not be visible",
    )
    expect(
        not is_visible(app, "ws product-intake --confirm", "SAFE_DRY_RUN"),
        report,
        "ws product-intake --confirm should not be visible",
    )

    product_answer_import = app.get_command_safety("ws product-answer-import")
    expect(
        product_answer_import.safety_class == "GUARDED_WRITE",
        report,
        "ws product-answer-import helper class should be GUARDED_WRITE",
    )
    expect(
        not is_visible(app, "ws product-answer-import", "READ_ONLY_WITH_LOCAL_REPORTS"),
        report,
        "ws product-answer-import should not be visible",
    )
    expect(
        not is_visible(app, "ws product-answer-import", "SAFE_DRY_RUN"),
        report,
        "ws product-answer-import should not be visible",
    )

    product_scope = app.get_command_safety("ws product-scope --dry-run")
    expect(
        product_scope.safety_class == "DRY_RUN_ONLY",
        report,
        "ws product-scope --dry-run helper class should be DRY_RUN_ONLY",
    )
    expect(
        not is_visible(app, "ws product-scope --dry-run", "READ_ONLY_WITH_LOCAL_REPORTS"),
        report,
        "ws product-scope --dry-run should not be visible in READ_ONLY_WITH_LOCAL_REPORTS",
    )
    expect(
        not is_visible(app, "ws product-scope --dry-run", "SAFE_DRY_RUN"),
        report,
        "ws product-scope --dry-run should remain hidden by current exposure policy",
    )

    product_scope_change = app.get_command_safety("ws product-scope-change --dry-run")
    expect(
        product_scope_change.safety_class == "DRY_RUN_ONLY",
        report,
        "ws product-scope-change --dry-run helper class should be DRY_RUN_ONLY",
    )
    expect(
        not is_visible(app, "ws product-scope-change --dry-run", "READ_ONLY_WITH_LOCAL_REPORTS"),
        report,
        "ws product-scope-change --dry-run should not be visible in READ_ONLY_WITH_LOCAL_REPORTS",
    )
    expect(
        not is_visible(app, "ws product-scope-change --dry-run", "SAFE_DRY_RUN"),
        report,
        "ws product-scope-change --dry-run should remain hidden by current exposure policy",
    )

    product_scope_change_confirm = app.get_command_safety("ws product-scope-change --confirm")
    expect(
        product_scope_change_confirm.safety_class == "GUARDED_WRITE",
        report,
        "ws product-scope-change --confirm helper class should be GUARDED_WRITE",
    )
    expect(
        not is_visible(app, "ws product-scope-change --confirm", "READ_ONLY_WITH_LOCAL_REPORTS"),
        report,
        "ws product-scope-change --confirm should not be visible in READ_ONLY_WITH_LOCAL_REPORTS",
    )
    expect(
        not is_visible(app, "ws product-scope-change --confirm", "SAFE_DRY_RUN"),
        report,
        "ws product-scope-change --confirm should remain hidden by current exposure policy",
    )

    product_scope_revision = app.get_command_safety("ws product-scope-revision --dry-run")
    expect(
        product_scope_revision.safety_class == "DRY_RUN_ONLY",
        report,
        "ws product-scope-revision --dry-run helper class should be DRY_RUN_ONLY",
    )
    expect(
        not is_visible(app, "ws product-scope-revision --dry-run", "READ_ONLY_WITH_LOCAL_REPORTS"),
        report,
        "ws product-scope-revision --dry-run should not be visible in READ_ONLY_WITH_LOCAL_REPORTS",
    )
    expect(
        not is_visible(app, "ws product-scope-revision --dry-run", "SAFE_DRY_RUN"),
        report,
        "ws product-scope-revision --dry-run should remain hidden by current exposure policy",
    )

    product_scope_revision_confirm = app.get_command_safety("ws product-scope-revision --confirm")
    expect(
        product_scope_revision_confirm.safety_class == "GUARDED_WRITE",
        report,
        "ws product-scope-revision --confirm helper class should be GUARDED_WRITE",
    )
    expect(
        not is_visible(app, "ws product-scope-revision --confirm", "READ_ONLY_WITH_LOCAL_REPORTS"),
        report,
        "ws product-scope-revision --confirm should not be visible in READ_ONLY_WITH_LOCAL_REPORTS",
    )
    expect(
        not is_visible(app, "ws product-scope-revision --confirm", "SAFE_DRY_RUN"),
        report,
        "ws product-scope-revision --confirm should remain hidden by current exposure policy",
    )

    product_lock_scope = app.get_command_safety("ws product-lock-scope")
    expect(
        product_lock_scope.safety_class == "GUARDED_WRITE",
        report,
        "ws product-lock-scope helper class should be GUARDED_WRITE",
    )
    expect(
        not is_visible(app, "ws product-lock-scope", "READ_ONLY_WITH_LOCAL_REPORTS"),
        report,
        "ws product-lock-scope should not be visible in READ_ONLY_WITH_LOCAL_REPORTS",
    )
    expect(
        not is_visible(app, "ws product-lock-scope", "SAFE_DRY_RUN"),
        report,
        "ws product-lock-scope should not be visible in SAFE_DRY_RUN",
    )

    product_prd = app.get_command_safety("ws product-prd --dry-run")
    expect(
        product_prd.safety_class == "DRY_RUN_ONLY",
        report,
        "ws product-prd --dry-run helper class should be DRY_RUN_ONLY",
    )
    expect(
        product_prd.tui_exposure == "hidden",
        report,
        "ws product-prd --dry-run should be hidden by default",
    )
    expect(
        not is_visible(app, "ws product-prd --dry-run", "SAFE_DRY_RUN"),
        report,
        "ws product-prd --dry-run should not be visible in SAFE_DRY_RUN",
    )

    product_prd_write = app.get_command_safety("ws product-prd --confirm")
    expect(
        product_prd_write.safety_class == "GUARDED_WRITE",
        report,
        "ws product-prd --confirm helper class should be GUARDED_WRITE",
    )
    expect(
        product_prd_write.tui_exposure == "hidden",
        report,
        "ws product-prd --confirm should be hidden by default",
    )
    expect(
        not is_visible(app, "ws product-prd --confirm", "READ_ONLY_WITH_LOCAL_REPORTS"),
        report,
        "ws product-prd --confirm should not be visible in READ_ONLY_WITH_LOCAL_REPORTS",
    )
    expect(
        not is_visible(app, "ws product-prd --confirm", "SAFE_DRY_RUN"),
        report,
        "ws product-prd --confirm should not be visible in SAFE_DRY_RUN",
    )

    product_prd_review = app.get_command_safety("ws product-prd-review --dry-run")
    expect(
        product_prd_review.safety_class == "DRY_RUN_ONLY",
        report,
        "ws product-prd-review --dry-run helper class should be DRY_RUN_ONLY",
    )
    expect(
        product_prd_review.tui_exposure == "hidden",
        report,
        "ws product-prd-review --dry-run should be hidden by default",
    )
    expect(
        not is_visible(app, "ws product-prd-review --dry-run", "SAFE_DRY_RUN"),
        report,
        "ws product-prd-review --dry-run should not be visible in SAFE_DRY_RUN",
    )

    product_prd_approve = app.get_command_safety("ws product-prd-approve")
    expect(
        product_prd_approve.safety_class == "GUARDED_WRITE",
        report,
        "ws product-prd-approve helper class should be GUARDED_WRITE",
    )
    expect(
        product_prd_approve.tui_exposure == "hidden",
        report,
        "ws product-prd-approve should be hidden by default",
    )
    expect(
        not is_visible(app, "ws product-prd-approve", "READ_ONLY_WITH_LOCAL_REPORTS"),
        report,
        "ws product-prd-approve should not be visible in READ_ONLY_WITH_LOCAL_REPORTS",
    )
    expect(
        not is_visible(app, "ws product-prd-approve", "SAFE_DRY_RUN"),
        report,
        "ws product-prd-approve should not be visible in SAFE_DRY_RUN",
    )

    product_prd_status = app.get_command_safety("ws product-prd-status")
    expect(
        product_prd_status.safety_class == "PURE_READ",
        report,
        "ws product-prd-status helper class should be PURE_READ",
    )
    expect(
        product_prd_status.tui_exposure == "visible",
        report,
        "ws product-prd-status should be visible by default",
    )
    expect(
        is_visible(app, "ws product-prd-status", "READ_ONLY_WITH_LOCAL_REPORTS"),
        report,
        "ws product-prd-status should be visible in READ_ONLY_WITH_LOCAL_REPORTS",
    )
    expect(
        is_visible(app, "ws product-prd-status", "SAFE_DRY_RUN"),
        report,
        "ws product-prd-status should be visible in SAFE_DRY_RUN",
    )

    product_wireframe = app.get_command_safety("ws product-wireframe --dry-run")
    expect(
        product_wireframe.safety_class == "DRY_RUN_ONLY",
        report,
        "ws product-wireframe --dry-run helper class should be DRY_RUN_ONLY",
    )
    expect(
        product_wireframe.tui_exposure == "hidden",
        report,
        "ws product-wireframe --dry-run should be hidden by default",
    )
    expect(
        not is_visible(app, "ws product-wireframe --dry-run", "READ_ONLY_WITH_LOCAL_REPORTS"),
        report,
        "ws product-wireframe --dry-run should not be visible in READ_ONLY_WITH_LOCAL_REPORTS",
    )
    expect(
        not is_visible(app, "ws product-wireframe --dry-run", "SAFE_DRY_RUN"),
        report,
        "ws product-wireframe --dry-run should not be visible in SAFE_DRY_RUN",
    )

    for command in ("ws product-list", "ws product-status"):
        safety = app.get_command_safety(command)
        expect(safety.safety_class == "PURE_READ", report, f"{command}: helper class should be PURE_READ")
        expect(is_visible(app, command, "READ_ONLY_WITH_LOCAL_REPORTS"), report, f"{command}: should be visible")

    safety = app.get_command_safety("ws product-help")
    expect(safety.safety_class == "PURE_READ", report, "ws product-help helper class should be PURE_READ")
    expect(is_visible(app, "ws product-help", "READ_ONLY_WITH_LOCAL_REPORTS"), report, "ws product-help should be visible")

    for command in ("ws feature-status", "ws stronghold-status", "ws handoff-status"):
        safety = app.get_command_safety(command)
        expect(safety.safety_class == "PURE_READ", report, f"{command}: helper class should be PURE_READ")
        expect(is_visible(app, command, "READ_ONLY_WITH_LOCAL_REPORTS"), report, f"{command}: should be visible")

    for command in ("ws build --dry-run", "ws agent-run --dry-run"):
        safety = app.get_command_safety(command)
        expect(safety.safety_class == "DRY_RUN_ONLY", report, f"{command}: helper class should be DRY_RUN_ONLY")
        expect(not is_visible(app, command, "READ_ONLY_STRICT"), report, f"{command}: must not be visible in READ_ONLY_STRICT")
        if safety.tui_exposure in VISIBLE_EXPOSURES:
            expect(is_visible(app, command, "SAFE_DRY_RUN"), report, f"{command}: visible dry-run should be visible in SAFE_DRY_RUN")
        else:
            expect(not is_visible(app, command, "SAFE_DRY_RUN"), report, f"{command}: hidden dry-run should remain hidden")

    missing = app.get_command_safety("ws definitely-not-a-command")
    expect(missing.safety_class == "UNKNOWN", report, "missing command should classify as UNKNOWN")
    expect(missing.tui_exposure == "hidden", report, "missing command should be hidden")
    expect(not is_visible(app, "ws definitely-not-a-command", "SAFE_DRY_RUN"), report, "missing command should not be visible")

    for command, entry in commands.items():
        if entry.get("safety_class") == "PROVIDER_CALL" or entry.get("external_provider_or_cloud"):
            expect(not is_visible(app, command, "READ_ONLY_WITH_LOCAL_REPORTS"), report, f"{command}: provider command visible in READ_ONLY_WITH_LOCAL_REPORTS")
            expect(not is_visible(app, command, "SAFE_DRY_RUN"), report, f"{command}: provider command visible in SAFE_DRY_RUN")


def print_summary(commands: dict[str, Any], report: VisibilityReport) -> None:
    class_counts = Counter(entry.get("safety_class", "INVALID") for entry in commands.values())
    exposure_counts = Counter(entry.get("tui_exposure", "INVALID") for entry in commands.values())

    print("TUI Action Visibility Validation")
    print("================================")
    print(f"Manifest: {MANIFEST_PATH}")
    print(f"Commands tested: {len(commands)}")
    print("")
    print("Counts by safety class:")
    for name in sorted(class_counts):
        print(f"- {name}: {class_counts[name]}")
    print("")
    print("Counts by TUI exposure:")
    for name in sorted(exposure_counts):
        print(f"- {name}: {exposure_counts[name]}")
    print("")
    print(f"Notes: {len(report.notes)}")
    for note in report.notes:
        print(f"- NOTE: {note}")
    print("")
    print(f"Visibility mismatches: {len(report.errors)}")
    for error in report.errors:
        print(f"- ERROR: {error}")
    print("")
    print(f"Result: {'FAIL' if report.errors else 'PASS'}")


def main() -> int:
    report = VisibilityReport()
    commands = load_manifest(report)
    app = import_tui_app(report) if commands else None
    if app is not None:
        validate_class_rules(commands, app, report)
        validate_known_commands(commands, app, report)

    print_summary(commands, report)
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

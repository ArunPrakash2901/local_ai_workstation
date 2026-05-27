#!/usr/bin/env python3
"""Tests for the unified workstation status dashboard."""

from __future__ import annotations

import contextlib
import importlib.util
import io
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "scripts" / "workstation_status.py"


def load_status_module():
    spec = importlib.util.spec_from_file_location("workstation_status", STATUS_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"could not load {STATUS_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_status(module, root: Path) -> tuple[int, str]:
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        rc = int(module.main(["status", "--root", str(root)]))
    return rc, stdout.getvalue()


def fixture_records() -> dict[str, list[dict[str, object]]]:
    return {
        "exchange_lane/result_packets": [{"result_id": "res_1", "result_status": "IMPORTED_PENDING_REVIEW", "trusted": False}],
        "exchange_lane/result_validations": [{"validation_id": "val_1", "result_id": "res_1", "validation_status": "VALIDATION_BLOCKED"}],
        "exchange_lane/loop_decisions": [{"loop_decision_id": "loop_1", "validation_id": "val_1", "decision": "BLOCKED_NEEDS_OPERATOR"}],
        "exchange_lane/dispatch_plans": [{"dispatch_plan_id": "dp_1", "planned_status": "PLANNED_NOT_DISPATCHED"}],
        "exchange_lane/packets": [{"packet_id": "xp_1", "packet_status": "APPROVED_FOR_DISPATCH_PLANNING"}],
        "runtime_lane/sessions": [{"session_id": "s_1", "status": "READY"}],
        "runtime_lane/assignments": [{"assignment_id": "asn_1", "assignment_status": "ASSIGNED_NOT_STARTED"}],
        "runtime_lane/blockers": [],
        "execution_lane/runs": [{"run_id": "run_1", "run_status": "PREPARED_NOT_EXECUTED"}],
        "execution_lane/worker_task_packets": [{"task_packet_id": "task_1"}],
        "execution_lane/handoff_previews": [],
    }


def run_with_fixtures(
    module,
    *,
    records: dict[str, list[dict[str, object]]] | None = None,
    adapters: dict[str, str] | None = None,
    injected_warning: str = "",
) -> str:
    records = records or fixture_records()
    adapters = adapters or {"codex_cli": "disabled", "gemini_cli": "disabled", "ollama_local": "planned"}

    def fake_json_records(_root: Path, relative_dir: str, warnings: list[str]) -> list[dict[str, object]]:
        if injected_warning and relative_dir == "exchange_lane/result_packets":
            warnings.append(injected_warning)
        return [dict(item) for item in records.get(relative_dir, [])]

    reports = {
        "MVP_FINAL_RELEASE_AUDIT.md": True,
        "MVP_PATH_LENGTH_HARDENING_REPORT.md": True,
        "MVP_REAL_CODEX_ACCEPTANCE_REPORT.md": True,
        "MVP_REAL_GEMINI_ACCEPTANCE_REPORT.md": True,
    }
    with (
        mock.patch.object(module, "json_records", side_effect=fake_json_records),
        mock.patch.object(module, "adapter_status", return_value=adapters),
        mock.patch.object(module, "report_status", return_value=("PASS", reports)),
        mock.patch.object(module, "git_alignment", return_value="aligned"),
        mock.patch.object(module, "generated_artifact_summary", return_value=(3, 3)),
    ):
        return module.build_status(Path("unused"))


def snapshot_files(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_current_repo_status_returns(module) -> None:
    rc, output = run_status(module, ROOT)
    assert_true(rc == 0, "current repo status should exit 0")
    assert_true("# Local AI Workstation Status" in output, "status output should include title")


def test_adapter_enabled_warnings(module) -> None:
    output = run_with_fixtures(module, adapters={"codex_cli": "enabled (codex)", "gemini_cli": "disabled", "ollama_local": "planned"})
    assert_true("codex_cli: enabled" in output, "codex enabled warning should be visible")
    assert_true("warning: real adapter enabled" in output, "enabled adapter warning should be visible")

    output = run_with_fixtures(module, adapters={"codex_cli": "disabled", "gemini_cli": "enabled (gemini)", "ollama_local": "planned"})
    assert_true("gemini_cli: enabled" in output, "gemini enabled warning should be visible")


def test_review_queue_detection(module) -> None:
    output = run_with_fixtures(module)
    assert_true("autonomy mode: MANUAL_REVIEW_ONLY" in output, "autonomy mode should be reported")
    assert_true("raw imported results: 1" in output, "raw imported result count should be detected")
    assert_true("blocked validations: 1" in output, "blocked validation count should be detected")
    assert_true("ready-for-operator-review summaries: 0" in output, "ready-for-operator-review summaries count should be detected")
    assert_true("BLOCKED_NEEDS_OPERATOR decisions: 1" in output, "blocked loop decision should be detected")


def test_malformed_json_warning(module) -> None:
    output = run_with_fixtures(module, injected_warning="malformed JSON: exchange_lane/result_packets/bad.json")
    assert_true("## Warnings" in output, "warnings section should be rendered")
    assert_true("malformed JSON" in output, "malformed JSON warning should be visible")


def test_status_is_pure_read(module) -> None:
    watched = [
        ROOT / "scripts" / "workstation_status.py",
        ROOT / "scripts" / "ws",
        ROOT / "registry" / "ws_command_safety.yaml",
    ]
    before = {str(path): path.read_text(encoding="utf-8", errors="replace") for path in watched}
    rc, _output = run_status(module, ROOT)
    after = {str(path): path.read_text(encoding="utf-8", errors="replace") for path in watched}
    assert_true(rc == 0, "pure-read status should exit 0")
    assert_true(before == after, "status command should not write or mutate source files")


def test_ws_route_and_registry_present() -> None:
    wrapper = (ROOT / "scripts/ws").read_text(encoding="utf-8")
    registry = (ROOT / "registry/ws_command_safety.yaml").read_text(encoding="utf-8")
    assert_true("workstation)" in wrapper, "ws wrapper should include workstation route")
    assert_true("workstation_status.py" in wrapper, "ws wrapper should call workstation_status.py")
    assert_true("ws workstation status:" in registry, "safety registry should include ws workstation status")
    assert_true("safety_class: PURE_READ" in registry.split("ws workstation status:", 1)[1].split("\n  ws ", 1)[0], "workstation status should be PURE_READ")


def main() -> int:
    module = load_status_module()
    tests = (
        test_current_repo_status_returns,
        test_adapter_enabled_warnings,
        test_review_queue_detection,
        test_malformed_json_warning,
        test_status_is_pure_read,
    )
    for test in tests:
        test(module)
        print(f"PASS: {test.__name__}")
    test_ws_route_and_registry_present()
    print("PASS: test_ws_route_and_registry_present")
    print("Workstation status validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

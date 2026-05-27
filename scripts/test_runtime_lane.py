#!/usr/bin/env python3
"""Validation for Runtime Session Lane metadata-only workflows."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import stat
import sys
import tempfile
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LANE_ROOT = ROOT / "runtime_lane"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"could not load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def copy_lane_scaffold(target: Path) -> None:
    for folder in ("contracts", "adapters"):
        shutil.copytree(LANE_ROOT / folder, target / folder)
    for folder in ("sessions", "blockers", "assignments", "workload_reports", "reports", "tools", "examples"):
        (target / folder).mkdir(parents=True, exist_ok=True)


def remove_tree(path: Path) -> None:
    def reset_permissions(function, target, _exc_info):
        os.chmod(target, stat.S_IWRITE | stat.S_IREAD)
        function(target)

    shutil.rmtree(path, onexc=reset_permissions)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    runtime_session = load_module("runtime_session", LANE_ROOT / "tools" / "runtime_session.py")
    audit_runtime_lane = load_module("audit_runtime_lane", LANE_ROOT / "tools" / "audit_runtime_lane.py")

    assert_true("adapter-list" in runtime_session.build_parser().format_help(), "help should expose adapter-list")
    assert_true("assignment-list" in runtime_session.build_parser().format_help(), "help should expose assignment-list")
    assert_true("workload" in runtime_session.build_parser().format_help(), "help should expose workload")
    assert_true("--root" in audit_runtime_lane.build_parser().format_help(), "audit should expose --root")

    real_audit = audit_runtime_lane.audit_runtime_lane(LANE_ROOT)
    assert_true(not real_audit.errors, "initial Runtime Lane audit should pass: " + "; ".join(real_audit.errors))

    source_text = (LANE_ROOT / "tools" / "runtime_session.py").read_text(encoding="utf-8")
    forbidden_terms = ("subprocess", "os.system", "Popen", "git checkout", "git commit", "git push", "git branch")
    for term in forbidden_terms:
        assert_true(term not in source_text, f"runtime_session.py should not contain execution term: {term}")

    codex_temp = Path.home() / ".codex" / "memories"
    temp_parent = codex_temp if codex_temp.is_dir() else Path(tempfile.gettempdir())
    tmp_root = temp_parent / f"runtime_lane_test_{uuid.uuid4().hex}"
    try:
        tmp_root.mkdir()
        test_root = tmp_root / "runtime_lane"
        copy_lane_scaffold(test_root)
        repo_root = test_root.parent
        discovery_queue = repo_root / "discovery_lane" / "execution_queues" / "positive_path_example_execution_queue.json"
        product_plan = repo_root / "product_development_lane" / "implementation_plans" / "positive_path_example_implementation_plan.md"
        product_manifest = repo_root / "product_development_lane" / "manifests" / "positive_path_example_product_development_manifest.json"
        review_manifest = repo_root / "product_development_lane" / "review_artifacts" / "manifests" / "positive_path_example_review_artifact_manifest.json"
        design_run = repo_root / "products" / "portfolio-website-redesign" / "design_runs" / "open_design" / "open-design-render-v1" / "design_run.yaml"
        write_text(discovery_queue, '{"set_id":"positive_path_example","queue_status":"READY_FOR_EXECUTION_LANE"}')
        write_text(product_plan, "# Implementation Plan\n")
        write_text(product_manifest, "{}\n")
        write_text(review_manifest, "{}\n")
        write_text(design_run, "run_id: open-design-render-v1\n")

        with contextlib.redirect_stdout(io.StringIO()) as output:
            rc = runtime_session.main(["adapter-list", "--root", str(test_root)])
        assert_true(rc == 0, "adapter-list should pass")
        assert_true("codex_cli" in output.getvalue(), "adapter-list should show codex_cli")
        assert_true("ollama_local" in output.getvalue(), "adapter-list should show ollama_local")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            rc = runtime_session.main(["help"])
        assert_true(rc == 0, "help should pass")
        help_text = output.getvalue()
        assert_true("assignment-list" in help_text, "help should mention assignment-list")
        assert_true("workload" in help_text, "help should mention workload")

        with contextlib.redirect_stdout(io.StringIO()):
            rc = runtime_session.main(
                [
                    "register",
                    "--root",
                    str(test_root),
                    "--session-id",
                    "codex-product-phase",
                    "--adapter",
                    "codex_cli",
                    "--label",
                    "Codex product phase",
                    "--cwd",
                    "D:/_ai_brain",
                    "--lane",
                    "Product Lane",
                    "--task",
                    "Review product packet",
                ]
            )
        assert_true(rc == 0, "register should pass")
        session_path = test_root / "sessions" / "codex-product-phase.json"
        assert_true(session_path.exists(), "register should create session JSON")
        session = json.loads(session_path.read_text(encoding="utf-8"))
        assert_true(session["commit_allowed"] is False, "commit should default false")
        assert_true(session["push_allowed"] is False, "push should default false")
        assert_true(session["merge_allowed"] is False, "merge should default false")
        assert_true(session["automated_terminal_control"] is False, "automated terminal control should default false")

        with contextlib.redirect_stdout(io.StringIO()):
            rc = runtime_session.main(
                [
                    "register",
                    "--root",
                    str(test_root),
                    "--session-id",
                    "ollama-local-phase",
                    "--adapter",
                    "ollama_local",
                    "--label",
                    "Ollama local model phase",
                    "--cwd",
                    "D:/_ai_brain",
                    "--lane",
                    "Exchange Lane",
                    "--task",
                    "Local model summary through Exchange only",
                ]
            )
        assert_true(rc == 0, "ollama_local register should pass")
        ollama_session_path = test_root / "sessions" / "ollama-local-phase.json"
        assert_true(ollama_session_path.exists(), "ollama_local register should create session JSON")
        ollama_session = json.loads(ollama_session_path.read_text(encoding="utf-8"))
        assert_true(ollama_session["adapter_type"] == "ollama_local", "ollama session should preserve adapter_type")
        assert_true(ollama_session["endpoint"] == "http://127.0.0.1:11434/v1", "ollama session should include endpoint")
        assert_true(ollama_session["model"] == "hermes3:8b", "ollama session should include model")
        assert_true(ollama_session["resource_status"] == "LOCAL_RESOURCE_UNKNOWN", "ollama session should include resource status")
        assert_true(ollama_session["trusted_output_default"] is False, "ollama session output should default untrusted")

        with contextlib.redirect_stderr(io.StringIO()):
            rc = runtime_session.main(
                [
                    "assign",
                    "--root",
                    str(test_root),
                    "--session-id",
                    "missing-session",
                    "--task-source",
                    str(product_plan),
                    "--label",
                    "Should fail",
                    "--type",
                    "product_development_implementation_plan",
                ]
            )
        assert_true(rc == 1, "assign should require an existing session")

        with contextlib.redirect_stderr(io.StringIO()):
            rc = runtime_session.main(
                [
                    "assign",
                    "--root",
                    str(test_root),
                    "--session-id",
                    "codex-product-phase",
                    "--task-source",
                    str(repo_root / "missing.md"),
                    "--label",
                    "Missing source",
                    "--type",
                    "product_development_implementation_plan",
                ]
            )
        assert_true(rc == 1, "assign should reject missing task source")

        with contextlib.redirect_stdout(io.StringIO()):
            rc = runtime_session.main(
                [
                    "update-status",
                    "--root",
                    str(test_root),
                    "--session-id",
                    "codex-product-phase",
                    "--status",
                    "RUNNING",
                    "--note",
                    "Operator started manual CLI session.",
                ]
            )
        assert_true(rc == 0, "update-status should pass")
        session = json.loads(session_path.read_text(encoding="utf-8"))
        assert_true(session["status"] == "RUNNING", "status should update")

        with contextlib.redirect_stdout(io.StringIO()):
            rc = runtime_session.main(
                [
                    "assign",
                    "--root",
                    str(test_root),
                    "--session-id",
                    "codex-product-phase",
                    "--task-source",
                    str(product_plan),
                    "--label",
                    "Implementation plan review",
                    "--type",
                    "product_development_implementation_plan",
                ]
            )
        assert_true(rc == 0, "assign should pass")
        assignment_files = list((test_root / "assignments").glob("*.json"))
        assert_true(len(assignment_files) == 1, "assignment JSON should be created")
        assert_true(len(assignment_files[0].stem) <= 96, "assignment filename stem should stay <= 96 chars")
        assignment = json.loads(assignment_files[0].read_text(encoding="utf-8"))
        assert_true(assignment["assignment_status"] == "ASSIGNED_NOT_STARTED", "assignment should default to assigned-not-started")
        assert_true(assignment["execution_allowed"] is False, "execution_allowed should default false")
        assert_true(assignment["commit_allowed"] is False, "assignment commit should default false")
        assert_true(assignment["push_allowed"] is False, "assignment push should default false")
        assert_true(assignment["merge_allowed"] is False, "assignment merge should default false")
        assert_true(len(assignment["task_source_checksum"]) == 64, "file task source should get sha256 checksum")

        with contextlib.redirect_stderr(io.StringIO()):
            rc = runtime_session.main(
                [
                    "assign",
                    "--root",
                    str(test_root),
                    "--session-id",
                    "codex-product-phase",
                    "--task-source",
                    str(product_plan),
                    "--label",
                    "Implementation plan review duplicate",
                    "--type",
                    "product_development_implementation_plan",
                ]
            )
        assert_true(rc == 1, "duplicate assignment should be rejected by default")

        with contextlib.redirect_stdout(io.StringIO()) as output:
            rc = runtime_session.main(["assignment-list", "--root", str(test_root)])
        assert_true(rc == 0, "assignment-list should pass")
        assert_true(assignment["assignment_id"] in output.getvalue(), "assignment-list should show assignment id")
        assert_true("Implementation plan review" in output.getvalue(), "assignment-list should show label")

        with contextlib.redirect_stdout(io.StringIO()) as output:
            rc = runtime_session.main([
                "assignment-status",
                "--root",
                str(test_root),
                "--assignment-id",
                assignment["assignment_id"],
            ])
        assert_true(rc == 0, "assignment-status should pass")
        assert_true("assignment_status: ASSIGNED_NOT_STARTED" in output.getvalue(), "assignment-status should show status")
        assert_true("session_status: RUNNING" in output.getvalue(), "assignment-status should show linked session status")

        with contextlib.redirect_stdout(io.StringIO()):
            rc = runtime_session.main(
                [
                    "update-assignment",
                    "--root",
                    str(test_root),
                    "--assignment-id",
                    assignment["assignment_id"],
                    "--status",
                    "COMPLETED_PENDING_REVIEW",
                    "--note",
                    "Plan reviewed and pending operator signoff.",
                ]
            )
        assert_true(rc == 0, "update-assignment should pass")
        assignment = json.loads(assignment_files[0].read_text(encoding="utf-8"))
        assert_true(assignment["assignment_status"] == "COMPLETED_PENDING_REVIEW", "assignment status should update")

        with contextlib.redirect_stdout(io.StringIO()):
            rc = runtime_session.main(
                [
                    "report-blocker",
                    "--root",
                    str(test_root),
                    "--session-id",
                    "codex-product-phase",
                    "--type",
                    "WAITING_FOR_PERMISSION_PROMPT",
                    "--description",
                    "CLI asks to approve file write.",
                ]
            )
        assert_true(rc == 0, "report-blocker should pass")
        blockers = list((test_root / "blockers").glob("*.json"))
        assert_true(len(blockers) == 1, "blocker JSON should be created")
        blocker = json.loads(blockers[0].read_text(encoding="utf-8"))
        assert_true(blocker["operator_action_required"], "blocker should require operator action")
        session = json.loads(session_path.read_text(encoding="utf-8"))
        assert_true(session["status"] == "WAITING_FOR_OPERATOR_APPROVAL", "permission blocker should update session")

        with contextlib.redirect_stdout(io.StringIO()):
            rc = runtime_session.main(
                [
                    "assign",
                    "--root",
                    str(test_root),
                    "--session-id",
                    "codex-product-phase",
                    "--task-source",
                    str(design_run),
                    "--label",
                    "Design run review while blocked",
                    "--type",
                    "product_design_run_packet",
                ]
            )
        assert_true(rc == 0, "assign should still write blocked assignment")
        blocked_assignment = None
        for candidate in (test_root / "assignments").glob("*.json"):
            candidate_data = json.loads(candidate.read_text(encoding="utf-8"))
            if candidate_data.get("assignment_label") == "Design run review while blocked":
                blocked_assignment = candidate
                blocked_assignment_data = candidate_data
                break
        assert_true(blocked_assignment is not None, "blocked assignment should be created")
        assert_true(blocked_assignment_data["assignment_status"] == "WAITING_FOR_OPERATOR_APPROVAL", "blocked session should mark assignment waiting for approval")

        with contextlib.redirect_stdout(io.StringIO()) as output:
            rc = runtime_session.main(["workload", "--root", str(test_root)])
        assert_true(rc == 0, "workload should pass")
        workload_text = output.getvalue()
        assert_true("Runtime Workload Dashboard" in workload_text, "workload should render dashboard")
        assert_true("codex-product-phase" in workload_text, "workload should show session id")
        assert_true("blocked_assignments" in workload_text, "workload should show blocked assignments")
        assert_true("completed_pending_review" in workload_text, "workload should show pending review assignments")

        with contextlib.redirect_stdout(io.StringIO()) as output:
            rc = runtime_session.main(["unassigned", "--root", str(test_root)])
        assert_true(rc == 0, "unassigned should pass")
        unassigned_text = output.getvalue()
        assert_true(str(discovery_queue) in unassigned_text, "unassigned should list discovery queue candidate")
        assert_true(str(product_plan) not in unassigned_text, "assigned source should not appear in unassigned output")

        with contextlib.redirect_stdout(io.StringIO()):
            rc = runtime_session.main(["workload", "--root", str(test_root), "--write-report"])
        assert_true(rc == 0, "workload write-report should pass")
        report_path = test_root / "workload_reports" / "runtime_workload_report.md"
        assert_true(report_path.exists(), "workload report should be written")
        assert_true("Safety Reminder" in report_path.read_text(encoding="utf-8"), "workload report should include safety reminder")

        with contextlib.redirect_stdout(io.StringIO()):
            rc = runtime_session.main(
                [
                    "resolve-blocker",
                    "--root",
                    str(test_root),
                    "--blocker-id",
                    blocker["blocker_id"],
                    "--resolution",
                    "Operator denied broad write request.",
                ]
            )
        assert_true(rc == 0, "resolve-blocker should pass")
        blocker = json.loads(blockers[0].read_text(encoding="utf-8"))
        assert_true(blocker["resolved_at"], "blocker should record resolution timestamp")
        session = json.loads(session_path.read_text(encoding="utf-8"))
        assert_true(session["status"] == "READY", "session should return to READY when blocker is resolved")

        with contextlib.redirect_stdout(io.StringIO()) as output:
            rc = runtime_session.main(["status", "--root", str(test_root)])
        assert_true(rc == 0, "status should pass")
        assert_true("codex-product-phase" in output.getvalue(), "status should list session")
        assert_true("blockers: 1" in output.getvalue(), "status should count blocker")

        with contextlib.redirect_stderr(io.StringIO()):
            rc = runtime_session.main(
                [
                    "register",
                    "--root",
                    str(test_root),
                    "--session-id",
                    "bad-adapter",
                    "--adapter",
                    "browser_chatgpt",
                    "--label",
                    "bad",
                    "--cwd",
                    "D:/_ai_brain",
                    "--lane",
                    "Runtime",
                    "--task",
                    "bad",
                ]
            )
        assert_true(rc == 1, "invalid adapter should be rejected")

        with contextlib.redirect_stderr(io.StringIO()):
            rc = runtime_session.main(
                [
                    "update-status",
                    "--root",
                    str(test_root),
                    "--session-id",
                    "codex-product-phase",
                    "--status",
                    "AUTO_EXECUTING",
                    "--note",
                    "bad",
                ]
            )
        assert_true(rc == 1, "invalid session status should be rejected")

        with contextlib.redirect_stderr(io.StringIO()):
            rc = runtime_session.main(
                [
                    "report-blocker",
                    "--root",
                    str(test_root),
                    "--session-id",
                    "codex-product-phase",
                    "--type",
                    "AUTO_APPROVAL",
                    "--description",
                    "bad",
                ]
            )
        assert_true(rc == 1, "invalid blocker type should be rejected")

        assignment = json.loads(assignment_files[0].read_text(encoding="utf-8"))
        assert_true(assignment["execution_allowed"] is False, "assignment execution should remain false")
        assert_true(assignment["commit_allowed"] is False, "assignment commit should remain false")
        assert_true(assignment["push_allowed"] is False, "assignment push should remain false")
        assert_true(assignment["merge_allowed"] is False, "assignment merge should remain false")

        audit = audit_runtime_lane.audit_runtime_lane(test_root)
        assert_true(not audit.errors, "audit should pass after fixture: " + "; ".join(audit.errors))
    finally:
        if tmp_root.exists() and temp_parent.resolve() in tmp_root.resolve().parents:
            remove_tree(tmp_root)

    print("Runtime Session Lane validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

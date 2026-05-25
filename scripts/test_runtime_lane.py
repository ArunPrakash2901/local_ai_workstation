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
    for folder in ("sessions", "blockers", "reports", "tools", "examples"):
        (target / folder).mkdir(parents=True, exist_ok=True)


def remove_tree(path: Path) -> None:
    def reset_permissions(function, target, _exc_info):
        os.chmod(target, stat.S_IWRITE | stat.S_IREAD)
        function(target)

    shutil.rmtree(path, onexc=reset_permissions)


def main() -> int:
    runtime_session = load_module("runtime_session", LANE_ROOT / "tools" / "runtime_session.py")
    audit_runtime_lane = load_module("audit_runtime_lane", LANE_ROOT / "tools" / "audit_runtime_lane.py")

    assert_true("adapter-list" in runtime_session.build_parser().format_help(), "help should expose adapter-list")
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

        with contextlib.redirect_stdout(io.StringIO()) as output:
            rc = runtime_session.main(["adapter-list", "--root", str(test_root)])
        assert_true(rc == 0, "adapter-list should pass")
        assert_true("codex_cli" in output.getvalue(), "adapter-list should show codex_cli")

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

        audit = audit_runtime_lane.audit_runtime_lane(test_root)
        assert_true(not audit.errors, "audit should pass after fixture: " + "; ".join(audit.errors))
    finally:
        if tmp_root.exists() and temp_parent.resolve() in tmp_root.resolve().parents:
            remove_tree(tmp_root)

    print("Runtime Session Lane validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""No-write local safety checks for workstation command safety metadata."""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path


os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]

AST_CHECKS = (
    ROOT / "scripts" / "check_local_safety.py",
    ROOT / "scripts" / "validate_ws_command_safety.py",
    ROOT / "scripts" / "test_tui_action_visibility.py",
    ROOT / "scripts" / "check_ws_manifest_drift.py",
    ROOT / "scripts" / "test_next_safe_action.py",
    ROOT / "scripts" / "test_action_dispatcher.py",
    ROOT / "scripts" / "test_product_registry.py",
    ROOT / "scripts" / "test_product_help.py",
    ROOT / "scripts" / "test_product_intake_questions.py",
    ROOT / "scripts" / "test_product_intake_start.py",
    ROOT / "scripts" / "test_product_answer_import.py",
    ROOT / "scripts" / "test_product_scope.py",
    ROOT / "scripts" / "test_product_scope_change.py",
    ROOT / "scripts" / "test_product_scope_change_confirm.py",
    ROOT / "scripts" / "test_product_scope_revision.py",
    ROOT / "scripts" / "test_product_scope_revision_confirm.py",
    ROOT / "scripts" / "test_product_scope_lock.py",
    ROOT / "scripts" / "test_product_prd.py",
    ROOT / "scripts" / "test_product_prd_write.py",
    ROOT / "scripts" / "test_product_prd_review.py",
    ROOT / "scripts" / "test_product_prd_approval.py",
    ROOT / "scripts" / "test_product_prd_status.py",
    ROOT / "scripts" / "test_product_wireframe.py",
    ROOT / "scripts" / "product_registry.py",
    ROOT / "scripts" / "product_intake_questions.py",
    ROOT / "scripts" / "product_intake_artifacts.py",
    ROOT / "scripts" / "product_answer_import.py",
    ROOT / "scripts" / "product_scope.py",
    ROOT / "scripts" / "product_scope_change.py",
    ROOT / "scripts" / "product_scope_revision.py",
    ROOT / "scripts" / "product_scope_lock.py",
    ROOT / "scripts" / "product_prd.py",
    ROOT / "scripts" / "product_prd_review.py",
    ROOT / "scripts" / "product_prd_approval.py",
    ROOT / "scripts" / "product_prd_status.py",
    ROOT / "scripts" / "product_wireframe.py",
    ROOT / "scripts" / "ws_product_new.py",
    ROOT / "scripts" / "ws_product_list.py",
    ROOT / "scripts" / "ws_product_status.py",
    ROOT / "scripts" / "ws_product_help.py",
    ROOT / "scripts" / "ws_product_questions.py",
    ROOT / "scripts" / "ws_product_intake.py",
    ROOT / "scripts" / "ws_product_answer_import.py",
    ROOT / "scripts" / "ws_product_scope.py",
    ROOT / "scripts" / "ws_product_scope_change.py",
    ROOT / "scripts" / "ws_product_scope_revision.py",
    ROOT / "scripts" / "ws_product_lock_scope.py",
    ROOT / "scripts" / "ws_product_prd.py",
    ROOT / "scripts" / "ws_product_prd_review.py",
    ROOT / "scripts" / "ws_product_prd_approve.py",
    ROOT / "scripts" / "ws_product_prd_status.py",
    ROOT / "scripts" / "ws_product_wireframe.py",
    ROOT / "tui" / "app.py",
    ROOT / "tui" / "next_action.py",
    ROOT / "tui" / "action_dispatcher.py",
)

CHECK_STEPS = (
    ("Command safety manifest validation", ROOT / "scripts" / "validate_ws_command_safety.py"),
    ("TUI action visibility validation", ROOT / "scripts" / "test_tui_action_visibility.py"),
    ("WS manifest drift validation", ROOT / "scripts" / "check_ws_manifest_drift.py"),
    ("Next Safe Action Engine validation", ROOT / "scripts" / "test_next_safe_action.py"),
    ("Safe Action Dispatcher validation", ROOT / "scripts" / "test_action_dispatcher.py"),
    ("Product registry validation", ROOT / "scripts" / "test_product_registry.py"),
    ("Product help validation", ROOT / "scripts" / "test_product_help.py"),
    ("Product intake question bank validation", ROOT / "scripts" / "test_product_intake_questions.py"),
    ("Product intake start validation", ROOT / "scripts" / "test_product_intake_start.py"),
    ("Product answer import validation", ROOT / "scripts" / "test_product_answer_import.py"),
    ("Product scope preview validation", ROOT / "scripts" / "test_product_scope.py"),
    ("Product scope change preview validation", ROOT / "scripts" / "test_product_scope_change.py"),
    ("Product scope change confirm validation", ROOT / "scripts" / "test_product_scope_change_confirm.py"),
    ("Product scope revision preview validation", ROOT / "scripts" / "test_product_scope_revision.py"),
    ("Product scope revision confirm validation", ROOT / "scripts" / "test_product_scope_revision_confirm.py"),
    ("Product scope lock validation", ROOT / "scripts" / "test_product_scope_lock.py"),
    ("Product PRD preview validation", ROOT / "scripts" / "test_product_prd.py"),
    ("Product PRD write validation", ROOT / "scripts" / "test_product_prd_write.py"),
    ("Product PRD review validation", ROOT / "scripts" / "test_product_prd_review.py"),
    ("Product PRD approval validation", ROOT / "scripts" / "test_product_prd_approval.py"),
    ("Product PRD status validation", ROOT / "scripts" / "test_product_prd_status.py"),
    ("Product wireframe validation", ROOT / "scripts" / "test_product_wireframe.py"),
)


def ast_check(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, f"missing: {path}"
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return False, f"{path}: {exc}"
    return True, str(path)


def run_python_step(step_name: str, script_path: Path, env: dict[str, str]) -> int:
    print("")
    print(f"{step_name}:")
    sys.stdout.flush()
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode


def main() -> int:
    print("Local AI Workstation safe local check")
    print("======================================")
    print("Scope: no ws commands, no agents, no models, no providers, no apply flows.")
    print("Bytecode writes disabled via PYTHONDONTWRITEBYTECODE=1.")
    print("")

    failures: list[str] = []
    print("AST checks:")
    for path in AST_CHECKS:
        ok, message = ast_check(path)
        print(f"- {'PASS' if ok else 'FAIL'} {message}")
        if not ok:
            failures.append(message)

    if failures:
        print("")
        print("Result: FAIL")
        return 1

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for step_name, script_path in CHECK_STEPS:
        rc = run_python_step(step_name, script_path, env)
        if rc != 0:
            print("")
            print(f"Safe local check result: FAIL {script_path.name}_exit={rc}")
            return rc

    print("")
    print("Safe local check result: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

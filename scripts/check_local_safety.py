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
    ROOT / "scripts" / "test_product_prd_revision.py",
    ROOT / "scripts" / "test_product_prd_review.py",
    ROOT / "scripts" / "test_product_prd_approval.py",
    ROOT / "scripts" / "test_product_prd_status.py",
    ROOT / "scripts" / "test_product_wireframe.py",
    ROOT / "scripts" / "test_product_wireframe_review.py",
    ROOT / "scripts" / "test_product_tech_plan.py",
    ROOT / "scripts" / "test_product_tech_plan_review.py",
    ROOT / "scripts" / "test_product_implementation_plan.py",
    ROOT / "scripts" / "test_exchange_registry.py",
    ROOT / "scripts" / "test_exchange_cli.py",
    ROOT / "scripts" / "test_exchange_dispatch.py",
    ROOT / "scripts" / "test_exchange_result_import.py",
    ROOT / "scripts" / "test_exchange_adapter_preview.py",
    ROOT / "scripts" / "test_exchange_codex_adapter.py",
    ROOT / "scripts" / "test_session_registry.py",
    ROOT / "scripts" / "test_session_cli.py",
    ROOT / "scripts" / "test_session_plan.py",
    ROOT / "scripts" / "test_session_plan_confirm.py",
    ROOT / "scripts" / "test_session_start_preview.py",
    ROOT / "scripts" / "test_session_cleanup_preview.py",
    ROOT / "scripts" / "test_exchange_session_preview.py",
    ROOT / "scripts" / "product_registry.py",
    ROOT / "scripts" / "exchange_registry.py",
    ROOT / "scripts" / "exchange_dispatch.py",
    ROOT / "scripts" / "exchange_result_import.py",
    ROOT / "scripts" / "exchange_adapter_preview.py",
    ROOT / "scripts" / "exchange_codex_adapter.py",
    ROOT / "scripts" / "session_registry.py",
    ROOT / "scripts" / "ws_session_plan.py",
    ROOT / "scripts" / "ws_session_start.py",
    ROOT / "scripts" / "ws_session_cleanup.py",
    ROOT / "scripts" / "product_intake_questions.py",
    ROOT / "scripts" / "product_intake_artifacts.py",
    ROOT / "scripts" / "product_answer_import.py",
    ROOT / "scripts" / "product_scope.py",
    ROOT / "scripts" / "product_scope_change.py",
    ROOT / "scripts" / "product_scope_revision.py",
    ROOT / "scripts" / "product_scope_lock.py",
    ROOT / "scripts" / "product_prd.py",
    ROOT / "scripts" / "product_prd_revision.py",
    ROOT / "scripts" / "product_prd_review.py",
    ROOT / "scripts" / "product_prd_approval.py",
    ROOT / "scripts" / "product_prd_status.py",
    ROOT / "scripts" / "product_wireframe.py",
    ROOT / "scripts" / "product_tech_plan.py",
    ROOT / "scripts" / "product_tech_plan_review.py",
    ROOT / "scripts" / "product_implementation_plan.py",
    ROOT / "scripts" / "product_implementation_plan_review.py",
    ROOT / "scripts" / "product_implementation_exchange_preview.py",
    ROOT / "scripts" / "product_design_adapter.py",
    ROOT / "scripts" / "product_design_run.py",
    ROOT / "scripts" / "product_design_run_review.py",
    ROOT / "scripts" / "product_design_runtime_probe.py",
    ROOT / "scripts" / "product_design_install_checklist.py",
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
    ROOT / "scripts" / "ws_product_prd_revision.py",
    ROOT / "scripts" / "ws_product_prd_review.py",
    ROOT / "scripts" / "ws_product_prd_approve.py",
    ROOT / "scripts" / "ws_product_prd_status.py",
    ROOT / "scripts" / "ws_product_wireframe.py",
    ROOT / "scripts" / "ws_product_wireframe_review.py",
    ROOT / "scripts" / "ws_product_tech_plan.py",
    ROOT / "scripts" / "ws_product_tech_plan_review.py",
    ROOT / "scripts" / "ws_product_implementation_plan.py",
    ROOT / "scripts" / "ws_product_implementation_plan_review.py",
    ROOT / "scripts" / "ws_product_implementation_exchange_preview.py",
    ROOT / "scripts" / "ws_product_design_adapter_preview.py",
    ROOT / "scripts" / "ws_product_design_render.py",
    ROOT / "scripts" / "ws_product_design_run_prepare.py",
    ROOT / "scripts" / "ws_product_design_run_status.py",
    ROOT / "scripts" / "ws_product_design_run_review.py",
    ROOT / "scripts" / "ws_product_design_runtime_probe.py",
    ROOT / "scripts" / "ws_product_design_install_checklist.py",
    ROOT / "scripts" / "ws_product_design_runtime_report.py",
    ROOT / "scripts" / "knowledge_inventory.py",
    ROOT / "scripts" / "ws_knowledge_inventory.py",
    ROOT / "scripts" / "test_knowledge_inventory.py",
    ROOT / "scripts" / "test_product_implementation_plan_review.py",
    ROOT / "scripts" / "test_product_implementation_exchange_preview.py",
    ROOT / "scripts" / "test_product_design_adapter_preview.py",
    ROOT / "scripts" / "test_product_design_render.py",
    ROOT / "scripts" / "test_product_design_run_prepare.py",
    ROOT / "scripts" / "test_product_design_run_status.py",
    ROOT / "scripts" / "test_product_design_run_review.py",
    ROOT / "scripts" / "test_product_design_runtime_probe.py",
    ROOT / "scripts" / "test_product_design_install_checklist.py",
    ROOT / "scripts" / "test_product_design_runtime_report.py",
    ROOT / "scripts" / "test_discovery_lane.py",
    ROOT / "scripts" / "test_product_development_lane.py",
    ROOT / "discovery_lane" / "tools" / "ingest_research_reports.py",
    ROOT / "discovery_lane" / "tools" / "approve_phase_packet.py",
    ROOT / "discovery_lane" / "tools" / "discovery_command.py",
    ROOT / "discovery_lane" / "tools" / "audit_discovery_lane.py",
    ROOT / "discovery_lane" / "tools" / "intake_research_set.py",
    ROOT / "discovery_lane" / "tools" / "ingest_research_set.py",
    ROOT / "discovery_lane" / "tools" / "approve_research_set.py",
    ROOT / "discovery_lane" / "tools" / "build_execution_queue.py",
    ROOT / "product_development_lane" / "tools" / "build_product_packet.py",
    ROOT / "product_development_lane" / "tools" / "audit_product_development_lane.py",
    ROOT / "product_development_lane" / "tools" / "product_dev_command.py",
    ROOT / "scripts" / "ws_exchange_new.py",
    ROOT / "scripts" / "ws_exchange_list.py",
    ROOT / "scripts" / "ws_exchange_status.py",
    ROOT / "scripts" / "ws_exchange_dispatch.py",
    ROOT / "scripts" / "ws_exchange_import_result.py",
    ROOT / "scripts" / "ws_exchange_adapter_preview.py",
    ROOT / "scripts" / "ws_session_list.py",
    ROOT / "scripts" / "ws_session_status.py",
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
    ("Product PRD revision validation", ROOT / "scripts" / "test_product_prd_revision.py"),
    ("Product PRD revision confirm validation", ROOT / "scripts" / "test_product_prd_revision_confirm.py"),
    ("Product PRD review validation", ROOT / "scripts" / "test_product_prd_review.py"),
    ("Product PRD approval validation", ROOT / "scripts" / "test_product_prd_approval.py"),
    ("Product PRD status validation", ROOT / "scripts" / "test_product_prd_status.py"),
    ("Product wireframe validation", ROOT / "scripts" / "test_product_wireframe.py"),
    ("Product wireframe review validation", ROOT / "scripts" / "test_product_wireframe_review.py"),
    ("Product technical plan validation", ROOT / "scripts" / "test_product_tech_plan.py"),
    ("Product technical plan review validation", ROOT / "scripts" / "test_product_tech_plan_review.py"),
    ("Product implementation plan validation", ROOT / "scripts" / "test_product_implementation_plan.py"),
    ("Product implementation plan review validation", ROOT / "scripts" / "test_product_implementation_plan_review.py"),
    ("Product implementation exchange preview validation", ROOT / "scripts" / "test_product_implementation_exchange_preview.py"),
    ("Product design adapter preview validation", ROOT / "scripts" / "test_product_design_adapter_preview.py"),
    ("Product design render validation", ROOT / "scripts" / "test_product_design_render.py"),
    ("Product design run prepare validation", ROOT / "scripts" / "test_product_design_run_prepare.py"),
    ("Product design run status validation", ROOT / "scripts" / "test_product_design_run_status.py"),
    ("Product design run review validation", ROOT / "scripts" / "test_product_design_run_review.py"),
    ("Product design runtime probe validation", ROOT / "scripts" / "test_product_design_runtime_probe.py"),
    ("Product design install checklist validation", ROOT / "scripts" / "test_product_design_install_checklist.py"),
    ("Product design runtime report validation", ROOT / "scripts" / "test_product_design_runtime_report.py"),
    ("Discovery Lane validation", ROOT / "scripts" / "test_discovery_lane.py"),
    ("Product Development Lane validation", ROOT / "scripts" / "test_product_development_lane.py"),
    ("Knowledge inventory validation", ROOT / "scripts" / "test_knowledge_inventory.py"),
    ("Exchange registry validation", ROOT / "scripts" / "test_exchange_registry.py"),
    ("Exchange CLI validation", ROOT / "scripts" / "test_exchange_cli.py"),
    ("Exchange dispatch validation", ROOT / "scripts" / "test_exchange_dispatch.py"),
    ("Exchange result import validation", ROOT / "scripts" / "test_exchange_result_import.py"),
    ("Exchange adapter preview validation", ROOT / "scripts" / "test_exchange_adapter_preview.py"),
    ("Exchange codex adapter validation", ROOT / "scripts" / "test_exchange_codex_adapter.py"),
    ("Session registry validation", ROOT / "scripts" / "test_session_registry.py"),
    ("Session CLI validation", ROOT / "scripts" / "test_session_cli.py"),
    ("Session plan validation", ROOT / "scripts" / "test_session_plan.py"),
    ("Session plan confirm validation", ROOT / "scripts" / "test_session_plan_confirm.py"),
    ("Session start preview validation", ROOT / "scripts" / "test_session_start_preview.py"),
    ("Session cleanup preview validation", ROOT / "scripts" / "test_session_cleanup_preview.py"),
    ("Exchange session preview validation", ROOT / "scripts" / "test_exchange_session_preview.py"),
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

#!/usr/bin/env python3
"""Validation for Exchange Lane v0.2 dispatch-planning metadata only."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXCHANGE_LANE_ROOT = ROOT / "exchange_lane"
RUNTIME_LANE_ROOT = ROOT / "runtime_lane"


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


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def remove_tree(path: Path) -> None:
    def reset_permissions(function, target, _exc_info):
        os.chmod(target, stat.S_IWRITE | stat.S_IREAD)
        function(target)

    shutil.rmtree(path, onexc=reset_permissions)


def copy_exchange_scaffold(target: Path) -> None:
    for folder in ("contracts", "tools", "examples"):
        shutil.copytree(EXCHANGE_LANE_ROOT / folder, target / folder)
    for folder in (
        "packets",
        "result_packets",
        "routing",
        "manifests",
        "reports",
        "dispatch_plans",
        "dispatch_plan_reports",
    ):
        (target / folder).mkdir(parents=True, exist_ok=True)
        gitkeep = EXCHANGE_LANE_ROOT / folder / ".gitkeep"
        if gitkeep.is_file():
            shutil.copy2(gitkeep, target / folder / ".gitkeep")


def copy_runtime_scaffold(target: Path) -> None:
    for folder in ("contracts", "tools", "adapters"):
        shutil.copytree(RUNTIME_LANE_ROOT / folder, target / folder)
    for folder in ("sessions", "blockers", "assignments", "workload_reports", "reports", "examples"):
        (target / folder).mkdir(parents=True, exist_ok=True)


def run_main(main_fn, argv: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        rc = int(main_fn(argv))
    return rc, stdout.getvalue(), stderr.getvalue()


def update_session_status(runtime_session, runtime_root: Path, session_id: str, status: str) -> None:
    path = runtime_root / "sessions" / f"{session_id}.json"
    data = read_json(path)
    data["status"] = status
    data["last_updated"] = runtime_session.utc_now()
    runtime_session.write_json(path, data)


def create_session(runtime_session, runtime_root: Path, repo_root: Path, session_id: str, adapter: str) -> Path:
    return runtime_session.register_session(
        runtime_root,
        session_id=session_id,
        adapter=adapter,
        label=f"{adapter} session",
        cwd=str(repo_root),
        lane="Exchange Lane Test",
        task="Plan exchange packet only.",
    )


def create_assignment(runtime_session, runtime_root: Path, session_id: str, task_source: Path, label: str) -> Path:
    return runtime_session.create_assignment(
        runtime_root,
        session_id=session_id,
        task_source=str(task_source),
        label=label,
        task_source_type="product_development_implementation_plan",
    )


def create_packet(exchange_packet, exchange_root: Path, source_artifact: Path, target_adapter: str) -> tuple[Path, str]:
    packet_path = exchange_packet.create_packet(
        exchange_root,
        source_artifact=str(source_artifact),
        source_lane="product_development_lane",
        target_adapter=target_adapter,
        task_type="implementation_planning",
        objective="Plan dispatch metadata only.",
    )
    packet = read_json(packet_path)
    return packet_path, str(packet["packet_id"])


def mark_ready(exchange_packet, exchange_root: Path, packet_id: str) -> None:
    rc, _stdout, stderr = run_main(
        exchange_packet.main,
        ["mark-ready", "--root", str(exchange_root), "--packet-id", packet_id, "--note", "packet reviewed"],
    )
    assert_true(rc == 0, f"mark-ready should pass: {stderr}")


def approve_planning(exchange_packet, exchange_root: Path, packet_id: str, note: str) -> tuple[int, str, str]:
    return run_main(
        exchange_packet.main,
        ["approve-planning", "--root", str(exchange_root), "--packet-id", packet_id, "--note", note],
    )


def plan_for_packet(exchange_root: Path, packet_id: str) -> dict[str, object]:
    matches: list[Path] = []
    for path in (exchange_root / "dispatch_plans").glob("*.json"):
        data = read_json(path)
        if data.get("packet_id") == packet_id:
            matches.append(path)
    assert_true(bool(matches), f"dispatch plan should exist for packet {packet_id}")
    latest = max(matches, key=lambda item: item.stat().st_mtime_ns)
    return read_json(latest)


def plan_packet(
    exchange_dispatch_plan,
    exchange_root: Path,
    runtime_root: Path,
    *,
    packet_id: str,
    session_id: str,
    assignment_id: str,
) -> tuple[int, str, str]:
    return run_main(
        exchange_dispatch_plan.main,
        [
            "plan",
            "--root",
            str(exchange_root),
            "--runtime-root",
            str(runtime_root),
            "--packet-id",
            packet_id,
            "--session-id",
            session_id,
            "--assignment-id",
            assignment_id,
        ],
    )


def run_ws_exchange(repo_root: Path, args: list[str]) -> tuple[int, str, str] | None:
    bash = shutil.which("bash")
    if bash is None:
        return None
    probe = subprocess.run(
        [bash, "-lc", "command -v python3 >/dev/null 2>&1"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    if probe.returncode != 0:
        return None

    # Detect if we are likely using WSL bash on Windows
    bash_lower = bash.lower().replace("/", "\\")
    is_wsl = "microsoft\\windowsapps\\bash.exe" in bash_lower or "system32\\bash.exe" in bash_lower

    def to_bash_path(p: Path) -> str:
        posix = p.as_posix()
        if is_wsl and len(posix) > 1 and posix[1] == ":":
            drive = posix[0].lower()
            return f"/mnt/{drive}{posix[2:]}"
        return posix

    env = os.environ.copy()
    bash_repo_root = to_bash_path(repo_root)
    env["WS_HOME"] = bash_repo_root
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    
    # Always pass --root to ensure we use the temp lane
    ws_args = ["--root", to_bash_path(repo_root / "exchange_lane")] + args
    
    result = subprocess.run(
        [bash, to_bash_path(ROOT / "scripts" / "ws"), "exchange", *ws_args],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr
def main() -> int:
    sys.modules.pop("exchange_packet", None)
    sys.modules.pop("exchange_dispatch_plan", None)
    sys.modules.pop("audit_exchange_lane", None)
    sys.modules.pop("runtime_session", None)
    sys.modules.pop("exchange_command", None)

    exchange_packet = load_module("exchange_packet", EXCHANGE_LANE_ROOT / "tools" / "exchange_packet.py")
    exchange_dispatch_plan = load_module(
        "exchange_dispatch_plan", EXCHANGE_LANE_ROOT / "tools" / "exchange_dispatch_plan.py"
    )
    audit_exchange_lane = load_module("audit_exchange_lane", EXCHANGE_LANE_ROOT / "tools" / "audit_exchange_lane.py")
    runtime_session = load_module("runtime_session", RUNTIME_LANE_ROOT / "tools" / "runtime_session.py")
    exchange_command = load_module("exchange_command", EXCHANGE_LANE_ROOT / "tools" / "exchange_command.py")

    assert_true((EXCHANGE_LANE_ROOT / "contracts" / "dispatch_plan_contract.md").is_file(), "dispatch plan contract should exist")
    assert_true((EXCHANGE_LANE_ROOT / "dispatch_plans").is_dir(), "dispatch_plans folder should exist")
    assert_true((EXCHANGE_LANE_ROOT / "dispatch_plan_reports").is_dir(), "dispatch_plan_reports folder should exist")
    assert_true("plan-status" in exchange_dispatch_plan.build_parser().format_help(), "dispatch plan help should include plan-status")
    assert_true("approve-planning" in exchange_packet.build_parser().format_help(), "packet help should include approve-planning")
    assert_true("dispatch-plan" in exchange_command.build_parser().format_help(), "exchange command help should include dispatch-plan")

    source_text = (EXCHANGE_LANE_ROOT / "tools" / "exchange_dispatch_plan.py").read_text(encoding="utf-8")
    forbidden_terms = ("subprocess", "os.system", "Popen", "git checkout", "git commit", "git push", "git branch")
    for term in forbidden_terms:
        assert_true(term not in source_text, f"exchange_dispatch_plan.py should not contain execution term: {term}")

    subparsers = exchange_command.build_parser()._subparsers._group_actions[0].choices
    assert_true("dispatch" not in subparsers, "ws exchange dispatch must not exist")
    assert_true("run" not in subparsers, "ws exchange run must not exist")
    assert_true("execute" not in subparsers, "ws exchange execute must not exist")
    assert_true("start-session" not in subparsers, "ws exchange start-session must not exist")
    assert_true("import-result" not in subparsers, "ws exchange import-result must not exist")

    codex_temp = Path.home() / ".codex" / "memories"
    temp_parent = codex_temp if codex_temp.is_dir() else Path(tempfile.gettempdir())
    tmp_root = temp_parent / f"exchange_lane_v02_test_{uuid.uuid4().hex}"
    try:
        tmp_root.mkdir()
        repo_root = tmp_root / "repo"
        exchange_root = repo_root / "exchange_lane"
        runtime_root = repo_root / "runtime_lane"
        copy_exchange_scaffold(exchange_root)
        copy_runtime_scaffold(runtime_root)

        source_artifact = repo_root / "product_development_lane" / "implementation_plans" / "test_plan.md"
        write_text(source_artifact, "# implementation plan\n")

        packet_path, draft_packet_id = create_packet(exchange_packet, exchange_root, source_artifact, "codex_cli")
        rc, _stdout, stderr = approve_planning(exchange_packet, exchange_root, draft_packet_id, "should fail")
        assert_true(rc == 1, f"approve-planning should refuse DRAFT packets: {stderr}")

        mark_ready(exchange_packet, exchange_root, draft_packet_id)
        rc, _stdout, stderr = approve_planning(exchange_packet, exchange_root, draft_packet_id, "ready for planning")
        assert_true(rc == 0, f"approve-planning should pass: {stderr}")
        approved_packet = read_json(packet_path)
        assert_true(
            approved_packet["packet_status"] == "APPROVED_FOR_DISPATCH_PLANNING",
            "approve-planning should set APPROVED_FOR_DISPATCH_PLANNING",
        )
        assert_true(bool(approved_packet.get("planning_approved_at")), "approve-planning should record timestamp")

        create_session(runtime_session, runtime_root, repo_root, "session-ready", "codex_cli")
        update_session_status(runtime_session, runtime_root, "session-ready", "READY")
        assignment_path = create_assignment(runtime_session, runtime_root, "session-ready", source_artifact, "compatible assignment")
        assignment_id = str(read_json(assignment_path)["assignment_id"])

        rc, _stdout, stderr = plan_packet(
            exchange_dispatch_plan,
            exchange_root,
            runtime_root,
            packet_id=draft_packet_id,
            session_id="session-ready",
            assignment_id=assignment_id,
        )
        assert_true(rc == 0, f"dispatch-plan should succeed: {stderr}")
        plan = plan_for_packet(exchange_root, draft_packet_id)
        assert_true(plan["planned_status"] == "PLANNED_NOT_DISPATCHED", "compatible dispatch plan should be planned")
        assert_true(plan["execution_allowed"] is False, "dispatch plan execution_allowed should stay false")
        assert_true(plan["cli_executed"] is False, "dispatch plan must not execute CLI")
        assert_true(plan["model_invoked"] is False, "dispatch plan must not invoke model")
        assert_true(plan["browser_automated"] is False, "dispatch plan must not automate browser")
        assert_true(plan["branch_created"] is False, "dispatch plan must not create branches")
        assert_true(plan["commit_performed"] is False, "dispatch plan must not commit")
        assert_true(plan["push_performed"] is False, "dispatch plan must not push")
        assert_true(plan["merge_performed"] is False, "dispatch plan must not merge")

        rc, stdout, stderr = run_main(exchange_dispatch_plan.main, ["plan-list", "--root", str(exchange_root)])
        assert_true(rc == 0, f"plan-list should pass: {stderr}")
        assert_true(str(plan["dispatch_plan_id"]) in stdout, "plan-list should include dispatch plan id")

        rc, stdout, stderr = run_main(
            exchange_dispatch_plan.main,
            ["plan-status", "--root", str(exchange_root), "--dispatch-plan-id", str(plan["dispatch_plan_id"])],
        )
        assert_true(rc == 0, f"plan-status should pass: {stderr}")
        assert_true('"planned_status": "PLANNED_NOT_DISPATCHED"' in stdout, "plan-status should print plan JSON")

        packet_path_source_changed, packet_id_source_changed = create_packet(
            exchange_packet, exchange_root, source_artifact, "codex_cli"
        )
        mark_ready(exchange_packet, exchange_root, packet_id_source_changed)
        rc, _stdout, stderr = approve_planning(
            exchange_packet, exchange_root, packet_id_source_changed, "approve source change case"
        )
        assert_true(rc == 0, f"approve-planning source-change case should pass: {stderr}")
        write_text(source_artifact, "# implementation plan changed\n")
        create_session(runtime_session, runtime_root, repo_root, "session-source-changed", "codex_cli")
        update_session_status(runtime_session, runtime_root, "session-source-changed", "READY")
        assignment_source_changed = create_assignment(
            runtime_session,
            runtime_root,
            "session-source-changed",
            source_artifact,
            "source changed assignment",
        )
        rc, _stdout, stderr = plan_packet(
            exchange_dispatch_plan,
            exchange_root,
            runtime_root,
            packet_id=packet_id_source_changed,
            session_id="session-source-changed",
            assignment_id=str(read_json(assignment_source_changed)["assignment_id"]),
        )
        assert_true(rc == 0, f"dispatch-plan source-changed should still write blocked plan: {stderr}")
        assert_true(
            plan_for_packet(exchange_root, packet_id_source_changed)["planned_status"] == "BLOCKED_SOURCE_CHANGED",
            "changed source artifact should block dispatch plan",
        )

        missing_session_source = repo_root / "product_development_lane" / "implementation_plans" / "missing_session.md"
        write_text(missing_session_source, "# missing session\n")
        packet_path_missing_session, packet_id_missing_session = create_packet(
            exchange_packet, exchange_root, missing_session_source, "codex_cli"
        )
        mark_ready(exchange_packet, exchange_root, packet_id_missing_session)
        rc, _stdout, stderr = approve_planning(
            exchange_packet, exchange_root, packet_id_missing_session, "approve missing session case"
        )
        assert_true(rc == 0, f"approve-planning missing-session case should pass: {stderr}")
        create_session(runtime_session, runtime_root, repo_root, "session-delete-me", "codex_cli")
        update_session_status(runtime_session, runtime_root, "session-delete-me", "READY")
        assignment_missing_session = create_assignment(
            runtime_session,
            runtime_root,
            "session-delete-me",
            missing_session_source,
            "assignment for missing session",
        )
        assignment_missing_session_id = str(read_json(assignment_missing_session)["assignment_id"])
        (runtime_root / "sessions" / "session-delete-me.json").unlink()
        assignment_data = read_json(assignment_missing_session)
        assignment_data["session_id"] = "session-missing"
        runtime_session.write_json(assignment_missing_session, assignment_data)
        rc, _stdout, stderr = plan_packet(
            exchange_dispatch_plan,
            exchange_root,
            runtime_root,
            packet_id=packet_id_missing_session,
            session_id="session-missing",
            assignment_id=assignment_missing_session_id,
        )
        assert_true(rc == 0, f"dispatch-plan missing-session should still write blocked plan: {stderr}")
        assert_true(
            plan_for_packet(exchange_root, packet_id_missing_session)["planned_status"] == "BLOCKED_NO_SESSION",
            "missing session should block dispatch plan",
        )

        missing_assignment_source = repo_root / "product_development_lane" / "implementation_plans" / "missing_assignment.md"
        write_text(missing_assignment_source, "# missing assignment\n")
        packet_path_missing_assignment, packet_id_missing_assignment = create_packet(
            exchange_packet, exchange_root, missing_assignment_source, "codex_cli"
        )
        mark_ready(exchange_packet, exchange_root, packet_id_missing_assignment)
        rc, _stdout, stderr = approve_planning(
            exchange_packet, exchange_root, packet_id_missing_assignment, "approve missing assignment case"
        )
        assert_true(rc == 0, f"approve-planning missing-assignment case should pass: {stderr}")
        create_session(runtime_session, runtime_root, repo_root, "session-missing-assignment", "codex_cli")
        update_session_status(runtime_session, runtime_root, "session-missing-assignment", "READY")
        rc, _stdout, stderr = plan_packet(
            exchange_dispatch_plan,
            exchange_root,
            runtime_root,
            packet_id=packet_id_missing_assignment,
            session_id="session-missing-assignment",
            assignment_id="missing-assignment",
        )
        assert_true(rc == 0, f"dispatch-plan missing-assignment should still write blocked plan: {stderr}")
        assert_true(
            plan_for_packet(exchange_root, packet_id_missing_assignment)["planned_status"] == "BLOCKED_ASSIGNMENT_MISSING",
            "missing assignment should block dispatch plan",
        )

        mismatch_source = repo_root / "product_development_lane" / "implementation_plans" / "mismatch.md"
        write_text(mismatch_source, "# adapter mismatch\n")
        packet_path_mismatch, packet_id_mismatch = create_packet(exchange_packet, exchange_root, mismatch_source, "codex_cli")
        mark_ready(exchange_packet, exchange_root, packet_id_mismatch)
        rc, _stdout, stderr = approve_planning(
            exchange_packet, exchange_root, packet_id_mismatch, "approve adapter mismatch case"
        )
        assert_true(rc == 0, f"approve-planning mismatch case should pass: {stderr}")
        create_session(runtime_session, runtime_root, repo_root, "session-gemini", "gemini_cli")
        update_session_status(runtime_session, runtime_root, "session-gemini", "READY")
        mismatch_assignment = create_assignment(
            runtime_session,
            runtime_root,
            "session-gemini",
            mismatch_source,
            "gemini assignment",
        )
        rc, _stdout, stderr = plan_packet(
            exchange_dispatch_plan,
            exchange_root,
            runtime_root,
            packet_id=packet_id_mismatch,
            session_id="session-gemini",
            assignment_id=str(read_json(mismatch_assignment)["assignment_id"]),
        )
        assert_true(rc == 0, f"dispatch-plan adapter-mismatch should still write blocked plan: {stderr}")
        assert_true(
            plan_for_packet(exchange_root, packet_id_mismatch)["planned_status"] == "BLOCKED_ADAPTER_MISMATCH",
            "adapter mismatch should block dispatch plan",
        )

        closed_source = repo_root / "product_development_lane" / "implementation_plans" / "closed.md"
        write_text(closed_source, "# closed session\n")
        packet_path_closed, packet_id_closed = create_packet(exchange_packet, exchange_root, closed_source, "codex_cli")
        mark_ready(exchange_packet, exchange_root, packet_id_closed)
        rc, _stdout, stderr = approve_planning(exchange_packet, exchange_root, packet_id_closed, "approve closed session case")
        assert_true(rc == 0, f"approve-planning closed-session case should pass: {stderr}")
        create_session(runtime_session, runtime_root, repo_root, "session-closed", "codex_cli")
        update_session_status(runtime_session, runtime_root, "session-closed", "CLOSED")
        closed_assignment = create_assignment(
            runtime_session,
            runtime_root,
            "session-closed",
            closed_source,
            "closed assignment",
        )
        rc, _stdout, stderr = plan_packet(
            exchange_dispatch_plan,
            exchange_root,
            runtime_root,
            packet_id=packet_id_closed,
            session_id="session-closed",
            assignment_id=str(read_json(closed_assignment)["assignment_id"]),
        )
        assert_true(rc == 0, f"dispatch-plan closed-session should still write blocked plan: {stderr}")
        assert_true(
            plan_for_packet(exchange_root, packet_id_closed)["planned_status"] == "BLOCKED_SESSION_NOT_READY",
            "closed session should block dispatch plan",
        )

        rc, _stdout, stderr = run_main(audit_exchange_lane.main, ["--root", str(exchange_root)])
        assert_true(rc == 0, f"audit should pass with dispatch plans: {stderr}")

        ws_result = run_ws_exchange(repo_root, ["approve-planning", "--packet-id", packet_id_missing_assignment, "--note", "duplicate approval"])
        if ws_result is None:
            print("Exchange Lane validation: ws exchange approve-planning/dispatch-plan skipped; bash or python3 unavailable")
        else:
            rc, _stdout, _stderr = ws_result
            assert_true(rc == 1, "ws exchange approve-planning should surface packet transition rules")

            ws_source = repo_root / "product_development_lane" / "implementation_plans" / "ws_case.md"
            write_text(ws_source, "# ws case\n")
            ws_packet_path, ws_packet_id = create_packet(exchange_packet, exchange_root, ws_source, "codex_cli")
            mark_ready(exchange_packet, exchange_root, ws_packet_id)
            rc, stdout, stderr = run_ws_exchange(
                repo_root,
                ["approve-planning", "--packet-id", ws_packet_id, "--note", "approved through ws"],
            )
            assert_true(rc == 0, f"ws exchange approve-planning should pass: {stderr}")
            assert_true("planning approved:" in stdout, "ws exchange approve-planning should report success")
            create_session(runtime_session, runtime_root, repo_root, "ws-session", "codex_cli")
            update_session_status(runtime_session, runtime_root, "ws-session", "READY")
            ws_assignment = create_assignment(runtime_session, runtime_root, "ws-session", ws_source, "ws assignment")
            rc, stdout, stderr = run_ws_exchange(
                repo_root,
                [
                    "dispatch-plan",
                    "--packet-id",
                    ws_packet_id,
                    "--session-id",
                    "ws-session",
                    "--assignment-id",
                    str(read_json(ws_assignment)["assignment_id"]),
                ],
            )
            assert_true(rc == 0, f"ws exchange dispatch-plan should pass: {stderr}")
            assert_true("dispatch plan written:" in stdout, "ws exchange dispatch-plan should report success")
            assert_true(read_json(ws_packet_path)["packet_status"] == "APPROVED_FOR_DISPATCH_PLANNING", "ws approve should not dispatch")

    finally:
        if tmp_root.exists():
            remove_tree(tmp_root)

    print("Exchange Lane validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

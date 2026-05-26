#!/usr/bin/env python3
"""Validation for Execution Lane MVP Slice 1 non-executing preparation."""

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
EXECUTION_LANE_ROOT = ROOT / "execution_lane"
DISCOVERY_LANE_ROOT = ROOT / "discovery_lane"
PRODUCT_DEV_LANE_ROOT = ROOT / "product_development_lane"


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"could not load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def remove_tree(path: Path) -> None:
    def reset_permissions(function, target, _exc_info):
        os.chmod(target, stat.S_IWRITE | stat.S_IREAD)
        function(target)

    shutil.rmtree(path, onexc=reset_permissions)


def copy_lane_scaffold(target_root: Path) -> None:
    execution_target = target_root / "execution_lane"
    discovery_target = target_root / "discovery_lane"
    product_dev_target = target_root / "product_development_lane"

    shutil.copytree(EXECUTION_LANE_ROOT / "contracts", execution_target / "contracts")
    for folder in ("runs", "run_reports", "worker_task_packets", "handoff_previews", "manifests", "tools"):
        (execution_target / folder).mkdir(parents=True, exist_ok=True)

    for folder in (
        "execution_queues",
        "execution_handoffs",
        "branch_plans",
        "phase_packets",
        "worker_prompts",
        "manifests",
        "approval_records",
        "research_set_ingests",
    ):
        shutil.copytree(DISCOVERY_LANE_ROOT / folder, discovery_target / folder)

    for folder in ("manifests", "implementation_plans"):
        shutil.copytree(PRODUCT_DEV_LANE_ROOT / folder, product_dev_target / folder)


def run_main(main_fn, argv: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        rc = int(main_fn(argv))
    return rc, stdout.getvalue(), stderr.getvalue()


def snapshot_lane_files(execution_root: Path) -> tuple[int, int, int]:
    runs = len(list((execution_root / "runs").glob("*.json")))
    packets = len(list((execution_root / "worker_task_packets").glob("*.json")))
    reports = len(list((execution_root / "run_reports").glob("*.md")))
    return runs, packets, reports


def run_ws_execution(repo_root: Path, args: list[str]) -> tuple[int, str, str] | None:
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

    bash_lower = bash.lower().replace("/", "\\")
    is_wsl = "microsoft\\windowsapps\\bash.exe" in bash_lower or "system32\\bash.exe" in bash_lower

    def to_bash_path(path: Path) -> str:
        posix = path.as_posix()
        if is_wsl and len(posix) > 1 and posix[1] == ":":
            return f"/mnt/{posix[0].lower()}{posix[2:]}"
        return posix

    def to_bash_arg(arg: str) -> str:
        candidate = Path(arg)
        if is_wsl and candidate.drive:
            return to_bash_path(candidate)
        return arg

    env = os.environ.copy()
    env["WS_HOME"] = to_bash_path(repo_root)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [
            bash,
            to_bash_path(ROOT / "scripts" / "ws"),
            "execution",
            "--root",
            to_bash_path(repo_root / "execution_lane"),
            *(to_bash_arg(arg) for arg in args),
        ],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


def main() -> int:
    sys.modules.pop("execution_command", None)
    sys.modules.pop("audit_execution_lane", None)
    execution_command = load_module("execution_command", EXECUTION_LANE_ROOT / "tools" / "execution_command.py")
    audit_execution_lane = load_module("audit_execution_lane", EXECUTION_LANE_ROOT / "tools" / "audit_execution_lane.py")

    assert_true("handoff-preview" in execution_command.build_parser().format_help(), "help should include handoff-preview")

    source_text = (EXECUTION_LANE_ROOT / "tools" / "execution_command.py").read_text(encoding="utf-8")
    forbidden_terms = ("subprocess", "os.system", "Popen(", "git checkout", "git commit", "git push", "git merge")
    for term in forbidden_terms:
        assert_true(term not in source_text, f"execution_command.py should not contain execution term: {term}")

    codex_temp = Path.home() / ".codex" / "memories"
    temp_parent = codex_temp if codex_temp.is_dir() else Path(tempfile.gettempdir())
    tmp_root = temp_parent / f"execution_lane_test_{uuid.uuid4().hex}"
    try:
        tmp_root.mkdir()
        repo_root = tmp_root / "repo"
        copy_lane_scaffold(repo_root)
        execution_root = repo_root / "execution_lane"
        queue_path = repo_root / "discovery_lane" / "execution_queues" / "positive_path_example_execution_queue.json"
        assert_true(queue_path.is_file(), "positive path execution queue fixture should exist in temp root")

        # 1 help works
        rc, stdout, stderr = run_main(execution_command.main, ["--root", str(execution_root), "help"])
        assert_true(rc == 0, f"help should pass: {stderr}")
        assert_true("prepare" in stdout, "help should list prepare")

        # 2 status works with empty lane
        rc, stdout, stderr = run_main(execution_command.main, ["--root", str(execution_root), "status"])
        assert_true(rc == 0, f"status should pass: {stderr}")
        assert_true("runs: 0" in stdout, "status should report empty runs")

        # 3 plan refuses missing queue
        rc, _stdout, _stderr = run_main(
            execution_command.main,
            ["--root", str(execution_root), "plan", "--queue", str(repo_root / "missing.json"), "--dry-run"],
        )
        assert_true(rc == 1, "plan should refuse missing queue")

        # 4 plan refuses queue not ready
        bad_queue_path = repo_root / "discovery_lane" / "execution_queues" / "not_ready_execution_queue.json"
        bad_queue = load_json(queue_path)
        bad_queue["queue_status"] = "BLOCKED_INVALID_APPROVALS"
        bad_queue_path.write_text(json.dumps(bad_queue, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        rc, _stdout, _stderr = run_main(
            execution_command.main,
            ["--root", str(execution_root), "plan", "--queue", str(bad_queue_path), "--dry-run"],
        )
        assert_true(rc == 1, "plan should reject non-ready queue")

        # 5 positive queue dry-run accepted
        before_plan = snapshot_lane_files(execution_root)
        rc, stdout, stderr = run_main(
            execution_command.main,
            ["--root", str(execution_root), "plan", "--queue", str(queue_path), "--dry-run"],
        )
        assert_true(rc == 0, f"plan dry-run should pass: {stderr}")
        assert_true("VALIDATION_PASS_NO_WRITE" in stdout, "plan should report dry-run no-write result")

        # 6 dry-run writes no files
        after_plan = snapshot_lane_files(execution_root)
        assert_true(before_plan == after_plan, "plan --dry-run must not write files")

        # 7 prepare requires --confirm
        rc, _stdout, _stderr = run_main(
            execution_command.main,
            ["--root", str(execution_root), "prepare", "--queue", str(queue_path)],
        )
        assert_true(rc == 1, "prepare must require --confirm")

        # 8,9,10 prepare creates run/task/report
        rc, stdout, stderr = run_main(
            execution_command.main,
            ["--root", str(execution_root), "prepare", "--queue", str(queue_path), "--confirm"],
        )
        assert_true(rc == 0, f"prepare should pass: {stderr}")
        assert_true("run_id:" in stdout, "prepare should print run_id")
        run_files = sorted((execution_root / "runs").glob("*.json"))
        task_files = sorted((execution_root / "worker_task_packets").glob("*.json"))
        report_files = sorted((execution_root / "run_reports").glob("*.md"))
        assert_true(len(run_files) == 1, "prepare should create one run manifest")
        assert_true(len(task_files) >= 1, "prepare should create worker task packets")
        assert_true(len(report_files) == 1, "prepare should create run report")

        run = load_json(run_files[0])

        # 11-15 conservative flags
        assert_true(run.get("execution_allowed") is False, "execution_allowed should be false")
        assert_true(run.get("branch_creation_allowed") is False, "branch_creation_allowed should be false")
        assert_true(run.get("commit_allowed") is False, "commit_allowed should be false")
        assert_true(run.get("push_allowed") is False, "push_allowed should be false")
        assert_true(run.get("merge_allowed") is False, "merge_allowed should be false")

        # 16 run-status works
        run_id = str(run["run_id"])
        rc, stdout, stderr = run_main(
            execution_command.main,
            ["--root", str(execution_root), "run-status", "--run", run_id],
        )
        assert_true(rc == 0, f"run-status should pass: {stderr}")
        assert_true("PREPARED_NOT_EXECUTED" in stdout, "run-status should show prepared status")

        # 17 handoff-preview dry-run works
        before_preview_count = len(list((execution_root / "handoff_previews").glob("*.json")))
        rc, stdout, stderr = run_main(
            execution_command.main,
            [
                "--root",
                str(execution_root),
                "handoff-preview",
                "--run",
                run_id,
                "--target",
                "codex_cli",
                "--dry-run",
            ],
        )
        assert_true(rc == 0, f"handoff-preview should pass: {stderr}")
        assert_true("preview_only: true" in stdout, "handoff-preview should state preview only")

        # 18 handoff-preview dry-run writes no files
        after_preview_count = len(list((execution_root / "handoff_previews").glob("*.json")))
        assert_true(before_preview_count == after_preview_count, "handoff-preview dry-run must write no files")

        # 19 audit passes
        rc, _stdout, _stderr = run_main(audit_execution_lane.main, ["--root", str(execution_root)])
        assert_true(rc == 0, "execution lane audit should pass")

        # 20 no branch/commit/push/merge occurs
        assert_true(run.get("branch_created") is False, "run should not create branch")
        assert_true(run.get("commit_performed") is False, "run should not commit")
        assert_true(run.get("push_performed") is False, "run should not push")
        assert_true(run.get("merge_performed") is False, "run should not merge")

        # 21 no model/provider invocation
        assert_true(run.get("model_invoked") is False, "run should not invoke model")
        assert_true(run.get("provider_called") is False, "run should not call provider")

        # 22 ws execution commands work if safe to test
        ws_result = run_ws_execution(repo_root, ["help"])
        if ws_result is None:
            print("Execution Lane validation: ws execution commands skipped; bash/python3 unavailable")
        else:
            rc, stdout, stderr = ws_result
            assert_true(rc == 0, f"ws execution help should pass: {stderr}")
            assert_true("Execution Lane" in stdout or "execution" in stdout.lower(), "ws execution help should print help")
            rc, _stdout, stderr = run_ws_execution(repo_root, ["status"])  # type: ignore[misc]
            assert_true(rc == 0, f"ws execution status should pass: {stderr}")
            rc, stdout, stderr = run_ws_execution(
                repo_root,
                ["plan", "--queue", str(queue_path), "--dry-run"],
            )  # type: ignore[misc]
            assert_true(rc == 0, f"ws execution plan should pass: {stderr}")
            assert_true("VALIDATION_PASS_NO_WRITE" in stdout, "ws execution plan should run dry-run")
            rc, _stdout, stderr = run_ws_execution(repo_root, ["audit"])  # type: ignore[misc]
            assert_true(rc == 0, f"ws execution audit should pass: {stderr}")
    finally:
        if tmp_root.exists():
            remove_tree(tmp_root)

    print("Execution Lane validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

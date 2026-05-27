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

from workstation_ids import check_path_length


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


def write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def remove_tree(path: Path) -> None:
    def reset_permissions(function, target, _exc_info):
        os.chmod(target, stat.S_IWRITE | stat.S_IREAD)
        function(target)

    shutil.rmtree(path, onexc=reset_permissions)


def copy_exchange_scaffold(target: Path) -> None:
    for folder in ("contracts", "tools", "examples", "adapter_commands"):
        shutil.copytree(EXCHANGE_LANE_ROOT / folder, target / folder)
    for folder in (
        "packets",
        "result_packets",
        "routing",
        "manifests",
        "reports",
        "dispatch_plans",
        "dispatch_plan_reports",
        "outbox",
        "result_validations",
        "loop_decisions",
        "repair_packets",
        "loop_reports",
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
        objective=(
            "Plan dispatch metadata only. "
            "Keep full intent in metadata while filenames remain compact for Windows-safe paths."
        ),
    )
    packet = read_json(packet_path)
    return packet_path, str(packet["packet_id"])


def clone_imported_result_fixture(
    source_exchange_root: Path,
    target_exchange_root: Path,
    result_id: str,
    capture_manifest_path: Path,
) -> Path:
    copy_exchange_scaffold(target_exchange_root)
    source_manifest = read_json(capture_manifest_path)
    packet_id = str(source_manifest["packet_id"])
    dispatch_plan_id = str(source_manifest["dispatch_plan_id"])
    packet_bucket = str(source_manifest.get("outbox_packet_bucket", packet_id))
    dispatch_bucket = str(source_manifest.get("outbox_dispatch_bucket", dispatch_plan_id))
    cloned_capture_dir = target_exchange_root / "outbox" / packet_bucket / dispatch_bucket
    shutil.copytree(capture_manifest_path.parent, cloned_capture_dir)

    cloned_manifest_path = cloned_capture_dir / "capture_manifest.json"
    cloned_manifest = read_json(cloned_manifest_path)
    cloned_manifest["raw_output_path"] = str((cloned_capture_dir / "raw_output.md").resolve())
    cloned_manifest["parsed_result_path"] = str((cloned_capture_dir / "parsed_result.json").resolve())
    cloned_manifest["validation_path"] = str((cloned_capture_dir / "validation.md").resolve())
    cloned_manifest["operator_report_path"] = str((cloned_capture_dir / "operator_report.md").resolve())
    cloned_manifest["imported_result_packet"] = str((target_exchange_root / "result_packets" / f"{result_id}.json").resolve())
    cloned_manifest["packet_id"] = packet_id
    cloned_manifest["dispatch_plan_id"] = dispatch_plan_id
    cloned_manifest["outbox_packet_bucket"] = packet_bucket
    cloned_manifest["outbox_dispatch_bucket"] = dispatch_bucket
    write_json(cloned_manifest_path, cloned_manifest)

    cloned_result = read_json(source_exchange_root / "result_packets" / f"{result_id}.json")
    cloned_result["source_capture_manifest"] = str(cloned_manifest_path.resolve())
    cloned_result["output_artifacts"] = {
        "raw_output": cloned_manifest["raw_output_path"],
        "parsed_result": cloned_manifest["parsed_result_path"],
        "validation": cloned_manifest["validation_path"],
        "operator_report": cloned_manifest["operator_report_path"],
    }
    write_json(target_exchange_root / "result_packets" / f"{result_id}.json", cloned_result)
    return cloned_manifest_path


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


def latest_record_by_field(exchange_root: Path, folder: str, field: str, value: str) -> dict[str, object]:
    matches: list[Path] = []
    for path in (exchange_root / folder).glob("*.json"):
        data = read_json(path)
        if str(data.get(field, "")) == value:
            matches.append(path)
    assert_true(bool(matches), f"{folder} record should exist for {field}={value}")
    latest = max(matches, key=lambda item: item.stat().st_mtime_ns)
    return read_json(latest)


def latest_record_path_by_field(exchange_root: Path, folder: str, field: str, value: str) -> Path:
    matches: list[Path] = []
    for path in (exchange_root / folder).glob("*.json"):
        data = read_json(path)
        if str(data.get(field, "")) == value:
            matches.append(path)
    assert_true(bool(matches), f"{folder} path should exist for {field}={value}")
    return max(matches, key=lambda item: item.stat().st_mtime_ns)


def find_capture_manifest(exchange_root: Path, packet_id: str, dispatch_plan_id: str) -> Path:
    matches: list[Path] = []
    for path in (exchange_root / "outbox").rglob("capture_manifest.json"):
        data = read_json(path)
        if str(data.get("packet_id", "")) == packet_id and str(data.get("dispatch_plan_id", "")) == dispatch_plan_id:
            matches.append(path)
    assert_true(bool(matches), f"capture manifest should exist for packet={packet_id} dispatch_plan={dispatch_plan_id}")
    return max(matches, key=lambda item: item.stat().st_mtime_ns)


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


def enable_fake_adapter_command(exchange_root: Path, adapter_id: str = "codex_cli", executable: str = "fake-codex") -> None:
    config_path = exchange_root / "adapter_commands" / f"{adapter_id}_command.json"
    config = read_json(config_path)
    config["enabled"] = True
    config["executable"] = executable
    config["base_args"] = ["--metadata-only-test"]
    config["input_mode"] = "stdin"
    config["prompt_argument_strategy"] = "stdin"
    config["cwd_policy"] = "exchange_root"
    config["timeout_seconds"] = 3
    config["allowed_environment_keys"] = ["PATH"]
    write_json(config_path, config)


def create_planned_dispatch(
    exchange_packet,
    exchange_dispatch_plan,
    runtime_session,
    exchange_root: Path,
    runtime_root: Path,
    repo_root: Path,
    *,
    source_name: str,
    session_id: str,
    adapter: str = "codex_cli",
) -> tuple[str, dict[str, object], Path]:
    source = repo_root / "product_development_lane" / "implementation_plans" / source_name
    write_text(source, f"# {source_name}\n")
    packet_path, packet_id = create_packet(exchange_packet, exchange_root, source, adapter)
    mark_ready(exchange_packet, exchange_root, packet_id)
    rc, _stdout, stderr = approve_planning(exchange_packet, exchange_root, packet_id, f"approve {source_name}")
    assert_true(rc == 0, f"approve-planning for {source_name} should pass: {stderr}")
    create_session(runtime_session, runtime_root, repo_root, session_id, adapter)
    update_session_status(runtime_session, runtime_root, session_id, "READY")
    assignment_path = create_assignment(runtime_session, runtime_root, session_id, source, f"{source_name} assignment")
    rc, _stdout, stderr = plan_packet(
        exchange_dispatch_plan,
        exchange_root,
        runtime_root,
        packet_id=packet_id,
        session_id=session_id,
        assignment_id=str(read_json(assignment_path)["assignment_id"]),
    )
    assert_true(rc == 0, f"dispatch-plan for {source_name} should pass: {stderr}")
    plan = plan_for_packet(exchange_root, packet_id)
    assert_true(plan["planned_status"] == "PLANNED_NOT_DISPATCHED", f"{source_name} should create planned dispatch")
    return packet_id, plan, packet_path


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

    def to_bash_arg(arg: str) -> str:
        candidate = Path(arg)
        if is_wsl and candidate.drive:
            return to_bash_path(candidate)
        return arg

    env = os.environ.copy()
    bash_repo_root = to_bash_path(repo_root)
    env["WS_HOME"] = bash_repo_root
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    
    # Always pass --root to ensure we use the temp lane
    ws_args = ["--root", to_bash_path(repo_root / "exchange_lane")] + [to_bash_arg(arg) for arg in args]
    
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
    sys.modules.pop("exchange_fake_dispatch", None)
    sys.modules.pop("exchange_import_result", None)
    sys.modules.pop("exchange_validate_result", None)
    sys.modules.pop("exchange_loop_decision", None)
    sys.modules.pop("exchange_real_dispatch", None)
    sys.modules.pop("audit_exchange_lane", None)
    sys.modules.pop("runtime_session", None)
    sys.modules.pop("exchange_command", None)

    exchange_packet = load_module("exchange_packet", EXCHANGE_LANE_ROOT / "tools" / "exchange_packet.py")
    exchange_dispatch_plan = load_module(
        "exchange_dispatch_plan", EXCHANGE_LANE_ROOT / "tools" / "exchange_dispatch_plan.py"
    )
    exchange_fake_dispatch = load_module("exchange_fake_dispatch", EXCHANGE_LANE_ROOT / "tools" / "exchange_fake_dispatch.py")
    exchange_import_result = load_module("exchange_import_result", EXCHANGE_LANE_ROOT / "tools" / "exchange_import_result.py")
    exchange_validate_result = load_module("exchange_validate_result", EXCHANGE_LANE_ROOT / "tools" / "exchange_validate_result.py")
    exchange_loop_decision = load_module("exchange_loop_decision", EXCHANGE_LANE_ROOT / "tools" / "exchange_loop_decision.py")
    exchange_real_dispatch = load_module("exchange_real_dispatch", EXCHANGE_LANE_ROOT / "tools" / "exchange_real_dispatch.py")
    audit_exchange_lane = load_module("audit_exchange_lane", EXCHANGE_LANE_ROOT / "tools" / "audit_exchange_lane.py")
    runtime_session = load_module("runtime_session", RUNTIME_LANE_ROOT / "tools" / "runtime_session.py")
    exchange_command = load_module("exchange_command", EXCHANGE_LANE_ROOT / "tools" / "exchange_command.py")

    assert_true((EXCHANGE_LANE_ROOT / "contracts" / "dispatch_plan_contract.md").is_file(), "dispatch plan contract should exist")
    assert_true((EXCHANGE_LANE_ROOT / "contracts" / "result_capture_contract.md").is_file(), "result capture contract should exist")
    assert_true((EXCHANGE_LANE_ROOT / "contracts" / "result_validation_contract.md").is_file(), "result validation contract should exist")
    assert_true((EXCHANGE_LANE_ROOT / "contracts" / "loop_decision_contract.md").is_file(), "loop decision contract should exist")
    assert_true((EXCHANGE_LANE_ROOT / "contracts" / "real_dispatch_contract.md").is_file(), "real dispatch contract should exist")
    assert_true((EXCHANGE_LANE_ROOT / "dispatch_plans").is_dir(), "dispatch_plans folder should exist")
    assert_true((EXCHANGE_LANE_ROOT / "dispatch_plan_reports").is_dir(), "dispatch_plan_reports folder should exist")
    for adapter_config in ("codex_cli_command.json", "gemini_cli_command.json"):
        adapter_config_path = EXCHANGE_LANE_ROOT / "adapter_commands" / adapter_config
        assert_true(adapter_config_path.is_file(), f"{adapter_config} should exist")
        assert_true(read_json(adapter_config_path)["enabled"] is False, f"{adapter_config} should default disabled")
    ollama_config_path = EXCHANGE_LANE_ROOT / "adapter_commands" / "ollama_local_command.json"
    assert_true(ollama_config_path.is_file(), "ollama_local command config should exist")
    ollama_config = read_json(ollama_config_path)
    assert_true(ollama_config["enabled"] is False, "ollama_local command config should default disabled")
    assert_true(ollama_config["adapter_type"] == "ollama_local", "ollama_local config should declare adapter_type")
    assert_true(ollama_config["endpoint"] == "http://127.0.0.1:11434/v1", "ollama_local config should declare endpoint")
    assert_true(ollama_config["model"] == "hermes3:8b", "ollama_local config should declare preferred model")
    assert_true(ollama_config["trusted_output_default"] is False, "ollama_local output should default untrusted")
    assert_true("plan-status" in exchange_dispatch_plan.build_parser().format_help(), "dispatch plan help should include plan-status")
    assert_true("fake-dispatch" in exchange_fake_dispatch.build_parser().format_help(), "fake dispatch help should include fake-dispatch")
    assert_true("import-result" in exchange_import_result.build_parser().format_help(), "import result help should include import-result")
    assert_true("validate-result" in exchange_validate_result.build_parser().format_help(), "validate result help should include validate-result")
    assert_true("loop-status" in exchange_loop_decision.build_parser().format_help(), "loop decision help should include loop-status")
    assert_true("dispatch" in exchange_real_dispatch.build_parser().format_help(), "real dispatch help should include dispatch")
    assert_true("approve-planning" in exchange_packet.build_parser().format_help(), "packet help should include approve-planning")
    assert_true("dispatch-plan" in exchange_command.build_parser().format_help(), "exchange command help should include dispatch-plan")
    assert_true("fake-dispatch" in exchange_command.build_parser().format_help(), "exchange command help should include fake-dispatch")
    assert_true("real-dispatch" in exchange_command.build_parser().format_help(), "exchange command help should include real-dispatch")
    assert_true("validate-result" in exchange_command.build_parser().format_help(), "exchange command help should include validate-result")
    rc, stdout, stderr = run_main(exchange_command.main, ["--root", str(EXCHANGE_LANE_ROOT), "adapter-list"])
    assert_true(rc == 0, f"adapter-list should pass: {stderr}")
    assert_true("ollama_local" in stdout, "adapter-list should include ollama_local")
    rc, stdout, stderr = run_main(
        exchange_command.main,
        ["--root", str(EXCHANGE_LANE_ROOT), "adapter-status", "--adapter-id", "ollama_local"],
    )
    assert_true(rc == 0, f"adapter-status should pass: {stderr}")
    assert_true("adapter_id: ollama_local" in stdout, "adapter-status should identify ollama_local")
    assert_true("endpoint: http://127.0.0.1:11434/v1" in stdout, "adapter-status should report Ollama endpoint")
    assert_true("model: hermes3:8b" in stdout, "adapter-status should report Ollama model")
    assert_true(
        "provider_dispatcher_implemented: false" in stdout,
        "adapter-status should report provider dispatcher disabled",
    )
    assert_true("real_provider_calls: disabled" in stdout, "adapter-status should report no provider calls")
    assert_true("writes: none" in stdout, "adapter-status should write nothing")
    assert_true("executes: no" in stdout, "adapter-status should execute nothing")

    source_text = (EXCHANGE_LANE_ROOT / "tools" / "exchange_dispatch_plan.py").read_text(encoding="utf-8")
    forbidden_terms = ("subprocess", "os.system", "Popen", "git checkout", "git commit", "git push", "git branch")
    for term in forbidden_terms:
        assert_true(term not in source_text, f"exchange_dispatch_plan.py should not contain execution term: {term}")
    for tool_name in (
        "exchange_fake_dispatch.py",
        "exchange_import_result.py",
        "exchange_validate_result.py",
        "exchange_loop_decision.py",
    ):
        tool_source = (EXCHANGE_LANE_ROOT / "tools" / tool_name).read_text(encoding="utf-8")
        for term in forbidden_terms:
            assert_true(term not in tool_source, f"{tool_name} should not contain execution term: {term}")
    real_dispatch_source = (EXCHANGE_LANE_ROOT / "tools" / "exchange_real_dispatch.py").read_text(encoding="utf-8")
    for term in ("os.system", "Popen", "shell=True", "git checkout", "git commit", "git push", "git branch"):
        assert_true(term not in real_dispatch_source, f"exchange_real_dispatch.py should not contain forbidden term: {term}")

    subparsers = exchange_command.build_parser()._subparsers._group_actions[0].choices
    assert_true("dispatch" not in subparsers, "ws exchange dispatch must not exist")
    assert_true("run" not in subparsers, "ws exchange run must not exist")
    assert_true("execute" not in subparsers, "ws exchange execute must not exist")
    assert_true("start-session" not in subparsers, "ws exchange start-session must not exist")
    assert_true("fake-dispatch" in subparsers, "ws exchange fake-dispatch should exist")
    assert_true("real-dispatch" in subparsers, "ws exchange real-dispatch should exist")
    assert_true("import-result" in subparsers, "ws exchange import-result should exist")
    assert_true("validate-result" in subparsers, "ws exchange validate-result should exist")
    assert_true("decide-loop" in subparsers, "ws exchange decide-loop should exist")
    assert_true("loop-status" in subparsers, "ws exchange loop-status should exist")
    assert_true("adapter-status" in subparsers, "ws exchange adapter-status should exist")
    safety_registry_text = (ROOT / "registry" / "ws_command_safety.yaml").read_text(encoding="utf-8")
    assert_true("ws exchange real-dispatch --dry-run:" in safety_registry_text, "ws real-dispatch dry-run should be in safety registry")
    assert_true("ws exchange real-dispatch --confirm:" in safety_registry_text, "ws real-dispatch confirm should be in safety registry")
    assert_true("ws exchange adapter-status:" in safety_registry_text, "ws adapter-status should be in safety registry")
    assert_true("GUARDED_EXECUTION" in safety_registry_text, "safety registry should include GUARDED_EXECUTION")

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
        assert_true(len(packet_path.stem) <= 96, "exchange packet filename stem should stay <= 96 chars")
        created_packet = read_json(packet_path)
        assert_true(
            "metadata while filenames remain compact" in str(created_packet.get("objective", "")),
            "long objective text should remain in packet JSON metadata",
        )
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
        assert_true(len(assignment_path.stem) <= 96, "runtime assignment filename stem should stay <= 96 chars")
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
        plan_path = latest_record_path_by_field(exchange_root, "dispatch_plans", "packet_id", draft_packet_id)
        assert_true(len(plan_path.stem) <= 96, "dispatch plan filename stem should stay <= 96 chars")
        assert_true(plan["planned_status"] == "PLANNED_NOT_DISPATCHED", "compatible dispatch plan should be planned")
        assert_true(plan["execution_allowed"] is False, "dispatch plan execution_allowed should stay false")
        assert_true(plan["cli_executed"] is False, "dispatch plan must not execute CLI")
        assert_true(plan["model_invoked"] is False, "dispatch plan must not invoke model")
        assert_true(plan["browser_automated"] is False, "dispatch plan must not automate browser")
        assert_true(plan["branch_created"] is False, "dispatch plan must not create branches")
        assert_true(plan["commit_performed"] is False, "dispatch plan must not commit")
        assert_true(plan["push_performed"] is False, "dispatch plan must not push")
        assert_true(plan["merge_performed"] is False, "dispatch plan must not merge")

        outbox_files_before = sorted(str(path.relative_to(exchange_root)) for path in (exchange_root / "outbox").rglob("*") if path.is_file())
        rc, stdout, stderr = run_main(
            exchange_real_dispatch.main,
            [
                "dispatch",
                "--root",
                str(exchange_root),
                "--runtime-root",
                str(runtime_root),
                "--dispatch-plan-id",
                str(plan["dispatch_plan_id"]),
                "--dry-run",
            ],
        )
        assert_true(rc == 0, f"real-dispatch dry-run should pass with disabled config: {stderr}")
        assert_true("guarded real dispatch dry-run" in stdout, "real-dispatch dry-run should print preview")
        outbox_files_after = sorted(str(path.relative_to(exchange_root)) for path in (exchange_root / "outbox").rglob("*") if path.is_file())
        assert_true(outbox_files_before == outbox_files_after, "real-dispatch dry-run should write no files")

        rc, _stdout, stderr = run_main(
            exchange_real_dispatch.main,
            [
                "dispatch",
                "--root",
                str(exchange_root),
                "--runtime-root",
                str(runtime_root),
                "--dispatch-plan-id",
                str(plan["dispatch_plan_id"]),
                "--confirm",
            ],
        )
        assert_true(rc == 1, "real-dispatch confirm should refuse disabled adapter command config")
        assert_true("Adapter command is not enabled" in stderr, "disabled adapter message should be explicit")

        rc, _stdout, stderr = run_main(
            exchange_real_dispatch.main,
            [
                "dispatch",
                "--root",
                str(exchange_root),
                "--runtime-root",
                str(runtime_root),
                "--dispatch-plan-id",
                "missing",
                "--confirm",
            ],
        )
        assert_true(rc == 1, "real-dispatch confirm should refuse missing dispatch plan")

        unsupported_plan = dict(plan)
        unsupported_plan["dispatch_plan_id"] = "unsupported_adapter_real_dispatch"
        unsupported_plan["target_adapter"] = "not_supported_adapter"
        write_json(exchange_root / "dispatch_plans" / "unsupported_adapter_real_dispatch.json", unsupported_plan)
        rc, _stdout, _stderr = run_main(
            exchange_real_dispatch.main,
            [
                "dispatch",
                "--root",
                str(exchange_root),
                "--runtime-root",
                str(runtime_root),
                "--dispatch-plan-id",
                "unsupported_adapter_real_dispatch",
                "--confirm",
            ],
        )
        assert_true(rc == 1, "real-dispatch confirm should refuse unsupported adapter")
        (exchange_root / "dispatch_plans" / "unsupported_adapter_real_dispatch.json").unlink()

        _ollama_packet_id, ollama_plan, _ollama_packet_path = create_planned_dispatch(
            exchange_packet,
            exchange_dispatch_plan,
            runtime_session,
            exchange_root,
            runtime_root,
            repo_root,
            source_name="ollama_local_plan.md",
            session_id="ollama-local-session",
            adapter="ollama_local",
        )
        ollama_outbox_before = sorted(str(path.relative_to(exchange_root)) for path in (exchange_root / "outbox").rglob("*") if path.is_file())
        rc, stdout, stderr = run_main(
            exchange_real_dispatch.main,
            [
                "dispatch",
                "--root",
                str(exchange_root),
                "--runtime-root",
                str(runtime_root),
                "--dispatch-plan-id",
                str(ollama_plan["dispatch_plan_id"]),
                "--dry-run",
            ],
        )
        assert_true(rc == 0, f"ollama_local real-dispatch dry-run should pass: {stderr}")
        assert_true("target_adapter: ollama_local" in stdout, "ollama dry-run should identify adapter")
        assert_true("provider_dispatcher: not implemented" in stdout, "ollama dry-run should refuse provider execution path")
        assert_true("executes: no" in stdout, "ollama dry-run should execute nothing")
        ollama_outbox_after = sorted(str(path.relative_to(exchange_root)) for path in (exchange_root / "outbox").rglob("*") if path.is_file())
        assert_true(ollama_outbox_before == ollama_outbox_after, "ollama dry-run should write no files")
        rc, _stdout, stderr = run_main(
            exchange_real_dispatch.main,
            [
                "dispatch",
                "--root",
                str(exchange_root),
                "--runtime-root",
                str(runtime_root),
                "--dispatch-plan-id",
                str(ollama_plan["dispatch_plan_id"]),
                "--confirm",
            ],
        )
        assert_true(rc == 1, "ollama_local real-dispatch confirm should refuse disabled config")
        assert_true("Adapter command is not enabled" in stderr, "ollama disabled config refusal should be explicit")

        blocked_packet_id, blocked_plan, _blocked_packet_path = create_planned_dispatch(
            exchange_packet,
            exchange_dispatch_plan,
            runtime_session,
            exchange_root,
            runtime_root,
            repo_root,
            source_name="real_blocked_session.md",
            session_id="real-blocked-session",
        )
        update_session_status(runtime_session, runtime_root, "real-blocked-session", "BLOCKED_QUOTA")
        rc, _stdout, stderr = run_main(
            exchange_real_dispatch.main,
            [
                "dispatch",
                "--root",
                str(exchange_root),
                "--runtime-root",
                str(runtime_root),
                "--dispatch-plan-id",
                str(blocked_plan["dispatch_plan_id"]),
                "--confirm",
            ],
        )
        assert_true(rc == 1, "real-dispatch confirm should refuse blocked session")
        assert_true("runtime session not dispatchable" in stderr, "blocked session should be reported")

        rc, _stdout, _stderr = run_main(
            exchange_fake_dispatch.main,
            [
                "fake-dispatch",
                "--root",
                str(exchange_root),
                "--dispatch-plan-id",
                str(plan["dispatch_plan_id"]),
            ],
        )
        assert_true(rc == 1, "fake-dispatch should require --confirm")
        rc, stdout, stderr = run_main(
            exchange_fake_dispatch.main,
            [
                "fake-dispatch",
                "--root",
                str(exchange_root),
                "--dispatch-plan-id",
                str(plan["dispatch_plan_id"]),
                "--confirm",
            ],
        )
        assert_true(rc == 0, f"fake-dispatch should create capture: {stderr}")
        assert_true("fake dispatch capture written:" in stdout, "fake-dispatch should report capture path")
        capture_manifest_path = find_capture_manifest(exchange_root, draft_packet_id, str(plan["dispatch_plan_id"]))
        assert_true(capture_manifest_path.is_file(), "fake-dispatch should write capture_manifest.json")
        assert_true(
            check_path_length(capture_manifest_path)["status"] != "fail",
            "nested fake-dispatch outbox path should stay below fail threshold",
        )
        capture_manifest = read_json(capture_manifest_path)
        assert_true((capture_manifest_path.parent / "raw_output.md").is_file(), "fake-dispatch should write raw_output.md")
        assert_true((capture_manifest_path.parent / "parsed_result.json").is_file(), "fake-dispatch should write parsed_result.json")
        assert_true((capture_manifest_path.parent / "validation.md").is_file(), "fake-dispatch should write validation.md")
        assert_true((capture_manifest_path.parent / "operator_report.md").is_file(), "fake-dispatch should write operator_report.md")
        assert_true(capture_manifest["fake_execution"] is True, "capture should mark fake_execution true")
        assert_true(capture_manifest["real_cli_execution"] is False, "capture should mark real_cli_execution false")
        assert_true(capture_manifest["model_or_provider_called"] is False, "capture should not call model/provider")
        assert_true(capture_manifest["terminal_started"] is False, "capture should not start terminal")
        assert_true(capture_manifest["branch_created"] is False, "capture should not create branches")
        assert_true(capture_manifest["commit_performed"] is False, "capture should not commit")
        assert_true(capture_manifest["push_performed"] is False, "capture should not push")
        assert_true(capture_manifest["merge_performed"] is False, "capture should not merge")
        source_dispatch_plan_path = Path(str(capture_manifest.get("source_dispatch_plan", "")))
        assert_true(source_dispatch_plan_path.is_file(), "capture should reference an existing source dispatch plan")
        source_dispatch_plan = read_json(source_dispatch_plan_path)

        missing_plan_manifest_path = capture_manifest_path.parent / "capture_manifest_missing_dispatch_plan.json"
        missing_plan_manifest = dict(capture_manifest)
        missing_plan_manifest["capture_id"] = f"{capture_manifest['capture_id']}_missing_plan"
        missing_plan_manifest["source_dispatch_plan"] = str(capture_manifest_path.parent / "missing_dispatch_plan.json")
        write_json(missing_plan_manifest_path, missing_plan_manifest)
        rc, _stdout, stderr = run_main(
            exchange_import_result.main,
            [
                "import-result",
                "--root",
                str(exchange_root),
                "--capture-manifest",
                str(missing_plan_manifest_path),
                "--confirm",
            ],
        )
        assert_true(rc == 1, "import-result should refuse missing source dispatch plan")
        assert_true("source dispatch plan" in stderr.lower(), "missing source dispatch plan should be reported clearly")

        rc, _stdout, _stderr = run_main(
            exchange_import_result.main,
            ["import-result", "--root", str(exchange_root), "--capture-manifest", str(capture_manifest_path)],
        )
        assert_true(rc == 1, "import-result should require --confirm")
        rc, stdout, stderr = run_main(
            exchange_import_result.main,
            [
                "import-result",
                "--root",
                str(exchange_root),
                "--capture-manifest",
                str(capture_manifest_path),
                "--confirm",
            ],
        )
        assert_true(rc == 0, f"import-result should create result packet: {stderr}")
        assert_true("result packet imported:" in stdout, "import-result should report imported packet")
        imported_manifest = read_json(capture_manifest_path)
        result_id = str(imported_manifest["imported_result_id"])
        result_path = exchange_root / "result_packets" / f"{result_id}.json"
        assert_true(result_path.is_file(), "import-result should create result packet")
        assert_true(len(result_path.stem) <= 96, "result packet filename stem should stay <= 96 chars")
        result_packet = read_json(result_path)
        assert_true(result_packet["result_status"] == "IMPORTED_PENDING_REVIEW", "imported result should be pending review")
        assert_true(result_packet["trusted"] is False, "imported result should be untrusted")
        assert_true(result_packet["human_review_required"] is True, "imported result should require human review")
        assert_true(
            str(result_packet.get("source_session_id", "")) == str(source_dispatch_plan.get("target_session_id", "")),
            "import-result should stamp source_session_id from dispatch plan",
        )
        assert_true(
            str(result_packet.get("source_assignment_id", "")) == str(source_dispatch_plan.get("target_assignment_id", "")),
            "import-result should stamp source_assignment_id from dispatch plan",
        )
        assert_true(
            str(result_packet.get("source_artifact_checksum", "")) == str(source_dispatch_plan.get("source_artifact_checksum", "")),
            "import-result should stamp source_artifact_checksum from dispatch plan",
        )
        rc, _stdout, _stderr = run_main(
            exchange_import_result.main,
            [
                "import-result",
                "--root",
                str(exchange_root),
                "--capture-manifest",
                str(capture_manifest_path),
                "--confirm",
            ],
        )
        assert_true(rc == 1, "duplicate import should be refused")
        rc, stdout, stderr = run_main(exchange_command.main, ["--root", str(exchange_root), "result-list"])
        assert_true(rc == 0, f"result-list should pass: {stderr}")
        assert_true(result_id in stdout, "result-list should include imported result")
        rc, stdout, stderr = run_main(
            exchange_command.main,
            ["--root", str(exchange_root), "result-status", "--result-id", result_id],
        )
        assert_true(rc == 0, f"result-status should pass: {stderr}")
        assert_true('"result_status": "IMPORTED_PENDING_REVIEW"' in stdout, "result-status should print result JSON")

        rc, stdout, stderr = run_main(
            exchange_validate_result.main,
            ["validate-result", "--root", str(exchange_root), "--result-id", result_id],
        )
        assert_true(rc == 0, f"validate-result should create validation record: {stderr}")
        assert_true("validation record written:" in stdout, "validate-result should report validation path")
        validation = latest_record_by_field(exchange_root, "result_validations", "result_id", result_id)
        validation_path = latest_record_path_by_field(exchange_root, "result_validations", "result_id", result_id)
        assert_true(len(validation_path.stem) <= 96, "validation filename stem should stay <= 96 chars")
        validation_id = str(validation["validation_id"])
        assert_true(validation["validation_status"] == "VALIDATION_PASSED", "conservative fake result should pass validation")
        assert_true(
            validation["recommended_loop_decision"] == "COMPLETED_PENDING_DAILY_REVIEW",
            "fake successful result should recommend daily-review completion",
        )
        assert_true(validation["human_escalation_required"] is False, "safe fake result should not require immediate escalation")

        rc, stdout, stderr = run_main(
            exchange_validate_result.main,
            ["validation-status", "--root", str(exchange_root), "--validation-id", validation_id],
        )
        assert_true(rc == 0, f"validation-status should pass: {stderr}")
        assert_true('"validation_status": "VALIDATION_PASSED"' in stdout, "validation-status should print validation JSON")

        rc, stdout, stderr = run_main(
            exchange_loop_decision.main,
            ["decide", "--root", str(exchange_root), "--validation-id", validation_id],
        )
        assert_true(rc == 0, f"decide-loop should create loop decision: {stderr}")
        assert_true("loop decision written:" in stdout, "decide-loop should report loop decision path")
        loop_decision = latest_record_by_field(exchange_root, "loop_decisions", "validation_id", validation_id)
        loop_path = latest_record_path_by_field(exchange_root, "loop_decisions", "validation_id", validation_id)
        assert_true(len(loop_path.stem) <= 96, "loop decision filename stem should stay <= 96 chars")
        loop_decision_id = str(loop_decision["loop_decision_id"])
        assert_true(
            loop_decision["decision"] == "COMPLETED_PENDING_DAILY_REVIEW",
            "successful fake result decision should be completed pending daily review",
        )
        assert_true(loop_decision["auto_continue_allowed"] is False, "fake result should not auto-continue in this slice")
        assert_true(loop_decision["human_escalation_required"] is False, "safe fake result should not escalate immediately")

        rc, stdout, stderr = run_main(exchange_loop_decision.main, ["loop-status", "--root", str(exchange_root)])
        assert_true(rc == 0, f"loop-status should pass: {stderr}")
        assert_true("completed_pending_daily_review: 1" in stdout, "loop-status should count completed daily-review decision")

        rc, _stdout, _stderr = run_main(
            exchange_loop_decision.main,
            ["repair-plan", "--root", str(exchange_root), "--loop-decision-id", loop_decision_id],
        )
        assert_true(rc == 1, "repair-plan should refuse non-repairable loop decisions")

        repair_validation_id = "validation__repair_fixture"
        repair_validation = dict(validation)
        repair_validation["validation_id"] = repair_validation_id
        repair_validation["validation_status"] = "VALIDATION_FAILED"
        repair_validation["recommended_loop_decision"] = "AUTO_REPAIR_ONCE"
        repair_validation["human_escalation_required"] = False
        repair_validation["reasons"] = ["bounded repair fixture"]
        repair_validation["retry_eligibility"] = {"retry_count": 0, "retry_budget": 1, "eligible": True}
        write_json(exchange_root / "result_validations" / f"{repair_validation_id}.json", repair_validation)
        rc, _stdout, stderr = run_main(
            exchange_loop_decision.main,
            ["decide", "--root", str(exchange_root), "--validation-id", repair_validation_id],
        )
        assert_true(rc == 0, f"repairable decide-loop fixture should pass: {stderr}")
        repairable_loop = latest_record_by_field(exchange_root, "loop_decisions", "validation_id", repair_validation_id)
        rc, stdout, stderr = run_main(
            exchange_loop_decision.main,
            ["repair-plan", "--root", str(exchange_root), "--loop-decision-id", str(repairable_loop["loop_decision_id"])],
        )
        assert_true(rc == 0, f"repair-plan should create metadata for repairable decision: {stderr}")
        assert_true("repair packet written:" in stdout, "repair-plan should report repair packet path")
        repair_packet = latest_record_by_field(exchange_root, "repair_packets", "loop_decision_id", str(repairable_loop["loop_decision_id"]))
        repair_path = latest_record_path_by_field(
            exchange_root, "repair_packets", "loop_decision_id", str(repairable_loop["loop_decision_id"])
        )
        assert_true(len(repair_path.stem) <= 96, "repair packet filename stem should stay <= 96 chars")
        assert_true(repair_packet["execution_allowed"] is False, "repair packet execution_allowed should stay false")
        assert_true(repair_packet["dispatch_allowed"] is False, "repair packet dispatch_allowed should stay false")
        assert_true(repair_packet["commit_allowed"] is False, "repair packet commit_allowed should stay false")
        assert_true(repair_packet["push_allowed"] is False, "repair packet push_allowed should stay false")
        assert_true(repair_packet["merge_allowed"] is False, "repair packet merge_allowed should stay false")

        enable_fake_adapter_command(exchange_root, executable="fake_adapter_cli")
        real_success_packet_id, real_success_plan, _real_success_packet_path = create_planned_dispatch(
            exchange_packet,
            exchange_dispatch_plan,
            runtime_session,
            exchange_root,
            runtime_root,
            repo_root,
            source_name="real_success.md",
            session_id="real-success-session",
        )

        class FakeCompleted:
            def __init__(self, stdout: str, stderr: str, returncode: int) -> None:
                self.stdout = stdout
                self.stderr = stderr
                self.returncode = returncode

        original_subprocess_run = exchange_real_dispatch.subprocess.run
        recorded_calls: list[dict[str, object]] = []

        def fake_success_run(argv, **kwargs):
            recorded_calls.append({"argv": argv, "kwargs": kwargs})
            return FakeCompleted("real dispatch mocked success", "", 0)

        exchange_real_dispatch.subprocess.run = fake_success_run
        try:
            rc, stdout, stderr = run_main(
                exchange_real_dispatch.main,
                [
                    "dispatch",
                    "--root",
                    str(exchange_root),
                    "--runtime-root",
                    str(runtime_root),
                    "--dispatch-plan-id",
                    str(real_success_plan["dispatch_plan_id"]),
                    "--confirm",
                ],
            )
        finally:
            exchange_real_dispatch.subprocess.run = original_subprocess_run
        assert_true(rc == 0, f"mocked real-dispatch success should pass: {stderr}")
        assert_true("real dispatch capture written:" in stdout, "real-dispatch should report capture")
        assert_true(recorded_calls and recorded_calls[0]["argv"][0] == "fake_adapter_cli", "real-dispatch test should use fake adapter executable")
        assert_true(recorded_calls[0]["kwargs"].get("shell") is False, "real-dispatch should use shell=False")
        real_capture = find_capture_manifest(exchange_root, real_success_packet_id, str(real_success_plan["dispatch_plan_id"]))
        assert_true(real_capture.is_file(), "real-dispatch should write capture_manifest.json")
        real_capture_manifest = read_json(real_capture)
        assert_true((real_capture.parent / "stdout.txt").is_file(), "real-dispatch should write stdout.txt")
        assert_true((real_capture.parent / "stderr.txt").is_file(), "real-dispatch should write stderr.txt")
        assert_true((real_capture.parent / "command_manifest.json").is_file(), "real-dispatch should write command_manifest.json")
        assert_true(real_capture_manifest["fake_execution"] is False, "real capture should mark fake_execution false")
        assert_true(real_capture_manifest["real_cli_execution"] is True, "real capture should mark real_cli_execution true when subprocess ran")
        assert_true(real_capture_manifest["model_or_provider_called"] is True, "real capture should mark model/provider called when subprocess ran")
        assert_true(real_capture_manifest["terminal_started"] is False, "real dispatch should not start terminal")
        assert_true(real_capture_manifest["branch_created"] is False, "real dispatch should not create branches")
        assert_true(real_capture_manifest["commit_performed"] is False, "real dispatch should not commit")
        assert_true(real_capture_manifest["push_performed"] is False, "real dispatch should not push")
        assert_true(real_capture_manifest["merge_performed"] is False, "real dispatch should not merge")
        real_command_manifest = read_json(real_capture.parent / "command_manifest.json")
        assert_true(real_command_manifest["shell"] is False, "command manifest should record shell false")
        assert_true(real_command_manifest["argv"][0] == "fake_adapter_cli", "command manifest should record fake argv")

        rc, stdout, stderr = run_main(
            exchange_import_result.main,
            ["import-result", "--root", str(exchange_root), "--capture-manifest", str(real_capture), "--confirm"],
        )
        assert_true(rc == 0, f"import-result should import real-dispatch capture: {stderr}")
        real_result_id = str(read_json(real_capture)["imported_result_id"])
        real_result_packet = read_json(exchange_root / "result_packets" / f"{real_result_id}.json")
        assert_true(real_result_packet["trusted"] is False, "imported real result should stay untrusted")
        assert_true(real_result_packet["real_cli_execution"] is True, "imported real result should record real CLI execution")
        rc, _stdout, stderr = run_main(
            exchange_validate_result.main,
            ["validate-result", "--root", str(exchange_root), "--result-id", real_result_id],
        )
        assert_true(rc == 0, f"validate-result should handle real-dispatch capture: {stderr}")
        real_validation = latest_record_by_field(exchange_root, "result_validations", "result_id", real_result_id)
        assert_true(real_validation["validation_status"] == "VALIDATION_PASSED", "successful real-dispatch metadata should validate")

        real_nonzero_packet_id, real_nonzero_plan, _real_nonzero_packet_path = create_planned_dispatch(
            exchange_packet,
            exchange_dispatch_plan,
            runtime_session,
            exchange_root,
            runtime_root,
            repo_root,
            source_name="real_nonzero.md",
            session_id="real-nonzero-session",
        )

        def fake_nonzero_run(argv, **kwargs):
            recorded_calls.append({"argv": argv, "kwargs": kwargs})
            return FakeCompleted("", "mocked nonzero", 7)

        exchange_real_dispatch.subprocess.run = fake_nonzero_run
        try:
            rc, _stdout, stderr = run_main(
                exchange_real_dispatch.main,
                [
                    "dispatch",
                    "--root",
                    str(exchange_root),
                    "--runtime-root",
                    str(runtime_root),
                    "--dispatch-plan-id",
                    str(real_nonzero_plan["dispatch_plan_id"]),
                    "--confirm",
                ],
            )
        finally:
            exchange_real_dispatch.subprocess.run = original_subprocess_run
        assert_true(rc == 0, f"mocked real-dispatch nonzero should still write capture: {stderr}")
        nonzero_capture = find_capture_manifest(exchange_root, real_nonzero_packet_id, str(real_nonzero_plan["dispatch_plan_id"]))
        nonzero_manifest = read_json(nonzero_capture)
        assert_true(nonzero_manifest["return_code"] == 7, "nonzero capture should record return code")
        assert_true(read_json(nonzero_capture.parent / "parsed_result.json")["validation_status"] == "CLI_RETURNED_NONZERO", "nonzero parsed result should record CLI_RETURNED_NONZERO")

        real_timeout_packet_id, real_timeout_plan, _real_timeout_packet_path = create_planned_dispatch(
            exchange_packet,
            exchange_dispatch_plan,
            runtime_session,
            exchange_root,
            runtime_root,
            repo_root,
            source_name="real_timeout.md",
            session_id="real-timeout-session",
        )

        def fake_timeout_run(argv, **kwargs):
            recorded_calls.append({"argv": argv, "kwargs": kwargs})
            raise exchange_real_dispatch.subprocess.TimeoutExpired(
                cmd=argv,
                timeout=kwargs.get("timeout", 3),
                output="partial stdout",
                stderr="partial stderr",
            )

        exchange_real_dispatch.subprocess.run = fake_timeout_run
        try:
            rc, _stdout, stderr = run_main(
                exchange_real_dispatch.main,
                [
                    "dispatch",
                    "--root",
                    str(exchange_root),
                    "--runtime-root",
                    str(runtime_root),
                    "--dispatch-plan-id",
                    str(real_timeout_plan["dispatch_plan_id"]),
                    "--confirm",
                ],
            )
        finally:
            exchange_real_dispatch.subprocess.run = original_subprocess_run
        assert_true(rc == 0, f"mocked real-dispatch timeout should still write capture: {stderr}")
        timeout_capture = find_capture_manifest(exchange_root, real_timeout_packet_id, str(real_timeout_plan["dispatch_plan_id"]))
        timeout_manifest = read_json(timeout_capture)
        assert_true(timeout_manifest["timed_out"] is True, "timeout capture should record timed_out true")
        assert_true(read_json(timeout_capture.parent / "parsed_result.json")["validation_status"] == "CLI_TIMEOUT", "timeout parsed result should record CLI_TIMEOUT")

        path_ok = check_path_length("C:/a")
        path_warn = check_path_length(Path("C:/") / ("a" * 181))
        path_fail = check_path_length(Path("C:/") / ("a" * 221))
        assert_true(path_ok["status"] == "ok", "check_path_length should classify short paths as ok")
        assert_true(path_warn["status"] == "warn", "check_path_length should classify warn-threshold paths as warn")
        assert_true(path_fail["status"] == "fail", "check_path_length should classify fail-threshold paths as fail")

        missing_exchange_root = tmp_root / "missing_capture_repo" / "exchange_lane"
        missing_manifest_path = clone_imported_result_fixture(exchange_root, missing_exchange_root, result_id, capture_manifest_path)
        missing_validation_file = Path(str(read_json(missing_manifest_path)["validation_path"]))
        missing_validation_file.unlink()
        rc, _stdout, stderr = run_main(
            exchange_validate_result.main,
            ["validate-result", "--root", str(missing_exchange_root), "--result-id", result_id],
        )
        assert_true(rc == 0, f"validate-result should write incomplete validation for missing artifact: {stderr}")
        missing_validation = latest_record_by_field(missing_exchange_root, "result_validations", "result_id", result_id)
        assert_true(
            missing_validation["validation_status"] == "VALIDATION_INCOMPLETE",
            "missing capture artifact should become VALIDATION_INCOMPLETE",
        )
        assert_true(
            missing_validation["recommended_loop_decision"] == "BLOCKED_VALIDATION_FAILED",
            "missing capture artifact should block loop progression",
        )

        forbidden_exchange_root = tmp_root / "forbidden_capture_repo" / "exchange_lane"
        forbidden_manifest_path = clone_imported_result_fixture(exchange_root, forbidden_exchange_root, result_id, capture_manifest_path)
        forbidden_manifest = read_json(forbidden_manifest_path)
        forbidden_manifest["branch_created"] = True
        write_json(forbidden_manifest_path, forbidden_manifest)
        rc, _stdout, stderr = run_main(
            exchange_validate_result.main,
            ["validate-result", "--root", str(forbidden_exchange_root), "--result-id", result_id],
        )
        assert_true(rc == 0, f"validate-result should write failed validation for forbidden flag: {stderr}")
        forbidden_validation = latest_record_by_field(forbidden_exchange_root, "result_validations", "result_id", result_id)
        assert_true(
            forbidden_validation["validation_status"] == "VALIDATION_FAILED",
            "forbidden safety flag should become VALIDATION_FAILED",
        )
        assert_true(
            forbidden_validation["recommended_loop_decision"] == "BLOCKED_FORBIDDEN_ACTION",
            "forbidden safety flag should block as forbidden action",
        )

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
        rc, _stdout, _stderr = run_main(
            exchange_real_dispatch.main,
            [
                "dispatch",
                "--root",
                str(exchange_root),
                "--runtime-root",
                str(runtime_root),
                "--dispatch-plan-id",
                str(plan_for_packet(exchange_root, packet_id_source_changed)["dispatch_plan_id"]),
                "--confirm",
            ],
        )
        assert_true(rc == 1, "real-dispatch should refuse non-PLANNED_NOT_DISPATCHED plans")
        rc, _stdout, _stderr = run_main(
            exchange_fake_dispatch.main,
            [
                "fake-dispatch",
                "--root",
                str(exchange_root),
                "--dispatch-plan-id",
                str(plan_for_packet(exchange_root, packet_id_source_changed)["dispatch_plan_id"]),
                "--confirm",
            ],
        )
        assert_true(rc == 1, "fake-dispatch should refuse blocked dispatch plans")

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
            rc, stdout, stderr = ws_result
            if rc != 1:
                print(f"DEBUG: ws exchange approve-planning returned {rc}")
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")
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

            ws_fake_source = repo_root / "product_development_lane" / "implementation_plans" / "ws_fake_case.md"
            write_text(ws_fake_source, "# ws fake case\n")
            ws_fake_packet_path, ws_fake_packet_id = create_packet(exchange_packet, exchange_root, ws_fake_source, "codex_cli")
            mark_ready(exchange_packet, exchange_root, ws_fake_packet_id)
            rc, _stdout, stderr = approve_planning(
                exchange_packet, exchange_root, ws_fake_packet_id, "approve ws fake dispatch case"
            )
            assert_true(rc == 0, f"approve-planning ws fake case should pass: {stderr}")
            create_session(runtime_session, runtime_root, repo_root, "ws-fake-session", "codex_cli")
            update_session_status(runtime_session, runtime_root, "ws-fake-session", "READY")
            ws_fake_assignment = create_assignment(
                runtime_session, runtime_root, "ws-fake-session", ws_fake_source, "ws fake assignment"
            )
            rc, _stdout, stderr = plan_packet(
                exchange_dispatch_plan,
                exchange_root,
                runtime_root,
                packet_id=ws_fake_packet_id,
                session_id="ws-fake-session",
                assignment_id=str(read_json(ws_fake_assignment)["assignment_id"]),
            )
            assert_true(rc == 0, f"direct dispatch plan for ws fake case should pass: {stderr}")
            ws_plan = plan_for_packet(exchange_root, ws_fake_packet_id)
            assert_true(ws_plan["planned_status"] == "PLANNED_NOT_DISPATCHED", "ws fake case should use an unblocked plan")
            rc, stdout, stderr = run_ws_exchange(
                repo_root,
                ["fake-dispatch", "--dispatch-plan-id", str(ws_plan["dispatch_plan_id"]), "--confirm"],
            )
            assert_true(rc == 0, f"ws exchange fake-dispatch should pass: {stderr}")
            assert_true("fake dispatch capture written:" in stdout, "ws fake-dispatch should report capture")
            ws_capture = find_capture_manifest(exchange_root, ws_fake_packet_id, str(ws_plan["dispatch_plan_id"]))
            assert_true(ws_capture.is_file(), "ws fake-dispatch should create capture manifest")
            rc, stdout, stderr = run_ws_exchange(
                repo_root,
                ["import-result", "--capture-manifest", str(ws_capture), "--confirm"],
            )
            assert_true(rc == 0, f"ws exchange import-result should pass: {stderr}")
            assert_true("result packet imported:" in stdout, "ws import-result should report import")
            ws_result_id = str(read_json(ws_capture)["imported_result_id"])
            rc, stdout, stderr = run_ws_exchange(repo_root, ["validate-result", "--result-id", ws_result_id])
            assert_true(rc == 0, f"ws exchange validate-result should pass: {stderr}")
            assert_true("validation record written:" in stdout, "ws validate-result should report validation")
            rc, stdout, stderr = run_ws_exchange(repo_root, ["loop-status"])
            assert_true(rc == 0, f"ws exchange loop-status should pass: {stderr}")
            assert_true("Exchange Loop Status" in stdout, "ws loop-status should report loop status")

    finally:
        if tmp_root.exists():
            remove_tree(tmp_root)

    print("Exchange Lane validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

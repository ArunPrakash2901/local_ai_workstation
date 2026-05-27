#!/usr/bin/env python3
"""Guarded Open Design daemon render planning and execution helpers."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from product_design_adapter import build_design_render_preview
from product_design_run import (
    DESIGN_EXECUTION_MODE_NOT_EXECUTED,
    DESIGN_RUN_FILENAME,
    DESIGN_RUN_STATUS_PREPARED,
    get_design_run_status,
)
from product_design_runtime_probe import (
    RENDER_CONTRACT_FOUND,
    RENDER_READY,
    probe_design_runtime,
)


OPEN_DESIGN_RENDER_DRY_RUN_ACTION = (
    "ws product-design-render --product <product_id> --tool open-design --dry-run"
)
OPEN_DESIGN_RENDER_CONFIRM_ACTION = (
    "ws product-design-render --product <product_id> --tool open-design --confirm"
)

RENDER_STATUS_EXECUTED_CAPTURED = "EXECUTED_CAPTURED"
RENDER_STATUS_BLOCKED = "BLOCKED_NEEDS_OPERATOR_UI_RESPONSE"
RENDER_STATUS_REFUSED = "REFUSED_PRECONDITION_FAILED"
RENDER_STATUS_FAILED = "FAILED_EXECUTION_ERROR"

DEFAULT_TIMEOUT_SECONDS = 240

PROVIDER_MODE_ENV = "OPEN_DESIGN_RENDER_PROVIDER_MODE"
PROVIDER_MODE_API = "api"
PROVIDER_MODE_LOCAL_CLI = "local_cli"
SUPPORTED_PROVIDER_MODES = {PROVIDER_MODE_API, PROVIDER_MODE_LOCAL_CLI}

PROVIDER_KEY_HINTS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "OPENROUTER_API_KEY",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_child(base: Path, child: Path) -> Path:
    base_resolved = base.resolve()
    child_resolved = child.resolve()
    if child_resolved == base_resolved:
        return child_resolved
    if base_resolved not in child_resolved.parents:
        raise ValueError(f"path escapes expected base: {child_resolved} not under {base_resolved}")
    return child_resolved


def _json_load(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}") from exc
    if not isinstance(loaded, dict):
        raise ValueError(f"expected object JSON in {path}")
    return loaded


def _json_write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")


def _append_text(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        if text and not text.endswith("\n"):
            handle.write("\n")


def _choose_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _provider_requirements(env_map: dict[str, str]) -> dict[str, Any]:
    mode_raw = str(env_map.get(PROVIDER_MODE_ENV, "")).strip().lower()
    has_any_key = any(bool(env_map.get(name)) for name in PROVIDER_KEY_HINTS)

    if mode_raw not in SUPPORTED_PROVIDER_MODES:
        return {
            "mode": mode_raw or "UNSET",
            "known": False,
            "satisfied": False,
            "reason": (
                f"Set {PROVIDER_MODE_ENV} to one of: "
                f"{', '.join(sorted(SUPPORTED_PROVIDER_MODES))}."
            ),
        }

    if mode_raw == PROVIDER_MODE_LOCAL_CLI:
        return {
            "mode": mode_raw,
            "known": True,
            "satisfied": True,
            "reason": "Local CLI provider mode selected.",
        }

    # mode_raw == PROVIDER_MODE_API
    if has_any_key:
        return {
            "mode": mode_raw,
            "known": True,
            "satisfied": True,
            "reason": "API provider mode selected with at least one provider key present.",
        }
    return {
        "mode": mode_raw,
        "known": True,
        "satisfied": False,
        "reason": "API provider mode selected but no provider API key is present.",
    }


def _collect_ui_blockers(run_events_text: str) -> list[str]:
    blockers: list[str] = []
    for raw_line in run_events_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        if "genui_surface_request" in lower:
            blockers.append("GENUI_SURFACE_REQUEST")
            continue
        if "question-form" in lower:
            blockers.append("QUESTION_FORM_REQUESTED")
            continue
        if "oauth-prompt" in lower:
            blockers.append("OAUTH_PROMPT_REQUESTED")
            continue
        if "confirmation" in lower and "ui" in lower:
            blockers.append("UI_CONFIRMATION_REQUESTED")
            continue
    # preserve order while deduping
    deduped: list[str] = []
    for item in blockers:
        if item not in deduped:
            deduped.append(item)
    return deduped


def _build_runtime_env(env_map: dict[str, str], od_data_dir: Path) -> dict[str, str]:
    # Restrict env propagation to minimal runtime keys + explicit provider keys.
    allowed_core = (
        "PATH",
        "HOME",
        "USER",
        "USERPROFILE",
        "TMP",
        "TEMP",
        "SystemRoot",
        "ComSpec",
        "NVM_DIR",
        "NVM_BIN",
        PROVIDER_MODE_ENV,
    )
    allowed_provider_keys = PROVIDER_KEY_HINTS
    runtime_env: dict[str, str] = {}
    for key in allowed_core:
        value = env_map.get(key)
        if value:
            runtime_env[key] = value
    for key in allowed_provider_keys:
        value = env_map.get(key)
        if value:
            runtime_env[key] = value
    runtime_env["OD_DATA_DIR"] = od_data_dir.as_posix()
    return runtime_env


def build_open_design_render_plan(
    root: str | Path,
    product_id: str,
    tool: str,
    *,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    root_path = Path(root).expanduser().resolve()
    env_map = dict(os.environ) if env is None else dict(env)

    render_preview = build_design_render_preview(root_path, product_id, tool)
    run_status = get_design_run_status(root_path, product_id, tool)
    runtime_probe = probe_design_runtime(root_path, tool, env=env_map)

    source_info = runtime_probe.get("source_checkout_detection", {})
    required_files = source_info.get("required_files", {}) if isinstance(source_info, dict) else {}
    source_path_raw = str(source_info.get("path", "")).strip()
    source_checkout_path = (
        Path(source_path_raw).expanduser().resolve() if source_path_raw else (root_path / "__missing_source_checkout__")
    )

    node_path = runtime_probe.get("detected_command_paths", {}).get("node")
    daemon_cli_rel = "apps/daemon/dist/cli.js"
    daemon_cli_abs = (
        source_checkout_path / daemon_cli_rel
    )

    planned_port = _choose_free_port()
    daemon_url = f"http://127.0.0.1:{planned_port}"

    run_dir_rel = str(run_status.get("run_dir", "")).strip().rstrip("/")
    run_dir_abs = _safe_child(root_path, root_path / run_dir_rel)

    allowed_root_rel = str(run_status.get("allowed_write_root", "")).strip()
    allowed_root_rel = allowed_root_rel.rstrip("/")
    allowed_root_abs = _safe_child(root_path, root_path / allowed_root_rel)

    if not allowed_root_abs.exists():
        # keep path planning deterministic; create happens only on confirm.
        allowed_root_exists = False
    else:
        allowed_root_exists = True

    capture_paths_abs = {
        "stdout.txt": _safe_child(allowed_root_abs, allowed_root_abs / "stdout.txt"),
        "stderr.txt": _safe_child(allowed_root_abs, allowed_root_abs / "stderr.txt"),
        "daemon_stdout.txt": _safe_child(allowed_root_abs, allowed_root_abs / "daemon_stdout.txt"),
        "daemon_stderr.txt": _safe_child(allowed_root_abs, allowed_root_abs / "daemon_stderr.txt"),
        "run_events.ndjson": _safe_child(allowed_root_abs, allowed_root_abs / "raw_output" / "run_events.ndjson"),
        "command_manifest.json": _safe_child(allowed_root_abs, allowed_root_abs / "command_manifest.json"),
        "render_manifest.json": _safe_child(allowed_root_abs, allowed_root_abs / "render_manifest.json"),
        "output_file_list.json": _safe_child(allowed_root_abs, allowed_root_abs / "output_file_list.json"),
        "render_review.md": _safe_child(allowed_root_abs, allowed_root_abs / "render_review.md"),
    }
    capture_paths_rel = {
        name: path.relative_to(root_path).as_posix() for name, path in capture_paths_abs.items()
    }

    planned_od_data_dir_abs = _safe_child(allowed_root_abs, allowed_root_abs / "open_design_data")
    planned_od_data_dir_rel = planned_od_data_dir_abs.relative_to(root_path).as_posix()

    timeout_seconds = int(env_map.get("OPEN_DESIGN_RENDER_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))
    if timeout_seconds <= 0:
        timeout_seconds = DEFAULT_TIMEOUT_SECONDS

    provider = _provider_requirements(env_map)

    blockers: list[str] = []
    if str(run_status.get("status")) != DESIGN_RUN_STATUS_PREPARED:
        blockers.append(f"RUN_STATUS_NOT_PREPARED:{run_status.get('status')}")
    if str(run_status.get("execution_mode")) != DESIGN_EXECUTION_MODE_NOT_EXECUTED:
        blockers.append(f"RUN_EXECUTION_MODE_INVALID:{run_status.get('execution_mode')}")
    if not run_status.get("design_run_yaml_present", False):
        blockers.append(f"MISSING_{DESIGN_RUN_FILENAME}")
    if not allowed_root_exists:
        blockers.append("ALLOWED_WRITE_ROOT_MISSING")
    if not bool(node_path):
        blockers.append("NODE_NOT_FOUND")
    if not bool(source_info.get("exists")):
        blockers.append("SOURCE_CHECKOUT_MISSING")
    if not bool(required_files.get("apps/daemon/dist/cli.js")):
        blockers.append("DAEMON_CLI_MISSING")
    if runtime_probe.get("readiness_classification") not in {RENDER_CONTRACT_FOUND, RENDER_READY}:
        blockers.append(f"RUNTIME_NOT_RENDER_CONTRACT:{runtime_probe.get('readiness_classification')}")
    if not provider["known"]:
        blockers.append("PROVIDER_REQUIREMENTS_UNKNOWN")
    elif not provider["satisfied"]:
        blockers.append("PROVIDER_REQUIREMENTS_UNSATISFIED")

    render_preview["render_confirm_allowed"] = len(blockers) == 0
    render_preview["render_confirm_refusal_reason"] = (
        "NONE" if len(blockers) == 0 else "REFUSED_PRECONDITION_FAILED"
    )

    return {
        "title": "Product Design Open Design Guarded Render Plan",
        "product_id": product_id,
        "tool": tool,
        "run_id": run_status.get("run_id"),
        "render_preview": render_preview,
        "run_status": run_status,
        "runtime_probe": runtime_probe,
        "source_checkout_path": source_checkout_path.as_posix(),
        "node_path": node_path,
        "daemon_cli_path": daemon_cli_abs.as_posix(),
        "planned_daemon_port": planned_port,
        "planned_daemon_url": daemon_url,
        "planned_od_data_dir": planned_od_data_dir_rel,
        "allowed_write_root": allowed_root_abs.relative_to(root_path).as_posix() + "/",
        "run_directory": run_dir_abs.relative_to(root_path).as_posix() + "/",
        "capture_paths": capture_paths_rel,
        "timeout_seconds": timeout_seconds,
        "provider_requirements": provider,
        "execution": "no",
        "provider_call": "no",
        "writes": "none",
        "confirm_allowed": len(blockers) == 0,
        "confirm_blockers": blockers,
    }


def render_open_design_render_plan(plan: dict[str, Any]) -> str:
    lines = [
        "# Product Design Render Preview",
        "",
        "- DRY RUN / no files written",
        f"- canonical ws command: `{OPEN_DESIGN_RENDER_DRY_RUN_ACTION}`",
        f"- product_id: `{plan['product_id']}`",
        f"- run_id: `{plan['run_id']}`",
        f"- tool: `{plan['tool']}`",
        "",
        "## Runtime Contract",
        f"- source checkout path: `{plan['source_checkout_path']}`",
        f"- node path: `{plan['node_path'] or 'NOT_FOUND'}`",
        f"- daemon CLI path: `{plan['daemon_cli_path']}`",
        f"- planned daemon URL: `{plan['planned_daemon_url']}`",
        f"- planned daemon port: `{plan['planned_daemon_port']}`",
        f"- planned OD_DATA_DIR: `{plan['planned_od_data_dir']}`",
        f"- allowed write root: `{plan['allowed_write_root']}`",
        f"- timeout_seconds: `{plan['timeout_seconds']}`",
        "",
        "## Planned Capture Paths",
    ]
    for key in (
        "stdout.txt",
        "stderr.txt",
        "daemon_stdout.txt",
        "daemon_stderr.txt",
        "run_events.ndjson",
        "command_manifest.json",
        "render_manifest.json",
        "output_file_list.json",
        "render_review.md",
    ):
        lines.append(f"- {key}: `{plan['capture_paths'][key]}`")

    lines.extend(
        [
            "",
            "## Provider Requirements",
            f"- mode: `{plan['provider_requirements']['mode']}`",
            f"- known: `{plan['provider_requirements']['known']}`",
            f"- satisfied: `{plan['provider_requirements']['satisfied']}`",
            f"- note: {plan['provider_requirements']['reason']}",
            "",
            "## Guarded Execution Flags",
            f"- execution: `{plan['execution']}`",
            f"- provider_call: `{plan['provider_call']}`",
            f"- writes: `{plan['writes']}`",
            f"- confirm_allowed: `{plan['confirm_allowed']}`",
            "- confirm_blockers:",
        ]
    )
    if plan["confirm_blockers"]:
        for blocker in plan["confirm_blockers"]:
            lines.append(f"  - `{blocker}`")
    else:
        lines.append("  - none")

    lines.extend(
        [
            "",
            "## Next Command",
            f"- `{OPEN_DESIGN_RENDER_CONFIRM_ACTION}`",
            "",
        ]
    )
    return "\n".join(lines)


def execute_open_design_render_confirm(
    root: str | Path,
    product_id: str,
    tool: str,
    *,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    root_path = Path(root).expanduser().resolve()
    env_map = dict(os.environ) if env is None else dict(env)
    plan = build_open_design_render_plan(root_path, product_id, tool, env=env_map)
    if not plan["confirm_allowed"]:
        raise ValueError(
            "REFUSED_PRECONDITION_FAILED: " + ", ".join(plan["confirm_blockers"])
        )

    run_status = plan["run_status"]
    run_dir_abs = _safe_child(root_path, root_path / str(run_status["run_dir"]).rstrip("/"))
    design_run_path = _safe_child(run_dir_abs, run_dir_abs / DESIGN_RUN_FILENAME)
    design_prompt_path = _safe_child(run_dir_abs, run_dir_abs / "design_prompt.md")
    run_payload = _json_load(design_run_path)

    capture_paths_abs = {
        name: _safe_child(root_path, root_path / rel)
        for name, rel in plan["capture_paths"].items()
    }
    for path in capture_paths_abs.values():
        _safe_child(run_dir_abs, path)
    od_data_dir_abs = _safe_child(root_path, root_path / plan["planned_od_data_dir"])
    _safe_child(run_dir_abs, od_data_dir_abs)

    # Capture dirs.
    for folder in ("raw_output", "prototype", "screenshots", "export"):
        _safe_child(run_dir_abs, run_dir_abs / folder).mkdir(parents=True, exist_ok=True)
    od_data_dir_abs.mkdir(parents=True, exist_ok=True)

    # Initialize capture files.
    for key in ("stdout.txt", "stderr.txt", "daemon_stdout.txt", "daemon_stderr.txt", "run_events.ndjson"):
        capture_paths_abs[key].write_text("", encoding="utf-8", newline="\n")

    daemon_url = str(plan["planned_daemon_url"])
    daemon_cmd = [
        str(plan["node_path"]),
        str(plan["daemon_cli_path"]),
        "daemon",
        "start",
        "--headless",
        "--port",
        str(plan["planned_daemon_port"]),
        "--host",
        "127.0.0.1",
    ]
    status_cmd = [
        str(plan["node_path"]),
        str(plan["daemon_cli_path"]),
        "status",
        "--json",
        "--daemon-url",
        daemon_url,
    ]

    command_manifest: dict[str, Any] = {
        "started_at": _utc_now_iso(),
        "root": root_path.as_posix(),
        "source_checkout_path": plan["source_checkout_path"],
        "daemon_url": daemon_url,
        "timeout_seconds": plan["timeout_seconds"],
        "commands": {
            "daemon_start": daemon_cmd,
            "daemon_status": status_cmd,
        },
        "no_shell": True,
        "shell_used": False,
    }

    daemon_process: subprocess.Popen[str] | None = None
    project_id: str | None = None
    run_stdout_text = ""
    run_stderr_text = ""
    output_file_list: dict[str, Any] = {"project_id": None, "files": []}
    ui_blockers: list[str] = []
    return_code: int | None = None
    timed_out = False
    status = RENDER_STATUS_FAILED
    failure_reason: str | None = None

    runtime_env = _build_runtime_env(env_map, od_data_dir_abs)

    try:
        daemon_out = capture_paths_abs["daemon_stdout.txt"].open("a", encoding="utf-8")
        daemon_err = capture_paths_abs["daemon_stderr.txt"].open("a", encoding="utf-8")
        try:
            daemon_process = subprocess.Popen(
                daemon_cmd,
                cwd=plan["source_checkout_path"],
                env=runtime_env,
                stdout=daemon_out,
                stderr=daemon_err,
                text=True,
                shell=False,
            )
        finally:
            daemon_out.close()
            daemon_err.close()

        # Readiness polling
        status_ok = False
        for _ in range(30):
            probe = subprocess.run(
                status_cmd,
                cwd=plan["source_checkout_path"],
                env=runtime_env,
                capture_output=True,
                text=True,
                timeout=10,
                shell=False,
            )
            if probe.returncode == 0:
                status_ok = True
                _append_text(capture_paths_abs["stdout.txt"], probe.stdout)
                break
            time.sleep(1)
        if not status_ok:
            status = RENDER_STATUS_REFUSED
            failure_reason = "DAEMON_STATUS_CHECK_FAILED"
            raise RuntimeError(failure_reason)

        project_name = f"{plan['product_id']} open-design render {plan['run_id']}"
        project_create_cmd = [
            str(plan["node_path"]),
            str(plan["daemon_cli_path"]),
            "project",
            "create",
            "--name",
            project_name,
            "--json",
            "--daemon-url",
            daemon_url,
        ]
        command_manifest["commands"]["project_create"] = project_create_cmd
        project_create = subprocess.run(
            project_create_cmd,
            cwd=plan["source_checkout_path"],
            env=runtime_env,
            capture_output=True,
            text=True,
            timeout=30,
            shell=False,
        )
        _append_text(capture_paths_abs["stdout.txt"], project_create.stdout)
        _append_text(capture_paths_abs["stderr.txt"], project_create.stderr)
        if project_create.returncode != 0:
            status = RENDER_STATUS_FAILED
            failure_reason = "PROJECT_CREATE_FAILED"
            raise RuntimeError(f"{failure_reason}: {project_create.stderr.strip()}")
        try:
            created_payload = json.loads(project_create.stdout)
        except json.JSONDecodeError as exc:
            status = RENDER_STATUS_FAILED
            failure_reason = "PROJECT_CREATE_INVALID_JSON"
            raise RuntimeError(failure_reason) from exc
        project_obj = created_payload.get("project")
        if isinstance(project_obj, dict):
            project_id = str(project_obj.get("id", "")).strip() or None
        if not project_id:
            project_id = str(created_payload.get("projectId", "")).strip() or None
        if not project_id:
            status = RENDER_STATUS_FAILED
            failure_reason = "PROJECT_ID_MISSING"
            raise RuntimeError(failure_reason)

        prompt_text = design_prompt_path.read_text(encoding="utf-8")
        run_start_cmd = [
            str(plan["node_path"]),
            str(plan["daemon_cli_path"]),
            "run",
            "start",
            "--project",
            project_id,
            "--message",
            prompt_text,
            "--follow",
            "--daemon-url",
            daemon_url,
        ]
        command_manifest["commands"]["run_start"] = run_start_cmd
        run_start = subprocess.run(
            run_start_cmd,
            cwd=plan["source_checkout_path"],
            env=runtime_env,
            capture_output=True,
            text=True,
            timeout=plan["timeout_seconds"],
            shell=False,
        )
        return_code = int(run_start.returncode)
        run_stdout_text = run_start.stdout
        run_stderr_text = run_start.stderr
        _append_text(capture_paths_abs["stdout.txt"], run_stdout_text)
        _append_text(capture_paths_abs["stderr.txt"], run_stderr_text)
        capture_paths_abs["run_events.ndjson"].write_text(
            run_stdout_text if run_stdout_text.endswith("\n") else (run_stdout_text + "\n"),
            encoding="utf-8",
            newline="\n",
        )

        ui_blockers = _collect_ui_blockers(run_stdout_text + "\n" + run_stderr_text)
        if ui_blockers:
            status = RENDER_STATUS_BLOCKED
            failure_reason = "GENUI_SURFACE_RESPONSE_REQUIRED"
        elif return_code == 0:
            status = RENDER_STATUS_EXECUTED_CAPTURED
        else:
            status = RENDER_STATUS_FAILED
            failure_reason = f"RUN_RETURNED_{return_code}"

        files_list_cmd = [
            str(plan["node_path"]),
            str(plan["daemon_cli_path"]),
            "files",
            "list",
            project_id,
            "--json",
            "--daemon-url",
            daemon_url,
        ]
        command_manifest["commands"]["files_list"] = files_list_cmd
        files_list = subprocess.run(
            files_list_cmd,
            cwd=plan["source_checkout_path"],
            env=runtime_env,
            capture_output=True,
            text=True,
            timeout=30,
            shell=False,
        )
        if files_list.returncode == 0:
            try:
                file_payload = json.loads(files_list.stdout)
            except json.JSONDecodeError:
                file_payload = {"files": []}
            files = file_payload.get("files")
            if isinstance(files, list):
                normalized_files: list[dict[str, Any]] = []
                for entry in files:
                    if not isinstance(entry, dict):
                        continue
                    name = str(entry.get("name", "")).strip()
                    if not name:
                        continue
                    candidate_path = _safe_child(
                        od_data_dir_abs / "projects" / project_id,
                        od_data_dir_abs / "projects" / project_id / name,
                    )
                    _safe_child(run_dir_abs, candidate_path)
                    normalized_files.append(
                        {
                            "name": name,
                            "size": entry.get("size"),
                            "kind": entry.get("kind"),
                            "project_path": candidate_path.relative_to(root_path).as_posix(),
                        }
                    )
                output_file_list = {"project_id": project_id, "files": normalized_files}
    except subprocess.TimeoutExpired:
        timed_out = True
        status = RENDER_STATUS_FAILED
        failure_reason = "RUN_TIMEOUT"
    finally:
        daemon_stop_cmd = [
            str(plan["node_path"]),
            str(plan["daemon_cli_path"]),
            "daemon",
            "stop",
            "--daemon-url",
            daemon_url,
        ]
        command_manifest["commands"]["daemon_stop"] = daemon_stop_cmd
        try:
            subprocess.run(
                daemon_stop_cmd,
                cwd=plan["source_checkout_path"],
                env=runtime_env,
                capture_output=True,
                text=True,
                timeout=15,
                shell=False,
            )
        except Exception:
            pass
        if daemon_process is not None and daemon_process.poll() is None:
            try:
                daemon_process.terminate()
                daemon_process.wait(timeout=5)
            except Exception:
                try:
                    daemon_process.kill()
                except Exception:
                    pass

    command_manifest["finished_at"] = _utc_now_iso()
    _json_write(capture_paths_abs["command_manifest.json"], command_manifest)

    render_manifest = {
        "product_id": plan["product_id"],
        "run_id": plan["run_id"],
        "status": status,
        "failure_reason": failure_reason,
        "timed_out": timed_out,
        "return_code": return_code,
        "daemon_url": daemon_url,
        "project_id": project_id,
        "ui_blockers": ui_blockers,
        "provider_call_attempted": project_id is not None,
        "open_design_executed": project_id is not None,
        "source_mutation_detected": False,
        "capture_paths": plan["capture_paths"],
        "od_data_dir": plan["planned_od_data_dir"],
        "created_at": _utc_now_iso(),
    }
    _json_write(capture_paths_abs["render_manifest.json"], render_manifest)
    _json_write(capture_paths_abs["output_file_list.json"], output_file_list)

    review_lines = [
        "# Open Design Guarded Render Review",
        "",
        f"- product_id: `{plan['product_id']}`",
        f"- run_id: `{plan['run_id']}`",
        f"- status: `{status}`",
        f"- failure_reason: `{failure_reason or 'NONE'}`",
        f"- return_code: `{return_code}`",
        f"- timed_out: `{timed_out}`",
        f"- project_id: `{project_id or 'NONE'}`",
        f"- ui_blockers: `{', '.join(ui_blockers) if ui_blockers else 'none'}`",
        f"- command manifest: `{plan['capture_paths']['command_manifest.json']}`",
        f"- render manifest: `{plan['capture_paths']['render_manifest.json']}`",
        f"- output file list: `{plan['capture_paths']['output_file_list.json']}`",
        "",
    ]
    capture_paths_abs["render_review.md"].write_text("\n".join(review_lines), encoding="utf-8", newline="\n")

    run_payload["status"] = status
    run_payload["execution_mode"] = "EXECUTED_GUARDED_DAEMON"
    run_payload["open_design_executed"] = bool(project_id is not None)
    run_payload["last_render_manifest"] = plan["capture_paths"]["render_manifest.json"]
    run_payload["last_command_manifest"] = plan["capture_paths"]["command_manifest.json"]
    run_payload["last_updated_at"] = _utc_now_iso()
    _json_write(design_run_path, run_payload)

    return {
        "product_id": plan["product_id"],
        "run_id": plan["run_id"],
        "status": status,
        "failure_reason": failure_reason,
        "timed_out": timed_out,
        "return_code": return_code,
        "project_id": project_id,
        "capture_paths": plan["capture_paths"],
        "ui_blockers": ui_blockers,
        "open_design_executed": bool(project_id is not None),
        "source_mutation_detected": False,
    }


def render_open_design_render_result(result: dict[str, Any]) -> str:
    lines = [
        "# Product Design Render Result",
        "",
        f"- product_id: `{result.get('product_id')}`",
        f"- run_id: `{result.get('run_id')}`",
        f"- status: `{result.get('status')}`",
        f"- failure_reason: `{result.get('failure_reason') or 'NONE'}`",
        f"- return_code: `{result.get('return_code')}`",
        f"- timed_out: `{result.get('timed_out')}`",
        f"- project_id: `{result.get('project_id') or 'NONE'}`",
        f"- open_design_executed: `{result.get('open_design_executed')}`",
        f"- source_mutation_detected: `{result.get('source_mutation_detected')}`",
        "",
        "## Capture Paths",
    ]
    capture_paths = result.get("capture_paths", {}) if isinstance(result.get("capture_paths"), dict) else {}
    for key in (
        "stdout.txt",
        "stderr.txt",
        "daemon_stdout.txt",
        "daemon_stderr.txt",
        "run_events.ndjson",
        "command_manifest.json",
        "render_manifest.json",
        "output_file_list.json",
        "render_review.md",
    ):
        if key in capture_paths:
            lines.append(f"- {key}: `{capture_paths[key]}`")
    blockers = result.get("ui_blockers") if isinstance(result.get("ui_blockers"), list) else []
    lines.extend(["", "## UI Blockers"])
    if blockers:
        for blocker in blockers:
            lines.append(f"- `{blocker}`")
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)

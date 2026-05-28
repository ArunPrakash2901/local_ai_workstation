#!/usr/bin/env python3
"""Managed Open Design runtime lifecycle helpers.

This module wraps the repo-supported `pnpm tools-dev` lifecycle without using
global `od`/`open-design` binaries. It starts/stops only the managed web stack;
it does not request a design run, spawn Codex/Gemini, or trust generated output.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from product_design_adapter import validate_design_tool
from product_design_runtime_probe import probe_design_runtime


MANAGED_RUNTIME_STATUS_ACTION = "ws product-design-runtime-status --tool open-design"
MANAGED_RUNTIME_START_DRY_RUN_ACTION = "ws product-design-runtime-start --tool open-design --dry-run"
MANAGED_RUNTIME_START_CONFIRM_ACTION = "ws product-design-runtime-start --tool open-design --confirm"
MANAGED_RUNTIME_STOP_DRY_RUN_ACTION = "ws product-design-runtime-stop --tool open-design --dry-run"
MANAGED_RUNTIME_STOP_CONFIRM_ACTION = "ws product-design-runtime-stop --tool open-design --confirm"

MANAGED_RUNTIME_MODE = "MANAGED_RUNTIME_MODE"
EXPERIMENTAL_HEADLESS_MODE = "EXPERIMENTAL_HEADLESS_DAEMON_MODE"

DEFAULT_NAMESPACE = "workstation"
DEFAULT_APP = "web"
DEFAULT_TIMEOUT_SECONDS = 45

FORBIDDEN_EXECUTABLE_NAMES = {
    "od",
    "od.exe",
    "open-design",
    "open-design.exe",
    "cmd",
    "cmd.exe",
    "powershell",
    "powershell.exe",
    "pwsh",
    "pwsh.exe",
    "bash",
    "bash.exe",
    "wsl",
    "wsl.exe",
}

REQUIRED_SOURCE_FILES = (
    "package.json",
    "pnpm-lock.yaml",
    "node_modules/",
    "tools/dev/package.json",
    "tools/dev/bin/tools-dev.mjs",
    "tools/dev/dist/index.mjs",
    "apps/daemon/package.json",
    "apps/daemon/dist/cli.js",
    "apps/web/package.json",
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


def _json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")


def _text_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    candidates = [stripped]
    start = stripped.find("{")
    end = stripped.rfind("}")
    if 0 <= start < end:
        candidates.append(stripped[start : end + 1])
    for candidate in candidates:
        if not candidate:
            continue
        try:
            loaded = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(loaded, dict):
            return loaded
    return {}


def _bool_file(source: Path, rel: str) -> bool:
    if rel.endswith("/"):
        return (source / rel.rstrip("/")).is_dir()
    return (source / rel).is_file()


def _is_forbidden_executable(path_text: str | None) -> bool:
    if not path_text:
        return True
    name = Path(path_text).name.lower()
    return name in FORBIDDEN_EXECUTABLE_NAMES or name.endswith(".cmd") or name.endswith(".bat")


def _managed_runtime_dir(root: Path) -> Path:
    return _safe_child(root, root / "product_development_lane" / "runtime" / "open_design" / "managed_runtime")


def _tools_dev_root(root: Path) -> Path:
    return _safe_child(_managed_runtime_dir(root), _managed_runtime_dir(root) / "tools_dev")


def _od_data_dir(root: Path) -> Path:
    return _safe_child(_managed_runtime_dir(root), _managed_runtime_dir(root) / "open_design_data")


def _capture_dir(root: Path) -> Path:
    return _safe_child(_managed_runtime_dir(root), _managed_runtime_dir(root) / "captures")


def _runtime_env(
    env_map: dict[str, str],
    od_data_dir: Path,
    *,
    tool_paths: list[str | None] | None = None,
) -> dict[str, str]:
    allowed = (
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
        "NO_COLOR",
    )
    result: dict[str, str] = {}
    for key in allowed:
        value = env_map.get(key)
        if value:
            result[key] = value
    prepend_dirs: list[str] = []
    for path_text in tool_paths or []:
        if not path_text:
            continue
        parent = Path(path_text).expanduser().parent.as_posix()
        if parent and parent not in prepend_dirs:
            prepend_dirs.append(parent)
    if prepend_dirs:
        current_path = result.get("PATH", "")
        result["PATH"] = ":".join([*prepend_dirs, current_path]) if current_path else ":".join(prepend_dirs)
    result["OD_DATA_DIR"] = od_data_dir.as_posix()
    return result


def _command_base(plan: dict[str, Any]) -> list[str]:
    return [
        str(plan["pnpm_path"]),
        "tools-dev",
    ]


def _status_command(plan: dict[str, Any]) -> list[str]:
    return [
        *_command_base(plan),
        "status",
        "--namespace",
        str(plan["namespace"]),
        "--tools-dev-root",
        str(plan["tools_dev_root"]),
        "--json",
    ]


def _check_command(plan: dict[str, Any]) -> list[str]:
    return [
        *_command_base(plan),
        "check",
        "--namespace",
        str(plan["namespace"]),
        "--tools-dev-root",
        str(plan["tools_dev_root"]),
        "--json",
    ]


def _managed_start_command(plan: dict[str, Any]) -> list[str]:
    return [
        *_command_base(plan),
        "start",
        str(plan["app"]),
        "--namespace",
        str(plan["namespace"]),
        "--tools-dev-root",
        str(plan["tools_dev_root"]),
        "--json",
    ]


def _managed_stop_command(plan: dict[str, Any]) -> list[str]:
    return [
        *_command_base(plan),
        "stop",
        "--namespace",
        str(plan["namespace"]),
        "--tools-dev-root",
        str(plan["tools_dev_root"]),
        "--json",
    ]


def _normalize_tool_path(path_text: str | None) -> str | None:
    if not path_text:
        return None
    return str(Path(path_text).expanduser())


def build_managed_runtime_plan(
    root: str | Path,
    tool: str,
    *,
    env: dict[str, str] | None = None,
    which_fn: Callable[..., str | None] | None = None,
) -> dict[str, Any]:
    validated_tool = validate_design_tool(tool)
    root_path = Path(root).expanduser().resolve()
    env_map = dict(os.environ) if env is None else dict(env)
    probe = probe_design_runtime(root_path, validated_tool, env=env_map, which_fn=which_fn)

    source_info = probe.get("source_checkout_detection", {})
    source_path_text = str(source_info.get("path", "")).strip() if isinstance(source_info, dict) else ""
    source_checkout = Path(source_path_text).expanduser() if source_path_text else Path("/mnt/d/open_design_eval/open-design")
    required_files = {rel: _bool_file(source_checkout, rel) for rel in REQUIRED_SOURCE_FILES}

    detected = probe.get("detected_command_paths", {})
    node_path = _normalize_tool_path(detected.get("node") if isinstance(detected, dict) else None)
    pnpm_path = _normalize_tool_path(detected.get("pnpm") if isinstance(detected, dict) else None)

    managed_dir = _managed_runtime_dir(root_path)
    tools_root = _tools_dev_root(root_path)
    od_data = _od_data_dir(root_path)
    captures = _capture_dir(root_path)

    blockers: list[str] = []
    if not source_checkout.is_dir():
        blockers.append("SOURCE_CHECKOUT_MISSING")
    for rel, present in required_files.items():
        if not present:
            blockers.append(f"MISSING_{rel.rstrip('/')}")
    if not node_path:
        blockers.append("NODE_NOT_FOUND")
    if not pnpm_path:
        blockers.append("PNPM_NOT_FOUND")
    if _is_forbidden_executable(pnpm_path):
        blockers.append("PNPM_PATH_IS_SHELL_WRAPPER_OR_FORBIDDEN")

    plan: dict[str, Any] = {
        "title": "Open Design Managed Runtime Plan",
        "tool": validated_tool,
        "mode": MANAGED_RUNTIME_MODE,
        "experimental_headless_mode": EXPERIMENTAL_HEADLESS_MODE,
        "source_checkout_path": source_checkout.as_posix(),
        "node_path": node_path,
        "pnpm_path": pnpm_path,
        "namespace": DEFAULT_NAMESPACE,
        "app": DEFAULT_APP,
        "tools_dev_root": tools_root.as_posix(),
        "od_data_dir": od_data.as_posix(),
        "capture_directory": captures.as_posix(),
        "required_source_files": required_files,
        "runtime_probe_readiness": probe.get("readiness_classification"),
        "status_command": [],
        "check_command": [],
        "start_command": [],
        "stop_command": [],
        "execution": "no",
        "provider_call": "no",
        "design_generation": "no",
        "writes": "none",
        "shell_used": False,
        "uses_global_od": False,
        "confirm_allowed": len(blockers) == 0,
        "confirm_blockers": blockers,
        "next_step": "Use managed runtime status first; start requires explicit --confirm.",
    }
    plan["status_command"] = _status_command(plan) if pnpm_path else []
    plan["check_command"] = _check_command(plan) if pnpm_path else []
    plan["start_command"] = _managed_start_command(plan) if pnpm_path else []
    plan["stop_command"] = _managed_stop_command(plan) if pnpm_path else []
    return plan


def _run_tools_dev(
    cmd: list[str],
    *,
    cwd: str,
    env: dict[str, str],
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    run_fn: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> subprocess.CompletedProcess[str]:
    return run_fn(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
    )


def execute_managed_runtime_status(
    root: str | Path,
    tool: str,
    *,
    env: dict[str, str] | None = None,
    which_fn: Callable[..., str | None] | None = None,
    run_fn: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    root_path = Path(root).expanduser().resolve()
    env_map = dict(os.environ) if env is None else dict(env)
    plan = build_managed_runtime_plan(root_path, tool, env=env_map, which_fn=which_fn)
    if not plan["status_command"]:
        return {
            "title": "Open Design Managed Runtime Status",
            "plan": plan,
            "status": "REFUSED_STATUS_UNAVAILABLE",
            "return_code": None,
            "stdout": "",
            "stderr": "pnpm not found or command contract unavailable",
            "parsed_status": {},
            "execution_attempted": False,
            "writes_files": False,
        }

    runtime_env = _runtime_env(
        env_map,
        Path(plan["od_data_dir"]),
        tool_paths=[plan.get("node_path"), plan.get("pnpm_path")],
    )
    result = _run_tools_dev(
        list(plan["status_command"]),
        cwd=str(plan["source_checkout_path"]),
        env=runtime_env,
        run_fn=run_fn,
    )
    parsed = _extract_json_object(result.stdout)

    return {
        "title": "Open Design Managed Runtime Status",
        "plan": plan,
        "status": "STATUS_OK" if result.returncode == 0 else "STATUS_FAILED",
        "return_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "parsed_status": parsed,
        "execution_attempted": True,
        "writes_files": False,
    }


def execute_managed_runtime_start(
    root: str | Path,
    tool: str,
    *,
    confirm: bool,
    dry_run: bool = False,
    env: dict[str, str] | None = None,
    which_fn: Callable[..., str | None] | None = None,
    run_fn: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    root_path = Path(root).expanduser().resolve()
    env_map = dict(os.environ) if env is None else dict(env)
    plan = build_managed_runtime_plan(root_path, tool, env=env_map, which_fn=which_fn)
    if dry_run:
        return {
            "title": "Open Design Managed Runtime Start Dry-Run",
            "plan": plan,
            "status": "DRY_RUN",
            "execution_attempted": False,
            "writes_files": False,
        }
    if not confirm:
        raise PermissionError("product-design-runtime-start requires --confirm")
    if not plan["confirm_allowed"]:
        raise ValueError("REFUSED_PRECONDITION_FAILED: " + ", ".join(plan["confirm_blockers"]))

    managed_dir = _managed_runtime_dir(root_path)
    capture_dir = _capture_dir(root_path)
    tools_root = _tools_dev_root(root_path)
    od_data = _od_data_dir(root_path)
    for path in (managed_dir, capture_dir, tools_root, od_data):
        path.mkdir(parents=True, exist_ok=True)

    runtime_env = _runtime_env(
        env_map,
        od_data,
        tool_paths=[plan.get("node_path"), plan.get("pnpm_path")],
    )
    started_at = _utc_now_iso()
    start_result = _run_tools_dev(
        list(plan["start_command"]),
        cwd=str(plan["source_checkout_path"]),
        env=runtime_env,
        run_fn=run_fn,
    )
    status_result = _run_tools_dev(
        list(plan["status_command"]),
        cwd=str(plan["source_checkout_path"]),
        env=runtime_env,
        run_fn=run_fn,
    )

    stdout_path = _safe_child(capture_dir, capture_dir / "start_stdout.txt")
    stderr_path = _safe_child(capture_dir, capture_dir / "start_stderr.txt")
    status_path = _safe_child(capture_dir, capture_dir / "status_after_start.json")
    manifest_path = _safe_child(capture_dir, capture_dir / "managed_runtime_manifest.json")
    _text_write(stdout_path, start_result.stdout)
    _text_write(stderr_path, start_result.stderr)
    _text_write(status_path, status_result.stdout)

    manifest = {
        "started_at": started_at,
        "completed_at": _utc_now_iso(),
        "mode": MANAGED_RUNTIME_MODE,
        "action": "start",
        "tool": tool,
        "source_checkout_path": plan["source_checkout_path"],
        "commands": {
            "start": plan["start_command"],
            "status": plan["status_command"],
        },
        "return_code": start_result.returncode,
        "status_return_code": status_result.returncode,
        "shell_used": False,
        "uses_global_od": False,
        "provider_call": False,
        "design_generation_started": False,
        "writes_source_repo": False,
        "stdout_path": stdout_path.relative_to(root_path).as_posix(),
        "stderr_path": stderr_path.relative_to(root_path).as_posix(),
        "status_path": status_path.relative_to(root_path).as_posix(),
    }
    _json_write(manifest_path, manifest)
    return {
        "title": "Open Design Managed Runtime Start Result",
        "plan": plan,
        "status": "STARTED_OR_ALREADY_RUNNING" if start_result.returncode == 0 else "START_FAILED",
        "return_code": start_result.returncode,
        "status_return_code": status_result.returncode,
        "manifest_path": manifest_path.relative_to(root_path).as_posix(),
        "stdout_path": stdout_path.relative_to(root_path).as_posix(),
        "stderr_path": stderr_path.relative_to(root_path).as_posix(),
        "status_path": status_path.relative_to(root_path).as_posix(),
        "execution_attempted": True,
        "writes_files": True,
    }


def execute_managed_runtime_stop(
    root: str | Path,
    tool: str,
    *,
    confirm: bool,
    dry_run: bool = False,
    env: dict[str, str] | None = None,
    which_fn: Callable[..., str | None] | None = None,
    run_fn: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    root_path = Path(root).expanduser().resolve()
    env_map = dict(os.environ) if env is None else dict(env)
    plan = build_managed_runtime_plan(root_path, tool, env=env_map, which_fn=which_fn)
    if dry_run:
        return {
            "title": "Open Design Managed Runtime Stop Dry-Run",
            "plan": plan,
            "status": "DRY_RUN",
            "execution_attempted": False,
            "writes_files": False,
        }
    if not confirm:
        raise PermissionError("product-design-runtime-stop requires --confirm")
    if not plan["stop_command"]:
        raise ValueError("REFUSED_PRECONDITION_FAILED: PNPM_NOT_FOUND")

    capture_dir = _capture_dir(root_path)
    capture_dir.mkdir(parents=True, exist_ok=True)
    runtime_env = _runtime_env(
        env_map,
        Path(plan["od_data_dir"]),
        tool_paths=[plan.get("node_path"), plan.get("pnpm_path")],
    )
    stop_result = _run_tools_dev(
        list(plan["stop_command"]),
        cwd=str(plan["source_checkout_path"]),
        env=runtime_env,
        run_fn=run_fn,
    )
    status_result = _run_tools_dev(
        list(plan["status_command"]),
        cwd=str(plan["source_checkout_path"]),
        env=runtime_env,
        run_fn=run_fn,
    )

    stdout_path = _safe_child(capture_dir, capture_dir / "stop_stdout.txt")
    stderr_path = _safe_child(capture_dir, capture_dir / "stop_stderr.txt")
    status_path = _safe_child(capture_dir, capture_dir / "status_after_stop.json")
    manifest_path = _safe_child(capture_dir, capture_dir / "managed_runtime_stop_manifest.json")
    _text_write(stdout_path, stop_result.stdout)
    _text_write(stderr_path, stop_result.stderr)
    _text_write(status_path, status_result.stdout)
    _json_write(
        manifest_path,
        {
            "completed_at": _utc_now_iso(),
            "mode": MANAGED_RUNTIME_MODE,
            "action": "stop",
            "tool": tool,
            "source_checkout_path": plan["source_checkout_path"],
            "commands": {
                "stop": plan["stop_command"],
                "status": plan["status_command"],
            },
            "return_code": stop_result.returncode,
            "status_return_code": status_result.returncode,
            "shell_used": False,
            "uses_global_od": False,
            "provider_call": False,
            "design_generation_started": False,
            "writes_source_repo": False,
            "stdout_path": stdout_path.relative_to(root_path).as_posix(),
            "stderr_path": stderr_path.relative_to(root_path).as_posix(),
            "status_path": status_path.relative_to(root_path).as_posix(),
        },
    )
    return {
        "title": "Open Design Managed Runtime Stop Result",
        "plan": plan,
        "status": "STOPPED_OR_NOT_RUNNING" if stop_result.returncode == 0 else "STOP_FAILED",
        "return_code": stop_result.returncode,
        "status_return_code": status_result.returncode,
        "manifest_path": manifest_path.relative_to(root_path).as_posix(),
        "stdout_path": stdout_path.relative_to(root_path).as_posix(),
        "stderr_path": stderr_path.relative_to(root_path).as_posix(),
        "status_path": status_path.relative_to(root_path).as_posix(),
        "execution_attempted": True,
        "writes_files": True,
    }


def render_managed_runtime_plan(plan: dict[str, Any], *, action: str) -> str:
    lines = [
        "# Open Design Managed Runtime",
        "",
        f"- action: `{action}`",
        f"- mode: `{plan['mode']}`",
        "- design generation: `no`",
        "- provider call: `no`",
        f"- source checkout: `{plan['source_checkout_path']}`",
        f"- node: `{plan['node_path'] or 'NOT_FOUND'}`",
        f"- pnpm: `{plan['pnpm_path'] or 'NOT_FOUND'}`",
        f"- namespace: `{plan['namespace']}`",
        f"- app: `{plan['app']}`",
        f"- tools-dev root: `{plan['tools_dev_root']}`",
        f"- OD_DATA_DIR: `{plan['od_data_dir']}`",
        "",
        "## Commands",
        f"- status: `{json.dumps(plan['status_command'])}`",
        f"- check: `{json.dumps(plan['check_command'])}`",
        f"- start: `{json.dumps(plan['start_command'])}`",
        f"- stop: `{json.dumps(plan['stop_command'])}`",
        "",
        "## Safety",
        f"- shell_used: `{plan['shell_used']}`",
        f"- uses_global_od: `{plan['uses_global_od']}`",
        f"- confirm_allowed: `{plan['confirm_allowed']}`",
        "- confirm_blockers:",
    ]
    if plan["confirm_blockers"]:
        for blocker in plan["confirm_blockers"]:
            lines.append(f"  - `{blocker}`")
    else:
        lines.append("  - none")
    lines.extend(
        [
            "",
            "## Mode Guidance",
            "- Managed runtime mode is the primary supported local Open Design path.",
            "- Headless daemon render confirm remains experimental until a real run succeeds safely.",
            "",
        ]
    )
    return "\n".join(lines)


def render_managed_runtime_status(result: dict[str, Any]) -> str:
    plan = result["plan"]
    parsed = result.get("parsed_status") or {}
    lines = [
        "# Open Design Managed Runtime Status",
        "",
        f"- mode: `{plan['mode']}`",
        f"- status: `{result['status']}`",
        f"- return_code: `{result['return_code']}`",
        f"- source checkout: `{plan['source_checkout_path']}`",
        f"- namespace: `{plan['namespace']}`",
        f"- tools-dev root: `{plan['tools_dev_root']}`",
        f"- execution_attempted: `{result['execution_attempted']}`",
        f"- writes_files: `{result['writes_files']}`",
        "- design generation: `no`",
        "- provider call: `no`",
        "",
        "## Runtime Apps",
    ]
    apps = parsed.get("apps") if isinstance(parsed, dict) else None
    if isinstance(apps, dict):
        for name, status in apps.items():
            if isinstance(status, dict):
                lines.append(
                    f"- {name}: state=`{status.get('state', 'unknown')}` "
                    f"pid=`{status.get('pid')}` url=`{status.get('url')}`"
                )
            else:
                lines.append(f"- {name}: `{status}`")
    else:
        lines.append("- unavailable")
    if result.get("stderr"):
        lines.extend(["", "## Stderr", result["stderr"].strip()])
    lines.append("")
    return "\n".join(lines)


def render_managed_runtime_result(result: dict[str, Any]) -> str:
    plan = result["plan"]
    lines = [
        f"# {result['title']}",
        "",
        f"- mode: `{plan['mode']}`",
        f"- status: `{result['status']}`",
        f"- return_code: `{result.get('return_code')}`",
        f"- status_return_code: `{result.get('status_return_code')}`",
        f"- execution_attempted: `{result['execution_attempted']}`",
        f"- writes_files: `{result['writes_files']}`",
        "- design_generation_started: `false`",
        "- provider_call: `false`",
    ]
    for key in ("manifest_path", "stdout_path", "stderr_path", "status_path"):
        if result.get(key):
            lines.append(f"- {key}: `{result[key]}`")
    lines.append("")
    return "\n".join(lines)

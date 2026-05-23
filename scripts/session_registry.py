#!/usr/bin/env python3
"""Deterministic runtime session manifest registry helpers (Phase 1)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


RUNTIME_ROOT_DIRNAME = "runtime"
SESSIONS_DIRNAME = "sessions"
SESSION_MANIFEST_FILENAME = "session.yaml"

ALLOWED_RUNTIME_TYPES = {
    "powershell",
    "wsl",
    "browser_profile",
    "ollama_http",
}
ALLOWED_ADAPTERS = {
    "codex_cli",
    "gemini_cli",
    "local_ollama",
    "browser_chatgpt",
    "browser_gemini",
    "future_mcp",
}
ALLOWED_STATUSES = {
    "STOPPED",
    "PLANNED",
    "RUNNING",
    "BLOCKED",
    "FAILED",
    "STALE",
    "UNKNOWN",
}
ALLOWED_SAFETY_MODES = {
    "DRY_RUN_ONLY",
    "REVIEW_ONLY",
    "GUARDED_EXECUTION",
    "BROWSER_TRANSPORT",
    "LOCAL_MODEL_WORKER",
}
REQUIRED_SESSION_FIELDS = (
    "session_id",
    "runtime_type",
    "adapter",
    "cwd",
    "shell",
    "allowed_targets",
    "allowed_safety_modes",
    "allowed_commands",
    "env_policy",
    "status",
    "pid",
    "started_at",
    "last_seen_at",
    "transcript_path",
    "current_exchange_id",
    "stop_conditions",
)
SESSION_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,80}$")

DEFAULT_ALLOWED_COMMANDS: list[str] = []
DEFAULT_STOP_CONDITIONS = [
    "Stop on safety gate failure.",
    "Stop on unknown command requirement.",
]

RUNTIME_ADAPTER_DEFAULTS: dict[tuple[str, str], dict[str, Any]] = {
    ("powershell", "codex_cli"): {
        "shell": "powershell",
        "cwd": "D:\\_ai_brain",
        "allowed_safety_modes": ["REVIEW_ONLY", "DRY_RUN_ONLY"],
        "allowed_targets": ["codex_cli"],
    },
    ("powershell", "gemini_cli"): {
        "shell": "powershell",
        "cwd": "D:\\_ai_brain",
        "allowed_safety_modes": ["REVIEW_ONLY", "DRY_RUN_ONLY"],
        "allowed_targets": ["gemini_cli"],
    },
    ("ollama_http", "local_ollama"): {
        "shell": "none",
        "cwd": "D:\\_ai_brain",
        "allowed_safety_modes": ["LOCAL_MODEL_WORKER", "REVIEW_ONLY"],
        "allowed_targets": ["local_ollama"],
    },
    ("browser_profile", "browser_chatgpt"): {
        "shell": "none",
        "cwd": "D:\\_ai_brain",
        "allowed_safety_modes": ["BROWSER_TRANSPORT"],
        "allowed_targets": ["browser_chatgpt"],
    },
    ("browser_profile", "browser_gemini"): {
        "shell": "none",
        "cwd": "D:\\_ai_brain",
        "allowed_safety_modes": ["BROWSER_TRANSPORT"],
        "allowed_targets": ["browser_gemini"],
    },
    ("wsl", "codex_cli"): {
        "shell": "bash",
        "cwd": "/mnt/d/_ai_brain",
        "allowed_safety_modes": ["REVIEW_ONLY", "DRY_RUN_ONLY"],
        "allowed_targets": ["codex_cli"],
    },
    ("wsl", "gemini_cli"): {
        "shell": "bash",
        "cwd": "/mnt/d/_ai_brain",
        "allowed_safety_modes": ["REVIEW_ONLY", "DRY_RUN_ONLY"],
        "allowed_targets": ["gemini_cli"],
    },
}


def _safe_child(base: Path, child: Path) -> Path:
    base_resolved = base.resolve()
    child_resolved = child.resolve()
    if child_resolved == base_resolved:
        return child_resolved
    if base_resolved not in child_resolved.parents:
        raise ValueError(f"path escapes expected base: {child_resolved} not under {base_resolved}")
    return child_resolved


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _as_list_of_str(name: str, value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{name} must be a list of strings")
    return [str(item).strip() for item in value if str(item).strip()]


def _opt_text_or_none(name: str, value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be null or string")
    text = _normalize_text(value)
    return text or None


def validate_session_id(session_id: str) -> bool:
    if not isinstance(session_id, str):
        return False
    candidate = session_id.strip()
    if candidate != session_id:
        return False
    if not SESSION_ID_RE.fullmatch(candidate):
        return False
    if any(token in candidate for token in ("/", "\\", "..", " ")):
        return False
    return True


def runtime_root(root: str | Path) -> Path:
    return Path(root).expanduser().resolve() / RUNTIME_ROOT_DIRNAME


def sessions_root(root: str | Path) -> Path:
    return runtime_root(root) / SESSIONS_DIRNAME


def session_dir(root: str | Path, session_id: str) -> Path:
    if not validate_session_id(session_id):
        raise ValueError(f"invalid session_id: {session_id!r}")
    base = sessions_root(root)
    return _safe_child(base, base / session_id)


def validate_session_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise ValueError("session manifest must be a mapping")

    missing = [name for name in REQUIRED_SESSION_FIELDS if name not in manifest]
    if missing:
        raise ValueError("missing required session fields: " + ", ".join(missing))

    session_id = _normalize_text(manifest.get("session_id", ""))
    if not validate_session_id(session_id):
        raise ValueError(f"invalid session_id: {session_id!r}")

    runtime_type = _normalize_text(manifest.get("runtime_type", ""))
    if runtime_type not in ALLOWED_RUNTIME_TYPES:
        raise ValueError(f"unsupported runtime_type: {runtime_type}")

    adapter = _normalize_text(manifest.get("adapter", ""))
    if adapter not in ALLOWED_ADAPTERS:
        raise ValueError(f"unsupported adapter: {adapter}")

    status = _normalize_text(manifest.get("status", ""))
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"unsupported status: {status}")

    cwd = _normalize_text(manifest.get("cwd", ""))
    shell = _normalize_text(manifest.get("shell", ""))
    env_policy = _normalize_text(manifest.get("env_policy", ""))
    transcript_path = _normalize_text(manifest.get("transcript_path", ""))
    if not cwd:
        raise ValueError("cwd must be a non-empty string")
    if not shell:
        raise ValueError("shell must be a non-empty string")
    if not env_policy:
        raise ValueError("env_policy must be a non-empty string")
    if not transcript_path:
        raise ValueError("transcript_path must be a non-empty string")

    allowed_targets = _as_list_of_str("allowed_targets", manifest.get("allowed_targets"))
    for item in allowed_targets:
        if item not in ALLOWED_ADAPTERS:
            raise ValueError(f"unsupported allowed target: {item}")

    allowed_safety_modes = _as_list_of_str("allowed_safety_modes", manifest.get("allowed_safety_modes"))
    for item in allowed_safety_modes:
        if item not in ALLOWED_SAFETY_MODES:
            raise ValueError(f"unsupported allowed safety mode: {item}")

    allowed_commands = _as_list_of_str("allowed_commands", manifest.get("allowed_commands"))
    stop_conditions = _as_list_of_str("stop_conditions", manifest.get("stop_conditions"))
    if not stop_conditions:
        raise ValueError("stop_conditions must include at least one item")

    pid = manifest.get("pid")
    if pid is not None and not isinstance(pid, int):
        raise ValueError("pid must be null or integer")

    started_at = _opt_text_or_none("started_at", manifest.get("started_at"))
    last_seen_at = _opt_text_or_none("last_seen_at", manifest.get("last_seen_at"))
    current_exchange_id = _opt_text_or_none("current_exchange_id", manifest.get("current_exchange_id"))

    normalized = dict(manifest)
    normalized["session_id"] = session_id
    normalized["runtime_type"] = runtime_type
    normalized["adapter"] = adapter
    normalized["cwd"] = cwd
    normalized["shell"] = shell
    normalized["allowed_targets"] = allowed_targets
    normalized["allowed_safety_modes"] = allowed_safety_modes
    normalized["allowed_commands"] = allowed_commands
    normalized["env_policy"] = env_policy
    normalized["status"] = status
    normalized["pid"] = pid
    normalized["started_at"] = started_at
    normalized["last_seen_at"] = last_seen_at
    normalized["transcript_path"] = transcript_path
    normalized["current_exchange_id"] = current_exchange_id
    normalized["stop_conditions"] = stop_conditions
    return normalized


def create_default_session_manifest(
    *,
    session_id: str,
    runtime_type: str,
    adapter: str,
    cwd: str,
    shell: str,
    allowed_targets: list[str] | None = None,
    allowed_safety_modes: list[str] | None = None,
    allowed_commands: list[str] | None = None,
    env_policy: str = "workspace_safe",
    status: str = "PLANNED",
) -> dict[str, Any]:
    manifest = {
        "session_id": session_id,
        "runtime_type": runtime_type,
        "adapter": adapter,
        "cwd": cwd,
        "shell": shell,
        "allowed_targets": allowed_targets or [adapter],
        "allowed_safety_modes": allowed_safety_modes or ["REVIEW_ONLY"],
        "allowed_commands": allowed_commands or [],
        "env_policy": env_policy,
        "status": status,
        "pid": None,
        "started_at": None,
        "last_seen_at": None,
        "transcript_path": f"runtime/sessions/{session_id}/transcript.log",
        "current_exchange_id": None,
        "stop_conditions": [
            "Stop on safety gate failure.",
            "Stop on unknown command requirement.",
        ],
    }
    return validate_session_manifest(manifest)


def save_session_manifest(root: str | Path, manifest: dict[str, Any], confirm: bool = False) -> dict[str, Any]:
    safe = validate_session_manifest(manifest)
    if not confirm:
        return {"manifest": safe, "files_written": []}

    base = sessions_root(root)
    base.mkdir(parents=True, exist_ok=True)
    target_dir = session_dir(root, safe["session_id"])
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = _safe_child(target_dir, target_dir / SESSION_MANIFEST_FILENAME)
    manifest_path.write_text(json.dumps(safe, indent=2) + "\n", encoding="utf-8", newline="\n")
    return {"manifest": safe, "files_written": [str(manifest_path)]}


def session_plan_exists(root: str | Path, session_id: str) -> bool:
    target_dir = session_dir(root, session_id)
    manifest_path = _safe_child(target_dir, target_dir / SESSION_MANIFEST_FILENAME)
    return manifest_path.is_file()


def initialize_session_dir(root: str | Path, session_id: str) -> Path:
    base = sessions_root(root)
    base.mkdir(parents=True, exist_ok=True)
    target_dir = session_dir(root, session_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def write_session_manifest(root: str | Path, manifest: dict[str, Any]) -> str:
    safe = validate_session_manifest(manifest)
    target_dir = initialize_session_dir(root, safe["session_id"])
    manifest_path = _safe_child(target_dir, target_dir / SESSION_MANIFEST_FILENAME)
    manifest_path.write_text(json.dumps(safe, indent=2) + "\n", encoding="utf-8", newline="\n")
    return str(manifest_path)


def create_session_placeholders(root: str | Path, session_id: str) -> list[str]:
    target_dir = initialize_session_dir(root, session_id)
    writes: list[str] = []
    for name in ("stdout.log", "stderr.log", "transcript.log"):
        path = _safe_child(target_dir, target_dir / name)
        path.write_text("", encoding="utf-8", newline="\n")
        writes.append(str(path))
    heartbeat_path = _safe_child(target_dir, target_dir / "heartbeat.json")
    heartbeat = {
        "session_id": session_id,
        "status": "PLANNED",
        "pid": None,
        "last_seen_at": None,
    }
    heartbeat_path.write_text(json.dumps(heartbeat, indent=2) + "\n", encoding="utf-8", newline="\n")
    writes.append(str(heartbeat_path))
    return writes


def save_session_plan(root: str | Path, plan: dict[str, Any], confirm: bool = False) -> dict[str, Any]:
    safe = validate_session_plan(plan)
    if not confirm:
        return {"plan": safe, "files_written": []}
    if session_plan_exists(root, safe["session_id"]):
        raise ValueError(f"session already exists: {safe['session_id']}")
    writes = [write_session_manifest(root, safe)]
    writes.extend(create_session_placeholders(root, safe["session_id"]))
    return {"plan": safe, "files_written": writes}


def _load_manifest(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore[import-not-found]
        except Exception as exc:
            raise ValueError(f"session manifest is not JSON and PyYAML is unavailable: {exc}") from exc
        data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError(f"session manifest must be a mapping: {path}")
    return validate_session_manifest(data)


def load_session_manifest(root: str | Path, session_id: str) -> dict[str, Any]:
    target_dir = session_dir(root, session_id)
    manifest_path = _safe_child(target_dir, target_dir / SESSION_MANIFEST_FILENAME)
    if not manifest_path.is_file():
        raise FileNotFoundError(f"session manifest not found: {manifest_path}")
    return _load_manifest(manifest_path)


def list_sessions(root: str | Path) -> list[dict[str, Any]]:
    base = sessions_root(root)
    if not base.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for child in sorted((p for p in base.iterdir() if p.is_dir()), key=lambda p: p.name):
        manifest_path = _safe_child(child, child / SESSION_MANIFEST_FILENAME)
        if not manifest_path.is_file():
            rows.append(
                {
                    "session_id": child.name,
                    "status": "UNKNOWN",
                    "runtime_type": "UNKNOWN",
                    "adapter": "UNKNOWN",
                    "cwd": str(child),
                    "error": "missing session.yaml",
                }
            )
            continue
        try:
            manifest = _load_manifest(manifest_path)
            rows.append(
                {
                    "session_id": manifest["session_id"],
                    "status": manifest["status"],
                    "runtime_type": manifest["runtime_type"],
                    "adapter": manifest["adapter"],
                    "cwd": manifest["cwd"],
                    "error": "",
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "session_id": child.name,
                    "status": "UNKNOWN",
                    "runtime_type": "UNKNOWN",
                    "adapter": "UNKNOWN",
                    "cwd": str(child),
                    "error": str(exc),
                }
            )
    return rows


def get_session_status(root: str | Path, session_id: str) -> dict[str, Any]:
    manifest = load_session_manifest(root, session_id)
    target_dir = session_dir(root, session_id)
    manifest["session_path"] = str(target_dir)
    return manifest


def render_session_status(manifest: dict[str, Any]) -> str:
    lines = [
        f"# Session Status: {manifest.get('session_id', '')}",
        "",
        f"- status: `{manifest.get('status', '')}`",
        f"- runtime_type: `{manifest.get('runtime_type', '')}`",
        f"- adapter: `{manifest.get('adapter', '')}`",
        f"- shell: `{manifest.get('shell', '')}`",
        f"- cwd: `{manifest.get('cwd', '')}`",
        f"- pid: `{manifest.get('pid', None)}`",
        f"- started_at: `{manifest.get('started_at', '')}`",
        f"- last_seen_at: `{manifest.get('last_seen_at', '')}`",
        f"- current_exchange_id: `{manifest.get('current_exchange_id', '')}`",
        f"- transcript_path: `{manifest.get('transcript_path', '')}`",
        "",
        "## Allowed Targets",
    ]
    targets = manifest.get("allowed_targets", [])
    if isinstance(targets, list) and targets:
        lines.extend([f"- {item}" for item in targets])
    else:
        lines.append("- none")

    lines.extend(["", "## Allowed Safety Modes"])
    modes = manifest.get("allowed_safety_modes", [])
    if isinstance(modes, list) and modes:
        lines.extend([f"- {item}" for item in modes])
    else:
        lines.append("- none")

    lines.extend(["", "## Allowed Commands"])
    commands = manifest.get("allowed_commands", [])
    if isinstance(commands, list) and commands:
        lines.extend([f"- {item}" for item in commands])
    else:
        lines.append("- none")

    lines.extend(["", "## Stop Conditions"])
    stops = manifest.get("stop_conditions", [])
    if isinstance(stops, list) and stops:
        lines.extend([f"- {item}" for item in stops])
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def render_session_list(manifests: list[dict[str, Any]]) -> str:
    if not manifests:
        return "No runtime sessions found under runtime/sessions\n"
    lines = [
        "session_id | status | runtime_type | adapter | cwd | note",
        "---------- | ------ | ------------ | ------- | --- | ----",
    ]
    for row in manifests:
        lines.append(
            f"{row.get('session_id','')} | {row.get('status','')} | {row.get('runtime_type','')} | "
            f"{row.get('adapter','')} | {row.get('cwd','')} | {row.get('error','')}"
        )
    return "\n".join(lines) + "\n"


def planned_session_paths(root: str | Path, session_id: str) -> list[str]:
    target = session_dir(root, session_id)
    return [
        str(_safe_child(target, target / SESSION_MANIFEST_FILENAME)),
        str(_safe_child(target, target / "stdout.log")),
        str(_safe_child(target, target / "stderr.log")),
        str(_safe_child(target, target / "transcript.log")),
        str(_safe_child(target, target / "heartbeat.json")),
    ]


def build_session_plan(
    *,
    session_id: str,
    runtime_type: str,
    adapter: str,
    root: str | Path = ".",
    cwd: str | None = None,
    shell: str | None = None,
    safety_modes: list[str] | None = None,
    target: str | None = None,
) -> dict[str, Any]:
    key = (_normalize_text(runtime_type), _normalize_text(adapter))
    defaults = RUNTIME_ADAPTER_DEFAULTS.get(key)
    if defaults is None:
        raise ValueError(
            f"incompatible runtime/adapter pair for Phase 2: runtime_type={runtime_type}, adapter={adapter}"
        )
    if adapter == "future_mcp":
        raise ValueError("future_mcp adapter is not enabled in Phase 2 session planning")
    if target and _normalize_text(target) not in ALLOWED_ADAPTERS:
        raise ValueError(f"unsupported target: {target}")

    planned_cwd = _normalize_text(cwd or defaults["cwd"])
    planned_shell = _normalize_text(shell or defaults["shell"])
    planned_modes = safety_modes or list(defaults["allowed_safety_modes"])
    planned_targets = [target] if target else list(defaults["allowed_targets"])

    manifest = create_default_session_manifest(
        session_id=session_id,
        runtime_type=key[0],
        adapter=key[1],
        cwd=planned_cwd,
        shell=planned_shell,
        allowed_targets=planned_targets,
        allowed_safety_modes=planned_modes,
        allowed_commands=list(DEFAULT_ALLOWED_COMMANDS),
        env_policy="workspace_safe",
        status="PLANNED",
    )
    manifest["stop_conditions"] = list(DEFAULT_STOP_CONDITIONS)
    manifest["planned_files"] = planned_session_paths(root, session_id)
    manifest["no_execution"] = True
    manifest["compatibility_result"] = "PASS"
    manifest["blockers"] = []
    manifest["warnings"] = []
    return manifest


def validate_session_plan(plan: dict[str, Any]) -> dict[str, Any]:
    validated = validate_session_manifest(plan)
    if validated.get("status") != "PLANNED":
        raise ValueError("session plan must have status PLANNED")
    if "planned_files" not in plan or not isinstance(plan["planned_files"], list):
        raise ValueError("session plan missing planned_files")
    if not all(isinstance(item, str) and item.strip() for item in plan["planned_files"]):
        raise ValueError("planned_files must be a non-empty list of paths")
    if "no_execution" in plan and not isinstance(plan["no_execution"], bool):
        raise ValueError("no_execution must be boolean when provided")
    validated["planned_files"] = plan["planned_files"]
    validated["no_execution"] = bool(plan.get("no_execution", True))
    validated["compatibility_result"] = str(plan.get("compatibility_result", "PASS"))
    validated["blockers"] = _as_list_of_str("blockers", plan.get("blockers"))
    validated["warnings"] = _as_list_of_str("warnings", plan.get("warnings"))
    return validated


def render_session_plan_preview(plan: dict[str, Any]) -> str:
    safe = validate_session_plan(plan)
    lines = [
        "# Runtime Session Plan",
        "",
        "- DRY RUN / no process started",
        f"- session_id: `{safe['session_id']}`",
        f"- runtime_type: `{safe['runtime_type']}`",
        f"- adapter: `{safe['adapter']}`",
        f"- cwd: `{safe['cwd']}`",
        f"- shell: `{safe['shell']}`",
        f"- planned status: `{safe['status']}`",
        f"- env policy: `{safe['env_policy']}`",
        f"- transcript path: `{safe['transcript_path']}`",
        "",
        "## Allowed Targets",
    ]
    if safe["allowed_targets"]:
        lines.extend([f"- {item}" for item in safe["allowed_targets"]])
    else:
        lines.append("- none")
    lines.extend(["", "## Allowed Safety Modes"])
    if safe["allowed_safety_modes"]:
        lines.extend([f"- {item}" for item in safe["allowed_safety_modes"]])
    else:
        lines.append("- none")
    lines.extend(["", "## Allowed Commands"])
    if safe["allowed_commands"]:
        lines.extend([f"- {item}" for item in safe["allowed_commands"]])
    else:
        lines.append("- none")
    lines.extend(["", "## Stop Conditions"])
    if safe["stop_conditions"]:
        lines.extend([f"- {item}" for item in safe["stop_conditions"]])
    else:
        lines.append("- none")
    lines.extend(["", "## Planned Files"])
    lines.extend([f"- {item}" for item in safe["planned_files"]])
    lines.extend(
        [
            "",
            f"- compatibility result: `{safe.get('compatibility_result', 'PASS')}`",
            "",
            "## Blockers",
        ]
    )
    if safe["blockers"]:
        lines.extend([f"- {item}" for item in safe["blockers"]])
    else:
        lines.append("- none")
    lines.extend(["", "## Warnings"])
    if safe["warnings"]:
        lines.extend([f"- {item}" for item in safe["warnings"]])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Next Step",
            "- Future `ws session-plan --confirm` or `ws session-start --confirm` (not implemented in this slice).",
            "",
        ]
    )
    return "\n".join(lines)


def load_session_for_start(root: str | Path, session_id: str) -> dict[str, Any]:
    return load_session_manifest(root, session_id)


def validate_session_start_preconditions(manifest: dict[str, Any]) -> dict[str, Any]:
    safe = validate_session_manifest(manifest)
    blockers: list[str] = []
    warnings: list[str] = []

    key = (safe["runtime_type"], safe["adapter"])
    if key not in RUNTIME_ADAPTER_DEFAULTS:
        blockers.append(
            "incompatible runtime/adapter manifest for current managed runtime policy: "
            f"{safe['runtime_type']} + {safe['adapter']}"
        )

    status = safe["status"]
    if status == "RUNNING":
        blockers.append("session status is RUNNING")
    elif status not in {"PLANNED", "STOPPED"}:
        blockers.append(f"session status must be PLANNED or STOPPED for start preview, got {status}")

    if safe.get("pid") is not None:
        blockers.append("session pid is already set")

    if safe["adapter"] not in safe.get("allowed_targets", []):
        blockers.append("session allowed_targets does not include adapter")

    if safe["runtime_type"] == "powershell":
        invocation_style = "pwsh managed one-shot placeholder (no execution)"
    elif safe["runtime_type"] == "wsl":
        invocation_style = "wsl bash managed one-shot placeholder (no execution)"
    elif safe["runtime_type"] == "ollama_http":
        invocation_style = "local ollama HTTP runtime placeholder (no execution)"
    else:
        invocation_style = "runtime placeholder (no execution)"

    preview_status = "PASS"
    if blockers:
        preview_status = "FAIL"
    elif warnings:
        preview_status = "WARN"

    return {
        "manifest": safe,
        "preview_status": preview_status,
        "blockers": blockers,
        "warnings": warnings,
        "planned_invocation_style": invocation_style,
        "planned_paths": {
            "stdout": f"runtime/sessions/{safe['session_id']}/stdout.log",
            "stderr": f"runtime/sessions/{safe['session_id']}/stderr.log",
            "transcript": safe["transcript_path"],
        },
    }


def build_session_start_preview(root: str | Path, session_id: str) -> dict[str, Any]:
    manifest = load_session_for_start(root, session_id)
    return validate_session_start_preconditions(manifest)


def render_session_start_preview(preview: dict[str, Any]) -> str:
    manifest = preview["manifest"]
    lines = [
        "# Runtime Session Start Preview",
        "",
        "- DRY RUN / no process started",
        f"- session_id: `{manifest['session_id']}`",
        f"- runtime_type: `{manifest['runtime_type']}`",
        f"- adapter: `{manifest['adapter']}`",
        f"- cwd: `{manifest['cwd']}`",
        f"- shell: `{manifest['shell']}`",
        f"- planned invocation style: `{preview.get('planned_invocation_style', '')}`",
        f"- env policy: `{manifest['env_policy']}`",
        "",
        "## Planned Output Paths",
        f"- stdout: `{preview['planned_paths']['stdout']}`",
        f"- stderr: `{preview['planned_paths']['stderr']}`",
        f"- transcript: `{preview['planned_paths']['transcript']}`",
        "",
        "## Stop Conditions",
    ]
    stops = manifest.get("stop_conditions", [])
    if isinstance(stops, list) and stops:
        lines.extend([f"- {item}" for item in stops])
    else:
        lines.append("- none")

    lines.extend(["", f"- preview status: `{preview.get('preview_status', 'FAIL')}`", "", "## Blockers"])
    blockers = preview.get("blockers", [])
    if blockers:
        lines.extend([f"- {item}" for item in blockers])
    else:
        lines.append("- none")

    lines.extend(["", "## Warnings"])
    warnings = preview.get("warnings", [])
    if warnings:
        lines.extend([f"- {item}" for item in warnings])
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Next Step",
            "- Future `ws session-start --confirm` (not implemented in this slice).",
            "",
        ]
    )
    return "\n".join(lines)


def inspect_session_cleanup_candidates(root: str | Path) -> dict[str, Any]:
    rows = list_sessions(root)
    keep: list[dict[str, str]] = []
    cleanup_candidates: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    for row in rows:
        sid = str(row.get("session_id", ""))
        status = str(row.get("status", "UNKNOWN"))
        note = ""
        action = "keep"
        if status in {"FAILED", "BLOCKED", "STALE"}:
            action = "candidate"
            note = "eligible for future cleanup confirm flow"
        elif status == "RUNNING":
            pid = None
            try:
                manifest = load_session_manifest(root, sid)
                pid = manifest.get("pid")
            except Exception:
                pass
            if pid is None:
                warnings.append(
                    {
                        "session_id": sid,
                        "status": status,
                        "note": "RUNNING without pid; possible stale session metadata",
                    }
                )
            keep.append({"session_id": sid, "status": status, "note": "keep running session metadata"})
            continue
        elif status == "PLANNED":
            note = "keep planned session"
        elif status == "UNKNOWN":
            warnings.append({"session_id": sid, "status": status, "note": str(row.get("error", ""))})
            note = "unknown manifest shape; inspect before cleanup"
        else:
            note = "no cleanup action"

        item = {"session_id": sid, "status": status, "note": note}
        if action == "candidate":
            cleanup_candidates.append(item)
        else:
            keep.append(item)

    return {
        "inspected_count": len(rows),
        "cleanup_candidates": cleanup_candidates,
        "keep": keep,
        "warnings": warnings,
        "preview_status": "PASS" if rows else "WARN",
    }


def render_session_cleanup_preview(report: dict[str, Any]) -> str:
    lines = [
        "# Runtime Session Cleanup Preview",
        "",
        "- DRY RUN / no files deleted",
        f"- sessions inspected: `{report.get('inspected_count', 0)}`",
        f"- preview status: `{report.get('preview_status', 'PASS')}`",
        "",
        "## Cleanup Candidates",
    ]
    candidates = report.get("cleanup_candidates", [])
    if candidates:
        for item in candidates:
            lines.append(f"- {item['session_id']} ({item['status']}): {item['note']}")
    else:
        lines.append("- none")

    lines.extend(["", "## Keep / No Action"])
    keep = report.get("keep", [])
    if keep:
        for item in keep:
            lines.append(f"- {item['session_id']} ({item['status']}): {item['note']}")
    else:
        lines.append("- none")

    lines.extend(["", "## Warnings"])
    warnings = report.get("warnings", [])
    if warnings:
        for item in warnings:
            lines.append(f"- {item['session_id']} ({item['status']}): {item['note']}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Next Step",
            "- Future `ws session-cleanup --confirm` (not implemented in this slice).",
            "",
        ]
    )
    return "\n".join(lines)

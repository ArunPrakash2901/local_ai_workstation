#!/usr/bin/env python3
"""Read-only operator dashboard for the Local AI Workstation."""

from __future__ import annotations
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


WS_HOME = Path(os.environ.get("WS_HOME", Path(__file__).resolve().parents[1]))
WS_SCRIPT = WS_HOME / "scripts" / "ws"
SAFETY_MODE = "READ_ONLY"
COMMAND_SAFETY_MANIFEST_PATH = WS_HOME / "registry" / "ws_command_safety.yaml"
COMMAND_SAFETY_POLICY_MODE = os.environ.get(
    "WS_TUI_COMMAND_SAFETY_MODE",
    "READ_ONLY_WITH_LOCAL_REPORTS",
).strip().upper() or "READ_ONLY_WITH_LOCAL_REPORTS"
VISIBLE_TUI_EXPOSURES = {"visible", "visible_with_label"}
HIDDEN_SAFETY_CLASSES = {"UNKNOWN", "PROVIDER_CALL", "DESTRUCTIVE"}
VALID_SAFETY_CLASSES = {
    "PURE_READ",
    "LOCAL_REPORT_WRITE",
    "DRY_RUN_ONLY",
    "GUARDED_WRITE",
    "AGENT_RUN",
    "PROVIDER_CALL",
    "DESTRUCTIVE",
    "UNKNOWN",
}
VALID_TUI_EXPOSURES = {"visible", "visible_with_label", "disabled", "hidden", "admin_only"}
VALID_CONFIRMATIONS = {
    "none",
    "light",
    "explicit",
    "typed",
    "branch",
    "dirty_worktree",
    "provider",
    "destructive",
    "required",
}
COMMAND_SAFETY_REQUIRED_FIELDS = {
    "safety_class",
    "description",
    "writes_local_files",
    "writes_project_files",
    "invokes_agent_or_model",
    "external_provider_or_cloud",
    "read_only_strict",
    "read_only_with_local_reports",
    "safe_dry_run",
    "tui_exposure",
    "confirmation",
    "operator_label",
    "warning_label",
    "evidence",
    "confidence",
    "notes",
}
DISABLED_ACTIONS = (
    "Learning safe dry-run actions: enabled in plain mode",
    "Learning model-backed actions: disabled",
    "Learning assessment, import, and advancement: disabled",
    "Research cockpit: not implemented",
    "Provider and browser execution: disabled",
    "Mutation, apply, and trading: disabled",
)
UNSAFE_DEFAULT_READS = (
    ".env",
    "credentials",
    "raw datasets",
    "model files",
    "archives",
    ".git",
)
STATUS_COMMANDS = (
    ("readiness", ("ready",)),
    ("strongholds", ("stronghold-status",)),
    ("handoffs", ("handoff-status",)),
    ("features", ("feature-status",)),
    ("agent_hygiene", ("agent-hygiene",)),
)
PLAIN_CONTROLS = (
    "r refresh dashboard",
    "1 next safe action / run safe dry-run (screen dependent)",
    "2 learning or artifact browser (screen dependent)",
    "3 artifacts or quick artifact view (screen dependent)",
    "4 system or decision view (screen dependent)",
    "h/? help",
    "q quit",
)
UNSAFE_ARTIFACT_PARTS = {
    ".env",
    "credentials",
    "raw datasets",
    "raw_datasets",
    "model files",
    "models",
    "archives",
    ".git",
}
LEARNING_DRY_RUN_ALLOWLIST = {
    ("learning-run", "--session", "--dry-run"),
    ("learning-review-session", "--dry-run"),
    ("learning-action-pack", "--dry-run"),
}
LEARNING_DRY_RUN_WRITES = {
    "learning-run": (
        "sessions/*_session_plan.md",
        "practice_log.md",
        "loop_log.md",
        "state.json",
    ),
    "learning-review-session": (
        "sessions/*_review_session_plan.md",
        "practice_log.md",
        "loop_log.md",
        "state.json",
    ),
}
DEFAULT_STATUS_TIMEOUT_SECONDS = 12
SAFE_RENDER_MARGIN = 2
DEBUG_ENABLED = os.environ.get("WS_TUI_DEBUG", "").strip() == "1"
FORCE_NO_COLOR = False
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

ANSI_CODES = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[97m",
}


UNAVAILABLE_ERROR_SNIPPETS = (
    "failed to start",
    "no such file or directory",
    "not recognized as an internal or external command",
    "access is denied",
    "permission denied",
    "e_accessdenied",
    "wsl is not recognized",
)


def debug_log(phase: str) -> None:
    if DEBUG_ENABLED:
        print(f"[DEBUG] {phase}", file=sys.stderr, flush=True)


def status_timeout_seconds() -> int:
    raw = os.environ.get("WS_TUI_STATUS_TIMEOUT", str(DEFAULT_STATUS_TIMEOUT_SECONDS)).strip()
    try:
        seconds = int(raw)
    except ValueError:
        return DEFAULT_STATUS_TIMEOUT_SECONDS
    return max(1, min(seconds, 120))


def normalize_subprocess_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        decoded = value.decode("utf-8", errors="replace")
        # Windows/WSL edge case: UTF-16-like fragments surfaced through bytes.
        if "\x00" in decoded and decoded.count("\x00") > max(1, len(decoded) // 5):
            decoded = value.decode("utf-16-le", errors="replace")
        decoded = decoded.replace("\x00", "").replace("\ufeff", "")
        return decoded
    if isinstance(value, str):
        return value.replace("\x00", "").replace("\ufeff", "")
    return str(value).replace("\x00", "").replace("\ufeff", "")


def colors_enabled() -> bool:
    if FORCE_NO_COLOR:
        return False
    if os.environ.get("NO_COLOR", "").strip():
        return False
    requested = os.environ.get("WS_TUI_COLOR", "auto").strip().lower()
    if requested in {"0", "false", "off", "never"}:
        return False
    if requested in {"1", "true", "on", "always"}:
        return True
    return sys.stdout.isatty()


def visible_len(text: str) -> int:
    return len(ANSI_RE.sub("", text))


def pad_visible(text: str, width: int) -> str:
    return text + (" " * max(0, width - visible_len(text)))


def paint(text: str, tone: str, *, bold: bool = False, dim: bool = False) -> str:
    if not colors_enabled():
        return text
    tone_code = ANSI_CODES.get(tone)
    if not tone_code:
        return text
    style_parts = []
    if bold:
        style_parts.append(ANSI_CODES["bold"])
    if dim:
        style_parts.append(ANSI_CODES["dim"])
    style_parts.append(tone_code)
    return "".join(style_parts) + text + ANSI_CODES["reset"]


def colorize_semantic(text: str) -> str:
    if not colors_enabled():
        return text

    token_rules = [
        ("READ_ONLY", "cyan", True),
        ("SAFE_DRY_RUN", "cyan", True),
        ("DEGRADED", "yellow", True),
        ("PARTIAL", "yellow", True),
        ("CHECK_FAILED", "yellow", True),
        ("UNAVAILABLE", "yellow", True),
        ("UNKNOWN", "cyan", False),
        ("READY", "green", False),
        ("OK", "green", False),
        ("ONLINE", "green", False),
        ("COOL", "green", False),
        ("INFO", "cyan", False),
        ("WARN", "yellow", True),
        ("CHECK", "yellow", True),
        ("BLOCKED", "yellow", True),
        ("WARM", "yellow", False),
        ("HOT", "yellow", True),
        ("PURPLE", "magenta", True),
        ("FAIL", "red", True),
        ("ERROR", "red", True),
        ("OFFLINE", "red", True),
        ("DANGER", "red", True),
        ("TIMEOUT", "red", True),
    ]

    rendered = text
    for token, tone, bold in token_rules:
        rendered = re.sub(
            rf"\b{re.escape(token)}\b",
            lambda match, tone=tone, bold=bold: paint(match.group(0), tone, bold=bold),
            rendered,
        )
    rendered = rendered.replace(
        "NEXT SAFE ACTION",
        paint("NEXT SAFE ACTION", "cyan", bold=True),
    )
    return rendered


def command_log_status(result: "CommandResult") -> str:
    if result.returncode == 124:
        return "TIMEOUT"
    if result.returncode == 0:
        return "OK"
    return "FAIL"


def readiness_badge(result: "CommandResult") -> str:
    if result.returncode == 124:
        return "TIMEOUT"
    if result.returncode != 0:
        return "CHECK"
    if "[FAIL]" in result.stdout or "[FAIL]" in result.stderr:
        return "DEGRADED"
    return "READY"


def readiness_operator_state(result: "CommandResult") -> str:
    lines = readiness_detail_lines(result)
    has_fail = any("[FAIL]" in line for line in lines)
    has_ok = any("[OK]" in line for line in lines)

    if result.returncode == 0:
        return "DEGRADED" if has_fail else "READY"
    if result.returncode == 124:
        return "CHECK_FAILED"
    if has_fail:
        return "DEGRADED"
    if command_unavailable(result):
        return "UNAVAILABLE"
    if lines:
        return "PARTIAL" if has_ok else "CHECK_FAILED"
    return "UNKNOWN"


def append_command_log_entry(command_log: list[str], status: str, command_text: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    command_log.append(f"[{timestamp}] {status} {command_text}")


def nonempty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def status_prefix(status: str) -> str:
    label = status.upper()
    if icon_mode() == "unicode":
        icon_by_status = {
            "OK": "✓",
            "READY": "✓",
            "INFO": "i",
            "WARN": "⚠",
            "DEGRADED": "⚠",
            "PARTIAL": "⚠",
            "CHECK": "⚠",
            "CHECK_FAILED": "⚠",
            "UNAVAILABLE": "?",
            "UNKNOWN": "?",
            "TIMEOUT": "⚠",
            "FAIL": "✕",
        }
        icon = icon_by_status.get(label)
        if icon:
            return f"[{label}] {icon}"
    return f"[{label}]"


def binary_status_marker(ok: bool | None) -> str:
    if ok is None:
        return "?"
    if icon_mode() == "unicode":
        return "✓" if ok else "✕"
    return "OK" if ok else "FAIL"


def readiness_detail_lines(result: "CommandResult") -> list[str]:
    return nonempty_lines(result.display_text)


def readiness_summary_line(result: "CommandResult") -> str:
    state = readiness_operator_state(result)
    lines = readiness_detail_lines(result)

    ollama_ok: bool | None = None
    wsl_ok: bool | None = None
    gpu_name = "GPU"
    gpu_used: str | None = None
    gpu_total: str | None = None
    gpu_temp: str | None = None
    project_count: str | None = None

    for line in lines:
        if "Ollama" in line and ("running" in line or "reachable" in line):
            if "[OK]" in line:
                ollama_ok = True
            elif "[FAIL]" in line:
                ollama_ok = False
        if "WSL" in line and "Ollama" in line:
            if "[OK]" in line:
                wsl_ok = True
            elif "[FAIL]" in line:
                wsl_ok = False

        gpu_match = re.search(
            r"(RTX[^:]*):\s*(\d+)\s*MiB,\s*(\d+)\s*MiB,\s*(\d+)",
            line,
        )
        if gpu_match:
            gpu_name = gpu_match.group(1).strip()
            gpu_used = gpu_match.group(2)
            gpu_total = gpu_match.group(3)
            gpu_temp = gpu_match.group(4)

        registry_match = re.search(r"Registry:\s*(\d+)\s+projects\s+detected", line)
        if registry_match:
            project_count = registry_match.group(1)

    top_prefix = status_prefix(state)
    vram_segment = (
        f"{gpu_name}: {gpu_used}/{gpu_total} MiB"
        if gpu_used is not None and gpu_total is not None
        else "VRAM unavailable"
    )
    temp_segment = f"{gpu_temp}{degrees_unit()}" if gpu_temp is not None else "Temp unavailable"
    projects_segment = f"{project_count} projects" if project_count is not None else "projects UNAVAILABLE"

    return (
        f"{top_prefix} "
        f"Ollama {binary_status_marker(ollama_ok)} | "
        f"WSL {binary_status_marker(wsl_ok)} | "
        f"{vram_segment} | "
        f"{temp_segment} | "
        f"{projects_segment}"
    )


def parse_handoff_rows(result: "CommandResult") -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for line in nonempty_lines(result.display_text):
        if "|" not in line:
            continue
        parts = [item.strip() for item in line.split("|")]
        if len(parts) < 4:
            continue
        if parts[0].lower().startswith("recent handoffs"):
            continue
        if set(parts[0]) == {"-"}:
            continue
        rows.append((parts[0], parts[1], parts[2], parts[3]))
    return rows


def summarize_handoffs(result: "CommandResult", limit: int = 3) -> list[str]:
    rows = parse_handoff_rows(result)
    if not rows:
        return [status_prefix("INFO") + " No recent handoffs."]
    return [f"{ts} | {owner} | {purpose} | {status}" for ts, owner, purpose, status in rows[:limit]]


def summarize_feature_rows(result: "CommandResult", limit: int = 3) -> list[str]:
    rows: list[str] = []
    for line in nonempty_lines(result.display_text):
        if "|" not in line:
            continue
        if line.lower().startswith("recent feature strongholds"):
            continue
        if set(line.strip()) == {"-"}:
            continue
        parts = [item.strip() for item in line.split("|")]
        if len(parts) < 4:
            continue
        rows.append(" | ".join(parts[:4]))
    if not rows:
        return [status_prefix("INFO") + " No recent feature strongholds."]
    return rows[:limit]


def parse_agent_hygiene(result: "CommandResult") -> dict[str, object]:
    summary: dict[str, object] = {
        "branch": "unknown",
        "unresolved": None,
        "reviewed": None,
        "ignored_ok": None,
    }
    ignores = {
        "auto_runs": None,
        "validation": None,
        "hygiene": None,
    }
    for line in nonempty_lines(result.display_text):
        if line.startswith("Current branch:"):
            summary["branch"] = line.split(":", 1)[1].strip() or "unknown"
            continue
        unresolved_match = re.search(r"Unresolved CODEX_RUNNING folders:\s*(\d+)", line)
        if unresolved_match:
            summary["unresolved"] = int(unresolved_match.group(1))
            continue
        reviewed_match = re.search(r"Reviewed CODEX_RUNNING folders:\s*(\d+)", line)
        if reviewed_match:
            summary["reviewed"] = int(reviewed_match.group(1))
            continue
        if line.startswith("auto_runs ignored by Git:"):
            ignores["auto_runs"] = line.endswith("yes")
            continue
        if line.startswith("Validation reports ignored by Git:"):
            ignores["validation"] = line.endswith("yes")
            continue
        if line.startswith("Hygiene reports ignored by Git:"):
            ignores["hygiene"] = line.endswith("yes")
            continue

    ignore_values = [value for value in ignores.values() if value is not None]
    if len(ignore_values) == 3:
        summary["ignored_ok"] = all(ignore_values)
    else:
        summary["ignored_ok"] = None
    return summary


def command_unavailable(result: "CommandResult") -> bool:
    combined = "\n".join([result.stdout, result.stderr]).lower()
    if result.returncode in {126, 127} and not result.stdout.strip():
        return True
    return any(snippet in combined for snippet in UNAVAILABLE_ERROR_SNIPPETS)


def agent_hygiene_status(summary: dict[str, object], result: "CommandResult") -> str:
    unresolved = summary.get("unresolved")
    ignored_ok = summary.get("ignored_ok")
    if result.returncode == 124:
        return "CHECK_FAILED"
    if unresolved == 0 and ignored_ok is True:
        return "OK"
    if result.returncode == 0:
        return "WARN"
    if command_unavailable(result):
        return "UNAVAILABLE"

    has_structured_data = (
        summary.get("branch") not in {None, "", "unknown"}
        or unresolved is not None
        or summary.get("reviewed") is not None
        or ignored_ok is not None
    )
    if has_structured_data:
        if isinstance(unresolved, int) and unresolved > 0:
            return "WARN"
        if ignored_ok is False:
            return "FAIL"
        return "CHECK_FAILED"

    combined = "\n".join([result.stdout, result.stderr]).upper()
    if "[FAIL]" in combined or " FAIL" in combined:
        return "FAIL"
    if "[WARN]" in combined or " WARN" in combined:
        return "WARN"
    if not result.stdout.strip() and not result.stderr.strip():
        return "UNKNOWN"
    return "CHECK_FAILED"


def agent_hygiene_summary_line(result: "CommandResult") -> str:
    summary = parse_agent_hygiene(result)
    status = agent_hygiene_status(summary, result)
    unresolved = summary.get("unresolved")
    reviewed = summary.get("reviewed")
    ignored_ok = summary.get("ignored_ok")
    ignored_text = "ignored outputs OK" if ignored_ok is True else "ignored outputs CHECK"
    branch_display = operator_branch_value(summary.get("branch", "unknown"))
    return (
        f"{status_prefix(status)} "
        f"branch {branch_display} | "
        f"unresolved {unresolved if unresolved is not None else 'UNKNOWN'} | "
        f"reviewed {reviewed if reviewed is not None else 'UNKNOWN'} | "
        f"{ignored_text}"
    )


@dataclass(frozen=True)
class LayoutSpec:
    mode: str
    width: int
    content_width: int
    sidebar_width: int


@dataclass(frozen=True)
class IconSet:
    ok: str
    warning: str
    blocked: str
    run: str
    dry_run: str
    linked: str
    artifact: str
    disabled: str


@dataclass(frozen=True)
class CommandSafety:
    command: str
    safety_class: str
    description: str
    writes_local_files: bool
    writes_project_files: bool
    invokes_agent_or_model: bool
    external_provider_or_cloud: bool
    read_only_strict: bool
    read_only_with_local_reports: bool
    safe_dry_run: bool
    tui_exposure: str
    confirmation: str
    operator_label: str
    warning_label: str
    evidence: tuple[str, ...]
    confidence: str
    notes: str
    tui_dispatch_policy: str = "hidden_local_report"
    tui_dispatch_allowed: bool = False
    report_write_scope: str = "unknown"


@dataclass(frozen=True)
class CommandSafetyManifest:
    loaded: bool
    warning: str | None
    commands: dict[str, CommandSafety]


_COMMAND_SAFETY_MANIFEST: CommandSafetyManifest | None = None


def parse_manifest_text(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as json_exc:
        try:
            import yaml  # type: ignore
        except ImportError as import_exc:
            raise ValueError(
                f"manifest is not JSON-compatible YAML and PyYAML is unavailable: {json_exc}"
            ) from import_exc
        try:
            parsed = yaml.safe_load(raw)
        except Exception as yaml_exc:  # pragma: no cover - optional parser path
            raise ValueError(f"manifest YAML parse failed: {yaml_exc}") from yaml_exc
    if not isinstance(parsed, dict):
        raise ValueError("manifest root must be a mapping")
    return parsed


def command_safety_from_entry(command: str, entry: dict[str, Any]) -> CommandSafety:
    missing = sorted(COMMAND_SAFETY_REQUIRED_FIELDS - set(entry))
    if missing:
        raise ValueError(f"{command} missing required fields: {', '.join(missing)}")

    safety_class = str(entry["safety_class"])
    tui_exposure = str(entry["tui_exposure"])
    confirmation = str(entry["confirmation"])
    if safety_class not in VALID_SAFETY_CLASSES:
        raise ValueError(f"{command} has invalid safety_class: {safety_class}")
    if tui_exposure not in VALID_TUI_EXPOSURES:
        raise ValueError(f"{command} has invalid tui_exposure: {tui_exposure}")
    if confirmation not in VALID_CONFIRMATIONS:
        raise ValueError(f"{command} has invalid confirmation: {confirmation}")

    boolean_fields = (
        "writes_local_files",
        "writes_project_files",
        "invokes_agent_or_model",
        "external_provider_or_cloud",
        "read_only_strict",
        "read_only_with_local_reports",
        "safe_dry_run",
    )
    for field_name in boolean_fields:
        if not isinstance(entry[field_name], bool):
            raise ValueError(f"{command} field {field_name} must be boolean")

    evidence = entry["evidence"]
    if not isinstance(evidence, list) or not all(isinstance(item, str) for item in evidence):
        raise ValueError(f"{command} evidence must be a list of strings")

    return CommandSafety(
        command=command,
        safety_class=safety_class,
        description=str(entry["description"]),
        writes_local_files=entry["writes_local_files"],
        writes_project_files=entry["writes_project_files"],
        invokes_agent_or_model=entry["invokes_agent_or_model"],
        external_provider_or_cloud=entry["external_provider_or_cloud"],
        read_only_strict=entry["read_only_strict"],
        read_only_with_local_reports=entry["read_only_with_local_reports"],
        safe_dry_run=entry["safe_dry_run"],
        tui_exposure=tui_exposure,
        confirmation=confirmation,
        operator_label=str(entry["operator_label"]),
        warning_label=str(entry["warning_label"]),
        evidence=tuple(evidence),
        confidence=str(entry["confidence"]),
        notes=str(entry["notes"]),
        tui_dispatch_policy=str(entry.get("tui_dispatch_policy", "hidden_local_report")),
        tui_dispatch_allowed=bool(entry.get("tui_dispatch_allowed", False)),
        report_write_scope=str(entry.get("report_write_scope", "unknown")),
    )


def load_command_safety_manifest() -> CommandSafetyManifest:
    global _COMMAND_SAFETY_MANIFEST
    if _COMMAND_SAFETY_MANIFEST is not None:
        return _COMMAND_SAFETY_MANIFEST

    path = COMMAND_SAFETY_MANIFEST_PATH
    if not path.is_file():
        _COMMAND_SAFETY_MANIFEST = CommandSafetyManifest(
            loaded=False,
            warning=f"Command safety manifest missing: {path}",
            commands={},
        )
        return _COMMAND_SAFETY_MANIFEST

    try:
        data = parse_manifest_text(path.read_text(encoding="utf-8"))
        commands_data = data.get("commands")
        if not isinstance(commands_data, dict):
            raise ValueError("manifest commands must be a mapping")
        commands = {
            str(command): command_safety_from_entry(str(command), entry)
            for command, entry in commands_data.items()
            if isinstance(entry, dict)
        }
        if len(commands) != len(commands_data):
            raise ValueError("all command entries must be mappings")
        _COMMAND_SAFETY_MANIFEST = CommandSafetyManifest(
            loaded=True,
            warning=None,
            commands=commands,
        )
    except Exception as exc:
        _COMMAND_SAFETY_MANIFEST = CommandSafetyManifest(
            loaded=False,
            warning=f"Command safety manifest invalid: {exc}",
            commands={},
        )
    return _COMMAND_SAFETY_MANIFEST


def command_name_from_args(args: tuple[str, ...]) -> str:
    if not args:
        return "ws"

    command = args[0]
    if command == "learning-run":
        if "--dry-run" in args and "--session" in args:
            return "ws learning-run --session --dry-run"
        if "--model" in args:
            return "ws learning-run --model"
    if command == "learning-review-session" and "--dry-run" in args:
        return "ws learning-review-session --dry-run"
    if command == "research-run":
        if "--dry-run" in args and "--review-paper" in args:
            return "ws research-run --review-paper --dry-run"
        if "--model" in args:
            return "ws research-run --model"
    if command == "feature-run":
        if "--dry-run" in args:
            return "ws feature-run --dry-run"
        if "--apply" in args:
            return "ws feature-run --apply"
    if command == "worktree-create" and "--apply" in args:
        return "ws worktree-create --apply"
    if command == "worktree-create" and "--dry-run" in args:
        return "ws worktree-create --dry-run"
    if command == "worktree-sync" and "--apply" in args:
        return "ws worktree-sync --apply"
    if command == "worktree-sync" and "--dry-run" in args:
        return "ws worktree-sync --dry-run"
    if command == "agent-run" and "--dry-run" in args:
        return "ws agent-run --dry-run"
    if command == "agent-run-worktree" and "--apply" in args:
        return "ws agent-run-worktree --apply"
    if command == "agent-run-worktree" and "--dry-run" in args:
        return "ws agent-run-worktree --dry-run"
    if command == "build":
        if "--dry-run" in args:
            return "ws build --dry-run"
        if "--plan-only" in args:
            return "ws build --plan-only"
        if "--apply" in args and "--escalate" in args and "codex" in args:
            return "ws build --apply --escalate codex"
        if "--apply" in args:
            return "ws build --apply"
    if command == "cleanup-apply" and "--apply" in args:
        return "ws cleanup-apply --apply"
    if command == "escalate" and len(args) > 1 and args[1] == "codex":
        return "ws escalate codex"

    return f"ws {command}"


def classify_unknown_command(command_name: str) -> CommandSafety:
    return CommandSafety(
        command=command_name,
        safety_class="UNKNOWN",
        description="Command not found in safety manifest.",
        writes_local_files=False,
        writes_project_files=False,
        invokes_agent_or_model=False,
        external_provider_or_cloud=False,
        read_only_strict=False,
        read_only_with_local_reports=False,
        safe_dry_run=False,
        tui_exposure="hidden",
        confirmation="required",
        operator_label=command_name,
        warning_label="Unknown command; hidden",
        evidence=(),
        confidence="low",
        notes="Generated by TUI fallback classification.",
    )


def fallback_known_command_safety(command_name: str) -> CommandSafety:
    if command_name in {"ws stronghold-status", "ws handoff-status", "ws feature-status"}:
        return CommandSafety(
            command=command_name,
            safety_class="PURE_READ",
            description="Fallback classification for existing hardcoded TUI status command.",
            writes_local_files=False,
            writes_project_files=False,
            invokes_agent_or_model=False,
            external_provider_or_cloud=False,
            read_only_strict=True,
            read_only_with_local_reports=True,
            safe_dry_run=True,
            tui_exposure="visible",
            confirmation="none",
            operator_label=command_name,
            warning_label="",
            evidence=("tui/app.py STATUS_COMMANDS",),
            confidence="low",
            notes="Used only when command safety manifest is unavailable.",
        )
    if command_name in {"ws ready", "ws agent-hygiene"}:
        return CommandSafety(
            command=command_name,
            safety_class="LOCAL_REPORT_WRITE",
            description="Fallback classification for existing hardcoded TUI status command.",
            writes_local_files=True,
            writes_project_files=False,
            invokes_agent_or_model=False,
            external_provider_or_cloud=False,
            read_only_strict=False,
            read_only_with_local_reports=True,
            safe_dry_run=True,
            tui_exposure="visible_with_label",
            confirmation="light",
            operator_label=command_name,
            warning_label="Writes local status/report artifact",
            evidence=("tui/app.py STATUS_COMMANDS",),
            confidence="low",
            notes="Used only when command safety manifest is unavailable.",
        )
    if command_name in {"ws learning-run --session --dry-run", "ws learning-review-session --dry-run"}:
        return CommandSafety(
            command=command_name,
            safety_class="DRY_RUN_ONLY",
            description="Fallback classification for existing hardcoded TUI learning dry-run action.",
            writes_local_files=True,
            writes_project_files=False,
            invokes_agent_or_model=False,
            external_provider_or_cloud=False,
            read_only_strict=False,
            read_only_with_local_reports=True,
            safe_dry_run=True,
            tui_exposure="visible_with_label",
            confirmation="light",
            operator_label=command_name,
            warning_label="Dry-run writes local plan/report artifacts",
            evidence=("tui/app.py LEARNING_DRY_RUN_ALLOWLIST",),
            confidence="low",
            notes="Used only when command safety manifest is unavailable.",
        )
    return classify_unknown_command(command_name)


def get_command_safety(command_name: str) -> CommandSafety:
    manifest = load_command_safety_manifest()
    if not manifest.loaded:
        return fallback_known_command_safety(command_name)
    return manifest.commands.get(command_name, classify_unknown_command(command_name))


def mode_allows_command(safety: CommandSafety, mode: str) -> bool:
    normalized_mode = mode.upper()
    if normalized_mode == "READ_ONLY_STRICT":
        return safety.read_only_strict
    if normalized_mode in {"READ_ONLY", "READ_ONLY_WITH_LOCAL_REPORTS"}:
        return safety.read_only_with_local_reports
    if normalized_mode == "SAFE_DRY_RUN":
        return safety.safe_dry_run
    return False


def is_command_visible(command_name: str, mode: str) -> bool:
    manifest = load_command_safety_manifest()
    if not manifest.loaded:
        return False
    safety = get_command_safety(command_name)
    if safety.safety_class in HIDDEN_SAFETY_CLASSES:
        return False
    if safety.tui_exposure not in VISIBLE_TUI_EXPOSURES:
        return False
    return mode_allows_command(safety, mode)


def get_command_warning_label(command_name: str) -> str:
    return get_command_safety(command_name).warning_label


def get_command_confirmation_level(command_name: str) -> str:
    return get_command_safety(command_name).confirmation


def manifest_allows_existing_status_command(args: tuple[str, ...]) -> bool:
    manifest = load_command_safety_manifest()
    if not manifest.loaded:
        return True
    return is_command_visible(command_name_from_args(args), COMMAND_SAFETY_POLICY_MODE)


def manifest_allows_learning_action(args: tuple[str, ...]) -> bool:
    if not is_allowlisted_learning_dry_run(args):
        return False
    manifest = load_command_safety_manifest()
    if not manifest.loaded:
        return True
    return is_command_visible(command_name_from_args(args), "SAFE_DRY_RUN")


def manifest_status_line() -> str:
    manifest = load_command_safety_manifest()
    if not manifest.loaded:
        return f"WARN {manifest.warning}"
    return f"READY {len(manifest.commands)} commands loaded"


def command_safety_summary_lines() -> list[str]:
    manifest = load_command_safety_manifest()
    lines = [
        f"Manifest   {manifest_status_line()}",
        f"Policy     {COMMAND_SAFETY_POLICY_MODE}",
    ]
    if not manifest.loaded:
        lines.append("Fallback   hardcoded TUI allowlists preserved; unknown dynamic actions hidden")
        return lines

    lines.append("Status command exposure:")
    for _, args in STATUS_COMMANDS:
        command_name = command_name_from_args(args)
        safety = get_command_safety(command_name)
        state = "VISIBLE" if is_command_visible(command_name, COMMAND_SAFETY_POLICY_MODE) else "DISABLED"
        warning = f" | {safety.warning_label}" if safety.warning_label else ""
        lines.append(f"- {command_name}: {state} | {safety.safety_class}{warning}")
    return lines


@dataclass(frozen=True)
class LearningAction:
    label: str
    command_text: str
    args: tuple[str, ...]
    risk_class: str
    expected_writes: tuple[str, ...] = ()
    executable: bool = False
    safety_class: str = "UNKNOWN"
    tui_exposure: str = "hidden"
    confirmation: str = "required"
    warning_label: str = ""


@dataclass(frozen=True)
class LearningArtifact:
    key: str
    label: str
    path: str | None
    timestamp: datetime | None
    exists: bool
    relative_path: str


@dataclass
class LearningStronghold:
    id: str
    path: Path
    title: str = "unknown"
    current_state: str = "unknown"
    session_status: str = "unknown"
    next_task: str | None = None
    last_completed_task: str | None = None
    state: dict = field(default_factory=dict)
    
    # Artifact paths (Windows strings for display)
    latest_session_plan: str | None = None
    latest_tutor_session: str | None = None
    latest_answer_template: str | None = None
    latest_imported_answers: str | None = None
    latest_assessment: str | None = None
    latest_normal_decision: str | None = None
    latest_review_plan: str | None = None
    latest_review_tutor_session: str | None = None
    latest_review_answer_template: str | None = None
    latest_review_answers: str | None = None
    latest_review_assessment: str | None = None
    latest_review_decision: str | None = None
    
    # Action Pack v1
    action_pack_v1: list[dict] = field(default_factory=list)
    ledger_v1: list[dict] = field(default_factory=list)
    confirmed_artifacts_v1: list[str] = field(default_factory=list)

    # State Sync v1
    latest_sync: dict | None = None
    backup_count: int = 0
    latest_backup_name: str | None = None
    pointer_plan: dict | None = None
    advancement_plan: dict | None = None
    latest_review_packet: dict | None = None

    # Provenance
    linked_tutor_session: str | None = None
    import_success: bool = False

    @property
    def next_action_label(self) -> str:
        return self.compute_next_action().label

    @property
    def next_action_command(self) -> str:
        return self.compute_next_action().command_text

    @property
    def decision_warning(self) -> str | None:
        review_decision = self.artifact_timestamp(
            "last_learning_review_decision_at",
            self.latest_review_decision,
        )
        review_plan = self.artifact_timestamp(
            "last_learning_review_plan_at",
            self.latest_review_plan,
        )
        review_tutor = self.artifact_timestamp(
            "last_review_tutor_session_at",
            self.latest_review_tutor_session,
        )
        if not review_decision:
            return None

        latest_normal_cycle = self.latest_timestamp(
            self.artifact_timestamp("last_tutor_session_at", self.latest_tutor_session),
            self.artifact_timestamp(
                "last_learning_answers_imported_at",
                self.latest_imported_answers,
            ),
            self.artifact_timestamp(
                "last_learning_assessment_at",
                self.latest_assessment,
            ),
            self.artifact_timestamp(
                "last_learning_decision_at",
                self.latest_normal_decision,
            ),
        )
        if latest_normal_cycle and review_decision <= latest_normal_cycle:
            return "[WARN] Older review decision does not match current session."
        return None

    def has_duplicate_confirmation(self, action_id: str) -> bool:
        """Check if an action has already been confirmed as applied in the ledger."""
        for entry in self.ledger_v1:
            if (entry.get("original_action_id") == action_id and 
                entry.get("confirmation_status") == "CONFIRMED_APPLIED"):
                return True
        return False

    def to_win(self, p: str | Path | None) -> str | None:
        if not p:
            return None
        # Simple heuristic for TUI display; real commands use wslpath
        return str(p).replace("/mnt/d/", "D:\\").replace("/", "\\")

    def artifact_timestamp(self, state_key: str, artifact_path: str | None) -> datetime | None:
        explicit = self.parse_timestamp(self.state.get(state_key))
        if explicit:
            return explicit
        return self.timestamp_from_path(artifact_path)

    @staticmethod
    def parse_timestamp(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y%m%d_%H%M%S")
        except ValueError:
            return None

    @classmethod
    def timestamp_from_path(cls, artifact_path: str | None) -> datetime | None:
        if not artifact_path:
            return None
        match = re.search(r"(\d{8}_\d{6})", Path(artifact_path).name)
        return cls.parse_timestamp(match.group(1)) if match else None

    @staticmethod
    def latest_timestamp(*values: datetime | None) -> datetime | None:
        candidates = [value for value in values if value is not None]
        return max(candidates) if candidates else None

    @staticmethod
    def is_newer(candidate: datetime | None, baseline: datetime | None) -> bool:
        return candidate is not None and (baseline is None or candidate > baseline)

    def has_fresh_review_cycle(self) -> bool:
        normal_decision = self.artifact_timestamp(
            "last_learning_decision_at",
            self.latest_normal_decision,
        )
        review_plan = self.artifact_timestamp(
            "last_learning_review_plan_at",
            self.latest_review_plan,
        )
        return self.is_newer(review_plan, normal_decision)

    def review_advance_is_fresh(self) -> bool:
        if self.state.get("last_learning_review_decision") != "ADVANCE_TO_NEXT_TASK":
            return False

        review_assessment = self.artifact_timestamp(
            "last_learning_review_assessment_at",
            self.latest_review_assessment,
        )
        review_decision = self.artifact_timestamp(
            "last_learning_review_decision_at",
            self.latest_review_decision,
        )
        review_plan = self.artifact_timestamp(
            "last_learning_review_plan_at",
            self.latest_review_plan,
        )
        review_tutor = self.artifact_timestamp(
            "last_review_tutor_session_at",
            self.latest_review_tutor_session,
        )
        latest_normal_cycle = self.latest_timestamp(
            self.artifact_timestamp("last_tutor_session_at", self.latest_tutor_session),
            self.artifact_timestamp(
                "last_learning_answers_imported_at",
                self.latest_imported_answers,
            ),
            self.artifact_timestamp(
                "last_learning_assessment_at",
                self.latest_assessment,
            ),
            self.artifact_timestamp(
                "last_learning_decision_at",
                self.latest_normal_decision,
            ),
        )

        return (
            review_assessment is not None
            and self.is_newer(review_decision, review_assessment)
            and (latest_normal_cycle is None or review_decision > latest_normal_cycle)
        )

    def make_action(
        self,
        label: str,
        command_text: str,
        args: tuple[str, ...],
        risk_class: str,
    ) -> LearningAction:
        command_key = command_name_from_args(args)
        safety = get_command_safety(command_key)
        executable = manifest_allows_learning_action(args)
        expected_writes = LEARNING_DRY_RUN_WRITES.get(args[0], ()) if executable else ()
        return LearningAction(
            label=label,
            command_text=command_text,
            args=args,
            risk_class=risk_class,
            expected_writes=expected_writes,
            executable=executable,
            safety_class=safety.safety_class,
            tui_exposure=safety.tui_exposure,
            confirmation=safety.confirmation,
            warning_label=safety.warning_label,
        )

    def compute_next_action(self) -> LearningAction:
        sid = self.id
        normal_assessment = self.artifact_timestamp(
            "last_learning_assessment_at",
            self.latest_assessment,
        )
        normal_decision = self.artifact_timestamp(
            "last_learning_decision_at",
            self.latest_normal_decision,
        )
        review_assessment = self.artifact_timestamp(
            "last_learning_review_assessment_at",
            self.latest_review_assessment,
        )
        review_decision = self.artifact_timestamp(
            "last_learning_review_decision_at",
            self.latest_review_decision,
        )
        review_plan = self.artifact_timestamp(
            "last_learning_review_plan_at",
            self.latest_review_plan,
        )
        review_tutor = self.artifact_timestamp(
            "last_review_tutor_session_at",
            self.latest_review_tutor_session,
        )

        # A newer current-session assessment invalidates any older normal decision.
        if self.is_newer(normal_assessment, normal_decision):
            return self.make_action(
                "Run learning decision",
                f"ws learning-decision {sid}",
                ("learning-decision", sid),
                "BLUE",
            )

        # The current normal decision controls entry into a review/remediation lane.
        if self.state.get("last_learning_decision") == "REVIEW_CURRENT_TASK":
            if not self.has_fresh_review_cycle():
                return self.make_action(
                    "Generate targeted review session",
                    f"ws learning-review-session {sid} --dry-run",
                    ("learning-review-session", sid, "--dry-run"),
                    "BLUE",
                )

            review_plan_path = self.state.get("last_learning_review_plan_path")
            if self.is_newer(review_plan, review_tutor):
                return self.make_action(
                    "Start review tutor",
                    f"ws learning-run {sid} --review-session --model hermes3:8b --from-plan {self.to_win(review_plan_path)}",
                    (
                        "learning-run",
                        sid,
                        "--review-session",
                        "--model",
                        "hermes3:8b",
                        "--from-plan",
                        self.to_win(review_plan_path) or "",
                    ),
                    "PURPLE",
                )
            if self.session_status == "awaiting_review_answers":
                return self.make_action(
                    "Import review answers",
                    f"ws learning-import-answers {sid} --from-file <answers_file> --review",
                    ("learning-import-answers", sid, "--from-file", "<answers_file>", "--review"),
                    "BLUE",
                )
            if self.session_status == "awaiting_review_assessment":
                return self.make_action(
                    "Assess review answers",
                    f"ws learning-assess {sid} --model hermes3:8b --review",
                    ("learning-assess", sid, "--model", "hermes3:8b", "--review"),
                    "PURPLE",
                )
            if self.is_newer(review_assessment, review_decision) or self.session_status == "review_assessed":
                return self.make_action(
                    "Run review learning decision",
                    f"ws learning-decision {sid} --review",
                    ("learning-decision", sid, "--review"),
                    "BLUE",
                )
            if self.review_advance_is_fresh():
                return self.make_action(
                    "Advance to next task",
                    f"ws learning-advance {sid}",
                    ("learning-advance", sid),
                    "BLUE",
                )
            if review_plan_path and not self.latest_review_tutor_session:
                return self.make_action(
                    "Start review tutor",
                    f"ws learning-run {sid} --review-session --model hermes3:8b --from-plan {self.to_win(review_plan_path)}",
                    (
                        "learning-run",
                        sid,
                        "--review-session",
                        "--model",
                        "hermes3:8b",
                        "--from-plan",
                        self.to_win(review_plan_path) or "",
                    ),
                    "PURPLE",
                )
            return self.make_action(
                "Inspect learning state / run decision",
                f"ws learning-decision {sid}",
                ("learning-decision", sid),
                "BLUE",
            )

        if self.review_advance_is_fresh():
            return self.make_action(
                "Advance to next task",
                f"ws learning-advance {sid}",
                ("learning-advance", sid),
                "BLUE",
            )

        # Normal loop
        if self.next_task and self.session_status in ["ready_for_next_session", "unknown", "LOCAL_CHECKLIST_READY"]:
            # Check if current plan focus matches next_task
            plan_path = self.state.get("last_learning_session_plan_path")
            plan_ts = self.artifact_timestamp(
                "last_learning_session_plan_at",
                self.latest_session_plan,
            )
            tutor_ts = self.artifact_timestamp(
                "last_tutor_session_at",
                self.latest_tutor_session,
            )
            has_current_plan = False
            if plan_path and Path(plan_path).is_file():
                adv_at = self.state.get("last_learning_advanced_at")
                plan_at = self.state.get("last_learning_session_plan_at")
                if not adv_at or (plan_at and plan_at > adv_at):
                    has_current_plan = True

            if not has_current_plan:
                return self.make_action(
                    "Plan next session",
                    f"ws learning-run {sid} --session --dry-run",
                    ("learning-run", sid, "--session", "--dry-run"),
                    "BLUE",
                )
            
            if not self.state.get("last_tutor_session_path") or self.is_newer(plan_ts, tutor_ts):
                return self.make_action(
                    "Start tutor session",
                    f"ws learning-run {sid} --session --model hermes3:8b --from-plan {self.to_win(plan_path)}",
                    (
                        "learning-run",
                        sid,
                        "--session",
                        "--model",
                        "hermes3:8b",
                        "--from-plan",
                        self.to_win(plan_path) or "",
                    ),
                    "PURPLE",
                )
            
            if self.session_status == "awaiting_human_answers":
                return self.make_action(
                    "Import answers",
                    f"ws learning-import-answers {sid} --from-file <answers_file>",
                    ("learning-import-answers", sid, "--from-file", "<answers_file>"),
                    "BLUE",
                )
            
            if self.session_status == "awaiting_assessment":
                return self.make_action(
                    "Assess answers",
                    f"ws learning-assess {sid} --model hermes3:8b",
                    ("learning-assess", sid, "--model", "hermes3:8b"),
                    "PURPLE",
                )
            
            if self.session_status == "assessed":
                return self.make_action(
                    "Record decision",
                    f"ws learning-decision {sid}",
                    ("learning-decision", sid),
                    "BLUE",
                )

        return self.make_action(
            "Inspect learning state / run decision",
            f"ws learning-decision {sid}",
            ("learning-decision", sid),
            "BLUE",
        )


@dataclass
class CommandResult:
    label: str
    args: tuple[str, ...]
    stdout: str
    stderr: str
    returncode: int

    @property
    def command_text(self) -> str:
        return "ws " + " ".join(self.args)

    @property
    def display_text(self) -> str:
        if self.returncode == 0:
            return self.stdout.strip() or "(no output)"
        if self.returncode == 124:
            timeout_line = ""
            stderr_lines: list[str] = []
            for line in self.stderr.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith("[TIMEOUT]") and not timeout_line:
                    timeout_line = stripped
                    continue
                stderr_lines.append(stripped)
            parts: list[str] = []
            if timeout_line:
                parts.append(timeout_line)
            if self.stdout.strip():
                parts.append(self.stdout.strip())
            if stderr_lines:
                parts.append("\n".join(stderr_lines))
            return "\n".join(parts) or f"[TIMEOUT] {self.command_text} timed out."
        parts = [f"Command failed with exit code {self.returncode}."]
        if self.stdout.strip():
            parts.append(self.stdout.strip())
        if self.stderr.strip():
            parts.append(self.stderr.strip())
        return "\n".join(parts)


@dataclass
class DashboardData:
    results: dict[str, CommandResult] = field(default_factory=dict)
    command_log: list[str] = field(default_factory=list)
    learning_strongholds: list[LearningStronghold] = field(default_factory=list)
    execution_log: list[str] = field(default_factory=list)


def get_latest_state_sync_audit(stronghold_dir: Path) -> dict | None:
    audit_file = stronghold_dir / "state_sync_audit.jsonl"
    if not audit_file.is_file():
        return None
    try:
        with open(audit_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if not lines:
                return None
            for line in reversed(lines):
                if line.strip():
                    return json.loads(line)
    except Exception:
        pass
    return None


def get_backup_info(stronghold_dir: Path) -> dict:
    backup_dir = stronghold_dir / "state_backups"
    if not backup_dir.is_dir():
        return {"count": 0, "latest": None}
    try:
        backups = sorted(
            [f for f in backup_dir.iterdir() if f.is_file() and f.suffix == ".json"],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        return {
            "count": len(backups),
            "latest": backups[0].name if backups else None
        }
    except Exception:
        return {"count": 0, "latest": None}


def get_latest_pointer_plan(stronghold_id: str) -> dict | None:
    script_path = WS_HOME / "scripts" / "learning_pointer_update_planner.py"
    if not script_path.is_file():
        return None
    try:
        res = subprocess.run(
            [sys.executable, str(script_path), stronghold_id, "--dry-run", "--json"],
            cwd=WS_HOME,
            capture_output=True,
            text=True,
            timeout=10,
            env={"WS_HOME": str(WS_HOME), "PYTHONDONTWRITEBYTECODE": "1"}
        )
        if res.returncode == 0:
            return json.loads(res.stdout)
    except Exception:
        pass
    return None


def get_latest_advancement_plan(stronghold_id: str) -> dict | None:
    script_path = WS_HOME / "scripts" / "learning_advancement_readiness_planner.py"
    if not script_path.is_file():
        return None
    try:
        res = subprocess.run(
            [sys.executable, str(script_path), stronghold_id, "--dry-run", "--json"],
            cwd=WS_HOME,
            capture_output=True,
            text=True,
            timeout=10,
            env={"WS_HOME": str(WS_HOME), "PYTHONDONTWRITEBYTECODE": "1"}
        )
        if res.returncode == 0:
            return json.loads(res.stdout)
    except Exception:
        pass
    return None


def get_latest_review_packet(stronghold_path: Path) -> dict | None:
    packet_dir = stronghold_path / "review_packets"
    if not packet_dir.is_dir():
        return None
    
    try:
        packets = sorted(
            [f for f in packet_dir.iterdir() if f.is_file() and f.suffix == ".md"],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        if not packets:
            return None
        
        latest = packets[0]
        if latest.stat().st_size > 100 * 1024: # 100KB limit
            return {"filename": latest.name, "error": "Packet file too large"}
        
        content = latest.read_text(encoding="utf-8")
        
        # Extraction logic
        packet_id = re.search(r"Packet ID: (ADV-PACKET-[A-Z\d]+Z)", content)
        timestamp = re.search(r"Timestamp UTC: ([A-Z\d]+Z)", content)
        
        readiness_status = re.search(r"## 2\. Advancement Readiness\n- \*\*Status\*\*: ([^\n]+)", content)
        readiness_score = re.search(r"- \*\*Score\*\*: ([\d/]+)", content)
        
        current_state = re.search(r"## 1\. Current State\n- \*\*State\*\*: ([^\n]+)", content)
        
        pointer_status = re.search(r"## 3\. Pointer Status\n.*?- \*\*Status\*\*: ([^\n]+)", content, re.DOTALL)
        sync_status = re.search(r"## 4\. State Sync Status\n.*?- \*\*Status\*\*: ([^\n]+)", content, re.DOTALL)
        
        checks = re.findall(r"- \[ \] ([^\n]+)", content)

        return {
            "filename": latest.name,
            "path": str(latest),
            "packet_id": packet_id.group(1) if packet_id else "unknown",
            "timestamp": timestamp.group(1) if timestamp else "unknown",
            "readiness_status": readiness_status.group(1) if readiness_status else "unknown",
            "readiness_score": readiness_score.group(1) if readiness_score else "unknown",
            "current_state": current_state.group(1) if current_state else "unknown",
            "pointer_status": pointer_status.group(1) if pointer_status else "unknown",
            "sync_status": sync_status.group(1) if sync_status else "unknown",
            "checks_count": len(checks),
            "checks_summary": checks[0] if checks else "None"
        }
    except Exception as e:
        return {"error": str(e)}


def discover_learning_strongholds() -> list[LearningStronghold]:
    base_dir = WS_HOME / "strongholds" / "learning"
    if not base_dir.is_dir():
        return []
    
    strongholds = []
    for d in base_dir.iterdir():
        state_file = d / "state.json"
        if not d.is_dir() or not state_file.is_file():
            continue
            
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            continue
            
        # Action Pack v1
        action_pack_v1 = []
        try:
            script_path = WS_HOME / "scripts" / "learning_action_pack.py"
            if script_path.is_file():
                res = subprocess.run(
                    [sys.executable, str(script_path), d.name, "--dry-run", "--json"],
                    capture_output=True,
                    text=True,
                    env={"WS_HOME": str(WS_HOME), "PYTHONDONTWRITEBYTECODE": "1"}
                )
                if res.returncode == 0:
                    action_pack_v1 = json.loads(res.stdout)
        except Exception:
            pass

        # Ledger v1
        ledger_v1 = []
        ledger_path = d / "learning_confirmations.jsonl"
        if ledger_path.is_file():
            try:
                with open(ledger_path, "r", encoding="utf-8") as f:
                    # Read all lines, but keep only the last 10
                    lines = f.readlines()
                    for line in lines[-10:]:
                        if line.strip():
                            ledger_v1.append(json.loads(line))
            except Exception:
                pass
        
        # Confirmed Artifacts v1
        confirmed_artifacts_v1 = []
        confirmed_dir = d / "confirmed_actions"
        if confirmed_dir.is_dir():
            try:
                # Get last 5 markdown files by modification time
                artifacts = sorted(
                    [f for f in confirmed_dir.iterdir() if f.is_file() and f.suffix == ".md"],
                    key=lambda x: x.stat().st_mtime,
                    reverse=True
                )
                confirmed_artifacts_v1 = [f.name for f in artifacts[:5]]
            except Exception:
                pass

        # State Sync v1
        latest_sync = get_latest_state_sync_audit(d)
        backup_info = get_backup_info(d)
        pointer_plan = get_latest_pointer_plan(d.name)
        advancement_plan = get_latest_advancement_plan(d.name)
        latest_review_packet = get_latest_review_packet(d)

        sh = LearningStronghold(
            id=state.get("stronghold_id", d.name),
            path=d,
            title=state.get("title", "unknown"),
            current_state=state.get("current_state", "unknown"),
            session_status=state.get("learning_session_status", "unknown"),
            next_task=state.get("next_learning_task"),
            last_completed_task=state.get("last_completed_learning_task"),
            state=state,
            action_pack_v1=action_pack_v1,
            ledger_v1=ledger_v1,
            confirmed_artifacts_v1=confirmed_artifacts_v1,
            latest_sync=latest_sync,
            backup_count=backup_info["count"],
            latest_backup_name=backup_info["latest"],
            pointer_plan=pointer_plan,
            advancement_plan=advancement_plan,
            latest_review_packet=latest_review_packet,
            latest_session_plan=state.get("last_learning_session_plan_path"),
            latest_tutor_session=state.get("last_tutor_session_path"),
            latest_answer_template=state.get("last_tutor_session_path"),
            latest_imported_answers=state.get("last_learning_answers_path"),
            latest_assessment=state.get("last_learning_assessment_path"),
            latest_review_plan=state.get("last_learning_review_plan_path"),
            latest_review_tutor_session=state.get("last_review_tutor_session_path"),
            latest_review_answers=state.get("last_learning_review_answers_path"),
            latest_review_assessment=state.get("last_learning_review_assessment_path"),
            linked_tutor_session=state.get("last_learning_answers_for_tutor_session_path"),
            import_success=state.get("last_learning_answers_import_success", False)
        )
        
        if sh.latest_tutor_session:
            tmpl = sh.latest_tutor_session.replace("_tutor_session.md", "_answer_template.md")
            if Path(tmpl).is_file():
                sh.latest_answer_template = tmpl

        if sh.latest_review_tutor_session:
            review_tmpl = sh.latest_review_tutor_session.replace(
                "_review_tutor_session.md",
                "_review_answer_template.md",
            )
            if Path(review_tmpl).is_file():
                sh.latest_review_answer_template = review_tmpl

        sh.latest_normal_decision = resolve_decision_report(
            sh.path,
            state.get("last_learning_decision_at"),
            "learning_decision",
        )
        sh.latest_review_decision = resolve_decision_report(
            sh.path,
            state.get("last_learning_review_decision_at"),
            "learning_review_decision",
        )

        strongholds.append(sh)
    
    return sorted(strongholds, key=lambda x: x.id)


def report_sort_key(path: Path) -> tuple[datetime, str]:
    timestamp = LearningStronghold.timestamp_from_path(str(path))
    return (timestamp or datetime.min, path.name)


def resolve_decision_report(
    stronghold_path: Path,
    state_timestamp: str | None,
    prefix: str,
) -> str | None:
    reports_dir = stronghold_path / "reports"
    if not reports_dir.is_dir():
        return None

    if state_timestamp:
        state_candidate = reports_dir / f"{prefix}_{state_timestamp}.md"
        if state_candidate.is_file():
            return str(state_candidate)

    matches = sorted(reports_dir.glob(f"{prefix}_*.md"), key=report_sort_key, reverse=True)
    return str(matches[0]) if matches else None


def run_status_command(label: str, args: tuple[str, ...], command_log: list[str]) -> CommandResult:
    command_text = "ws " + " ".join(args)
    timeout_seconds = status_timeout_seconds()
    debug_log(f"collecting status: {command_text}")
    try:
        completed = subprocess.run(
            ["bash", str(WS_SCRIPT), *args],
            cwd=WS_HOME,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        timeout_message = f"[TIMEOUT] {command_text} did not complete within {timeout_seconds}s"
        partial_stdout = normalize_subprocess_text(exc.stdout)
        partial_stderr = normalize_subprocess_text(exc.stderr)
        stderr_parts = [timeout_message]
        if partial_stderr.strip():
            stderr_parts.append(partial_stderr.strip())
        result = CommandResult(
            label=label,
            args=args,
            stdout=partial_stdout,
            stderr="\n".join(stderr_parts),
            returncode=124,
        )
        append_command_log_entry(command_log, command_log_status(result), command_text)
        return result
    except OSError as exc:
        launch_message = f"[ERROR] {command_text} failed to start: {exc}"
        result = CommandResult(
            label=label,
            args=args,
            stdout="",
            stderr=launch_message,
            returncode=127,
        )
        append_command_log_entry(command_log, command_log_status(result), command_text)
        return result
    result = CommandResult(
        label=label,
        args=args,
        stdout=normalize_subprocess_text(completed.stdout),
        stderr=normalize_subprocess_text(completed.stderr),
        returncode=completed.returncode,
    )
    append_command_log_entry(command_log, command_log_status(result), command_text)
    return result


def is_allowlisted_learning_dry_run(args: tuple[str, ...]) -> bool:
    if not args:
        return False
    if args[0] == "learning-run":
        return len(args) == 4 and (args[0], args[2], args[3]) in LEARNING_DRY_RUN_ALLOWLIST
    if args[0] == "learning-review-session":
        return len(args) == 3 and (args[0], args[2]) in LEARNING_DRY_RUN_ALLOWLIST
    return False


def run_learning_action(action: LearningAction) -> CommandResult:
    if not action.executable or not is_allowlisted_learning_dry_run(action.args):
        raise ValueError("Learning action is not allowlisted for execution.")

    completed = subprocess.run(
        ["bash", str(WS_SCRIPT), *action.args],
        cwd=WS_HOME,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    return CommandResult(
        label=action.label,
        args=action.args,
        stdout=normalize_subprocess_text(completed.stdout),
        stderr=normalize_subprocess_text(completed.stderr),
        returncode=completed.returncode,
    )


def disabled_status_command_result(label: str, args: tuple[str, ...], reason: str) -> CommandResult:
    command_text = "ws " + " ".join(args)
    return CommandResult(
        label=label,
        args=args,
        stdout="",
        stderr=f"[CHECK] {command_text} disabled by command safety manifest: {reason}",
        returncode=126,
    )


def first_learning_stronghold(data: DashboardData) -> LearningStronghold | None:
    return data.learning_strongholds[0] if data.learning_strongholds else None


def write_tui_execution_report(
    action: LearningAction,
    result: CommandResult,
    refreshed_action: LearningAction | None,
) -> Path:
    reports_dir = WS_HOME / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = reports_dir / f"TUI_EXECUTION_{timestamp}.md"
    report = "\n".join(
        [
            "# TUI Execution Report",
            "",
            f"- Timestamp: {timestamp}",
            f"- Action Label: {action.label}",
            f"- Risk Class: {action.risk_class}",
            f"- Command: `{action.command_text}`",
            f"- Exit Code: {result.returncode}",
            f"- Refreshed Recommendation: {refreshed_action.label if refreshed_action else 'none'}",
            f"- Refreshed Command: `{refreshed_action.command_text if refreshed_action else 'none'}`",
            "",
            "## Stdout",
            "```text",
            result.stdout.rstrip(),
            "```",
            "",
            "## Stderr",
            "```text",
            result.stderr.rstrip(),
            "```",
            "",
        ]
    )
    report_path.write_text(report, encoding="utf-8", newline="\n")
    return report_path


def collect_dashboard_data(command_log: list[str] | None = None) -> DashboardData:
    log = command_log if command_log is not None else []
    debug_log("collecting status")
    results: dict[str, CommandResult] = {}
    for label, args in STATUS_COMMANDS:
        if not manifest_allows_existing_status_command(args):
            command_name = command_name_from_args(args)
            safety = get_command_safety(command_name)
            results[label] = disabled_status_command_result(
                label,
                args,
                f"{safety.safety_class}/{safety.tui_exposure} not allowed in {COMMAND_SAFETY_POLICY_MODE}",
            )
            append_command_log_entry(log, "CHECK", "ws " + " ".join(args))
            continue
        results[label] = run_status_command(label, args, log)
    debug_log("collecting learning strongholds")
    learning_strongholds = discover_learning_strongholds()
    return DashboardData(
        results=results,
        command_log=log,
        learning_strongholds=learning_strongholds,
    )


def section(title: str, body: str) -> str:
    line = "=" * len(title)
    return f"{title}\n{line}\n{body.strip() or '(no output)'}"


def visible_lines(text: str, limit: int = 4) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[:limit] or ["(no output)"]


def fit_text(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    return text[: width - 3] + "..."


def hard_clip_text(text: str, width: int) -> str:
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    return text[:width]


def hard_clip_rendered_line(line: str, width: int) -> str:
    if width <= 0:
        return ""
    plain = ANSI_RE.sub("", line)
    if len(plain) <= width:
        return line
    clipped = hard_clip_text(plain, width)
    return colorize_semantic(clipped) if colors_enabled() else clipped


def enforce_max_width(lines: Iterable[str], width: int) -> list[str]:
    return [hard_clip_rendered_line(line, width) for line in lines]


def wrap_lines(lines: Iterable[str], width: int) -> list[str]:
    wrapped: list[str] = []
    for line in lines:
        if not line:
            wrapped.append("")
            continue
        chunks = textwrap.wrap(
            line,
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        )
        wrapped.extend(chunks or [""])
    return wrapped


def panel(title: str, lines: Iterable[str], width: int) -> list[str]:
    inner = width - 4
    border = "+" + "-" * (width - 2) + "+"
    title_text = fit_text(title, inner)
    rendered = [border, f"| {title_text.ljust(inner)} |", border]
    for line in wrap_lines(lines, inner):
        rendered.append(f"| {fit_text(line, inner).ljust(inner)} |")
    rendered.append(border)
    return rendered


def layout_spec() -> LayoutSpec:
    terminal_width = max(shutil.get_terminal_size((120, 30)).columns, 80)
    width = max(60, terminal_width - SAFE_RENDER_MARGIN)
    if terminal_width >= 150:
        mode = "xwide"
    elif terminal_width >= 120:
        mode = "wide"
    elif terminal_width >= 100:
        mode = "medium"
    else:
        mode = "narrow"
    return LayoutSpec(
        mode=mode,
        width=width,
        content_width=width,
        sidebar_width=0,
    )


def icon_mode() -> str:
    requested = os.environ.get("WS_TUI_ICONS", "auto").strip().lower()
    encoding = sys.stdout.encoding or ""
    unicode_supported = False
    if encoding:
        try:
            "✓⚠✕▶◇↔▣○".encode(encoding)
            unicode_supported = True
        except UnicodeEncodeError:
            unicode_supported = False
        except LookupError:
            unicode_supported = False
    if requested == "ascii":
        return "ascii"
    if requested == "unicode":
        if unicode_supported:
            return "unicode"
        debug_log(
            f"unicode icons requested but stdout encoding '{encoding or 'unknown'}' cannot render them; using ascii fallback"
        )
        return "ascii"
    return "unicode" if unicode_supported else "ascii"


def side_by_side_widths(total_width: int, gap: int = 1) -> tuple[int, int]:
    left_width = (total_width - gap) // 2
    right_width = total_width - left_width - gap
    return left_width, right_width


def can_render_side_by_side(
    *,
    total_width: int,
    left_title: str,
    left_lines: Iterable[str],
    right_title: str,
    right_lines: Iterable[str],
    min_card_width: int = 48,
    gap: int = 1,
) -> bool:
    if total_width < 140:
        return False

    left_width, right_width = side_by_side_widths(total_width, gap=gap)
    if left_width < min_card_width or right_width < min_card_width:
        return False

    left_inner = max(1, left_width - 4)
    right_inner = max(1, right_width - 4)
    if len(left_title) > max(1, left_inner - 2) or len(right_title) > max(1, right_inner - 2):
        return False

    for line in left_lines:
        if len(line) > left_inner:
            return False
    for line in right_lines:
        if len(line) > right_inner:
            return False
    return True


def icons() -> IconSet:
    if icon_mode() == "unicode":
        return IconSet(
            ok="✓",
            warning="⚠",
            blocked="✕",
            run="▶",
            dry_run="◇",
            linked="↔",
            artifact="▣",
            disabled="○",
        )
    return IconSet(
        ok="[OK]",
        warning="[!!]",
        blocked="[X]",
        run="[Run]",
        dry_run="[Dry]",
        linked="[LINK]",
        artifact="[File]",
        disabled="[Disabled]",
    )


def merge_columns(left: list[str], right: list[str], spec: LayoutSpec) -> list[str]:
    height = max(len(left), len(right))
    output: list[str] = []
    for index in range(height):
        left_line = left[index] if index < len(left) else " " * spec.sidebar_width
        right_line = right[index] if index < len(right) else " " * spec.content_width
        output.append(f"{left_line.ljust(spec.sidebar_width)}   {right_line}")
    return output


def badge(label: str) -> str:
    return f"[{label}]"


def latest_artifact(*paths: str | None) -> str | None:
    available = [path for path in paths if path]
    if not available:
        return None
    return max(
        available,
        key=lambda item: (
            LearningStronghold.timestamp_from_path(item) or datetime.min,
            item,
        ),
    )


def artifact_label(path: str | None) -> str:
    if not path:
        return "none"
    return Path(path).name


def format_artifact_timestamp(timestamp: datetime | None) -> str:
    return timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "n/a"


def artifact_relative_path(sh: LearningStronghold, artifact_path: str | None) -> str:
    if not artifact_path:
        return "none"
    try:
        return str(Path(artifact_path).resolve().relative_to(sh.path.resolve()))
    except ValueError:
        return "outside stronghold"


def artifact_file_timestamp(path: str | None) -> datetime | None:
    if not path:
        return None
    candidate = Path(path)
    if not candidate.is_file():
        return None
    return datetime.fromtimestamp(candidate.stat().st_mtime)


def learning_artifact_catalog(sh: LearningStronghold) -> list[LearningArtifact]:
    specs = [
        (
            "latest_session_plan",
            "Latest Session Plan",
            sh.latest_session_plan,
            "last_learning_session_plan_at",
        ),
        (
            "latest_tutor_session",
            "Latest Tutor Session",
            sh.latest_tutor_session,
            "last_tutor_session_at",
        ),
        (
            "latest_answer_template",
            "Latest Answer Template",
            sh.latest_answer_template,
            None,
        ),
        (
            "latest_human_answers",
            "Latest Human Answers",
            sh.latest_imported_answers,
            "last_learning_answers_imported_at",
        ),
        (
            "latest_assessment",
            "Latest Assessment",
            sh.latest_assessment,
            "last_learning_assessment_at",
        ),
        (
            "latest_decision",
            "Latest Decision",
            sh.latest_normal_decision,
            "last_learning_decision_at",
        ),
        (
            "latest_review_plan",
            "Latest Review Plan",
            sh.latest_review_plan,
            "last_learning_review_plan_at",
        ),
        (
            "latest_review_tutor_session",
            "Latest Review Tutor Session",
            sh.latest_review_tutor_session,
            "last_review_tutor_session_at",
        ),
        (
            "latest_review_answer_template",
            "Latest Review Answer Template",
            sh.latest_review_answer_template,
            None,
        ),
        (
            "latest_review_answers",
            "Latest Review Answers",
            sh.latest_review_answers,
            "last_learning_review_answers_imported_at",
        ),
        (
            "latest_review_assessment",
            "Latest Review Assessment",
            sh.latest_review_assessment,
            "last_learning_review_assessment_at",
        ),
        (
            "latest_review_decision",
            "Latest Review Decision",
            sh.latest_review_decision,
            "last_learning_review_decision_at",
        ),
        (
            "progress_log",
            "Progress Log",
            str(sh.path / "progress.md"),
            None,
        ),
        (
            "practice_log",
            "Practice Log",
            str(sh.path / "practice_log.md"),
            None,
        ),
    ]
    artifacts: list[LearningArtifact] = []
    for key, label, path, state_key in specs:
        candidate = Path(path) if path else None
        timestamp = (
            sh.artifact_timestamp(state_key, path)
            if state_key
            else LearningStronghold.timestamp_from_path(path)
        )
        if timestamp is None:
            timestamp = artifact_file_timestamp(path)
        artifacts.append(
            LearningArtifact(
                key=key,
                label=label,
                path=path,
                timestamp=timestamp,
                exists=bool(candidate and candidate.is_file()),
                relative_path=artifact_relative_path(sh, path),
            )
        )
    return artifacts


def artifact_by_key(sh: LearningStronghold, key: str) -> LearningArtifact | None:
    return next((artifact for artifact in learning_artifact_catalog(sh) if artifact.key == key), None)


def latest_catalog_artifact(sh: LearningStronghold, keys: tuple[str, ...]) -> LearningArtifact | None:
    candidates = [
        artifact
        for artifact in learning_artifact_catalog(sh)
        if artifact.key in keys and artifact.path
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            item.timestamp or datetime.min,
            item.path or "",
        ),
    )


def glyph(unicode_char: str, ascii_char: str) -> str:
    return unicode_char if icon_mode() == "unicode" else ascii_char


def sep_dot() -> str:
    return " · " if icon_mode() == "unicode" else " | "


def degrees_unit() -> str:
    return "°C" if icon_mode() == "unicode" else "C"


def operator_branch_value(value: object) -> str:
    raw = str(value).strip() if value is not None else ""
    return "UNKNOWN" if not raw or raw.lower() == "unknown" else raw


def two_sided_line(left: str, right: str, width: int) -> str:
    width = max(1, width)
    left_text = left.strip()
    right_text = right.strip()
    if not right_text:
        return fit_text(left_text, width)
    if len(right_text) >= width:
        return hard_clip_text(right_text, width)

    left_budget = width - len(right_text) - 1
    if left_budget <= 0:
        return hard_clip_text(right_text, width)

    left_fitted = fit_text(left_text, left_budget)
    spacing = max(1, width - len(left_fitted) - len(right_text))
    row = left_fitted + (" " * spacing) + right_text
    return hard_clip_text(row, width)


def render_banner(dashboard: DashboardData, width: int) -> list[str]:
    width = max(width, 56)
    inner = width - 6
    hygiene = parse_agent_hygiene(dashboard.results["agent_hygiene"])
    hygiene_state = agent_hygiene_status(hygiene, dashboard.results["agent_hygiene"])
    unresolved = hygiene.get("unresolved")
    unresolved_display = (
        "0" if unresolved == 0 else str(unresolved) if unresolved is not None else "UNAVAILABLE"
    )
    branch_display = operator_branch_value(hygiene.get("branch", "unknown"))
    title_left = "LOCAL AI WORKSTATION"
    title_right_candidates = [
        datetime.now().strftime("%H:%M %d %b"),
        datetime.now().strftime("%H:%M %d%b"),
        datetime.now().strftime("%H:%M"),
    ]
    title_right = next(
        (
            candidate
            for candidate in title_right_candidates
            if len(title_left) + 1 + len(candidate) <= inner
        ),
        title_right_candidates[-1],
    )
    title_line = two_sided_line(title_left, title_right, inner)

    mode_left = f"{SAFETY_MODE}{sep_dot()}SAFE_DRY_RUN"
    mode_right_candidates = [
        f"branch {branch_display}{sep_dot()}unresolved {unresolved_display}{sep_dot()}hygiene {hygiene_state}",
        f"branch {branch_display}{sep_dot()}hygiene {hygiene_state}",
        f"{branch_display}{sep_dot()}unresolved {unresolved_display}{sep_dot()}{hygiene_state}",
        f"{branch_display}{sep_dot()}{hygiene_state}",
        f"hygiene {hygiene_state}",
        hygiene_state,
    ]
    mode_right = next(
        (
            candidate
            for candidate in mode_right_candidates
            if len(mode_left) + 1 + len(candidate) <= inner
        ),
        mode_right_candidates[-1],
    )
    mode_line = two_sided_line(mode_left, mode_right, inner)

    if icon_mode() == "unicode":
        top = "╔" + ("═" * (width - 2)) + "╗"
        bottom = "╚" + ("═" * (width - 2)) + "╝"
        vbar = "║"
    else:
        top = "+" + ("-" * (width - 2)) + "+"
        bottom = "+" + ("-" * (width - 2)) + "+"
        vbar = "|"

    rendered = [top]
    for raw in (title_line, mode_line):
        padded = pad_visible(raw, inner)
        rendered.append(f"{vbar}  {colorize_semantic(padded)}  {vbar}")
    rendered.append(bottom)
    return rendered


def render_card(title: str, lines: Iterable[str], width: int) -> list[str]:
    width = max(width, 24)
    inner = width - 4
    h = glyph("─", "-")
    v = glyph("│", "|")
    tl = glyph("╭", "+")
    tr = glyph("╮", "+")
    bl = glyph("╰", "+")
    br = glyph("╯", "+")
    title_text = fit_text(title, max(1, inner - 2))
    top_prefix = f"{tl}{h} {title_text} "
    top_fill = max(0, width - len(top_prefix) - 1)
    top = top_prefix + (h * top_fill) + tr
    bottom = bl + (h * (width - 2)) + br

    rendered = [top]
    for line in lines:
        wrapped = wrap_lines([line], inner)
        for segment in wrapped or [""]:
            plain = fit_text(segment, inner)
            styled = colorize_semantic(plain)
            rendered.append(f"{v} {pad_visible(styled, inner)} {v}")
    rendered.append(bottom)
    return rendered


def merge_card_columns(left: list[str], right: list[str], *, left_width: int, right_width: int, gap: int = 1) -> list[str]:
    height = max(len(left), len(right))
    output: list[str] = []
    for index in range(height):
        left_line = left[index] if index < len(left) else " " * left_width
        right_line = right[index] if index < len(right) else " " * right_width
        output.append(f"{pad_visible(left_line, left_width)}{' ' * gap}{pad_visible(right_line, right_width)}")
    return output


def parse_readiness_summary(result: CommandResult) -> dict[str, object]:
    summary: dict[str, object] = {
        "state": readiness_operator_state(result),
        "ollama_ok": None,
        "wsl_ok": None,
        "gpu_model": "UNKNOWN",
        "gpu_used": None,
        "gpu_total": None,
        "gpu_temp": None,
        "projects": None,
    }
    for raw_line in readiness_detail_lines(result):
        line = raw_line.replace("\x00", "").strip()
        if "Ollama" in line and ("reachable" in line or "running" in line or "localhost:11434" in line):
            if "[OK]" in line:
                summary["ollama_ok"] = True
            elif "[FAIL]" in line:
                summary["ollama_ok"] = False
        if "WSL" in line and "Ollama" in line:
            if "[OK]" in line:
                summary["wsl_ok"] = True
            elif "[FAIL]" in line:
                summary["wsl_ok"] = False
        gpu_match = re.search(r"(RTX[^:]*):\s*(\d+)\s*MiB,\s*(\d+)\s*MiB,\s*(\d+)", line)
        if gpu_match:
            summary["gpu_model"] = gpu_match.group(1).strip()
            summary["gpu_used"] = int(gpu_match.group(2))
            summary["gpu_total"] = int(gpu_match.group(3))
            summary["gpu_temp"] = int(gpu_match.group(4))
        project_match = re.search(r"Registry:\s*(\d+)\s+projects\s+detected", line)
        if project_match:
            summary["projects"] = int(project_match.group(1))
    return summary


def bool_signal(ok: bool | None) -> str:
    if ok is None:
        return "UNAVAILABLE"
    marker = glyph("●", "*")
    return f"{marker} ONLINE" if ok else f"{marker} OFFLINE"


def meter(used: int | None, total: int | None, *, slots: int = 10) -> str:
    if used is None or total is None or total <= 0:
        return "n/a"
    ratio = max(0.0, min(1.0, used / total))
    filled = max(0, min(slots, int(round(ratio * slots))))
    full = glyph("▉", "#")
    empty = glyph("░", "-")
    return (full * filled) + (empty * (slots - filled))


def temp_band(temp_c: int | None) -> str:
    if temp_c is None:
        return "UNKNOWN"
    if temp_c < 55:
        return "COOL"
    if temp_c <= 75:
        return "WARM"
    if temp_c <= 85:
        return "HOT"
    return "DANGER"


def machine_card_lines(dashboard: DashboardData) -> list[str]:
    parsed = parse_readiness_summary(dashboard.results["readiness"])
    state = str(parsed.get("state", "UNKNOWN"))
    used = parsed.get("gpu_used")
    total = parsed.get("gpu_total")
    temp = parsed.get("gpu_temp")
    projects = parsed.get("projects")
    has_vram = isinstance(used, int) and isinstance(total, int) and total > 0
    has_temp = isinstance(temp, int)
    vram_row = (
        f"VRAM        {meter(used, total)} {used} / {total} MiB"
        if has_vram
        else "VRAM        UNAVAILABLE"
    )
    temp_row = (
        f"Temp        {meter(temp, 100)} {temp}{degrees_unit()} {temp_band(temp)}"
        if has_temp
        else "Temp        UNAVAILABLE"
    )
    return [
        f"Readiness   {state}",
        f"Ollama      {bool_signal(parsed.get('ollama_ok'))}",
        f"WSL         {bool_signal(parsed.get('wsl_ok'))}",
        f"GPU         {parsed.get('gpu_model')}",
        vram_row,
        temp_row,
        f"Projects    {projects if isinstance(projects, int) else 'UNAVAILABLE'}",
    ]


def safety_card_lines(dashboard: DashboardData) -> list[str]:
    summary = parse_agent_hygiene(dashboard.results["agent_hygiene"])
    unresolved = summary.get("unresolved")
    reviewed = summary.get("reviewed")
    ignored_ok = summary.get("ignored_ok")
    hygiene_state = agent_hygiene_status(summary, dashboard.results["agent_hygiene"])
    unavailable = hygiene_state in {"UNAVAILABLE", "CHECK_FAILED", "UNKNOWN"}
    unresolved_text = str(unresolved) if unresolved is not None else ("UNAVAILABLE" if unavailable else "UNKNOWN")
    reviewed_text = str(reviewed) if reviewed is not None else ("UNAVAILABLE" if unavailable else "UNKNOWN")
    outputs_text = (
        "ignored OK"
        if ignored_ok is True
        else "ignored FAIL"
        if ignored_ok is False
        else "UNAVAILABLE"
        if unavailable
        else "ignored CHECK"
    )
    return [
        f"Mode        {SAFETY_MODE}",
        f"Cmd policy  {COMMAND_SAFETY_POLICY_MODE}",
        "Execution   SAFE_DRY_RUN",
        f"Branch      {operator_branch_value(summary.get('branch', 'unknown'))}",
        f"Unresolved  {unresolved_text}",
        f"Reviewed    {reviewed_text}",
        f"Outputs     {outputs_text}",
        f"Agent       hygiene {hygiene_state}",
    ]


def parse_stronghold_rows(result: CommandResult) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for line in nonempty_lines(result.display_text):
        if "|" not in line:
            continue
        if line.lower().startswith("type"):
            continue
        if set(line.replace("|", "").replace("-", "").strip()) == set():
            continue
        parts = [item.strip() for item in line.split("|")]
        if len(parts) < 4:
            continue
        rows.append((parts[0], parts[1], parts[2], parts[3]))
    return rows


def parse_feature_rows(result: CommandResult) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for line in nonempty_lines(result.display_text):
        if "|" not in line:
            continue
        if line.lower().startswith("recent feature strongholds"):
            continue
        if set(line.replace("|", "").replace("-", "").strip()) == set():
            continue
        parts = [item.strip() for item in line.split("|")]
        if len(parts) < 5:
            continue
        feature_id, project, title, state = parts[0], parts[1], parts[2], parts[3]
        rows.append((feature_id, project, title, state))
    return rows


def workflow_rail_lines(sh: LearningStronghold, action: LearningAction) -> list[str]:
    done = glyph("●", "*")
    pending = glyph("◎", "o")
    up = glyph("▲", "^")
    bar = glyph("─", "-") * 16
    checklist_done = sh.current_state.upper() in {
        "LOCAL_CHECKLIST_READY",
        "ARCHITECT_REVIEW_READY",
        "CONTRACT_READY",
    } or bool(sh.next_task)
    decision_done = bool(sh.latest_normal_decision or sh.latest_review_decision)
    review_needed = bool(sh.decision_warning)
    action_label = action.label.lower()
    if review_needed:
        if "review tutor" in action_label:
            stage3_label = "review tutor needed"
        elif "review session" in action_label:
            stage3_label = "review session needed"
        else:
            stage3_label = "review step needed"
    else:
        stage3_label = "advance window"
    stage3 = pending if review_needed else done

    lines = [
        "checklist ready      decision recorded      " + stage3_label,
        f"      {done if checklist_done else pending} {bar} {done if decision_done else pending} {bar} {stage3}",
    ]
    if review_needed:
        lines.append(" " * 52 + f"{up} NEXT SAFE STEP")
    else:
        lines.append(" " * 52 + "READY FOR SAFE PROGRESSION")
    if action.executable:
        lines.append("Safe dry-run is allowlisted for this recommended action.")
    return lines


def blocker_text(sh: LearningStronghold, action: LearningAction) -> str:
    if sh.decision_warning:
        return sh.decision_warning.replace("[WARN] ", "", 1)
    if not action.executable:
        return human_disabled_reason(action)
    return "No safety blocker detected."


def active_stronghold_lines(sh: LearningStronghold | None, next_action_engine_result: "NextSafeAction" = None) -> list[str]:
    if sh is None:
        return ["No learning stronghold discovered."]
    action = sh.compute_next_action()
    risk_state = "READY" if action.executable else "WARN"
    
    if next_action_engine_result:
        engine_label = next_action_engine_result.label
        engine_reason = next_action_engine_result.blocker or next_action_engine_result.reason
        engine_safety = next_action_engine_result.safety_class
        cmd_safety = get_command_safety(next_action_engine_result.command) if next_action_engine_result.command else None
        engine_warning = cmd_safety.warning_label if cmd_safety and cmd_safety.warning_label else "no provider call"
        
        next_action_display = [
            "NEXT SAFE ACTION",
            f"{glyph('▶', '>')} [1] {engine_label}",
            f"  Reason: {engine_reason}",
            f"  Safety: {engine_safety} {sep_dot()} {engine_warning}",
        ]
        if next_action_engine_result.disabled:
            next_action_display.append(f"  Status: Disabled - {next_action_engine_result.reason}")
    else:
        next_action_display = [
            "NEXT SAFE ACTION",
            f"{glyph('▶', '>')} [1] {action.label}",
        ]

    lines = [
        sh.title,
        f"ID: {sh.id}",
        "",
        *workflow_rail_lines(sh, action),
        "",
        f"Current task    {sh.next_task or 'none'}",
        f"Session state   {sh.session_status}",
        f"Risk            {action.risk_class}{sep_dot()}{risk_state}",
        f"Command safety  {action.safety_class}{sep_dot()}{action.tui_exposure}",
    ]
    lines.extend([
        "",
        "ACTION PACK V1 (DRY-RUN)",
        f"Proposed actions: {len(sh.action_pack_v1)}",
    ])
    
    for i, ap_action in enumerate(sh.action_pack_v1, start=1):
        status_label = f"[{ap_action.get('status')}]"
        aid = ap_action.get("action_id")
        lines.append(f"[{i}] {ap_action.get('title')} {status_label}")
        lines.append(f"    ID: {aid} {sep_dot()} {ap_action.get('action_type')}")
        lines.append(f"    Safety: {ap_action.get('safety_class')}")
        if ap_action.get("warnings"):
            lines.append(f"    [WARN] {', '.join(ap_action.get('warnings'))}")
        
        # Confirmation commands
        if ap_action.get("requires_confirmation"):
            lines.append("    [CONFIRMATION CLI-ONLY IN V1]")
            lines.append(f"    Preview: ws learning-confirm {sh.id} --action-id {aid} --dry-run")
            lines.append(f"    Apply:   ws learning-confirm {sh.id} --action-id {aid} --confirm")

    if sh.ledger_v1:
        lines.extend([
            "",
            "RECENT CONFIRMATIONS (LEDGER V1)",
        ])
        for entry in reversed(sh.ledger_v1[-5:]):
            ts = entry.get("timestamp_utc", "unknown")
            etype = entry.get("confirmed_action_type", "unknown")
            lines.append(f"- {ts} {sep_dot()} {etype}")
            lines.append(f"  ID: {entry.get('confirmation_id')}")

    if sh.confirmed_artifacts_v1:
        lines.extend([
            "",
            "CONFIRMED ARTIFACTS",
        ])
        for art in sh.confirmed_artifacts_v1:
            lines.append(f"- {art}")
    elif not sh.ledger_v1:
        lines.extend([
            "",
            "RECENT CONFIRMATIONS",
            "No confirmations recorded yet.",
        ])

    if sh.latest_sync:
        ls = sh.latest_sync
        applied = len(ls.get("applied_changes", []))
        skipped = len(ls.get("skipped_changes", []))
        blocked = len(ls.get("blocked_changes", []))
        lines.extend([
            "",
            "STATE SYNC STATUS (PHASE 7B)",
            f"Latest Sync ID: {ls.get('sync_id')}",
            f"Timestamp UTC:  {ls.get('timestamp_utc')}",
            f"Status:         {ls.get('confirmation_status')}",
            f"Changes:        {applied} applied, {skipped} skipped, {blocked} blocked",
            f"Backup:         {artifact_label(ls.get('backup_path'))}",
            f"Total Backups:  {sh.backup_count}",
        ])
        if ls.get("warnings"):
            lines.append(f"Warnings:       {', '.join(ls.get('warnings'))}")
    else:
        lines.extend([
            "",
            "STATE SYNC STATUS",
            "No state synchronization recorded yet.",
        ])

    if sh.pointer_plan:
        pp = sh.pointer_plan
        status = pp.get("candidate_status", "unknown")
        lines.extend([
            "",
            "POINTER PLAN STATUS (PHASE 9A)",
            f"Candidate:      {pp.get('candidate_next_learning_task') or 'none'}",
            f"Status:         {status}",
            f"Evidence:       {pp.get('evidence_quality')}",
            f"Risk:           {pp.get('risk_level')}",
            f"Eligible 9B:    {pp.get('apply_allowed_in_phase_9b')}",
            f"Source ID:      {pp.get('source_confirmation_id')}",
        ])
        
        if status == "already_synchronized":
            lines.append("Pointer already synchronized; no pointer apply is needed.")
            
        if pp.get("blockers"):
            lines.append(f"Blockers:       {len(pp.get('blockers'))} found")
            for b in pp.get("blockers")[:2]: # Show first 2
                lines.append(f"  X {b}")
        if pp.get("warnings"):
            lines.append(f"Warnings:       {len(pp.get('warnings'))} found")
            for w in pp.get("warnings")[:2]: # Show first 2
                lines.append(f"  ! {w}")
    else:
        lines.extend([
            "",
            "POINTER PLAN STATUS",
            "No pointer plan available.",
        ])

    if sh.advancement_plan:
        ap = sh.advancement_plan
        status = ap.get("readiness_status", "unknown").upper()
        lines.extend([
            "",
            "ADVANCEMENT READINESS STATUS (PHASE 10A)",
            f"Status:         {status}",
            f"Score:          {ap.get('readiness_score')}/100",
            f"Future State:   {ap.get('proposed_future_state')}",
            f"Risk Level:     {ap.get('risk_level')}",
            f"Evidence:       {ap.get('evidence_quality')}",
            f"Eligible 10B:   {ap.get('apply_allowed_in_phase_10b')}",
        ])
        
        if status == "READY_FOR_HUMAN_REVIEW":
            lines.append("Ready for human review does not mean automatic advancement.")
            
        if ap.get("blockers"):
            lines.append(f"Blockers:       {len(ap.get('blockers'))} found")
            for b in ap.get("blockers")[:2]:
                lines.append(f"  X {b}")
        if ap.get("warnings"):
            lines.append(f"Warnings:       {len(ap.get('warnings'))} found")
            for w in ap.get("warnings")[:2]:
                lines.append(f"  ! {w}")
        if ap.get("required_human_checks"):
            lines.append(f"Checks:         {len(ap.get('required_human_checks'))} required")
            for c in ap.get("required_human_checks")[:2]:
                lines.append(f"  ? {c}")
    else:
        lines.extend([
            "",
            "ADVANCEMENT READINESS STATUS",
            "No advancement plan available.",
        ])

    if sh.latest_review_packet:
        rp = sh.latest_review_packet
        lines.extend([
            "",
            "ADVANCEMENT REVIEW PACKET (PHASE 10C)",
        ])
        if "error" in rp:
            lines.append(f"Error:          {rp['error']}")
        else:
            lines.extend([
                f"Packet ID:      {rp.get('packet_id')}",
                f"Timestamp:      {rp.get('timestamp')}",
                f"Status:         {rp.get('readiness_status')}",
                f"Score:          {rp.get('readiness_score')}",
                f"Pointer:        {rp.get('pointer_status')}",
                f"Sync:           {rp.get('sync_status')}",
                f"Checks:         {rp.get('checks_count')} found",
                f"Summary:        {rp.get('checks_summary')}",
                f"Filename:       {rp.get('filename')}",
            ])
            lines.append("Review packet is advisory.")
    else:
        lines.extend([
            "",
            "ADVANCEMENT REVIEW PACKET",
            "No review packets discovered.",
        ])

    lines.extend([
        "",
        "SYNC MANUAL ACTIONS / BLOCKERS",
        "** ADVANCEMENT REMAINS MANUAL (HIGH RISK) **",
        "** NEXT_LEARNING_TASK BLOCKED (MEDIUM RISK) **",
        "Pointer apply is not implemented in this phase.",
        "Advancement apply is not implemented in this phase.",
        "TUI packet visibility is read-only.",
    ])

    lines.extend([
        "",
        "BLOCKER",
        blocker_text(sh, action),
        "",
        *next_action_display,
    ])
    return lines


def tree_lines(root: str, child: str, leaf: str) -> list[str]:
    branch = glyph("└─", "|-")
    return [
        root,
        f"{branch} {child}",
        f"   {branch} {leaf}",
        "",
    ]


def work_map_lines(dashboard: DashboardData) -> list[str]:
    lines: list[str] = []
    sh = first_learning_stronghold(dashboard)
    if sh is not None:
        lines.extend(tree_lines("learning", sh.title, sh.current_state))

    strongholds = parse_stronghold_rows(dashboard.results["strongholds"])
    research = next((row for row in strongholds if row[0].lower() == "research"), None)
    if research:
        lines.extend(tree_lines("research", research[1], research[2]))

    feature_rows = parse_feature_rows(dashboard.results["features"])
    if feature_rows:
        _, project, title, state = feature_rows[0]
        lines.extend(tree_lines("feature", f"{project}: {title}", state))

    if not lines:
        return ["No active work map rows available."]
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def handoff_trail_lines(result: CommandResult, limit: int = 3) -> list[str]:
    rows = parse_handoff_rows(result)[:limit]
    if not rows:
        return ["No recent handoffs."]
    branch = glyph("└─", "|-")
    lines: list[str] = []
    for timestamp, owner, purpose, state in rows:
        short_ts = timestamp[-8:] if len(timestamp) >= 8 else timestamp
        lines.append(f"{short_ts}  {owner}")
        lines.append(f" {branch} {purpose}")
        lines.append(f"    {branch} {state}")
        lines.append("")
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def artifact_lineage_lines(sh: LearningStronghold | None) -> list[str]:
    if sh is None:
        return ["No learning stronghold discovered."]
    review_lane = learning_in_review_lane(sh) or bool(sh.decision_warning)
    if review_lane:
        labels = ("Review Plan", "Review Tutor", "Review Assessment", "Decision")
        paths = (
            sh.latest_review_plan,
            sh.latest_review_tutor_session,
            sh.latest_review_assessment,
            sh.latest_review_decision or sh.latest_normal_decision,
        )
    else:
        labels = ("Plan", "Tutor", "Assessment", "Decision")
        paths = (
            sh.latest_session_plan,
            sh.latest_tutor_session,
            sh.latest_assessment,
            sh.latest_normal_decision,
        )
    arrow = f" {glyph('──▶', '->')} "
    line1 = arrow.join(labels)
    markers = []
    for index, path in enumerate(paths):
        if index == 3 and sh.decision_warning:
            markers.append(f"{glyph('⚠', '!')} stale")
        elif path:
            markers.append(glyph("✓", "OK"))
        else:
            markers.append(glyph("◎", "o"))
    line2 = "      ".join(markers)
    lines = [line1, line2]
    if sh.decision_warning:
        lines.append(
            "Last known decision does not align with the active learning session."
        )
    else:
        lines.append("Decision lineage aligns with active session state.")
    return lines


def compact_command_stream_lines(dashboard: DashboardData, *, limit: int = 2) -> list[str]:
    rows = dashboard.command_log[-limit:]
    rendered: list[str] = []
    status_icon_map = {
        "OK": glyph("✓", "OK"),
        "FAIL": glyph("✕", "!!"),
        "TIMEOUT": glyph("⏱", "T/O"),
        "CHECK": glyph("⚠", "CHK"),
    }
    for row in rows:
        match = re.match(r"\[(\d{2}:\d{2}:\d{2})\]\s+([A-Z]+)\s+(.+)", row.strip())
        if not match:
            rendered.append(row.strip())
            continue
        ts, status, command = match.groups()
        marker = status_icon_map.get(status, status)
        rendered.append(f"{ts}  {marker}  {command}")
    if not rendered:
        rendered.append("No status reads recorded.")
    execution = dashboard.execution_log[-1] if dashboard.execution_log else "Executions: none recorded in plain mode."
    rendered.extend(["", execution])
    return rendered


def artifact_highlight_lines(sh: LearningStronghold | None, *, limit: int = 4) -> list[str]:
    if sh is None:
        return ["No learning stronghold discovered."]
    return learning_artifact_highlights(sh, limit=limit)


def system_details_lines(dashboard: DashboardData) -> list[str]:
    readiness = dashboard.results["readiness"]
    lines = ["Readiness summary:", readiness_summary_line(readiness), ""]
    lines.append("Readiness details:")
    lines.extend(readiness_detail_lines(readiness) or ["(no readiness output)"])
    lines.append("")
    lines.append("Agent hygiene summary:")
    lines.append(agent_hygiene_summary_line(dashboard.results["agent_hygiene"]))
    lines.append("")
    lines.append("Agent hygiene details:")
    lines.extend(readiness_detail_lines(dashboard.results["agent_hygiene"]) or ["(no hygiene output)"])
    lines.append("")
    lines.append("Command safety registry:")
    lines.extend(command_safety_summary_lines())
    return lines


def footer_controls(screen: str, show_backend_command: bool) -> list[str]:
    if screen == "home":
        return [
            "[1] Next safe action   [2] Learning   [3] Artifacts   [4] System",
            "[r] Refresh            [?] Help       [q] Quit",
        ]
    if screen == "learning":
        toggle = "[5] Hide command" if show_backend_command else "[5] Show command"
        return [
            f"[1] Run safe dry-run   [2] Artifact browser   [3] Plan   [4] Assessment   {toggle}",
            "[6] Refresh            [0] Home              [?] Help   [q] Quit",
        ]
    if screen == "artifacts":
        return [
            "[1] Artifact browser   [2] View review plan   [3] View review assessment   [4] View decision",
            "[r] Refresh            [0] Home               [?] Help                     [q] Quit",
        ]
    return [
        "[r] Refresh            [0] Home               [?] Help       [q] Quit",
    ]


def compose_home_screen(dashboard: DashboardData, spec: LayoutSpec) -> list[str]:
    from next_action import compute_next_safe_action
    manifest = load_command_safety_manifest()
    next_action_result = compute_next_safe_action(dashboard, manifest, COMMAND_SAFETY_POLICY_MODE)
    
    lines: list[str] = []
    width = spec.width
    machine_lines = machine_card_lines(dashboard)
    safety_lines = safety_card_lines(dashboard)

    if can_render_side_by_side(
        total_width=width,
        left_title="MACHINE",
        left_lines=machine_lines,
        right_title="SAFETY ENVELOPE",
        right_lines=safety_lines,
    ):
        left_w, right_w = side_by_side_widths(width, gap=1)
        machine = render_card("MACHINE", machine_lines, left_w)
        safety = render_card("SAFETY ENVELOPE", safety_lines, right_w)
        lines.extend(merge_card_columns(machine, safety, left_width=left_w, right_width=right_w))
    else:
        lines.extend(render_card("MACHINE", machine_lines, width))
        lines.append("")
        lines.extend(render_card("SAFETY ENVELOPE", safety_lines, width))

    lines.append("")
    if first_learning_stronghold(dashboard) is None:
        lines.extend(render_card("ACTIVE STRONGHOLD", [
            "No learning stronghold discovered.",
            "",
            "NEXT SAFE ACTION",
            f"- {next_action_result.label}",
            f"  Reason: {next_action_result.reason}",
            f"  Status: {'Enabled' if next_action_result.enabled else 'Disabled'}"
        ], width))
    else:
        lines.extend(render_card("ACTIVE STRONGHOLD", active_stronghold_lines(first_learning_stronghold(dashboard), next_action_result), width))
    lines.append("")

    work_lines = work_map_lines(dashboard)
    handoff_lines = handoff_trail_lines(dashboard.results["handoffs"], limit=3)
    if can_render_side_by_side(
        total_width=width,
        left_title="WORK MAP",
        left_lines=work_lines,
        right_title="HANDOFF TRAIL",
        right_lines=handoff_lines,
    ):
        left_w, right_w = side_by_side_widths(width, gap=1)
        work = render_card("WORK MAP", work_lines, left_w)
        handoffs = render_card("HANDOFF TRAIL", handoff_lines, right_w)
        lines.extend(merge_card_columns(work, handoffs, left_width=left_w, right_width=right_w))
    else:
        lines.extend(render_card("WORK MAP", work_lines, width))
        lines.append("")
        lines.extend(render_card("HANDOFF TRAIL", handoff_lines, width))

    lines.append("")
    lines.extend(render_card("ARTIFACT LINEAGE", artifact_lineage_lines(first_learning_stronghold(dashboard)), width))
    lines.append("")
    lines.extend(render_card("COMMAND STREAM", compact_command_stream_lines(dashboard, limit=2), width))
    return lines


def compose_learning_screen(dashboard: DashboardData, spec: LayoutSpec, *, show_backend_command: bool) -> list[str]:
    from next_action import compute_next_safe_action
    manifest = load_command_safety_manifest()
    next_action_result = compute_next_safe_action(dashboard, manifest, COMMAND_SAFETY_POLICY_MODE)
    
    width = spec.width
    sh = first_learning_stronghold(dashboard)
    lines: list[str] = []
    
    if sh is None:
        lines.extend(render_card("LEARNING", [
            "No learning stronghold discovered.",
            "",
            "NEXT SAFE ACTION",
            f"- {next_action_result.label}",
            f"  Reason: {next_action_result.reason}",
            f"  Status: {'Enabled' if next_action_result.enabled else 'Disabled'}"
        ], width))
    else:
        lines.extend(render_card("LEARNING", active_stronghold_lines(sh, next_action_result), width))
    lines.append("")

    if sh is None:
        lines.extend(render_card("SAFE ACTIONS", ["No learning stronghold discovered."], width))
    else:
        action = sh.compute_next_action()
        action_lines = [
            "Recommended Next",
            f"- {action.label}",
            f"Risk/Status: {action.risk_class}{sep_dot()}{'READY' if action.executable else 'WARN'}",
            f"Safety class: {action.safety_class}",
            f"TUI exposure: {action.tui_exposure}{sep_dot()}confirmation {action.confirmation}",
            f"Current task: {sh.next_task or 'none'}",
            f"Session state: {sh.session_status}",
            "Backend command: hidden by default.",
        ]
        if action.warning_label:
            action_lines.append(f"Warning: {action.warning_label}")
        if show_backend_command:
            action_lines.extend(["", "Backend Command:", action.command_text])
        else:
            action_lines.append("Press [5] to reveal backend command drawer.")
        action_lines.extend(
            [
                "",
                "[1] Run safe dry-run" if action.executable else f"[1 disabled] {human_disabled_reason(action)}",
                "[2] Open artifact browser",
                "[3] View latest plan",
                "[4] View latest assessment",
                "[p] Open Action Pack Previewer",
                "[5] Hide backend command" if show_backend_command else "[5] Show backend command",
                "[6] Refresh",
                "[0] Home",
            ]
        )
        lines.extend(render_card("SAFE ACTIONS", action_lines, width))

    lines.append("")
    lines.extend(render_card("ARTIFACT HIGHLIGHTS", artifact_highlight_lines(sh, limit=4), width))
    lines.append("")
    lines.extend(render_card("COMMAND STREAM", compact_command_stream_lines(dashboard, limit=2), width))
    return lines


def compose_artifacts_screen(dashboard: DashboardData, spec: LayoutSpec) -> list[str]:
    width = spec.width
    sh = first_learning_stronghold(dashboard)
    lines: list[str] = []
    lines.extend(render_card("ARTIFACT LINEAGE", artifact_lineage_lines(sh), width))
    lines.append("")
    lines.extend(render_card("REVIEW ARTIFACTS", artifact_highlight_lines(sh, limit=4), width))
    lines.append("")
    lines.extend(render_card("RECENT HANDOFFS", handoff_trail_lines(dashboard.results["handoffs"], limit=3), width))
    lines.append("")
    lines.extend(
        render_card(
            "ARTIFACT ACTIONS",
            [
                "[1] Open artifact browser",
                "[2] View latest review plan",
                "[3] View latest review assessment",
                "[4] View latest decision",
                "[0] Home",
            ],
            width,
        )
    )
    lines.append("")
    lines.extend(render_card("COMMAND STREAM", compact_command_stream_lines(dashboard, limit=2), width))
    return lines


def compose_system_screen(dashboard: DashboardData, spec: LayoutSpec) -> list[str]:
    from tui.next_action import compute_next_safe_action
    manifest = load_command_safety_manifest()
    
    width = spec.width
    lines: list[str] = []

    # Calculate NEXT SAFE ACTION specific to System context
    next_action_result = compute_next_safe_action(dashboard, manifest, COMMAND_SAFETY_POLICY_MODE, screen_context="system")
    
    if next_action_result.action_id == "system.manifest_missing":
        next_action_lines = [
            "NEXT SAFE ACTION",
            f"- {next_action_result.label}",
            f"  Reason: {next_action_result.reason}",
        ]
    elif next_action_result.disabled:
        next_action_lines = [
            "NEXT SAFE ACTION",
            f"- {next_action_result.label}",
            f"  Reason: {next_action_result.reason}",
            f"  Alternative: {next_action_result.description}",
        ]
    else:
        cmd_safety = get_command_safety(next_action_result.command) if next_action_result.command else None
        scope = getattr(cmd_safety, 'report_write_scope', 'unknown') if cmd_safety else "unknown"
        warning = cmd_safety.warning_label if cmd_safety else ""
        
        next_action_lines = [
            "NEXT SAFE ACTION",
            f"{glyph('▶', '>')} [1] {next_action_result.label}",
            f"  Safety: {next_action_result.safety_class} {sep_dot()} scope={scope}",
            f"  Warning: {warning}",
            f"  Confirmation: {next_action_result.confirmation_required}",
        ]
        
    next_action_lines.extend([
        "",
        "No-write check:",
        "  python scripts\\check_local_safety.py",
        "",
        "Readiness check:",
        "  ws ready",
        "  Writes local readiness/status reports.",
    ])

    machine_lines = machine_card_lines(dashboard)
    safety_lines = safety_card_lines(dashboard)

    if can_render_side_by_side(
        total_width=width,
        left_title="MACHINE",
        left_lines=machine_lines,
        right_title="SAFETY ENVELOPE",
        right_lines=safety_lines,
    ):
        left_w, right_w = side_by_side_widths(width, gap=1)
        machine = render_card("MACHINE", machine_lines, left_w)
        safety = render_card("SAFETY ENVELOPE", safety_lines, right_w)
        lines.extend(merge_card_columns(machine, safety, left_width=left_w, right_width=right_w))
    else:
        lines.extend(render_card("MACHINE", machine_lines, width))
        lines.append("")
        lines.extend(render_card("SAFETY ENVELOPE", safety_lines, width))

    lines.append("")
    lines.extend(render_card("SYSTEM COMMANDS", next_action_lines, width))
    lines.append("")
    lines.extend(render_card("SYSTEM DETAILS", system_details_lines(dashboard), width))
    lines.append("")
    lines.extend(render_card("COMMAND STREAM", compact_command_stream_lines(dashboard, limit=2), width))
    return lines


def render_cockpit_screen(
    dashboard: DashboardData,
    *,
    screen: str,
    show_backend_command: bool,
    notice: str | None = None,
) -> str:
    spec = layout_spec()
    width = spec.width
    lines: list[str] = []
    lines.extend(render_banner(dashboard, width))
    if notice:
        lines.append("")
        lines.extend(render_card("NOTICE", [notice], width))
    lines.append("")

    if screen == "learning":
        lines.extend(compose_learning_screen(dashboard, spec, show_backend_command=show_backend_command))
    elif screen == "artifacts":
        lines.extend(compose_artifacts_screen(dashboard, spec))
    elif screen in {"system", "health"}:
        lines.extend(compose_system_screen(dashboard, spec))
    else:
        lines.extend(compose_home_screen(dashboard, spec))

    lines.append("")
    for footer in footer_controls("system" if screen == "health" else screen, show_backend_command):
        lines.append(colorize_semantic(fit_text(footer, width)))
    lines.append(colorize_semantic(fit_text(snapshot_footer_line(dashboard), width)))
    safe_lines = enforce_max_width(lines, width)
    return "\n".join(safe_lines).rstrip() + "\n"


def render_snapshot(data: DashboardData) -> str:
    return render_cockpit_screen(
        data,
        screen="home",
        show_backend_command=False,
    )


def print_textual_missing_message() -> None:
    print("Textual is not installed. Install later with the approved dependency process.")


def recent_learning_events(sh: LearningStronghold | None) -> list[str]:
    if sh is None:
        return ["No learning stronghold discovered."]
    loop_log = sh.path / "loop_log.md"
    if not loop_log.is_file():
        return ["No loop log found."]
    lines = [line.strip() for line in loop_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    return lines[-4:] or ["No recent learning events."]


def human_disabled_reason(action: LearningAction) -> str:
    if action.safety_class in HIDDEN_SAFETY_CLASSES:
        return f"Hidden by command safety manifest: {action.safety_class}."
    if action.tui_exposure in {"hidden", "admin_only"}:
        return f"Not exposed in this TUI mode: {action.tui_exposure}."
    if action.tui_exposure == "disabled":
        return "Command safety manifest marks this action disabled."
    if action.risk_class == "PURPLE":
        return "Requires local model execution; future phase."
    if action.label.startswith("Import"):
        return "Requires answer file picker; future phase."
    if action.label.startswith("Advance"):
        return "Requires manual approval; future phase."
    return "Requires manual command or a future phase."


def learning_in_review_lane(sh: LearningStronghold) -> bool:
    decision = str(sh.state.get("last_learning_decision", "")).upper()
    status = sh.session_status.lower()
    return "review" in status or decision == "REVIEW_CURRENT_TASK"


def learning_artifact_highlights(sh: LearningStronghold, limit: int = 4) -> list[str]:
    review_lane = learning_in_review_lane(sh)
    if review_lane:
        candidates = [
            ("Review Plan", sh.latest_review_plan),
            ("Review Tutor", sh.latest_review_tutor_session),
            ("Review Assessment", sh.latest_review_assessment),
            ("Decision", sh.latest_review_decision or sh.latest_normal_decision),
        ]
    else:
        session_status = sh.session_status.lower()
        if "answers" in session_status:
            candidates = [
                ("Plan", sh.latest_session_plan),
                ("Tutor", sh.latest_tutor_session),
                ("Answers", sh.latest_imported_answers),
                ("Decision", sh.latest_normal_decision),
            ]
        else:
            candidates = [
                ("Plan", sh.latest_session_plan),
                ("Tutor", sh.latest_tutor_session),
                ("Assessment", sh.latest_assessment),
                ("Decision", sh.latest_normal_decision),
            ]
    lines = [f"{label}: {artifact_label(path)}" for label, path in candidates]
    return lines[:limit]


def snapshot_footer_line(dashboard: DashboardData) -> str:
    hygiene = parse_agent_hygiene(dashboard.results["agent_hygiene"])
    hygiene_status = agent_hygiene_status(hygiene, dashboard.results["agent_hygiene"])
    sep = sep_dot()
    branch_display = operator_branch_value(hygiene.get("branch", "unknown"))
    return (
        f"[{SAFETY_MODE}{sep}SAFE_DRY_RUN] "
        f"{branch_display}{sep}"
        f"agent hygiene {hygiene_status}{sep}q quit{sep}? help"
    )


def plain_footer_line(dashboard: DashboardData) -> str:
    return snapshot_footer_line(dashboard)


def provenance_lines(sh: LearningStronghold) -> list[str]:
    ico = icons()
    if not sh.latest_tutor_session or not sh.latest_imported_answers:
        return [f"{ico.warning} No linked answers imported for the current session."]
    linked = sh.to_win(sh.linked_tutor_session)
    current = sh.to_win(sh.latest_tutor_session)
    if linked == current and sh.import_success:
        return [f"{ico.linked} Answers match the current tutor session."]
    return [f"{ico.warning} Answers are not linked to the current tutor session."]


def render_plain_screen(
    dashboard: DashboardData,
    *,
    screen: str,
    show_backend_command: bool,
    notice: str | None = None,
) -> str:
    return render_cockpit_screen(
        dashboard,
        screen=screen,
        show_backend_command=show_backend_command,
        notice=notice,
    )


def path_is_within(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def read_learning_artifact(sh: LearningStronghold, artifact_path: str | None) -> tuple[Path, str]:
    if not artifact_path:
        raise ValueError("No artifact is available for this slot.")

    candidate = Path(artifact_path).resolve()
    root = sh.path.resolve()
    if not candidate.is_file() or candidate.suffix.lower() != ".md":
        raise ValueError("Selected artifact is not a readable markdown file.")
    if not path_is_within(root, candidate):
        raise ValueError("Selected artifact is outside the learning stronghold.")
    lowered_parts = {part.lower() for part in candidate.parts}
    if lowered_parts.intersection(UNSAFE_ARTIFACT_PARTS):
        raise ValueError("Selected artifact resolves into a blocked unsafe path.")
    return candidate, candidate.read_text(encoding="utf-8")


def render_learning_artifact_menu(sh: LearningStronghold, notice: str | None = None) -> str:
    spec = layout_spec()
    artifacts = learning_artifact_catalog(sh)
    lines = []
    if notice:
        lines.extend([f"Notice: {notice}", ""])
    for index, artifact in enumerate(artifacts, start=1):
        status = "exists" if artifact.exists else "missing"
        lines.append(
            f"[{index:>2}] {artifact.label} | {status} | {artifact.relative_path} | "
            f"{format_artifact_timestamp(artifact.timestamp)}"
        )
    lines.extend(
        [
            "",
            "Select an existing artifact by number.",
            "Copy path: read the displayed relative path and copy manually if needed.",
            "[0] Back",
        ]
    )
    return "\n".join(panel("Artifact Browser", lines, spec.width))


def render_artifact_page(
    artifact: LearningArtifact,
    path: Path,
    body_lines: list[str],
    *,
    page_index: int,
    page_size: int,
    show_all: bool,
) -> str:
    spec = layout_spec()
    total_lines = len(body_lines)
    if show_all:
        start = 0
        end = total_lines
        page_label = "all lines"
    else:
        start = page_index * page_size
        end = min(start + page_size, total_lines)
        page_count = max((total_lines + page_size - 1) // page_size, 1)
        page_label = f"page {page_index + 1}/{page_count}"
    visible = body_lines[start:end] or ["(artifact is empty)"]
    header = panel(
        f"Artifact Viewer - {artifact.label}",
        [
            f"Path: {path}",
            f"Relative path: {artifact.relative_path}",
            f"Timestamp: {format_artifact_timestamp(artifact.timestamp)}",
            f"Showing: {page_label} | lines {start + 1}-{end if end else 0} of {total_lines}",
            "Copy path manually from the Path line above.",
        ],
        spec.width,
    )
    numbered = [
        f"{line_number:>4}: {line}"
        for line_number, line in enumerate(visible, start=start + 1)
    ]
    controls = panel(
        "Viewer Controls",
        ["n next page | p previous page | a show all | b back"],
        spec.width,
    )
    return "\n".join([*header, *numbered, *controls])


def render_learning_action_pack_menu(sh: LearningStronghold, notice: str | None = None) -> str:
    spec = layout_spec()
    lines = []
    if notice:
        lines.extend([f"Notice: {notice}", ""])
    
    lines.append(f"Proposed actions for {sh.title}: {len(sh.action_pack_v1)}")
    lines.append("")
    
    for i, action in enumerate(sh.action_pack_v1, start=1):
        lines.append(f"[{i:>2}] {action.get('title')} ({action.get('action_id')})")
    
    lines.extend([
        "",
        "Select an action number to trigger a DRY-RUN preview.",
        "[0] Back",
    ])
    return "\n".join(panel("Action Pack Previewer", lines, spec.width))


def run_learning_confirmation_command(sh: LearningStronghold, action_id: str, mode: str) -> dict:
    """
    Run the learning confirmation core script with strict guards.
    mode: 'preview' (dry-run) or 'apply' (confirm)
    """
    if mode not in ("preview", "apply"):
        return {"error": f"Invalid confirmation mode: {mode}", "status": "ERROR"}

    command_args = [sys.executable, str(WS_HOME / "scripts" / "learning_confirmation_core.py"), sh.id, "--action-id", action_id, "--json"]
    
    if mode == "preview":
        command_args.append("--dry-run")
    else:
        command_args.append("--confirm")

    # HARD GUARD Validation
    unsafe_chars = (';', '&', '|', '>', '<', '`', '$', '(', ')', '[', ']', '{', '}', '*', '?', '~')
    blocked_flags = ("--confirm-sync", "--repair-ledger", "--apply", "--confirm-pointer", "--advance", "--confirm-advancement", "--create-packet") 
    
    for arg in command_args:
        # Reject shell metacharacters in IDs and all args
        if any(c in str(arg) for c in unsafe_chars):
             return {"error": f"CRITICAL: Unsafe characters detected in argument '{arg}'.", "status": "BLOCKED"}
        
        # Mode guards for state synchronization (Read-only in Phase 8)
        if any(flag == str(arg) for flag in blocked_flags):
             return {"error": f"CRITICAL: State-sync write flag '{arg}' detected. Execution blocked.", "status": "BLOCKED"}
        
        if mode == "preview" and "--confirm" in str(arg):
            return {"error": "CRITICAL: --confirm detected in preview command. Execution blocked.", "status": "BLOCKED"}
        if mode == "apply" and "--dry-run" in str(arg):
            return {"error": "CRITICAL: --dry-run detected in apply command. Execution blocked.", "status": "BLOCKED"}
    
    try:
        res = subprocess.run(
            command_args,
            cwd=WS_HOME,
            capture_output=True,
            text=True,
            timeout=15,
            env={"WS_HOME": str(WS_HOME), "PYTHONDONTWRITEBYTECODE": "1"}
        )
        if res.returncode == 0:
            try:
                return json.loads(res.stdout)
            except json.JSONDecodeError:
                return {"error": f"Invalid JSON output from core: {res.stdout[:200]}", "status": "FAILED"}
        else:
            stderr_out = normalize_subprocess_text(res.stderr)
            return {"error": f"Command failed: {stderr_out}", "status": "FAILED"}
    except subprocess.TimeoutExpired:
        return {"error": "Confirmation command timed out.", "status": "TIMEOUT"}
    except Exception as e:
        return {"error": str(e), "status": "ERROR"}


def run_dry_run_preview(sh: LearningStronghold, action_id: str) -> dict:
    return run_learning_confirmation_command(sh, action_id, "preview")


def verify_apply_success(sh: LearningStronghold, action_id: str, pre_ledger_count: int, pre_artifacts: set[str], pre_state_mtime: float | None) -> dict:
    """Verify that exactly one ledger entry and one artifact were created, and state.json was not touched."""
    # Re-discover to get fresh data
    strongholds = discover_learning_strongholds()
    sh_fresh = next((s for s in strongholds if s.id == sh.id), None)
    
    if not sh_fresh:
        return {"error": "Stronghold lost during verification.", "status": "VERIFY_FAILED"}
        
    post_ledger_count = len(sh_fresh.ledger_v1)
    post_artifacts = set(sh_fresh.confirmed_artifacts_v1)
    
    state_file = sh_fresh.path / "state.json"
    post_state_mtime = state_file.stat().st_mtime if state_file.is_file() else None
    
    errors = []
    if post_ledger_count != pre_ledger_count + 1:
        errors.append(f"Ledger count mismatch: expected {pre_ledger_count + 1}, got {post_ledger_count}")
    
    new_artifacts = post_artifacts - pre_artifacts
    if len(new_artifacts) != 1:
        errors.append(f"Artifact count mismatch: expected 1 new file, got {len(new_artifacts)}")
        
    latest_entry = sh_fresh.ledger_v1[-1] if sh_fresh.ledger_v1 else {}
    if latest_entry.get("original_action_id") != action_id:
        errors.append(f"Latest ledger entry ID mismatch: expected {action_id}, got {latest_entry.get('original_action_id')}")
        
    if latest_entry.get("confirmation_status") != "CONFIRMED_APPLIED":
        errors.append(f"Latest ledger entry status mismatch: {latest_entry.get('confirmation_status')}")
        
    if pre_state_mtime is not None and post_state_mtime != pre_state_mtime:
        errors.append(f"CRITICAL: state.json was mutated (mtime changed from {pre_state_mtime} to {post_state_mtime})")

    if errors:
        return {"error": "; ".join(errors), "status": "VERIFY_FAILED"}
        
    return {
        "status": "SUCCESS",
        "confirmation_id": latest_entry.get("confirmation_id"),
        "timestamp_utc": latest_entry.get("timestamp_utc"),
        "original_action_id": latest_entry.get("original_action_id"),
        "confirmed_action_type": latest_entry.get("confirmed_action_type"),
        "artifact_path": next(iter(new_artifacts)) if new_artifacts else "unknown"
    }


def run_guarded_apply(sh: LearningStronghold, action_id: str) -> dict:
    """Perform pre-verification, run --confirm, and post-verification."""
    # 1. Pre-verification
    pre_ledger_count = len(sh.ledger_v1)
    pre_artifacts = set(sh.confirmed_artifacts_v1)
    state_file = sh.path / "state.json"
    pre_state_mtime = state_file.stat().st_mtime if state_file.is_file() else None
    
    # 2. Run Apply
    print(f"Applying action {action_id}...")
    result = run_learning_confirmation_command(sh, action_id, "apply")
    
    if "error" in result:
        return result
        
    # 3. Post-verification
    return verify_apply_success(sh, action_id, pre_ledger_count, pre_artifacts, pre_state_mtime)


def show_learning_action_confirm_prompt(sh: LearningStronghold, action_id: str) -> str | None:
    """Required two-step typed confirmation."""
    expected = f"APPLY {action_id}"
    print(f"\nTo apply this action, type exactly: {expected}")
    phrase = input("confirmation> ").strip()
    
    if phrase != expected:
        print("\nConfirmation cancelled: phrase did not match.")
        input("Press Enter to continue...")
        return None
        
    result = run_guarded_apply(sh, action_id)
    
    spec = layout_spec()
    width = spec.width
    
    if result.get("status") == "SUCCESS":
        lines = [
            f"Successfully confirmed action {action_id}",
            "",
            f"Confirmation ID:  {result.get('confirmation_id')}",
            f"Timestamp:        {result.get('timestamp_utc')}",
            f"Type:             {result.get('confirmed_action_type')}",
            f"Artifact:         {result.get('artifact_path')}",
            "",
            "SAFETY NOTE: Core learning state was not mutated.",
        ]
        print("\n" + "\n".join(panel("Apply Success", lines, width)))
        # Return a notice so the dashboard refreshes
        return f"Applied {action_id} successfully."
    else:
        print("\n" + "\n".join(panel("Apply Error", [result.get("error", "Unknown error")], width)))
        input("\nPress Enter to continue...")
        return None


def show_learning_action_pack_preview(sh: LearningStronghold, ap_action: dict) -> str | None:
    action_id = ap_action.get("action_id")
    print(f"\nTriggering preview for {action_id}...")
    result = run_dry_run_preview(sh, action_id)
    
    spec = layout_spec()
    width = spec.width
    
    if "error" in result:
        print("\n" + "\n".join(panel("Preview Error", [result["error"]], width)))
        input("\nPress Enter to continue...")
        return None
        
    audit = result.get("proposed_audit_record", {})
    lines = [
        f"Action ID:      {audit.get('original_action_id')}",
        f"Original Type:  {audit.get('original_action_type')}",
        f"Confirmed Type: {audit.get('confirmed_action_type')}",
        f"Title:          {audit.get('title')}",
        f"Rationale:      {audit.get('rationale')}",
        "",
        f"Proposed Effect: {audit.get('proposed_effect')}",
        f"Confirmed Effect: {audit.get('confirmed_effect')}",
        "",
        f"Safety Class:   {audit.get('safety_class')}",
        f"Status Preview: {audit.get('confirmation_status')}",
        "",
        f"Target Ledger:   {result.get('ledger_path', 'learning_confirmations.jsonl')}",
        f"Target Artifact: {result.get('artifact_path')}",
        "",
        "SAFETY NOTE:",
        "TUI preview is read-only. To apply, run the guarded CLI --confirm",
        "command manually after reviewing the preview.",
    ]
    
    if audit.get("warnings"):
        lines.extend(["", "WARNINGS:", *audit.get("warnings")])
        
    print("\n" + "\n".join(panel(f"Confirmation Preview - {action_id}", lines, width)))
    
    if sh.has_duplicate_confirmation(action_id):
        print("\nAction already confirmed; duplicate TUI apply is blocked in v1.")
        input("Press Enter to return to menu...")
        return None

    choice = input("\n[a] Apply this action | [any other] Return to menu> ").strip().lower()
    if choice == "a":
        return show_learning_action_confirm_prompt(sh, action_id)
    
    return None


def show_learning_action_pack_menu(sh: LearningStronghold) -> str | None:
    current_notice: str | None = None
    while True:
        print()
        print(render_learning_action_pack_menu(sh, current_notice))
        current_notice = None
        choice = input("action pack menu> ").strip().lower()
        if choice == "0":
            return None
        if not choice.isdigit():
            current_notice = "Unknown option. Choose an action number or 0 to go back."
            continue
        index = int(choice)
        if index < 1 or index > len(sh.action_pack_v1):
            current_notice = "Action selection is out of range."
            continue
        ap_action = sh.action_pack_v1[index - 1]
        current_notice = show_learning_action_pack_preview(sh, ap_action)


def show_learning_artifact(sh: LearningStronghold, artifact: LearningArtifact | None) -> str | None:
    if artifact is None:
        return "No artifact is available for this slot."
    try:
        path, body = read_learning_artifact(sh, artifact.path)
    except ValueError as exc:
        return str(exc)

    body_lines = body.splitlines()
    if not body_lines:
        body_lines = ["(artifact is empty)"]
    page_index = 0
    page_size = 80
    show_all = False
    page_count = max((len(body_lines) + page_size - 1) // page_size, 1)
    notice: str | None = None

    while True:
        if notice:
            print("\n" + "\n".join(panel("Notice", [notice], layout_spec().width)))
            notice = None
        print()
        print(
            render_artifact_page(
                artifact,
                path,
                body_lines,
                page_index=page_index,
                page_size=page_size,
                show_all=show_all,
            )
        )
        choice = input("artifact viewer [n next, p previous, a all, b back]> ").strip().lower()
        if choice == "b":
            return None
        if choice == "a":
            show_all = True
            continue
        if choice == "n":
            if show_all:
                show_all = False
                page_index = min(1, page_count - 1)
                continue
            if page_index + 1 >= page_count:
                notice = "Already at the last page."
                continue
            page_index += 1
            continue
        if choice == "p":
            if show_all:
                show_all = False
                page_index = 0
                continue
            if page_index == 0:
                notice = "Already at the first page."
                continue
            page_index -= 1
            continue
        notice = "Unknown option. Use n, p, a, or b."


def show_learning_artifact_menu(sh: LearningStronghold) -> str | None:
    current_notice: str | None = None
    while True:
        artifacts = learning_artifact_catalog(sh)
        print()
        print(render_learning_artifact_menu(sh, current_notice))
        current_notice = None
        choice = input("artifact menu> ").strip().lower()
        if choice == "0":
            return None
        if not choice.isdigit():
            current_notice = "Unknown option. Choose an artifact number or 0 to go back."
            continue
        index = int(choice)
        if index < 1 or index > len(artifacts):
            current_notice = "Artifact selection is out of range."
            continue
        artifact = artifacts[index - 1]
        if not artifact.exists:
            current_notice = f"{artifact.label} is missing; no file was opened."
            continue
        current_notice = show_learning_artifact(sh, artifact)


def run_plain_mode(notice: str | None = None) -> int:
    debug_log("rendering header")
    if DEBUG_ENABLED:
        print("plain mode [READ_ONLY] initializing dashboard...", flush=True)
        print("Collecting status commands with timeout protection.", flush=True)
    debug_log("collecting status")
    try:
        dashboard = collect_dashboard_data([])
    except KeyboardInterrupt:
        print("\nInterrupted during startup. Exiting plain dashboard.")
        return 130
    debug_log("entering plain loop")
    current_notice = notice
    screen = "home"
    show_backend_command = False

    while True:
        print(
            render_plain_screen(
                dashboard,
                screen=screen,
                show_backend_command=show_backend_command,
                notice=current_notice,
            ),
            end="",
        )
        current_notice = None
        try:
            debug_log("waiting for input")
            choice = input("select action> ").strip().lower()
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print("\nInterrupted. Exiting plain dashboard.")
            return 130

        if choice == "q":
            return 0
        if choice in {"h", "?"}:
            current_notice = "Help: " + " | ".join(PLAIN_CONTROLS)
            continue

        if screen == "home":
            if choice == "1":
                screen, dashboard, current_notice = execute_next_safe_action(screen, dashboard)
                continue
            if choice == "2":
                screen = "learning"
                continue
            if choice == "3":
                screen = "artifacts"
                continue
            if choice == "4":
                screen = "system"
                continue
            if choice == "r":
                dashboard = collect_dashboard_data(dashboard.command_log)
                continue
            if choice == "0":
                return 0
            current_notice = "Unknown option. Use 1, 2, 3, 4, r, ?, or q from Home."
            continue

        if screen == "learning":
            sh = first_learning_stronghold(dashboard)
            latest_plan = (
                latest_catalog_artifact(
                    sh,
                    ("latest_session_plan", "latest_review_plan"),
                )
                if sh
                else None
            )
            latest_assessment = (
                latest_catalog_artifact(
                    sh,
                    ("latest_assessment", "latest_review_assessment"),
                )
                if sh
                else None
            )
            if choice in {"0"}:
                screen = "home"
                show_backend_command = False
                continue
            if choice in {"1", "x"}:
                screen, dashboard, current_notice = execute_next_safe_action(screen, dashboard)
                continue
            if choice == "2" and sh is not None:
                current_notice = show_learning_artifact_menu(sh)
                continue
            if choice == "3" and sh is not None:
                current_notice = show_learning_artifact(sh, latest_plan)
                continue
            if choice == "4" and sh is not None:
                current_notice = show_learning_artifact(sh, latest_assessment)
                continue
            if choice == "p" and sh is not None:
                current_notice = show_learning_action_pack_menu(sh)
                continue
            if choice == "5":
                show_backend_command = not show_backend_command
                continue
            if choice in {"6", "r"}:
                dashboard = collect_dashboard_data(dashboard.command_log)
                continue
            current_notice = "Unknown option. Use the numbered actions, p, x, or 0 to go back."
            continue

        if screen == "artifacts":
            sh = first_learning_stronghold(dashboard)
            latest_review_plan = (
                artifact_by_key(sh, "latest_review_plan")
                or artifact_by_key(sh, "latest_session_plan")
                if sh
                else None
            )
            latest_review_assessment = (
                artifact_by_key(sh, "latest_review_assessment")
                or artifact_by_key(sh, "latest_assessment")
                if sh
                else None
            )
            latest_decision = (
                artifact_by_key(sh, "latest_review_decision")
                or artifact_by_key(sh, "latest_decision")
                if sh
                else None
            )
            if choice == "0":
                screen = "home"
                continue
            if choice == "1" and sh is not None:
                current_notice = show_learning_artifact_menu(sh)
                continue
            if choice == "2" and sh is not None:
                current_notice = show_learning_artifact(sh, latest_review_plan)
                continue
            if choice == "3" and sh is not None:
                current_notice = show_learning_artifact(sh, latest_review_assessment)
                continue
            if choice == "4" and sh is not None:
                current_notice = show_learning_artifact(sh, latest_decision)
                continue
            if choice == "r":
                dashboard = collect_dashboard_data(dashboard.command_log)
                continue
            current_notice = "Unknown option. Use 1, 2, 3, 4, r, 0, or q on Artifacts."
            continue

        if screen in {"system", "health"}:
            if choice == "0":
                screen = "home"
                continue
            if choice == "1":
                screen, dashboard, current_notice = execute_next_safe_action(screen, dashboard)
                continue
            if choice == "r":
                dashboard = collect_dashboard_data(dashboard.command_log)
                continue
            current_notice = "Unknown option. Use 1, r, 0, or q on System."


def execute_next_safe_action(current_screen: str, dashboard: DashboardData) -> tuple[str, DashboardData, str]:
    from tui.next_action import compute_next_safe_action
    from tui.action_dispatcher import dispatch_next_safe_action
    manifest = load_command_safety_manifest()
    
    # 1. Compute
    action = compute_next_safe_action(dashboard, manifest, COMMAND_SAFETY_POLICY_MODE, screen_context=current_screen)

    # 2. Dispatch
    # We pass None as executor so the dispatcher will handle subprocess execution for safe paths.
    # Note: the dispatcher handles navigation, blocking, disablement, and preview/execution logging.
    dispatch_result = dispatch_next_safe_action(action, COMMAND_SAFETY_POLICY_MODE, manifest, None)

    if dispatch_result.status == "navigation":
        dashboard.execution_log.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] {dispatch_result.log_line}"
        )
        return dispatch_result.navigate_to or current_screen, dashboard, dispatch_result.operator_message

    if dispatch_result.status in {"blocked", "disabled", "hidden", "error"}:
        dashboard.execution_log.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] {dispatch_result.log_line}"
        )
        return current_screen, dashboard, dispatch_result.operator_message

    # 3. Interactive Confirmation
    print("\n" + section("ACTION PREVIEW", render_action_preview(dispatch_result)))
    if dispatch_result.confirmation_required != "none":
        confirmation = input(f"Execute this {dispatch_result.safety_class} action? y/N> ").strip().lower()
        if confirmation != "y":
            return current_screen, dashboard, "Execution cancelled by operator."

    # 4. Refresh before execution to ensure no drift
    refreshed = collect_dashboard_data(dashboard.command_log)
    refreshed.execution_log = dashboard.execution_log
    
    fresh_action = compute_next_safe_action(refreshed, manifest, COMMAND_SAFETY_POLICY_MODE, screen_context=current_screen)
    if fresh_action.command != action.command or fresh_action.action_id != action.action_id:
        return current_screen, refreshed, "Recommended action changed during refresh. Execution cancelled."

    # 5. Execute
    refreshed.execution_log.append(
        f"[{datetime.now().strftime('%H:%M:%S')}] START {dispatch_result.command}"
    )
    
    # Actually run the command
    args = shlex.split(dispatch_result.command[3:])
    completed = subprocess.run(
        ["bash", str(WS_SCRIPT), *args],
        cwd=WS_HOME,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    returncode = completed.returncode
    stdout = normalize_subprocess_text(completed.stdout)
    stderr = normalize_subprocess_text(completed.stderr)

    post_run = collect_dashboard_data(refreshed.command_log)
    post_run.execution_log = refreshed.execution_log
    
    post_run.execution_log.append(
        f"[{datetime.now().strftime('%H:%M:%S')}] END {dispatch_result.command} exit={returncode}"
    )

    result_display = f"Exit code {returncode}\n\nStdout:\n{stdout}\n\nStderr:\n{stderr}"
    print("\n" + section("Action Result", result_display))
    input("\nPress Enter to return to dashboard...")

    status = "completed" if returncode == 0 else f"failed with exit code {returncode}"
    return current_screen, post_run, f"Action {status}; dashboard refreshed."


def render_action_preview(dispatch_result) -> str:
    lines = [
        dispatch_result.label,
        f"Command: {dispatch_result.command}",
        f"Safety: {dispatch_result.safety_class}",
        f"Warning: {dispatch_result.warning_label or 'none'}",
        f"Confirmation: {dispatch_result.confirmation_required}",
        f"Reason: {dispatch_result.reason}",
    ]
    return "\n".join(lines)


def build_textual_app():
    try:
        from textual.app import App, ComposeResult
        from textual.binding import Binding
        from textual.containers import Horizontal, VerticalScroll
        from textual.widgets import Footer, Header, Static
    except ImportError:
        return None

    class OperatorDashboard(App):
        CSS = """
        Screen {
            layout: vertical;
        }

        #summary {
            height: auto;
            padding: 1 2;
        }

        #content {
            height: 1fr;
        }

        .column {
            width: 1fr;
            padding: 0 1 1 1;
        }

        .panel {
            border: solid $accent;
            margin: 0 0 1 0;
            padding: 1;
        }

        #help {
            display: none;
            border: solid $warning;
            padding: 1;
            margin: 0 1 1 1;
        }
        """

        BINDINGS = [
            Binding("r", "refresh_dashboard", "Refresh"),
            Binding("q", "quit", "Quit"),
            Binding("?", "toggle_help", "Help"),
        ]

        def __init__(self) -> None:
            super().__init__()
            self.dashboard = collect_dashboard_data([])

        def compose(self) -> ComposeResult:
            yield Header()
            yield Static(self.summary_text(), id="summary")
            with Horizontal(id="content"):
                with VerticalScroll(classes="column"):
                    yield Static(
                        self.dashboard.results["readiness"].display_text,
                        id="readiness",
                        classes="panel",
                    )
                    yield Static(
                        self.dashboard.results["strongholds"].display_text,
                        id="strongholds",
                        classes="panel",
                    )
                    yield Static(
                        self.dashboard.results["features"].display_text,
                        id="features",
                        classes="panel",
                    )
                with VerticalScroll(classes="column"):
                    yield Static(
                        self.dashboard.results["handoffs"].display_text,
                        id="handoffs",
                        classes="panel",
                    )
                    yield Static(
                        self.dashboard.results["agent_hygiene"].display_text,
                        id="agent-hygiene",
                        classes="panel",
                    )
                    yield Static(self.command_log_text(), id="command-log", classes="panel")
            yield Static(
                "\n".join(
                    [
                        "Help",
                        "r refresh dashboard",
                        "q quit",
                        "? toggle help",
                        "",
                        *DISABLED_ACTIONS,
                    ]
                ),
                id="help",
            )
            yield Footer()

        def summary_text(self) -> str:
            disabled = " | ".join(DISABLED_ACTIONS)
            return (
                f"Safety mode: {SAFETY_MODE} | "
                f"command policy: {COMMAND_SAFETY_POLICY_MODE} | "
                f"manifest: {manifest_status_line()} | "
                f"{disabled}"
            )

        def command_log_text(self) -> str:
            return "Command Log\n" + "\n".join(self.dashboard.command_log)

        def action_refresh_dashboard(self) -> None:
            self.dashboard = collect_dashboard_data(self.dashboard.command_log)
            self.query_one("#summary", Static).update(self.summary_text())
            self.query_one("#readiness", Static).update(
                self.dashboard.results["readiness"].display_text
            )
            self.query_one("#strongholds", Static).update(
                self.dashboard.results["strongholds"].display_text
            )
            self.query_one("#features", Static).update(
                self.dashboard.results["features"].display_text
            )
            self.query_one("#handoffs", Static).update(
                self.dashboard.results["handoffs"].display_text
            )
            self.query_one("#agent-hygiene", Static).update(
                self.dashboard.results["agent_hygiene"].display_text
            )
            self.query_one("#command-log", Static).update(self.command_log_text())

        def action_toggle_help(self) -> None:
            help_widget = self.query_one("#help", Static)
            help_widget.styles.display = (
                "block" if help_widget.styles.display == "none" else "none"
            )

    return OperatorDashboard


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only workstation operator dashboard")
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="disable ANSI colors even when output is a TTY",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--snapshot",
        action="store_true",
        help="print the read-only dashboard as plain text and exit",
    )
    mode_group.add_argument(
        "--plain",
        action="store_true",
        help="launch the stdlib-only line-based dashboard",
    )
    mode_group.add_argument(
        "--textual",
        action="store_true",
        help="require the Textual dashboard; exit safely if Textual is unavailable",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    global FORCE_NO_COLOR
    debug_log("starting app")
    debug_log("parsing args")
    args = parse_args(argv)
    if args.no_color:
        FORCE_NO_COLOR = True
    if args.snapshot:
        debug_log("collecting status")
        data = collect_dashboard_data([])
        print(render_snapshot(data), end="")
        return 0

    if args.plain:
        debug_log("entering plain mode")
        return run_plain_mode()

    textual_app = build_textual_app()
    if args.textual:
        if textual_app is None:
            print_textual_missing_message()
            return 1
        textual_app().run()
        return 0

    if textual_app is None:
        return run_plain_mode("Textual is not installed. Falling back to plain mode.")

    textual_app().run()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
        sys.exit(130)

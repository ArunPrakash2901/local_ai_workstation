#!/bin/bash
set -euo pipefail

WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
MODEL_HOME="${MODEL_HOME:-/mnt/d/ollama/models}"
if [ -f "$WS_HOME/scripts/ws_env.sh" ]; then
    source "$WS_HOME/scripts/ws_env.sh"
fi
WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
MODEL_HOME="${MODEL_HOME:-/mnt/d/ollama/models}"

PROJECT_KEY=${1:-}
TASK_FILE=${2:-}
shift 2 || true

if [ -z "$PROJECT_KEY" ] || [ -z "$TASK_FILE" ]; then
    echo "Usage: ws auto <project_key> <task_file> [flags]"
    exit 1
fi

TASK_FILE=${TASK_FILE//\\//}
if [[ "$TASK_FILE" =~ ^([A-Za-z]):/(.*)$ ]]; then
    drive=$(echo "${BASH_REMATCH[1]}" | tr 'A-Z' 'a-z')
    TASK_FILE="/mnt/$drive/${BASH_REMATCH[2]}"
fi

PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"
export AUTO_PROJECT_KEY="$PROJECT_KEY"
export AUTO_TASK_FILE="$TASK_FILE"

"$PYTHON" - "$@" <<'PY'
import argparse
import difflib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
import tempfile
import traceback
from datetime import datetime
from pathlib import Path

import yaml

ws_home = Path(os.environ.get("WS_HOME", "/mnt/d/_ai_brain"))
model_home = Path(os.environ.get("MODEL_HOME", "/mnt/d/ollama/models"))
project_key = os.environ.get("AUTO_PROJECT_KEY", "")
task_file_arg = os.environ.get("AUTO_TASK_FILE", "")
scripts = ws_home / "scripts"
auto_root = ws_home / "auto_runs"
auto_root.mkdir(parents=True, exist_ok=True)

parser = argparse.ArgumentParser(prog="ws auto")
parser.add_argument("--plan-only", action="store_true")
parser.add_argument("--apply", action="store_true")
parser.add_argument("--branch", action="store_true")
parser.add_argument("--max-tasks", type=int, default=1)
parser.add_argument("--max-attempts", type=int, default=2)
parser.add_argument("--max-cloud-attempts", type=int, default=1)
parser.add_argument("--max-files", type=int, default=5)
parser.add_argument("--max-minutes", type=int, default=60)
parser.add_argument("--stop-on-fail", action="store_true")
parser.add_argument("--auto-escalate", choices=["codex"], default=None)
parser.add_argument("--no-escalate", action="store_true")
parser.add_argument("--planner-profile", default="hermes_default")
parser.add_argument("--coder-profile", default="")
parser.add_argument("--reviewer-profile", default="")
parser.add_argument("--profile", default="")
parser.add_argument("--context", type=int, default=8192)
parser.add_argument("--dry-run", action="store_true")
args = parser.parse_args(sys.argv[1:])

if args.apply:
    args.plan_only = False
elif not args.plan_only:
    args.plan_only = True

if args.profile:
    args.planner_profile = args.profile
    args.coder_profile = args.profile
    args.reviewer_profile = args.profile

projects_yaml = ws_home / "registry" / "projects.yaml"
models_yaml = ws_home / "registry" / "models.yaml"
active_model_yaml = ws_home / "registry" / "active_model.yaml"
active_kv_yaml = ws_home / "registry" / "active_kv_profile.yaml"
paths_yaml = ws_home / "registry" / "paths.yaml"
current_run_dir = None

def fatal_exception_handler(exc_type, exc, tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc, tb)
        return
    target = current_run_dir
    if target is not None:
        try:
            heartbeat(target, f"internal exception: {exc_type.__name__}: {exc}")
            write_run_file(target, "status.txt", "FAILED_INTERNAL\n")
            write_run_file(target, "exception.log", "".join(traceback.format_exception(exc_type, exc, tb)))
            project_ctx = globals().get("project_dir")
            if project_ctx is not None:
                write_run_file(target, "git_status_after.md", git_status(project_ctx, run_dir=target) + "\n")
            run_cmd(["bash", str(scripts / "ws_auto_report.sh"), str(target)], timeout=30, run_dir=target, label="auto report failed internal")
        except Exception:
            pass
    sys.__excepthook__(exc_type, exc, tb)
    sys.exit(1)

sys.excepthook = fatal_exception_handler

def run_cmd(cmd, *, cwd=None, timeout=60, check=False, run_dir=None, label="command"):
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    start = time.time()
    heartbeat_every = min(15, max(timeout // 4, 5))
    output = ""
    while True:
        try:
            out, _ = proc.communicate(timeout=heartbeat_every)
            output += out or ""
            break
        except subprocess.TimeoutExpired:
            if run_dir:
                heartbeat(run_dir, f"{label} still running")
            if time.time() - start >= timeout:
                proc.kill()
                out, _ = proc.communicate()
                output += out or ""
                output += "\n[timeout exceeded]\n"
                if run_dir:
                    heartbeat(run_dir, f"{label} timed out")
                return 124, output.strip()
            continue
    if check and proc.returncode != 0:
        raise RuntimeError(output)
    if run_dir:
        heartbeat(run_dir, f"{label} completed rc={proc.returncode}")
    return proc.returncode, output.strip()

def write_text(path: Path, text: str):
    path.write_text(text, encoding="utf-8", newline="\n")

def append_text(path: Path, text: str):
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(text)

def heartbeat(run_dir: Path, message: str):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    append_text(run_dir / "heartbeat.log", f"{stamp} {message}\n")

def write_run_file(run_dir: Path, name: str, content: str):
    write_text(run_dir / name, content)

def to_wsl(path: str) -> str:
    p = path.replace("\\", "/")
    m = re.match(r"^([A-Za-z]):/(.*)$", p)
    if m:
        return f"/mnt/{m.group(1).lower()}/{m.group(2)}"
    return p

def normalize_path(path: str) -> Path:
    return Path(to_wsl(path)).resolve()

def load_yaml(path: Path):
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

projects = load_yaml(projects_yaml).get("projects", {})
models = load_yaml(models_yaml)
active_model = load_yaml(active_model_yaml)
active_kv = load_yaml(active_kv_yaml)
paths_cfg = load_yaml(paths_yaml)
task_file = normalize_path(task_file_arg)

def detect_repo(project_dir: Path, run_dir: Path | None = None):
    return (project_dir / ".git").exists() or run_cmd(["git", "-C", str(project_dir), "rev-parse", "--is-inside-work-tree"], timeout=20, run_dir=run_dir, label="git detect repo")[0] == 0

def project_meta_for(key: str):
    project = projects.get(key)
    if not project:
        raise KeyError(f"Project key not found: {key}")
    wsl_path = project.get("wsl_path", "")
    project_dir = normalize_path(wsl_path) if wsl_path else None
    graph_path = project.get("graph_path") or ""
    if graph_path and not str(graph_path).startswith("/mnt/"):
        graph_path = to_wsl(str(graph_path))
    return {
        "project_key": key,
        "display_name": project.get("display_name", key),
        "windows_path": project.get("windows_path", ""),
        "wsl_path": str(project_dir) if project_dir else "",
        "graph_path": graph_path,
        "project_type": project.get("project_type", "unknown"),
        "priority": project.get("priority", "unknown"),
        "safe_to_modify": project.get("safe_to_modify", False),
        "status": project.get("status", "unknown"),
        "notes": project.get("notes", ""),
    }

project = project_meta_for(project_key)
project_dir = Path(project["wsl_path"]) if project["wsl_path"] else Path()
if not project_dir.exists():
    print(f"Project path not found: {project_dir}")
    sys.exit(1)

if not task_file.exists():
    print(f"Task file not found: {task_file}")
    sys.exit(1)

task_text = task_file.read_text(encoding="utf-8", errors="replace")
heading_re = re.compile(r"(?m)^#{1,2}\s+Task\s+(\d+)(?:\s*[:\-]\s*|\s+)?(.*\S)?\s*$")
matches = list(heading_re.finditer(task_text))
if not matches:
    matches = [None]

def section(body: str, name: str) -> str:
    pat = re.compile(rf"(?ms)^\s*{re.escape(name)}:\s*\n(.*?)(?=^\s*[A-Za-z][A-Za-z ]*:\s*$|^#{1,2}\s+Task\s+\d+|\Z)")
    m = pat.search(body)
    return m.group(1).strip() if m else ""

def normalize_text(value: str) -> str:
    lines = [line.rstrip() for line in value.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines).strip()

def bullets(value: str, default: str = "") -> list[str]:
    value = normalize_text(value)
    if not value:
        return [default] if default else []
    out = []
    for line in value.splitlines():
        s = line.strip()
        if s:
            out.append(s[2:].strip() if s.startswith("- ") else s)
    return out or ([default] if default else [])

def slugify(value: str, fallback: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return s[:60] if s else fallback

def extract_task(match, index: int):
    if match is None:
        title = task_file.stem
        body = task_text
        task_num = 1
    else:
        task_num = int(match.group(1))
        title = (match.group(2) or "").strip(" :-.\t") or f"Task {task_num:03d}"
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) and matches[index + 1] is not None else len(task_text)
        body = task_text[start:end].strip()
    goal = normalize_text(section(body, "Goal"))
    acceptance = bullets(section(body, "Acceptance Criteria"))
    allowed = bullets(section(body, "Allowed Files"))
    denied = bullets(section(body, "Denied Files"))
    test_command = normalize_text(section(body, "Test Command"))
    risk_raw = normalize_text(section(body, "Risk")).splitlines()[0].strip().lower() if section(body, "Risk") else ""
    notes = normalize_text(section(body, "Notes"))
    source = normalize_text(section(body, "Source")) or "unknown"
    escalation = normalize_text(section(body, "Escalation")).splitlines()[0].strip().lower() if section(body, "Escalation") else "none"
    parser_notes = []
    if not goal:
        parser_notes.append("Missing Goal")
    if not acceptance:
        parser_notes.append("Missing Acceptance Criteria")
    if not risk_raw:
        parser_notes.append("Missing Risk")
        risk = "needs_review"
    elif risk_raw in {"low", "medium", "high", "needs_review"}:
        risk = risk_raw
    else:
        parser_notes.append(f"Unrecognized Risk value: {risk_raw}")
        risk = "needs_review"
    return {
        "task_num": task_num,
        "title": title,
        "body": body if body.endswith("\n") else body + "\n",
        "goal": goal,
        "acceptance": acceptance,
        "allowed": allowed,
        "denied": denied,
        "test_command": test_command,
        "risk": risk,
        "notes": notes,
        "source": source,
        "escalation": escalation or "none",
        "parser_notes": parser_notes,
    }

tasks = [extract_task(match, idx) for idx, match in enumerate(matches)]
task_limit = min(max(args.max_tasks, 1), len(tasks))
tasks = tasks[:task_limit]

if args.dry_run:
    print(f"Project: {project_key}")
    print(f"Task file: {task_file}")
    print(f"Tasks detected: {len(matches)}")
    print(f"Tasks selected: {len(tasks)}")
    print(f"Plan only: {args.plan_only}")
    print(f"Apply: {args.apply}")
    print(f"Branch: {args.branch}")
    print(f"Auto escalate: {args.auto_escalate or 'none'}")
    print(f"Run root: {auto_root}")
    sys.exit(0)

def current_ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def make_run_dir(task_info):
    task_slug = slugify(task_info["title"], f"task_{task_info['task_num']:03d}")
    base = f"{current_ts()}_{project_key}_{task_info['task_num']:03d}_{task_slug}"
    candidate = auto_root / base
    suffix = 1
    while candidate.exists():
        candidate = auto_root / f"{base}_{suffix}"
        suffix += 1
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate

for task_info in tasks:
    run_dir = make_run_dir(task_info)
    task_info["_run_dir"] = str(run_dir)
    write_run_file(run_dir, "task.md", task_info["body"])
    write_run_file(run_dir, "run_config.md", "\n".join([
        "# Run Config",
        "",
        f"- Project Key: {project_key}",
        f"- Task File: {task_file}",
        f"- Plan Only: {args.plan_only}",
        f"- Apply: {args.apply}",
        f"- Branch: {args.branch}",
        f"- Max Tasks: {args.max_tasks}",
        f"- Max Attempts: {args.max_attempts}",
        f"- Max Cloud Attempts: {args.max_cloud_attempts}",
        f"- Max Files: {args.max_files}",
        f"- Max Minutes: {args.max_minutes}",
        f"- Stop On Fail: {args.stop_on_fail}",
        f"- Auto Escalate: {args.auto_escalate or 'none'}",
        f"- Planner Profile: {args.planner_profile}",
        f"- Coder Profile: {args.coder_profile or 'default'}",
        f"- Reviewer Profile: {args.reviewer_profile or 'default'}",
        f"- All Roles Profile: {args.profile or 'none'}",
        f"- Context: {args.context}",
        f"- Run Folder: {run_dir}",
        f"- Planner Model: pending",
        f"- Coder Model: pending",
        f"- Reviewer Model: pending",
        "",
    ]))
    write_run_file(run_dir, "project_metadata.md", "\n".join([
        "# Project Metadata",
        "",
        f"- Project Key: {project['project_key']}",
        f"- Project Name: {project['display_name']}",
        f"- Project Type: {project['project_type']}",
        f"- Windows Path: {project['windows_path']}",
        f"- WSL Path: {project['wsl_path']}",
        f"- Project Dir: {project_dir}",
        f"- Graph Path: {project['graph_path'] or 'not_graphed'}",
        f"- Safe To Modify: {project['safe_to_modify']}",
        f"- Status: {project['status']}",
        f"- Notes: {project['notes']}",
        "",
    ]))
    write_run_file(run_dir, "status.txt", "STARTED\n")
    write_run_file(run_dir, "heartbeat.log", "")
    write_run_file(run_dir, "local_attempts.md", "# Local Attempts\n")
    write_run_file(run_dir, "test_output.md", "# Test Output\n\nNot run yet.\n")
    write_run_file(run_dir, "apply_guard.md", "# Apply Guard\n\nNot run yet.\n")
    write_run_file(run_dir, "model_roles.md", json.dumps({"status": "pending"}, indent=2, sort_keys=True))
    heartbeat(run_dir, "run folder created")
    heartbeat(run_dir, "run config written")

if run_cmd(["bash", str(scripts / "ws"), "paths"], timeout=30, run_dir=Path(tasks[0]["_run_dir"]) if tasks else None, label="ws paths preflight")[0] != 0:
    print("ws paths failed during preflight.")
    sys.exit(1)
if run_cmd(["bash", str(scripts / "ws"), "model"], timeout=30, run_dir=Path(tasks[0]["_run_dir"]) if tasks else None, label="ws model preflight")[0] != 0:
    print("ws model failed during preflight.")
    sys.exit(1)
if run_cmd(["bash", str(scripts / "ws"), "kv"], timeout=30, run_dir=Path(tasks[0]["_run_dir"]) if tasks else None, label="ws kv preflight")[0] != 0:
    print("ws kv failed during preflight.")
    sys.exit(1)

model_router_rc, model_router_out = run_cmd(
    ["bash", str(scripts / "ws_auto_model_router.sh"), "--planner-profile", args.planner_profile, "--coder-profile", args.coder_profile or "", "--reviewer-profile", args.reviewer_profile or ""],
    timeout=30,
    run_dir=Path(tasks[0]["_run_dir"]) if tasks else None,
    label="model router",
)
if model_router_rc != 0:
    if tasks:
        first_run = Path(tasks[0]["_run_dir"])
        heartbeat(first_run, "model router failed")
        write_run_file(first_run, "status.txt", "BLOCKED_LOCAL\n")
        write_run_file(first_run, "final_report.md", "# Auto Run Final Report\n\n## Summary\n- Final Status: BLOCKED_LOCAL\n- Reason: model router failed during preflight.\n")
    print(model_router_out)
    sys.exit(model_router_rc)
model_info = json.loads(model_router_out)
planner_model = model_info["planner"]["selected_model"]
coder_model = model_info["coder"]["selected_model"]
reviewer_model = model_info["reviewer"]["selected_model"]

def current_ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def make_run_dir(task_info):
    task_slug = slugify(task_info["title"], f"task_{task_info['task_num']:03d}")
    base = f"{current_ts()}_{project_key}_{task_info['task_num']:03d}_{task_slug}"
    candidate = auto_root / base
    suffix = 1
    while candidate.exists():
        candidate = auto_root / f"{base}_{suffix}"
        suffix += 1
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate

def git_status(project_dir: Path, run_dir: Path | None = None):
    if detect_repo(project_dir, run_dir=run_dir):
        code, out = run_cmd(["git", "-C", str(project_dir), "status", "--short", "--branch"], timeout=30, run_dir=run_dir, label="git status")
        if code == 0:
            return out
    return "not a git repo"

def branch_name(task_info):
    return f"auto/{project_key}/{task_info['task_num']:03d}-{current_ts()}"

def graph_context_for(task_info, run_dir: Path | None = None):
    graph_path = project.get("graph_path") or ""
    if graph_path:
        graph_path = to_wsl(graph_path)
    if not graph_path and project.get("wsl_path"):
        graph_path = str(Path(project["wsl_path"]) / "graphify-out" / "graph.json")
    graph_file = Path(graph_path)
    query = "\n".join(filter(None, [task_info["title"], task_info["goal"], "\n".join(task_info["acceptance"])]))
    graphify = ws_home / "runtimes" / "graphify_venv" / "bin" / "graphify"
    if graph_file.is_file() and graphify.is_file():
        rc, out = run_cmd(
            [str(graphify), "query", query, "--graph", str(graph_file)],
            timeout=120,
            run_dir=run_dir,
            label="graphify query",
        )
        if rc == 0 and out.strip():
            return out[:10000] + ("\n...[truncated]" if len(out) > 10000 else "")
        if out.strip():
            return f"Graphify query failed locally: {out.strip()[:1200]}"
    return f"No graph context available at {graph_file}."

def compose_context_pack(task_info, graph_context):
    allowed = normalized_allowed_files(task_info)
    if not allowed:
        allowed = infer_allowed_files(task_info)
    return "\n".join([
        "# Context Pack",
        "",
        "## Task",
        f"- ID: {task_info['task_num']:03d}",
        f"- Title: {task_info['title']}",
        f"- Source: {task_info['source']}",
        f"- Risk: {task_info['risk']}",
        "",
        "## Goal",
        task_info["goal"] or "not specified",
        "",
        "## Acceptance Criteria",
        "\n".join(f"- {x}" for x in task_info["acceptance"]) or "- not specified",
        "",
        "## Allowed Files",
        "\n".join(f"- {x}" for x in allowed) or "- not specified",
        "",
        "## Denied Files",
        "\n".join(f"- {x}" for x in (task_info["denied"] or [".env", "credentials", "raw datasets", "data/*", "models/*", "node_modules/*", ".git/*"])),
        "",
        "## Test Command",
        task_info["test_command"] or "not specified",
        "",
        "## Project Metadata",
        f"- Key: {project['project_key']}",
        f"- Name: {project['display_name']}",
        f"- Type: {project['project_type']}",
        f"- Windows Path: {project['windows_path']}",
        f"- WSL Path: {project['wsl_path']}",
        f"- Graph Path: {project['graph_path'] or 'not_graphed'}",
        f"- Safe To Modify: {project['safe_to_modify']}",
        f"- Status: {project['status']}",
        f"- Notes: {project['notes']}",
        "",
        "## Compact Graphify Context",
        graph_context,
        "",
        "## Local Model Notes",
        f"- Planner model: {planner_model}",
        f"- Coder model: {coder_model}",
        f"- Reviewer model: {reviewer_model}",
        f"- Active local model: {model_info['active']['active_model']}",
        f"- Active KV profile: {model_info['active']['active_kv_profile']}",
        f"- Context: {args.context}",
        "",
        "## Safety Boundary",
        "Do not read or modify secrets, credentials, raw datasets, model files, archives, dependency folders, .git, or graphify-out. Keep changes bounded to Allowed Files.",
        "",
    ])

def build_plan_prompt(task_info, graph_context, role="planner", review=None, codex=None):
    allowed = normalized_allowed_files(task_info)
    if not allowed:
        allowed = infer_allowed_files(task_info)
    header = {
        "planner": "You are the local planner for a bounded workstation auto-run. Return a concise implementation plan only. Do not invent scope. If you cannot plan safely, say BLOCKED and why.",
        "coder": "You are the local coder for a bounded workstation auto-run. Return only a single git-style unified diff block if safe, with diff --git and a/ b/ path prefixes. The diff must stay within Allowed Files and respect the file count limit. If blocked, say BLOCKED and why. Do not include extra prose unless blocked.",
        "reviewer": "You are the local reviewer for a bounded workstation auto-run. Explain why the current attempt or test failed or was blocked, and name the smallest safe next fix. Keep it concise.",
    }[role]
    parts = [
        f"Project: {project['project_key']}",
        f"Task: {task_info['title']}",
        f"Task ID: {task_info['task_num']:03d}",
        f"Task Source: {task_info['source']}",
        f"Risk: {task_info['risk']}",
        "",
        "Goal:",
        task_info["goal"] or "not specified",
        "",
        "Acceptance Criteria:",
        "\n".join(f"- {x}" for x in task_info["acceptance"]) or "- not specified",
        "",
        "Allowed Files:",
        "\n".join(f"- {x}" for x in allowed) or "- not specified",
        "",
        "Denied Files:",
        "\n".join(f"- {x}" for x in (task_info["denied"] or [".env", "credentials", "raw datasets", "data/*", "models/*", "node_modules/*", ".git/*"])),
        "",
        "Test Command:",
        task_info["test_command"] or "not specified",
        "",
        "Project Metadata:",
        json.dumps(project, indent=2, sort_keys=True),
        "",
        "Graph Context:",
        graph_context,
        "",
        "Context Pack:",
        compose_context_pack(task_info, graph_context),
    ]
    if review:
        parts.extend(["", "Reviewer Guidance:", review])
    if codex:
        parts.extend(["", "Codex Guidance:", codex])
    return header + "\n\n" + "\n".join(parts)

def extract_diff(text: str):
    text = strip_code_fences(text)
    m = re.search(r"```(?:diff|patch)\s*\n(.*?)```", text, re.S)
    if m:
        return normalize_diff(m.group(1))
    if "diff --git" in text:
        start = text.index("diff --git")
        return normalize_diff(text[start:])
    if re.search(r"^---\s+(?:a/|b/|/)", text, re.M) and re.search(r"^\+\+\+\s+(?:a/|b/|/)", text, re.M):
        start = re.search(r"^---\s+(?:a/|b/|/)", text, re.M).start()
        return normalize_diff(text[start:])
    return ""

def normalize_diff(text: str):
    lines = [line.rstrip() for line in text.strip().splitlines()]
    normalized = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("--- ") and i + 1 < len(lines) and lines[i + 1].startswith("+++ "):
            old_path = line[4:].strip()
            new_path = lines[i + 1][4:].strip()
            if old_path != "/dev/null" and not old_path.startswith(("a/", "b/")):
                old_path = f"a/{old_path}"
            if new_path != "/dev/null" and not new_path.startswith(("a/", "b/")):
                new_path = f"b/{new_path}"
            normalized.append(f"--- {old_path}")
            normalized.append(f"+++ {new_path}")
            i += 2
            continue
        normalized.append(line)
        i += 1
    return "\n".join(normalized).strip() + "\n"

def strip_code_fences(text: str):
    m = re.search(r"```(?:json|diff|patch|text|markdown)?\s*\n(.*?)```", text, re.S)
    return m.group(1).strip() if m else text.strip()

def patch_is_approximate(text: str):
    markers = (
        "index 1234567..89abcdef",
        "index 1234567..",
        "@@ -1,5 +1,6 *",
        "@@ -20,6 +20,7 @@ The `ws` command is part of the local AI workstation. It offers a range of com...",
    )
    if any(marker in text for marker in markers):
        return True
    if re.search(r"^@@[^\n]*\.\.\.[^\n]*$", text, re.M):
        return True
    if re.search(r"^index\s+[0-9a-f]{7,8}\.\.[0-9a-f]{7,8}\s*$", text, re.M) and "placeholder" in text.lower():
        return True
    return False

def validate_patch_syntax(patch_text: str):
    text = patch_text.strip()
    if not text:
        return False, "empty patch"
    if "```" in text:
        return False, "markdown fence found in patch"
    if "index 1234567..89abcdef" in text or re.search(r"^index\s+[0-9a-f]{7,8}\.\.[0-9a-f]{7,8}\s*$", text, re.M):
        return False, "placeholder hashes found in patch"
    if re.search(r"^@@[^\n]*\.\.\.[^\n]*$", text, re.M):
        return False, "ellipsis found in hunk header"
    has_file_header = False
    has_hunk = False
    for line in text.splitlines():
        if line.startswith("diff --git "):
            has_file_header = True
            continue
        if line.startswith(("index ", "new file mode", "deleted file mode", "similarity index", "rename from", "rename to")):
            continue
        if line.startswith("--- "):
            has_file_header = True
            continue
        if line.startswith("+++ "):
            has_file_header = True
            continue
        if line.startswith("@@ "):
            if not re.match(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@(?: .*)?$", line):
                return False, f"malformed hunk header: {line}"
            has_hunk = True
            continue
        if line.startswith((" ", "+", "-")):
            continue
        if line.startswith("\\ No newline at end of file"):
            continue
        if not line.strip():
            continue
        return False, f"unexpected patch content: {line}"
    if not has_file_header:
        return False, "no file headers found"
    if not has_hunk:
        return False, "no hunk headers found"
    return True, "SAFE"

def docs_rewrite_candidates(allowed_files, project_dir: Path):
    doc_names = {"START_HERE.md", "WORKSTATION_MANUAL.md", "LOCAL_AI_STACK_STATUS.md", "FINAL_RECOMMENDED_PROFILE.md", "README.md"}
    candidates = []
    total = 0
    for rel in allowed_files:
        rel_norm = rel.replace("\\", "/")
        name = Path(rel_norm).name
        if name not in doc_names and Path(rel_norm).suffix.lower() not in {".md", ".txt"}:
            return None
        path = (project_dir / rel_norm).resolve()
        try:
            path.relative_to(project_dir)
        except ValueError:
            return None
        if not path.exists() or not path.is_file():
            return None
        size = path.stat().st_size
        if size > 20000:
            return None
        total += size
        if total > 40000:
            return None
        candidates.append(rel_norm)
    return candidates

def load_rewrite_snapshots(project_dir: Path, allowed_files):
    snapshots = []
    for rel in allowed_files:
        path = project_dir / rel
        snapshots.append({
            "path": rel,
            "content": path.read_text(encoding="utf-8", errors="replace"),
        })
    return snapshots

def build_docs_rewrite_prompt(task_info, graph_context, snapshots, ws_help_text, review=None):
    parts = [
        "You are the local coder for a bounded workstation auto-run.",
        "You will be shown the exact current contents of allowed documentation files.",
        "Return ONLY JSON or NO_PATCH.",
        "Do not use markdown fences, placeholder hashes, ellipses, invented context, or diff headers.",
        "Each edit must target an exact substring copied from the current file content shown below.",
        "Do not invent file content. Do not rewrite an entire file unless the edit is anchored to an exact substring from the file.",
        "If you cannot safely change a file, omit it.",
        "If nothing needs to change, return NO_PATCH.",
        "",
        "Task:",
        task_info["body"].strip(),
        "",
        "Goal:",
        task_info["goal"].strip() or "not specified",
        "",
        "Acceptance Criteria:",
        "\n".join(f"- {x}" for x in task_info["acceptance"]) or "- not specified",
        "",
        "Allowed Files:",
        "\n".join(f"- {x}" for x in normalized_allowed_files(task_info) or infer_allowed_files(task_info)) or "- not specified",
        "",
        "Current File Contents:",
    ]
    for snap in snapshots:
        parts.extend([
            f"## File: {snap['path']}",
            "BEGIN FILE CONTENT",
            snap["content"],
            "END FILE CONTENT",
            "",
        ])
    parts.extend([
        "Graph Context:",
        graph_context,
        "",
        "ws help Output:",
        ws_help_text or "not available",
        "",
        "Return JSON in this form:",
        '{"edits":[{"path":"START_HERE.md","find":"exact substring from file","replace":"replacement text","count":1}]}',
        "",
        "Rules:",
        "- `find` must be copied exactly from the current file content shown above.",
        "- `replace` may be new text, but it must stay within the allowed file and task scope.",
        "- If no exact anchor exists, return NO_PATCH.",
    ])
    if review:
        parts.extend(["", "Reviewer Guidance:", review])
    return "\n".join(parts)

def parse_rewrite_response(text: str):
    stripped = strip_code_fences(text)
    if stripped.strip() == "NO_PATCH":
        return None, "NO_PATCH"
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None, "no JSON object found"
    payload = stripped[start:end + 1]
    try:
        data = json.loads(payload)
    except Exception as exc:
        return None, f"invalid JSON payload: {exc}"
    if isinstance(data, dict) and "edits" in data:
        items = data["edits"]
        edits = []
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    return None, "invalid edits entry"
                path = str(item.get("path", "")).strip().replace("\\", "/")
                find = item.get("find", "")
                replace = item.get("replace", "")
                count = item.get("count", 1)
                if not path or not isinstance(find, str) or not isinstance(replace, str):
                    return None, "invalid edit entry"
                try:
                    count = int(count)
                except Exception:
                    return None, "invalid edit count"
                if count < 1:
                    return None, "invalid edit count"
                edits.append({"path": path, "find": find, "replace": replace, "count": count})
            return edits, "SAFE"
        return None, "invalid edits payload"
    if isinstance(data, dict) and "files" in data:
        items = data["files"]
        rewrite_map = {}
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    return None, "invalid files entry"
                path = str(item.get("path", "")).strip().replace("\\", "/")
                content = item.get("content", "")
                if not path or not isinstance(content, str):
                    return None, "invalid file entry"
                rewrite_map[path] = content
            return rewrite_map, "SAFE"
        if isinstance(items, dict):
            for path, content in items.items():
                path = str(path).strip().replace("\\", "/")
                if not path or not isinstance(content, str):
                    return None, "invalid file entry"
                rewrite_map[path] = content
            return rewrite_map, "SAFE"
        return None, "invalid files payload"
    if isinstance(data, dict):
        rewrite_map = {}
        for path, content in data.items():
            path = str(path).strip().replace("\\", "/")
            if not path or not isinstance(content, str):
                return None, "invalid file entry"
            rewrite_map[path] = content
        return rewrite_map, "SAFE"
    return None, "invalid JSON payload"

def build_patch_from_rewrites(project_dir: Path, rewrite_map, run_dir: Path, allowed_files=None):
    grounded_dir = run_dir / "grounded_rewrites"
    grounded_dir.mkdir(parents=True, exist_ok=True)
    diffs = []
    changed = []
    allowed_set = {x.replace("\\", "/") for x in allowed_files} if allowed_files else None
    if isinstance(rewrite_map, list):
        grouped = {}
        for edit in rewrite_map:
            rel = edit["path"].replace("\\", "/")
            grouped.setdefault(rel, []).append(edit)
        items = grouped.items()
    else:
        items = ((rel, [{"find": None, "replace": content, "count": 1}]) for rel, content in rewrite_map.items())

    for rel, edits in items:
        rel_norm = rel.replace("\\", "/")
        if allowed_set is not None and rel_norm not in allowed_set:
            return None, [], f"file outside allowed files {rel_norm}"
        real_path = (project_dir / rel_norm).resolve()
        try:
            real_path.relative_to(project_dir)
        except ValueError:
            return None, [], f"unsafe path {rel_norm}"
        if not real_path.exists() or not real_path.is_file():
            return None, [], f"missing file {rel_norm}"
        temp_path = grounded_dir / rel_norm
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        old_text = real_path.read_text(encoding="utf-8", errors="replace")
        new_text = old_text
        if isinstance(rewrite_map, list):
            for edit in edits:
                find = edit["find"]
                replace = edit["replace"]
                count = edit.get("count", 1)
                if find not in new_text:
                    return None, [], f"anchor not found {rel_norm}: {find[:80]}"
                new_text = new_text.replace(find, replace, count)
        else:
            new_text = edits[0]["replace"]
        temp_path.write_text(new_text, encoding="utf-8", newline="\n")
        if old_text == new_text:
            continue
        diff = "".join(difflib.unified_diff(
            old_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=f"a/{rel_norm}",
            tofile=f"b/{rel_norm}",
            lineterm="\n",
        ))
        if diff.strip():
            diffs.append(diff.strip())
            changed.append(rel_norm)
    if not diffs:
        return "", changed, "no changes"
    return "\n\n".join(diffs) + "\n", changed, "SAFE"

def load_allowed_file_snapshots(project_dir: Path, allowed_files, *, max_file_bytes=20000, max_total_bytes=40000):
    snapshots = []
    total = 0
    for rel in allowed_files:
        rel_norm = rel.replace("\\", "/")
        path = (project_dir / rel_norm).resolve()
        try:
            path.relative_to(project_dir)
        except ValueError:
            return None, f"unsafe path {rel_norm}"
        if not path.exists() or not path.is_file():
            return None, f"missing file {rel_norm}"
        size = path.stat().st_size
        if size > max_file_bytes:
            return None, f"file too large {rel_norm}"
        total += size
        if total > max_total_bytes:
            return None, "allowed file content too large"
        snapshots.append({
            "path": rel_norm,
            "content": path.read_text(encoding="utf-8", errors="replace"),
        })
    return snapshots, "SAFE"

def record_rejected_patch(run_dir: Path, patch_text: str, reason: str, stage: str, *, approximate: bool = False):
    write_run_file(run_dir, "rejected_patch.diff", patch_text)
    write_run_file(run_dir, "patch_validation.md", "\n".join([
        "# Patch Validation",
        "",
        f"- Stage: {stage}",
        f"- Result: rejected",
        f"- Reason: {reason}",
        f"- Approximate: {'yes' if approximate else 'no'}",
        "",
    ]))

def write_patch_validation(run_dir: Path, *, stage: str, result: str, reason: str, repair_attempted: bool, repair_result: str = "not run", approximate: bool = False):
    write_run_file(run_dir, "patch_validation.md", "\n".join([
        "# Patch Validation",
        "",
        f"- Stage: {stage}",
        f"- Result: {result}",
        f"- Reason: {reason}",
        f"- Approximate: {'yes' if approximate else 'no'}",
        f"- Repair Attempted: {'yes' if repair_attempted else 'no'}",
        f"- Repair Result: {repair_result}",
        "",
    ]))

def write_codex_patch_validation(run_dir: Path, *, status: str, reason: str, patch_present: bool, advice_only: bool = False, guard_result: str = "not run", apply_result: str = "not run"):
    write_run_file(run_dir, "codex_patch_validation.md", "\n".join([
        "# Codex Patch Validation",
        "",
        f"- Status: {status}",
        f"- Reason: {reason}",
        f"- Patch Present: {'yes' if patch_present else 'no'}",
        f"- Advice Only: {'yes' if advice_only else 'no'}",
        f"- Guard Result: {guard_result}",
        f"- Apply Result: {apply_result}",
        "",
    ]))

def write_codex_patch_apply(run_dir: Path, *, status: str, patch_path: str = "", guard_out: str = "", check_out: str = "", apply_out: str = ""):
    write_run_file(run_dir, "codex_patch_apply.md", "\n".join([
        "# Codex Patch Apply",
        "",
        f"- Status: {status}",
        f"- Patch Path: {patch_path or 'none'}",
        "",
        "## Apply Guard",
        "",
        guard_out.strip() or "not run",
        "",
        "## Git Apply Check",
        "",
        check_out.strip() or "not run",
        "",
        "## Git Apply",
        "",
        apply_out.strip() or "not run",
        "",
    ]))

def build_codex_patch_packet(task_info, graph_context, allowed_snapshots, local_plan_text, attempts_text, test_text, apply_guard_text):
    allowed = normalized_allowed_files(task_info) or infer_allowed_files(task_info)
    parts = [
        "# Auto Escalation Packet",
        "",
        "## Mode",
        "Codex Patch Mode",
        "",
        "## Codex Instructions",
        "Return ONLY a valid git-style unified diff.",
        "Do not write files directly.",
        "Do not use markdown fences.",
        "Do not include explanations or advice-only text.",
        "Do not use placeholder hashes, ellipses, or invented context.",
        "Paths must stay inside Allowed Files only.",
        "If you cannot produce a valid patch, return NO_PATCH.",
        "",
        "## Task",
        task_info["body"].strip(),
        "",
        "## Project Metadata",
        json.dumps(project, indent=2, sort_keys=True),
        "",
        "## Graph Context",
        graph_context,
        "",
        "## Allowed Files",
        "\n".join(f"- {x}" for x in allowed) or "- not specified",
        "",
        "## Allowed File Contents",
    ]
    if allowed_snapshots:
        for snap in allowed_snapshots:
            parts.extend([
                f"### File: {snap['path']}",
                "BEGIN FILE CONTENT",
                snap["content"],
                "END FILE CONTENT",
                "",
            ])
    else:
        parts.extend([
            "not available",
            "",
        ])
    parts.extend([
        "## Local Plan",
        local_plan_text or "not available",
        "",
        "## Attempts",
        attempts_text or "not available",
        "",
        "## Test Output",
        test_text or "not available",
        "",
        "## Apply Guard Reason",
        apply_guard_text or "not run",
        "",
        "## Specific Question for Frontier Model",
        "Why did this local build fail, and what is the smallest safe patch as a valid git-style unified diff?",
        "",
        "## Safety Notice",
        "Secrets, raw datasets, credentials, .env files, private keys, and broker keys were excluded.",
        "",
    ])
    return "\n".join(parts)

def docs_only(paths):
    if not paths:
        return False
    allowed_roots = ("reports/", "prompts/", "registry/", "global/", "plans/", "tasks/", "README", "START_HERE.md", "WORKSTATION_MANUAL.md", "LOCAL_AI_STACK_STATUS.md", "FINAL_RECOMMENDED_PROFILE.md", ".gitignore", ".graphifyignore")
    for rel in paths:
        p = rel.replace("\\", "/")
        if p.startswith("scripts/"):
            return False
        if not any(p.startswith(root) for root in allowed_roots):
            return False
    return True

def normalized_allowed_files(task_info):
    allowed = [x.strip() for x in task_info.get("allowed", []) if x and x.strip()]
    if allowed == ["not specified"]:
        allowed = []
    return allowed

def infer_allowed_files(task_info):
    explicit = []
    text = "\n".join(
        [
            task_info.get("body", ""),
            task_info.get("goal", ""),
            "\n".join(task_info.get("acceptance", [])),
            task_info.get("notes", ""),
        ]
    )
    candidates = [
        "START_HERE.md",
        "WORKSTATION_MANUAL.md",
        "LOCAL_AI_STACK_STATUS.md",
        "FINAL_RECOMMENDED_PROFILE.md",
        "README.md",
    ]
    for name in candidates:
        if name in text:
            explicit.append(name)
    return explicit

def write_run_file(run_dir: Path, name: str, content: str):
    write_text(run_dir / name, content)

def parse_changed_files_from_status(status_text: str):
    out = []
    for line in status_text.splitlines():
        if not line or line.startswith("## ") or line.startswith("!! "):
            continue
        if line.startswith("?? "):
            rel = line[3:].strip()
        else:
            rel = line[3:].strip() if len(line) > 3 else line.strip()
        if rel:
            out.append(rel)
    return out

def parse_test_result(test_text: str):
    if "NO_TESTS" in test_text or "No test command found." in test_text:
        return "NO_TESTS"
    m = re.search(r"Exit Code:\s*(\d+)", test_text)
    if m:
        return "PASS" if m.group(1) == "0" else "FAIL"
    return "UNKNOWN"

def create_run_dir(task_info):
    task_slug = slugify(task_info["title"], f"task_{task_info['task_num']:03d}")
    base = f"{current_ts()}_{project_key}_{task_info['task_num']:03d}_{task_slug}"
    candidate = auto_root / base
    idx = 1
    while candidate.exists():
        candidate = auto_root / f"{base}_{idx}"
        idx += 1
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate

def call_local_model(model: str, system_prompt: str, user_prompt: str, timeout_seconds: int = 120, run_dir: Path | None = None, label: str = "local model"):
    with tempfile.TemporaryDirectory(dir=str(run_dir) if run_dir else None) as temp_dir:
        temp_dir = Path(temp_dir)
        system_path = temp_dir / "system_prompt.txt"
        user_path = temp_dir / "user_prompt.txt"
        write_text(system_path, system_prompt)
        write_text(user_path, user_prompt)
        code, out = run_cmd(
            [
                "python3",
                str(scripts / "ollama_call.py"),
                "http://localhost:11434",
                model,
                str(system_path),
                str(user_path),
            ],
            timeout=timeout_seconds,
            run_dir=run_dir,
            label=label,
        )
        if code == 124:
            return "Error: local model call timed out"
        return out

if args.plan_only:
    mode = "PLAN_ONLY"
elif args.apply:
    mode = "APPLY"
else:
    mode = "PLAN_ONLY"

overall_results = []
for task_info in tasks:
    run_dir = Path(task_info["_run_dir"])
    current_run_dir = run_dir
    git_status_before = git_status(project_dir, run_dir=run_dir)
    write_run_file(run_dir, "model_roles.md", json.dumps(model_info, indent=2, sort_keys=True))
    write_run_file(run_dir, "run_config.md", run_dir.joinpath("run_config.md").read_text(encoding="utf-8", errors="replace") + "\n".join([
        "",
        f"- Planner Model: {planner_model}",
        f"- Coder Model: {coder_model}",
        f"- Reviewer Model: {reviewer_model}",
        "",
    ]))
    graph_context = graph_context_for(task_info, run_dir)
    write_run_file(run_dir, "graph_context.md", graph_context + "\n")
    context_pack = compose_context_pack(task_info, graph_context)
    write_run_file(run_dir, "context_pack.md", context_pack)
    write_run_file(run_dir, "git_status_before.md", git_status_before + "\n")
    write_run_file(run_dir, "status.txt", "IN_PROGRESS\n")
    heartbeat(run_dir, "preflight complete")
    ws_help_rc, ws_help_out = run_cmd(["bash", str(scripts / "ws"), "help"], timeout=30, run_dir=run_dir, label="ws help")
    ws_help_text = ws_help_out if ws_help_rc == 0 else ""
    write_run_file(run_dir, "ws_help.md", ws_help_text + "\n")

    planner_prompt = build_plan_prompt(task_info, graph_context, role="planner")
    planner_system = "You are the local planner for a bounded workstation auto-run. Return a concise implementation plan only."
    planner_response = call_local_model(planner_model, planner_system, planner_prompt, timeout_seconds=180, run_dir=run_dir, label="planner model")
    write_run_file(run_dir, "local_plan.md", planner_response + "\n")
    write_run_file(run_dir, "local_attempts.md", "# Local Attempts\n\n## Planning\n\n")
    append_text(run_dir / "local_attempts.md", f"- Model: {planner_model}\n")
    append_text(run_dir / "local_attempts.md", f"- Outcome: {'blocked' if planner_response.startswith('Error:') else 'planned'}\n")
    append_text(run_dir / "local_attempts.md", f"- Preview:\n\n{planner_response[:2000]}\n")

    if args.plan_only:
        write_run_file(run_dir, "status.txt", "PLAN_ONLY\n")
        run_cmd(["bash", str(scripts / "ws_auto_report.sh"), str(run_dir)], timeout=30, run_dir=run_dir, label="auto report")
        overall_results.append((run_dir, "PLAN_ONLY"))
        continue

    if args.branch:
        branch_name = f"auto/{project_key}/{task_info['task_num']:03d}-{current_ts()}"
        branch_result = run_cmd(["git", "-C", str(project_dir), "switch", "-c", branch_name], timeout=30, run_dir=run_dir, label="git branch create")
        if branch_result[0] != 0:
            branch_result = run_cmd(["git", "-C", str(project_dir), "switch", branch_name], timeout=30, run_dir=run_dir, label="git branch switch")
        branch_created = branch_result[0] == 0
        write_run_file(run_dir, "run_config.md", run_dir.joinpath("run_config.md").read_text(encoding="utf-8") + f"- Git Branch: {branch_name}\n")
    else:
        branch_name = run_cmd(["git", "-C", str(project_dir), "branch", "--show-current"], timeout=30, run_dir=run_dir, label="git current branch")[1].strip() or "unknown"
        branch_created = True

    if not detect_repo(project_dir, run_dir=run_dir):
        write_run_file(run_dir, "status.txt", "SAFETY_BLOCKED\n")
        append_text(run_dir / "local_attempts.md", "\n- Safety: project is not a git repository; apply mode blocked.\n")
        run_cmd(["bash", str(scripts / "ws_auto_report.sh"), str(run_dir)], timeout=30, run_dir=run_dir, label="auto report")
        overall_results.append((run_dir, "SAFETY_BLOCKED"))
        if args.stop_on_fail:
            break
        continue

    write_run_file(run_dir, "git_status_before.md", git_status(project_dir, run_dir=run_dir) + "\n")

    allowed_file = run_dir / "allowed_files.txt"
    allowed = normalized_allowed_files(task_info)
    if not allowed:
        inferred_allowed = infer_allowed_files(task_info)
        if inferred_allowed:
            allowed = inferred_allowed
            append_text(run_dir / "local_attempts.md", f"- Inferred Allowed Files: {', '.join(inferred_allowed)}\n")
    if allowed:
        allowed_file.write_text("\n".join(allowed) + "\n", encoding="utf-8", newline="\n")
    else:
        allowed_file.write_text("not specified\n", encoding="utf-8", newline="\n")
    grounded_allowed = docs_rewrite_candidates(allowed, project_dir)
    grounded_snapshots = load_rewrite_snapshots(project_dir, grounded_allowed) if grounded_allowed else []
    grounded_docs_mode = bool(grounded_allowed)

    local_status = "BLOCKED_LOCAL"
    tests_passed = False
    files_changed = []
    final_patch = ""
    proposed_patch = run_dir / "proposed.patch"
    proposed_patch_ready = False
    patch_repair_attempted = False
    reviewer_notes = ""
    codex_status = "none"
    codex_used = False
    codex_patch_status = "not-run"
    codex_patch_applied = False
    cloud_attempts = 0
    applied_once = False
    last_test_text = ""
    apply_guard_text = ""
    tests_ran = False

    for attempt in range(1, max(args.max_attempts, 1) + 1):
        append_text(run_dir / "local_attempts.md", f"\n## Attempt {attempt}\n")
        if grounded_docs_mode:
            coder_prompt = build_docs_rewrite_prompt(task_info, graph_context, grounded_snapshots, ws_help_text, review=reviewer_notes)
            coder_system = "You are the local coder for a grounded documentation rewrite. Return only JSON or NO_PATCH. Do not emit diffs, markdown fences, placeholder hashes, ellipses, or invented context."
        else:
            coder_prompt = build_plan_prompt(task_info, graph_context, role="coder", review=reviewer_notes)
            coder_system = "You are the local coder for a bounded workstation auto-run. Return only a single git-style unified diff block if safe, with diff --git and a/ b/ path prefixes. The diff must stay within Allowed Files and respect the file count limit. If blocked, say BLOCKED and why. Do not include extra prose unless blocked. Do not invent file content, placeholder hashes, or ellipses. If you cannot produce a valid patch, return NO_PATCH."
        coder_response = call_local_model(coder_model, coder_system, coder_prompt, timeout_seconds=180, run_dir=run_dir, label="coder model")
        append_text(run_dir / "local_attempts.md", f"- Coder Model: {coder_model}\n")
        append_text(run_dir / "local_attempts.md", f"- Coder Preview:\n\n{coder_response[:3000]}\n")
        patch = ""
        if grounded_docs_mode:
            rewrite_map, rewrite_reason = parse_rewrite_response(coder_response)
            if rewrite_map is None:
                if rewrite_reason == "NO_PATCH":
                    reviewer_prompt = build_plan_prompt(task_info, graph_context, role="reviewer")
                    reviewer_system = "You are the local reviewer for a bounded workstation auto-run. Explain the smallest safe next fix."
                    reviewer_notes = call_local_model(reviewer_model, reviewer_system, reviewer_prompt + "\n\nCurrent coder output:\n\n" + coder_response[:3000], timeout_seconds=180, run_dir=run_dir, label="reviewer model")
                    append_text(run_dir / "local_attempts.md", f"- Reviewer Model: {reviewer_model}\n")
                    append_text(run_dir / "local_attempts.md", f"- Reviewer Notes:\n\n{reviewer_notes[:3000]}\n")
                    continue
                approximate = True if grounded_docs_mode else patch_is_approximate(coder_response)
                record_rejected_patch(run_dir, coder_response, rewrite_reason, f"attempt {attempt}", approximate=approximate)
                write_patch_validation(run_dir, stage=f"attempt {attempt}", result="rejected", reason=rewrite_reason, repair_attempted=False, repair_result="parse-failed", approximate=approximate)
                local_status = "PATCH_INVALID_APPROXIMATE" if approximate else "PATCH_INVALID"
                break
            patch, changed_files_from_rewrite, patch_reason = build_patch_from_rewrites(project_dir, rewrite_map, run_dir, allowed)
            if patch_reason == "no changes":
                reviewer_prompt = build_plan_prompt(task_info, graph_context, role="reviewer")
                reviewer_system = "You are the local reviewer for a bounded workstation auto-run. Explain the smallest safe next fix."
                reviewer_notes = call_local_model(reviewer_model, reviewer_system, reviewer_prompt + "\n\nCurrent coder output:\n\n" + coder_response[:3000], timeout_seconds=180, run_dir=run_dir, label="reviewer model")
                append_text(run_dir / "local_attempts.md", f"- Reviewer Model: {reviewer_model}\n")
                append_text(run_dir / "local_attempts.md", f"- Reviewer Notes:\n\n{reviewer_notes[:3000]}\n")
                continue
            if patch_reason != "SAFE":
                approximate = True if grounded_docs_mode else patch_is_approximate(coder_response)
                record_rejected_patch(run_dir, coder_response, patch_reason, f"attempt {attempt}", approximate=approximate)
                write_patch_validation(run_dir, stage=f"attempt {attempt}", result="rejected", reason=patch_reason, repair_attempted=False, repair_result="rewrite-failed", approximate=approximate)
                local_status = "PATCH_INVALID_APPROXIMATE" if approximate else "PATCH_INVALID"
                break
            append_text(run_dir / "local_attempts.md", f"- Grounded Rewrite Files: {', '.join(changed_files_from_rewrite) or 'none'}\n")
        else:
            patch = extract_diff(coder_response)
            if not patch:
                reviewer_prompt = build_plan_prompt(task_info, graph_context, role="reviewer")
                reviewer_system = "You are the local reviewer for a bounded workstation auto-run. Explain the smallest safe next fix."
                reviewer_notes = call_local_model(reviewer_model, reviewer_system, reviewer_prompt + "\n\nCurrent coder output:\n\n" + coder_response[:3000], timeout_seconds=180, run_dir=run_dir, label="reviewer model")
                append_text(run_dir / "local_attempts.md", f"- Reviewer Model: {reviewer_model}\n")
                append_text(run_dir / "local_attempts.md", f"- Reviewer Notes:\n\n{reviewer_notes[:3000]}\n")
                continue

        patch = normalize_diff(patch)
        patch_ok, patch_reason = validate_patch_syntax(patch)
        if not patch_ok:
            approximate = True if grounded_docs_mode else (patch_is_approximate(coder_response) or patch_is_approximate(patch))
            record_rejected_patch(run_dir, patch, patch_reason, f"attempt {attempt}", approximate=approximate)
            append_text(run_dir / "local_attempts.md", f"- Patch Validation: {patch_reason}\n")
            if not patch_repair_attempted:
                patch_repair_attempted = True
                repair_allowed = normalized_allowed_files(task_info) or infer_allowed_files(task_info) or ["START_HERE.md", "WORKSTATION_MANUAL.md"]
                repair_prompt = "\n".join([
                    "Repair this patch into a valid git-style unified diff only.",
                    "Output only the diff. No markdown fences. No explanations.",
                    "",
                    "Git Apply Error:",
                    patch_reason,
                    "",
                    "Rejected Patch:",
                    patch,
                    "",
                    "Allowed Files:",
                    "\n".join(f"- {x}" for x in repair_allowed),
                    "",
                ])
                repair_system = "You are the local coder for a bounded workstation auto-run. Return only a valid git-style unified diff. Do not use markdown fences or prose."
                repair_response = call_local_model(coder_model, repair_system, repair_prompt, timeout_seconds=180, run_dir=run_dir, label="coder patch repair")
                append_text(run_dir / "local_attempts.md", f"- Patch Repair Model: {coder_model}\n")
                append_text(run_dir / "local_attempts.md", f"- Patch Repair Preview:\n\n{repair_response[:3000]}\n")
                repair_patch = normalize_diff(extract_diff(repair_response))
                repair_ok, repair_reason = validate_patch_syntax(repair_patch)
                if not repair_ok:
                    repair_approximate = patch_is_approximate(repair_response) or patch_is_approximate(repair_patch)
                    write_patch_validation(run_dir, stage=f"attempt {attempt}", result="rejected", reason=patch_reason, repair_attempted=True, repair_result=repair_reason, approximate=repair_approximate)
                    local_status = "PATCH_INVALID_APPROXIMATE" if approximate or repair_approximate else "PATCH_INVALID"
                    break
                patch = repair_patch
                write_run_file(run_dir, "repair_patch.diff", patch)
                write_patch_validation(run_dir, stage=f"attempt {attempt}", result="repaired", reason=patch_reason, repair_attempted=True, repair_result="syntax-ok", approximate=approximate)
            else:
                write_patch_validation(run_dir, stage=f"attempt {attempt}", result="rejected", reason=patch_reason, repair_attempted=True, repair_result="not-repaired", approximate=approximate)
                local_status = "PATCH_INVALID_APPROXIMATE" if approximate else "PATCH_INVALID"
                break

        proposed_patch.write_text(patch, encoding="utf-8", newline="\n")
        proposed_patch_ready = True
        guard_rc, guard_out = run_cmd(
            ["bash", str(scripts / "ws_apply_guard.sh"), str(project_dir), str(proposed_patch), str(allowed_file), str(args.max_files)],
            timeout=120,
            run_dir=run_dir,
            label="apply guard",
        )
        apply_guard_text = guard_out.strip()
        guard_reason = "blocked by guard"
        guard_lower = apply_guard_text.lower()
        if "max is" in guard_lower or "changes" in guard_lower:
            guard_reason = "file limit exceeded"
        elif "outside allowed files" in guard_lower:
            guard_reason = "outside allowed files"
        elif "unsafe" in guard_lower or "escapes project" in guard_lower:
            guard_reason = "unsafe path or content"
        elif "no changed file paths" in guard_lower:
            guard_reason = "no changed files in patch"
        elif guard_rc == 0 and apply_guard_text.startswith("SAFE"):
            guard_reason = "passed"
        write_run_file(run_dir, "apply_guard.md", "\n".join([
            "# Apply Guard",
            "",
            f"- Phase: attempt {attempt}",
            f"- Guard Exit Code: {guard_rc}",
            f"- Guard Reason: {guard_reason}",
            f"- Branch Name: {branch_name}",
            f"- Branch Created: {'yes' if branch_created else 'no'}",
            f"- Allowed File Exists: {'yes' if allowed_file.exists() else 'no'}",
            f"- Patch Ready Before Guard: {'yes' if proposed_patch_ready else 'no'}",
            f"- Edits Made Before Block: {'yes' if proposed_patch_ready or applied_once else 'no'}",
            f"- Tests Ran: {'yes' if tests_ran else 'no'}",
            "",
            "## Guard Output",
            "",
            apply_guard_text or "blank",
            "",
        ]))
        append_text(run_dir / "local_attempts.md", f"- Apply Guard Result: {guard_rc}\n\n{apply_guard_text}\n")
        if guard_rc != 0 or "SAFE" not in apply_guard_text.splitlines()[0:2]:
            reviewer_prompt = build_plan_prompt(task_info, graph_context, role="reviewer", review=apply_guard_text)
            reviewer_system = "You are the local reviewer for a bounded workstation auto-run. Explain the smallest safe next fix."
            reviewer_notes = call_local_model(reviewer_model, reviewer_system, reviewer_prompt, timeout_seconds=180, run_dir=run_dir, label="reviewer model")
            append_text(run_dir / "local_attempts.md", f"- Reviewer Model: {reviewer_model}\n")
            append_text(run_dir / "local_attempts.md", f"- Reviewer Notes:\n\n{reviewer_notes[:3000]}\n")
            continue

        git_apply_check_rc, git_apply_check_out = run_cmd(["git", "-C", str(project_dir), "apply", "--check", str(proposed_patch)], timeout=120, run_dir=run_dir, label="git apply check")
        append_text(run_dir / "local_attempts.md", f"- Git Apply Check Exit: {git_apply_check_rc}\n\n{git_apply_check_out.strip()}\n")
        if git_apply_check_rc != 0:
            record_rejected_patch(run_dir, patch, git_apply_check_out.strip() or "git apply check failed", f"attempt {attempt}")
            write_patch_validation(run_dir, stage=f"attempt {attempt}", result="rejected", reason=git_apply_check_out.strip() or "git apply check failed", repair_attempted=patch_repair_attempted, repair_result="git-apply-check-failed")
            if not patch_repair_attempted:
                patch_repair_attempted = True
                repair_allowed = normalized_allowed_files(task_info) or infer_allowed_files(task_info) or ["START_HERE.md", "WORKSTATION_MANUAL.md"]
                repair_prompt = "\n".join([
                    "Repair this patch into a valid git-style unified diff only.",
                    "Output only the diff. No markdown fences. No explanations.",
                    "",
                    "Git Apply Error:",
                    git_apply_check_out.strip() or "git apply check failed",
                    "",
                    "Rejected Patch:",
                    patch,
                    "",
                    "Allowed Files:",
                    "\n".join(f"- {x}" for x in repair_allowed),
                    "",
                ])
                repair_system = "You are the local coder for a bounded workstation auto-run. Return only a valid git-style unified diff. Do not use markdown fences or prose."
                repair_response = call_local_model(coder_model, repair_system, repair_prompt, timeout_seconds=180, run_dir=run_dir, label="coder patch repair")
                append_text(run_dir / "local_attempts.md", f"- Patch Repair Model: {coder_model}\n")
                append_text(run_dir / "local_attempts.md", f"- Patch Repair Preview:\n\n{repair_response[:3000]}\n")
                repair_patch = normalize_diff(extract_diff(repair_response))
                repair_ok, repair_reason = validate_patch_syntax(repair_patch)
                if not repair_ok:
                    write_patch_validation(run_dir, stage=f"attempt {attempt}", result="rejected", reason=git_apply_check_out.strip() or "git apply check failed", repair_attempted=True, repair_result=repair_reason)
                    local_status = "PATCH_INVALID"
                    break
                write_run_file(run_dir, "repair_patch.diff", repair_patch)
                proposed_patch.write_text(repair_patch, encoding="utf-8", newline="\n")
                proposed_patch_ready = True
                guard_rc, guard_out = run_cmd(
                    ["bash", str(scripts / "ws_apply_guard.sh"), str(project_dir), str(proposed_patch), str(allowed_file), str(args.max_files)],
                    timeout=120,
                    run_dir=run_dir,
                    label="apply guard patch repair",
                )
                if guard_rc != 0 or "SAFE" not in guard_out.splitlines()[0:2]:
                    write_patch_validation(run_dir, stage=f"attempt {attempt}", result="repaired", reason=git_apply_check_out.strip() or "git apply check failed", repair_attempted=True, repair_result="guard-blocked")
                    local_status = "PATCH_INVALID"
                    break
                git_apply_check_rc, git_apply_check_out = run_cmd(["git", "-C", str(project_dir), "apply", "--check", str(proposed_patch)], timeout=120, run_dir=run_dir, label="git apply check repair")
                append_text(run_dir / "local_attempts.md", f"- Repair Git Apply Check Exit: {git_apply_check_rc}\n\n{git_apply_check_out.strip()}\n")
                if git_apply_check_rc != 0:
                    write_patch_validation(run_dir, stage=f"attempt {attempt}", result="repaired", reason=git_apply_check_out.strip() or "git apply check failed", repair_attempted=True, repair_result="still-invalid")
                    local_status = "PATCH_INVALID"
                    break
            else:
                reviewer_notes = call_local_model(reviewer_model, "You are the local reviewer for a bounded workstation auto-run. Explain why the patch did not apply cleanly and what the smallest safe next fix is.", coder_prompt + "\n\nPatch:\n\n" + patch + "\n\nApply check output:\n" + git_apply_check_out, timeout_seconds=180, run_dir=run_dir, label="reviewer model")
                append_text(run_dir / "local_attempts.md", f"- Reviewer Model: {reviewer_model}\n")
                append_text(run_dir / "local_attempts.md", f"- Reviewer Notes:\n\n{reviewer_notes[:3000]}\n")
                continue

        git_apply_rc, git_apply_out = run_cmd(["git", "-C", str(project_dir), "apply", str(proposed_patch)], timeout=120, run_dir=run_dir, label="git apply")
        append_text(run_dir / "local_attempts.md", f"- Git Apply Exit: {git_apply_rc}\n\n{git_apply_out.strip()}\n")
        if git_apply_rc != 0:
            record_rejected_patch(run_dir, patch, git_apply_out.strip() or "git apply failed", f"attempt {attempt}")
            write_patch_validation(run_dir, stage=f"attempt {attempt}", result="rejected", reason=git_apply_out.strip() or "git apply failed", repair_attempted=patch_repair_attempted, repair_result="git-apply-failed")
            if not patch_repair_attempted:
                patch_repair_attempted = True
                repair_allowed = normalized_allowed_files(task_info) or infer_allowed_files(task_info) or ["START_HERE.md", "WORKSTATION_MANUAL.md"]
                repair_prompt = "\n".join([
                    "Repair this patch into a valid git-style unified diff only.",
                    "Output only the diff. No markdown fences. No explanations.",
                    "",
                    "Git Apply Error:",
                    git_apply_out.strip() or "git apply failed",
                    "",
                    "Rejected Patch:",
                    patch,
                    "",
                    "Allowed Files:",
                    "\n".join(f"- {x}" for x in repair_allowed),
                    "",
                ])
                repair_system = "You are the local coder for a bounded workstation auto-run. Return only a valid git-style unified diff. Do not use markdown fences or prose."
                repair_response = call_local_model(coder_model, repair_system, repair_prompt, timeout_seconds=180, run_dir=run_dir, label="coder patch repair")
                append_text(run_dir / "local_attempts.md", f"- Patch Repair Model: {coder_model}\n")
                append_text(run_dir / "local_attempts.md", f"- Patch Repair Preview:\n\n{repair_response[:3000]}\n")
                repair_patch = normalize_diff(extract_diff(repair_response))
                repair_ok, repair_reason = validate_patch_syntax(repair_patch)
                if not repair_ok:
                    write_patch_validation(run_dir, stage=f"attempt {attempt}", result="rejected", reason=git_apply_out.strip() or "git apply failed", repair_attempted=True, repair_result=repair_reason)
                    local_status = "PATCH_INVALID"
                    break
                write_run_file(run_dir, "repair_patch.diff", repair_patch)
                proposed_patch.write_text(repair_patch, encoding="utf-8", newline="\n")
                proposed_patch_ready = True
                guard_rc, guard_out = run_cmd(
                    ["bash", str(scripts / "ws_apply_guard.sh"), str(project_dir), str(proposed_patch), str(allowed_file), str(args.max_files)],
                    timeout=120,
                    run_dir=run_dir,
                    label="apply guard patch repair",
                )
                if guard_rc != 0 or "SAFE" not in guard_out.splitlines()[0:2]:
                    write_patch_validation(run_dir, stage=f"attempt {attempt}", result="repaired", reason=git_apply_out.strip() or "git apply failed", repair_attempted=True, repair_result="guard-blocked")
                    local_status = "PATCH_INVALID"
                    break
                if run_cmd(["git", "-C", str(project_dir), "apply", "--check", str(proposed_patch)], timeout=120, run_dir=run_dir, label="git apply check repair")[0] != 0:
                    write_patch_validation(run_dir, stage=f"attempt {attempt}", result="repaired", reason=git_apply_out.strip() or "git apply failed", repair_attempted=True, repair_result="still-invalid")
                    local_status = "PATCH_INVALID"
                    break
            else:
                reviewer_notes = call_local_model(reviewer_model, "You are the local reviewer for a bounded workstation auto-run. Explain why the patch failed to apply and the smallest safe next fix.", coder_prompt + "\n\nPatch:\n\n" + patch + "\n\nApply output:\n" + git_apply_out, timeout_seconds=180, run_dir=run_dir, label="reviewer model")
                append_text(run_dir / "local_attempts.md", f"- Reviewer Model: {reviewer_model}\n")
                append_text(run_dir / "local_attempts.md", f"- Reviewer Notes:\n\n{reviewer_notes[:3000]}\n")
                continue

        applied_once = True
        if task_info["test_command"]:
            test_rc, test_stdout = run_cmd(["bash", str(scripts / "ws_test_runner.sh"), str(project_dir), str(run_dir), task_info["test_command"], str(args.max_minutes)], timeout=max(args.max_minutes * 60 + 30, 120), run_dir=run_dir, label="test runner", check=False)
            last_test_text = test_stdout
            write_run_file(run_dir, "test_output.md", test_stdout + "\n")
        else:
            test_rc, test_stdout = run_cmd(["bash", str(scripts / "ws_test_runner.sh"), str(project_dir), str(run_dir), "", str(args.max_minutes)], timeout=max(args.max_minutes * 60 + 30, 120), run_dir=run_dir, label="test runner", check=False)
            last_test_text = test_stdout
            write_run_file(run_dir, "test_output.md", test_stdout + "\n")
        tests_ran = True

        if test_rc == 0:
            tests_passed = True
            local_status = "PASSED"
            break

        reviewer_prompt = build_plan_prompt(task_info, graph_context, role="reviewer", review=test_stdout)
        reviewer_system = "You are the local reviewer for a bounded workstation auto-run. Explain why tests failed and the smallest safe next fix."
        reviewer_notes = call_local_model(reviewer_model, reviewer_system, reviewer_prompt, timeout_seconds=180, run_dir=run_dir, label="reviewer model")
        append_text(run_dir / "local_attempts.md", f"- Reviewer Model: {reviewer_model}\n")
        append_text(run_dir / "local_attempts.md", f"- Reviewer Notes:\n\n{reviewer_notes[:3000]}\n")
        local_status = "FAILED_TESTS"

    if not tests_passed and args.auto_escalate == "codex" and args.no_escalate is False and cloud_attempts < max(args.max_cloud_attempts, 0):
        allowed_for_codex = normalized_allowed_files(task_info) or infer_allowed_files(task_info)
        allowed_snapshots, snapshot_reason = load_allowed_file_snapshots(project_dir, allowed_for_codex)
        if snapshot_reason != "SAFE":
            allowed_snapshots = []
        packet = run_dir / "codex_packet.md"
        packet.write_text(
            build_codex_patch_packet(
                task_info,
                graph_context,
                allowed_snapshots,
                run_dir.joinpath("local_plan.md").read_text(encoding="utf-8", errors="replace"),
                run_dir.joinpath("local_attempts.md").read_text(encoding="utf-8", errors="replace"),
                last_test_text or run_dir.joinpath("test_output.md").read_text(encoding="utf-8", errors="replace"),
                apply_guard_text or "not run",
            ),
            encoding="utf-8",
            newline="\n",
        )
        bridge_rc, bridge_out = run_cmd(
            ["bash", str(scripts / "ws_auto_codex_bridge.sh"), str(run_dir), str(packet)],
            timeout=300,
            run_dir=run_dir,
            label="codex bridge",
        )
        try:
            usage = json.loads(bridge_out.strip())
        except Exception:
            usage = {}
        if usage.get("used"):
            codex_used = True
            cloud_attempts += 1
            codex_status = "SENT"
            codex_response_path = run_dir / "codex_response.md"
            codex_response = codex_response_path.read_text(encoding="utf-8", errors="replace") if codex_response_path.exists() else ""
            append_text(run_dir / "local_attempts.md", f"- Codex Status: SENT\n")
            append_text(run_dir / "local_attempts.md", f"- Codex Patch Mode: requested\n")
            append_text(run_dir / "local_attempts.md", f"- Codex Response:\n\n{codex_response[:4000]}\n")
            codex_patch = extract_diff(codex_response)
            if not codex_patch:
                codex_patch_status = "BLOCKED_CODEX_ADVICE_ONLY"
                local_status = codex_patch_status
                write_codex_patch_validation(run_dir, status=codex_patch_status, reason="Codex response did not include an applyable diff.", patch_present=False, advice_only=True)
                write_codex_patch_apply(run_dir, status="not applied", patch_path=str(run_dir / "codex_patch.diff"))
            else:
                codex_patch = normalize_diff(codex_patch)
                write_run_file(run_dir, "codex_patch.diff", codex_patch)
                patch_ok, patch_reason = validate_patch_syntax(codex_patch)
                if not patch_ok:
                    codex_patch_status = "BLOCKED_CODEX_PATCH_INVALID"
                    write_codex_patch_validation(run_dir, status=codex_patch_status, reason=patch_reason, patch_present=True)
                    write_codex_patch_apply(run_dir, status="invalid", patch_path=str(run_dir / "codex_patch.diff"))
                    record_rejected_patch(run_dir, codex_patch, patch_reason, "codex patch validation", approximate=patch_is_approximate(codex_patch) or patch_is_approximate(codex_response))
                    local_status = codex_patch_status
                else:
                    proposed_patch.write_text(codex_patch, encoding="utf-8", newline="\n")
                    proposed_patch_ready = True
                    guard_rc, guard_out = run_cmd(
                        ["bash", str(scripts / "ws_apply_guard.sh"), str(project_dir), str(proposed_patch), str(allowed_file), str(args.max_files)],
                        timeout=120,
                        run_dir=run_dir,
                        label="apply guard codex patch",
                    )
                    write_run_file(run_dir, "apply_guard.md", (run_dir / "apply_guard.md").read_text(encoding="utf-8", errors="replace") + "\n\n## Codex Patch\n\n" + guard_out.strip() + "\n")
                    append_text(run_dir / "local_attempts.md", f"- Codex Patch Guard Result: {guard_rc}\n\n{guard_out.strip()}\n")
                    if guard_rc != 0 or "SAFE" not in guard_out.splitlines()[0:2]:
                        codex_patch_status = "BLOCKED_CODEX_PATCH_INVALID"
                        write_codex_patch_validation(run_dir, status=codex_patch_status, reason=(guard_out.strip() or "apply guard blocked"), patch_present=True, guard_result=guard_out.strip() or "blocked")
                        write_codex_patch_apply(run_dir, status="blocked by guard", patch_path=str(run_dir / "codex_patch.diff"), guard_out=guard_out)
                        record_rejected_patch(run_dir, codex_patch, guard_out.strip() or "apply guard blocked", "codex patch guard", approximate=patch_is_approximate(codex_patch) or patch_is_approximate(codex_response))
                        local_status = codex_patch_status
                    else:
                        git_apply_check_rc, git_apply_check_out = run_cmd(["git", "-C", str(project_dir), "apply", "--check", str(proposed_patch)], timeout=120, run_dir=run_dir, label="git apply check codex patch")
                        append_text(run_dir / "local_attempts.md", f"- Codex Patch Git Apply Check Exit: {git_apply_check_rc}\n\n{git_apply_check_out.strip()}\n")
                        if git_apply_check_rc != 0:
                            codex_patch_status = "BLOCKED_CODEX_PATCH_INVALID"
                            write_codex_patch_validation(run_dir, status=codex_patch_status, reason=(git_apply_check_out.strip() or "git apply check failed"), patch_present=True, guard_result="SAFE", apply_result=git_apply_check_out.strip() or "git apply check failed")
                            write_codex_patch_apply(run_dir, status="git apply check failed", patch_path=str(run_dir / "codex_patch.diff"), guard_out=guard_out, check_out=git_apply_check_out)
                            record_rejected_patch(run_dir, codex_patch, git_apply_check_out.strip() or "git apply check failed", "codex patch git apply check", approximate=patch_is_approximate(codex_patch) or patch_is_approximate(codex_response))
                            local_status = codex_patch_status
                        else:
                            git_apply_rc, git_apply_out = run_cmd(["git", "-C", str(project_dir), "apply", str(proposed_patch)], timeout=120, run_dir=run_dir, label="git apply codex patch")
                            append_text(run_dir / "local_attempts.md", f"- Codex Patch Git Apply Exit: {git_apply_rc}\n\n{git_apply_out.strip()}\n")
                            if git_apply_rc != 0:
                                codex_patch_status = "BLOCKED_CODEX_PATCH_INVALID"
                                write_codex_patch_validation(run_dir, status=codex_patch_status, reason=(git_apply_out.strip() or "git apply failed"), patch_present=True, guard_result="SAFE", apply_result=git_apply_out.strip() or "git apply failed")
                                write_codex_patch_apply(run_dir, status="git apply failed", patch_path=str(run_dir / "codex_patch.diff"), guard_out=guard_out, check_out=git_apply_check_out, apply_out=git_apply_out)
                                record_rejected_patch(run_dir, codex_patch, git_apply_out.strip() or "git apply failed", "codex patch apply", approximate=patch_is_approximate(codex_patch) or patch_is_approximate(codex_response))
                                local_status = codex_patch_status
                            else:
                                codex_patch_status = "APPLIED"
                                codex_patch_applied = True
                                write_codex_patch_validation(run_dir, status="APPLIED", reason="Codex patch applied locally after validation.", patch_present=True, guard_result="SAFE", apply_result="applied")
                                write_codex_patch_apply(run_dir, status="applied", patch_path=str(run_dir / "codex_patch.diff"), guard_out=guard_out, check_out=git_apply_check_out, apply_out=git_apply_out)
                                applied_once = True
                                if task_info["test_command"]:
                                    test_rc, test_stdout = run_cmd(["bash", str(scripts / "ws_test_runner.sh"), str(project_dir), str(run_dir), task_info["test_command"], str(args.max_minutes)], timeout=max(args.max_minutes * 60 + 30, 120), run_dir=run_dir, label="test runner codex patch", check=False)
                                else:
                                    test_rc, test_stdout = run_cmd(["bash", str(scripts / "ws_test_runner.sh"), str(project_dir), str(run_dir), "", str(args.max_minutes)], timeout=max(args.max_minutes * 60 + 30, 120), run_dir=run_dir, label="test runner codex patch", check=False)
                                last_test_text = test_stdout
                                write_run_file(run_dir, "test_output.md", test_stdout + "\n")
                                tests_ran = True
                                if test_rc == 0:
                                    tests_passed = True
                                    local_status = "PASSED_WITH_CODEX"
                                else:
                                    local_status = "FAILED_TESTS"
                                    last_test_text = test_stdout
            if codex_patch_status == "not-run":
                codex_patch_status = "BLOCKED_CODEX_ADVICE_ONLY"
        else:
            codex_status = usage.get("status", "BLOCKED_CODEX")
            append_text(run_dir / "local_attempts.md", f"- Codex Status: {codex_status}\n")
            if usage.get("redaction_status") != "SAFE":
                local_status = "SAFETY_BLOCKED"
            else:
                local_status = "BLOCKED_CODEX"
        if bridge_out.strip():
            append_text(run_dir / "local_attempts.md", f"- Codex Bridge Output:\n\n{bridge_out.strip()}\n")

    git_after = git_status(project_dir, run_dir=run_dir)
    changed = parse_changed_files_from_status(git_after)
    if not changed and project_dir.exists() and detect_repo(project_dir, run_dir=run_dir):
        diff_rc, diff_out = run_cmd(["git", "-C", str(project_dir), "diff", "--name-only"], timeout=30, run_dir=run_dir, label="git diff names")
        if diff_rc == 0:
            changed = [line.strip() for line in diff_out.splitlines() if line.strip()]

    if args.plan_only:
        status = "PLAN_ONLY"
    elif tests_passed and changed:
        status = "PASSED_WITH_CODEX" if codex_used else "PASSED"
    elif tests_passed and not changed:
        status = "NO_CHANGES"
    elif codex_used and not tests_passed:
        if local_status in {"BLOCKED_CODEX_ADVICE_ONLY", "BLOCKED_CODEX_PATCH_INVALID", "SAFETY_BLOCKED", "FAILED_TESTS", "NEEDS_USER_REVIEW"}:
            status = local_status
        elif changed:
            status = "NEEDS_USER_REVIEW"
        else:
            status = "BLOCKED_CODEX"
    elif local_status == "SAFETY_BLOCKED":
        status = "SAFETY_BLOCKED"
    elif last_test_text and "No test command found." in last_test_text and docs_only(changed):
        status = "PASSED"
    elif last_test_text and "No test command found." in last_test_text:
        status = "NEEDS_USER_REVIEW"
    elif local_status == "PATCH_INVALID_APPROXIMATE":
        status = "BLOCKED_PATCH_INVALID_APPROXIMATE" if changed else "PATCH_INVALID_APPROXIMATE"
    elif local_status == "PATCH_INVALID":
        status = "BLOCKED_PATCH_INVALID" if changed else "PATCH_INVALID"
    elif local_status == "FAILED_TESTS":
        status = "BLOCKED_LOCAL_WITH_CHANGES" if changed else "FAILED_TESTS"
    elif local_status == "NEEDS_USER_REVIEW":
        status = "NEEDS_USER_REVIEW"
    else:
        if local_status == "BLOCKED_LOCAL" and changed:
            status = "BLOCKED_LOCAL_WITH_CHANGES"
        else:
            status = local_status if local_status != "BLOCKED_LOCAL" else "BLOCKED_LOCAL"

    write_run_file(run_dir, "status.txt", status + "\n")
    write_run_file(run_dir, "git_status_after.md", git_after + "\n")
    if changed:
        diff_parts = []
        diff_rc, diff_out = run_cmd(["git", "-C", str(project_dir), "diff", "--no-ext-diff"], timeout=30, run_dir=run_dir, label="git diff patch")
        if diff_out.strip():
            diff_parts.append(diff_out.strip())
        for line in git_after.splitlines():
            if line.startswith("?? "):
                rel = line[3:].strip()
                if rel:
                    nrc, ndiff = run_cmd(["git", "-C", str(project_dir), "diff", "--no-index", "--", "/dev/null", rel], timeout=30, run_dir=run_dir, label=f"git diff new {rel}")
                    if ndiff.strip():
                        diff_parts.append(ndiff.strip())
        if diff_parts:
            write_run_file(run_dir, "final_diff.patch", "\n\n".join(diff_parts) + "\n")

    run_cmd(["bash", str(scripts / "ws_auto_report.sh"), str(run_dir)], timeout=30, run_dir=run_dir, label="auto report")
    overall_results.append((run_dir, status))

    if args.stop_on_fail and status not in {"PASSED", "PASSED_WITH_CODEX", "PLAN_ONLY", "NO_CHANGES"}:
        break

for run_dir, status in overall_results:
    print(f"{status}: {run_dir}")
PY

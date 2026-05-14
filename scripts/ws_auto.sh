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
        "coder": "You are the local coder for a bounded workstation auto-run. Return only a single unified diff block if safe. The diff must stay within Allowed Files and respect the file count limit. If blocked, say BLOCKED and why. Do not include extra prose unless blocked.",
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
    m = re.search(r"```(?:diff|patch)\s*\n(.*?)```", text, re.S)
    if m:
        return m.group(1).strip() + "\n"
    if "diff --git" in text:
        start = text.index("diff --git")
        return text[start:].strip() + "\n"
    return ""

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

    local_status = "BLOCKED_LOCAL"
    tests_passed = False
    files_changed = []
    final_patch = ""
    proposed_patch = run_dir / "proposed.patch"
    proposed_patch_ready = False
    reviewer_notes = ""
    codex_status = "none"
    codex_used = False
    cloud_attempts = 0
    applied_once = False
    last_test_text = ""
    apply_guard_text = ""
    tests_ran = False

    for attempt in range(1, max(args.max_attempts, 1) + 1):
        append_text(run_dir / "local_attempts.md", f"\n## Attempt {attempt}\n")
        coder_prompt = build_plan_prompt(task_info, graph_context, role="coder", review=reviewer_notes)
        coder_system = "You are the local coder for a bounded workstation auto-run. Return only a single unified diff block if safe. If blocked, say BLOCKED and why."
        coder_response = call_local_model(coder_model, coder_system, coder_prompt, timeout_seconds=180, run_dir=run_dir, label="coder model")
        append_text(run_dir / "local_attempts.md", f"- Coder Model: {coder_model}\n")
        append_text(run_dir / "local_attempts.md", f"- Coder Preview:\n\n{coder_response[:3000]}\n")
        patch = extract_diff(coder_response)
        if not patch:
            reviewer_prompt = build_plan_prompt(task_info, graph_context, role="reviewer")
            reviewer_system = "You are the local reviewer for a bounded workstation auto-run. Explain the smallest safe next fix."
            reviewer_notes = call_local_model(reviewer_model, reviewer_system, reviewer_prompt + "\n\nCurrent coder output:\n\n" + coder_response[:3000], timeout_seconds=180, run_dir=run_dir, label="reviewer model")
            append_text(run_dir / "local_attempts.md", f"- Reviewer Model: {reviewer_model}\n")
            append_text(run_dir / "local_attempts.md", f"- Reviewer Notes:\n\n{reviewer_notes[:3000]}\n")
            continue

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
            reviewer_notes = call_local_model(reviewer_model, "You are the local reviewer for a bounded workstation auto-run. Explain why the patch did not apply cleanly and what the smallest safe next fix is.", coder_prompt + "\n\nPatch:\n\n" + patch + "\n\nApply check output:\n" + git_apply_check_out, timeout_seconds=180, run_dir=run_dir, label="reviewer model")
            append_text(run_dir / "local_attempts.md", f"- Reviewer Model: {reviewer_model}\n")
            append_text(run_dir / "local_attempts.md", f"- Reviewer Notes:\n\n{reviewer_notes[:3000]}\n")
            continue

        git_apply_rc, git_apply_out = run_cmd(["git", "-C", str(project_dir), "apply", str(proposed_patch)], timeout=120, run_dir=run_dir, label="git apply")
        append_text(run_dir / "local_attempts.md", f"- Git Apply Exit: {git_apply_rc}\n\n{git_apply_out.strip()}\n")
        if git_apply_rc != 0:
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
        packet = run_dir / "codex_packet.md"
        packet.write_text(
            "\n".join([
                "# Auto Escalation Packet",
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
                "## Local Plan",
                run_dir.joinpath("local_plan.md").read_text(encoding="utf-8", errors="replace"),
                "",
                "## Apply Guard Reason",
                apply_guard_text or "not run",
                "",
                "## Attempts",
                run_dir.joinpath("local_attempts.md").read_text(encoding="utf-8", errors="replace"),
                "",
                "## Test Output",
                last_test_text or run_dir.joinpath("test_output.md").read_text(encoding="utf-8", errors="replace"),
                "",
                "## Specific Question for Frontier Model",
                "Why did this local build fail/block, and what is the smallest safe next fix?",
                "",
                "## Safety Notice",
                "Secrets, raw datasets, credentials, .env files, private keys, and broker keys were excluded.",
                "",
            ]),
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
            append_text(run_dir / "local_attempts.md", f"- Codex Response:\n\n{codex_response[:4000]}\n")
            codex_advice_only = True
            if codex_response:
                retry_prompt = build_plan_prompt(task_info, graph_context, role="coder", codex=codex_response[:4000], review=reviewer_notes)
                retry_response = call_local_model(coder_model, coder_system, retry_prompt, timeout_seconds=180, run_dir=run_dir, label="coder model retry")
                retry_patch = extract_diff(retry_response)
                append_text(run_dir / "local_attempts.md", f"\n## Codex-Guided Retry\n\n- Coder Model: {coder_model}\n- Preview:\n\n{retry_response[:3000]}\n")
                codex_advice_only = not bool(retry_patch)
                if retry_patch:
                    proposed_patch.write_text(retry_patch, encoding="utf-8", newline="\n")
                    proposed_patch_ready = True
                    guard_rc, guard_out = run_cmd(
                        ["bash", str(scripts / "ws_apply_guard.sh"), str(project_dir), str(proposed_patch), str(allowed_file), str(args.max_files)],
                        timeout=120,
                        run_dir=run_dir,
                        label="apply guard codex retry",
                    )
                    write_run_file(run_dir, "apply_guard.md", (run_dir / "apply_guard.md").read_text(encoding="utf-8", errors="replace") + "\n\n## Codex Retry\n\n" + guard_out.strip() + "\n")
                    if guard_rc == 0 and "SAFE" in guard_out.splitlines()[0:2]:
                        if run_cmd(["git", "-C", str(project_dir), "apply", "--check", str(proposed_patch)], timeout=120, run_dir=run_dir, label="git apply check codex retry")[0] == 0:
                            run_cmd(["git", "-C", str(project_dir), "apply", str(proposed_patch)], timeout=120, run_dir=run_dir, label="git apply codex retry")
                            if task_info["test_command"]:
                                test_rc, test_stdout = run_cmd(["bash", str(scripts / "ws_test_runner.sh"), str(project_dir), str(run_dir), task_info["test_command"], str(args.max_minutes)], timeout=max(args.max_minutes * 60 + 30, 120), run_dir=run_dir, label="test runner codex retry", check=False)
                            else:
                                test_rc, test_stdout = run_cmd(["bash", str(scripts / "ws_test_runner.sh"), str(project_dir), str(run_dir), "", str(args.max_minutes)], timeout=max(args.max_minutes * 60 + 30, 120), run_dir=run_dir, label="test runner codex retry", check=False)
                            write_run_file(run_dir, "test_output.md", test_stdout + "\n")
                            if test_rc == 0:
                                tests_passed = True
                                local_status = "PASSED_WITH_CODEX"
                            else:
                                local_status = "FAILED_TESTS"
                                last_test_text = test_stdout
                    else:
                        append_text(run_dir / "local_attempts.md", "- Codex advice produced no applyable patch.\n")
            if codex_advice_only and not tests_passed:
                local_status = "NEEDS_USER_REVIEW"
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
        if changed:
            status = "NEEDS_USER_REVIEW"
        else:
            status = "BLOCKED_CODEX"
    elif local_status == "SAFETY_BLOCKED":
        status = "SAFETY_BLOCKED"
    elif last_test_text and "No test command found." in last_test_text and docs_only(changed):
        status = "PASSED"
    elif last_test_text and "No test command found." in last_test_text:
        status = "NEEDS_USER_REVIEW"
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

#!/bin/bash

set -euo pipefail

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
REPORTS_DIR="$WS_HOME/reports"
WORKTREES_ROOT="$WS_HOME/worktrees"
AUTO_RUNS_DIR="$WS_HOME/auto_runs"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

PROJECT_KEY=${1:-}
TASK_FILE=${2:-}
DRY_RUN=0
WORKTREE_PATH=""
MAX_FILES=""
MAX_MINUTES=""
STOP_ON_FAIL=0

# Parse arguments
shift 2 || true
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --worktree)
            WORKTREE_PATH="${2:-}"
            shift 2
            ;;
        --max-files)
            MAX_FILES="${2:-}"
            shift 2
            ;;
        --max-minutes)
            MAX_MINUTES="${2:-}"
            shift 2
            ;;
        --stop-on-fail)
            STOP_ON_FAIL=1
            shift
            ;;
        *)
            shift
            ;;
    esac
done

if [ -z "$PROJECT_KEY" ] || [ -z "$TASK_FILE" ]; then
    echo "Usage: ws agent-run-worktree <project_key> <task_file> --worktree <path> --dry-run [flags]"
    exit 1
fi

if [ "$DRY_RUN" -eq 0 ]; then
    echo "Error: --dry-run is mandatory in this MVP."
    exit 1
fi

if [ -z "$WORKTREE_PATH" ]; then
    echo "Error: --worktree <path> is mandatory."
    exit 1
fi

to_wsl_path() {
    case "$1" in
        /*) printf '%s' "$1" ;;
        *) wslpath -u "$1" 2>/dev/null || printf '%s' "$1" ;;
    esac
}

to_windows_path() {
    wslpath -w "$1" 2>/dev/null || printf '%s' "$1"
}

TASK_WSL=$(to_wsl_path "$TASK_FILE")
WORKTREE_WSL=$(to_wsl_path "$WORKTREE_PATH")

NOW_TS=$(date +"%Y%m%d_%H%M%S")
RUN_NAME="${NOW_TS}_${PROJECT_KEY}_$(basename "$TASK_WSL" .md)_worktree_agent_dry_run"
RUN_DIR="$AUTO_RUNS_DIR/$RUN_NAME"

if [ ! -x "$PYTHON" ]; then
    PYTHON="python3"
fi

RESULT_INFO=$( "$PYTHON" - "$PROJECT_KEY" "$TASK_WSL" "$WORKTREE_WSL" "$WS_HOME" "$RUN_DIR" "$NOW_TS" "$MAX_FILES" "$MAX_MINUTES" "$STOP_ON_FAIL" << 'PY'
import sys
import json
import os
import yaml
import subprocess
from pathlib import Path

project_key = sys.argv[1]
task_path = Path(sys.argv[2])
worktree_path = Path(sys.argv[3])
ws_home = Path(sys.argv[4])
run_dir = Path(sys.argv[5])
now_ts = sys.argv[6]
max_files = sys.argv[7]
max_minutes = sys.argv[8]
stop_on_fail = sys.argv[9] == "1"

checks = []
def add_check(name: str, passed: bool, detail: str) -> None:
    checks.append((name, passed, detail))

# 1. Project exists
projects_yaml = ws_home / "registry" / "projects.yaml"
project_found = False
project_data = {}
if projects_yaml.is_file():
    with open(projects_yaml, "r") as f:
        data = yaml.safe_load(f)
        project_data = data.get("projects", {}).get(project_key)
        if project_data:
            project_found = True
add_check("project exists in registry", project_found, project_key if project_found else "not found")

# 2. Task file exists
add_check("task file exists", task_path.is_file(), str(task_path))

# 3. Task has explicit Allowed Files
allowed_files = []
if task_path.is_file():
    content = task_path.read_text(encoding="utf-8")
    import re
    # Try header style first: ## Allowed Files
    match = re.search(r"## Allowed Files\s*\n(.*?)(?:\n##|$)", content, re.DOTALL | re.IGNORECASE)
    if not match:
        # Try colon style: Allowed Files:
        match = re.search(r"Allowed Files:\s*\n(.*?)(?:\n[A-Z]|$)", content, re.DOTALL | re.IGNORECASE)
    
    if match:
        allowed_files = [f.strip("- ").strip() for f in match.group(1).strip().split("\n") if f.strip()]
add_check("task has explicit Allowed Files", len(allowed_files) > 0, f"{len(allowed_files)} files")

# 4. Worktree path exists and is under D:\_ai_brain\worktrees
wt_exists = worktree_path.is_dir()
add_check("worktree path exists", wt_exists, str(worktree_path))

wt_under_root = str(worktree_path).startswith(str(ws_home / "worktrees"))
add_check("worktree path is under approved root", wt_under_root, str(worktree_path))

# 5. Worktree is listed by git worktree list
wt_listed = False
if wt_exists:
    res = subprocess.run(["git", "-C", str(ws_home), "worktree", "list"], capture_output=True, text=True)
    if str(worktree_path) in res.stdout:
        wt_listed = True
add_check("worktree is listed by git worktree list", wt_listed, "Yes" if wt_listed else "No")

# 6. ws worktree-review returns READY
wt_ready = False
wt_branch = "unknown"
wt_head = "unknown"
main_head = "unknown"
if wt_exists:
    # Get latest review report
    reports_dir = ws_home / "reports"
    review_mds = sorted(list(reports_dir.glob("WORKTREE_REVIEW_*.md")), reverse=True)
    
    # Get worktree branch
    wt_branch = subprocess.run(["git", "-C", str(worktree_path), "branch", "--show-current"], capture_output=True, text=True).stdout.strip()
    wt_head = subprocess.run(["git", "-C", str(worktree_path), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    main_head = subprocess.run(["git", "-C", str(ws_home), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()

    for rmd in review_mds:
        rc = rmd.read_text(encoding="utf-8")
        if wt_branch in rc and "Classification**: READY" in rc:
            wt_ready = True
            break
add_check("ws worktree-review returns READY", wt_ready, "READY" if wt_ready else "not ready")

# 7. Worktree git status is clean
wt_clean = False
if wt_exists:
    res = subprocess.run(["git", "-C", str(worktree_path), "status", "--porcelain"], capture_output=True, text=True)
    if not res.stdout.strip():
        wt_clean = True
add_check("worktree git status is clean", wt_clean, "clean" if wt_clean else "dirty")

# 8. Main repo git status is clean
main_clean = False
res = subprocess.run(["git", "-C", str(ws_home), "status", "--porcelain"], capture_output=True, text=True)
if not res.stdout.strip():
    main_clean = True
add_check("main repo git status is clean", main_clean, "clean" if main_clean else "dirty")

passed = all(item[1] for item in checks)

classification = "WORKTREE_AGENT_DRY_RUN_READY" if passed else "WORKTREE_AGENT_DRY_RUN_BLOCKED"

# Create packet folder
run_dir.mkdir(parents=True, exist_ok=True)

(run_dir / "status.txt").write_text(classification, encoding="utf-8")

if task_path.is_file():
    (run_dir / "task.md").write_text(task_path.read_text(encoding="utf-8"), encoding="utf-8")

worktree_context = f"""# Worktree Context
- Path: {worktree_path}
- Branch: {wt_branch}
- HEAD: {wt_head}
- Main HEAD: {main_head}
"""
(run_dir / "worktree_context.md").write_text(worktree_context, encoding="utf-8")

allowed_files_content = "# Allowed Files (Worktree Rooted)\n"
for f in allowed_files:
    allowed_files_content += f"- {f}\n"
(run_dir / "allowed_files.md").write_text(allowed_files_content, encoding="utf-8")

agent_prompt = f"""# Agent Execution Prompt (Theoretical)
Project: {project_key}
Task: {task_path.name}
Worktree: {worktree_path}
Branch: {wt_branch}

## Goal
Execute the implementation plan described in {task_path.name} inside the isolated worktree at {worktree_path}.

## Constraints
- Only mutate files listed in allowed_files.md
- Run tests after modification
- Stop on failure: {stop_on_fail}
"""
(run_dir / "agent_prompt.md").write_text(agent_prompt, encoding="utf-8")

metadata = {
    "timestamp": now_ts,
    "project": project_key,
    "task_file": str(task_path),
    "worktree_path": str(worktree_path),
    "branch": wt_branch,
    "wt_head": wt_head,
    "main_head": main_head,
    "classification": classification,
    "max_files": max_files,
    "max_minutes": max_minutes,
    "stop_on_fail": stop_on_fail,
    "allowed_files": allowed_files
}
(run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

check_rows = "\n".join(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |" for name, ok, detail in checks)
manual_command = f"ws agent-run-worktree {project_key} {task_path.name} --worktree {worktree_path} --apply"

dry_run_report = f"""# Worktree Agent Dry-Run Report

- Timestamp: {now_ts}
- Project: {project_key}
- Task: {task_path}
- Worktree: {worktree_path}
- Classification: {classification}

## Preflight Gates
| Check | Result | Detail |
| --- | --- | --- |
{check_rows}

## Execution Parameters
- Max Files: {max_files or 'default'}
- Max Minutes: {max_minutes or 'default'}
- Stop on Fail: {stop_on_fail}

## Theoretical Commands
A future real execution might use:
`{manual_command}`

**Explicit Statement: No Codex or AI provider was invoked during this dry-run. No files were mutated.**
"""
(run_dir / "dry_run_report.md").write_text(dry_run_report, encoding="utf-8")

print(f"{classification}|{run_dir}|{manual_command}")
PY
)

IFS="|" read -r CLASSIFICATION RUN_DIR_PATH NEXT_ACTION <<< "$RESULT_INFO"

echo "Classification: $CLASSIFICATION"
echo "Run directory: $(to_windows_path "$RUN_DIR_PATH")"
echo "Next safe action: $NEXT_ACTION"

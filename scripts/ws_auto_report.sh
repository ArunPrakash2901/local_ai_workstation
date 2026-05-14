#!/bin/bash
set -euo pipefail

WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
if [ -f "$WS_HOME/scripts/ws_env.sh" ]; then
    source "$WS_HOME/scripts/ws_env.sh"
fi
WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"

RUN_DIR=${1:-}

if [ -z "$RUN_DIR" ]; then
    echo "Usage: ws_auto_report.sh <run_dir>"
    exit 1
fi

RUN_DIR=${RUN_DIR//\\//}
if [[ "$RUN_DIR" =~ ^([A-Za-z]):/(.*)$ ]]; then
    drive=$(echo "${BASH_REMATCH[1]}" | tr 'A-Z' 'a-z')
    RUN_DIR="/mnt/$drive/${BASH_REMATCH[2]}"
fi

if [ ! -d "$RUN_DIR" ]; then
    echo "Run directory not found: $RUN_DIR"
    exit 1
fi

PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

"$PYTHON" - "$RUN_DIR" <<'PY'
import json
import re
import sys
from pathlib import Path

run_dir = Path(sys.argv[1])
project_meta = run_dir.joinpath("project_metadata.md").read_text(encoding="utf-8", errors="replace") if run_dir.joinpath("project_metadata.md").exists() else ""
run_config = run_dir.joinpath("run_config.md").read_text(encoding="utf-8", errors="replace") if run_dir.joinpath("run_config.md").exists() else ""
model_roles = run_dir.joinpath("model_roles.md").read_text(encoding="utf-8", errors="replace") if run_dir.joinpath("model_roles.md").exists() else ""
git_before = run_dir.joinpath("git_status_before.md").read_text(encoding="utf-8", errors="replace") if run_dir.joinpath("git_status_before.md").exists() else ""
git_after = run_dir.joinpath("git_status_after.md").read_text(encoding="utf-8", errors="replace") if run_dir.joinpath("git_status_after.md").exists() else ""
attempts = run_dir.joinpath("local_attempts.md").read_text(encoding="utf-8", errors="replace") if run_dir.joinpath("local_attempts.md").exists() else ""
test_output = run_dir.joinpath("test_output.md").read_text(encoding="utf-8", errors="replace") if run_dir.joinpath("test_output.md").exists() else ""
apply_guard = run_dir.joinpath("apply_guard.md").read_text(encoding="utf-8", errors="replace") if run_dir.joinpath("apply_guard.md").exists() else ""
patch_validation = run_dir.joinpath("patch_validation.md").read_text(encoding="utf-8", errors="replace") if run_dir.joinpath("patch_validation.md").exists() else ""
rejected_patch = run_dir.joinpath("rejected_patch.diff").read_text(encoding="utf-8", errors="replace") if run_dir.joinpath("rejected_patch.diff").exists() else ""
codex_usage = run_dir.joinpath("codex_usage.md").read_text(encoding="utf-8", errors="replace") if run_dir.joinpath("codex_usage.md").exists() else ""
codex_response = run_dir.joinpath("codex_response.md").read_text(encoding="utf-8", errors="replace") if run_dir.joinpath("codex_response.md").exists() else ""
exception_log = run_dir.joinpath("exception.log").read_text(encoding="utf-8", errors="replace") if run_dir.joinpath("exception.log").exists() else ""
status = run_dir.joinpath("status.txt").read_text(encoding="utf-8", errors="replace").strip() if run_dir.joinpath("status.txt").exists() else "unknown"

project_key = re.search(r"(?m)^- Project Key:\s*(.+)$", project_meta)
project_key = project_key.group(1).strip() if project_key else "unknown"
task_line = re.search(r"(?m)^# Task\s+([^\n]+)$", run_dir.joinpath("task.md").read_text(encoding="utf-8", errors="replace")) if run_dir.joinpath("task.md").exists() else None
task_title = task_line.group(1).strip() if task_line else run_dir.name
branch = re.search(r"(?m)^- Git Branch:\s*(.+)$", run_config)
branch = branch.group(1).strip() if branch else "not used"

changed_files = []
project_dir_match = re.search(r"(?m)^- Project Dir:\s*(.+)$", project_meta)
project_dir = project_dir_match.group(1).strip() if project_dir_match else ""
if project_dir:
    try:
        import subprocess
        if Path(project_dir).exists():
            proc = subprocess.run(["git", "-C", project_dir, "diff", "--name-only"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False)
            if proc.returncode == 0:
                changed_files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    except Exception:
        changed_files = []
if not changed_files and git_after:
    for line in git_after.splitlines():
        if line.startswith("?? "):
            changed_files.append(line[3:].strip())
        elif line and not line.startswith("## "):
            changed_files.append(line[3:].strip())
if not changed_files and run_dir.joinpath("final_diff.patch").exists():
    text = run_dir.joinpath("final_diff.patch").read_text(encoding="utf-8", errors="replace")
    changed_files = sorted(set(re.findall(r"^\+\+\+ b/(.+)$", text, re.M)))

if status == "PLAN_ONLY":
    changed_files = []

codex_used = "Sent: true" in codex_usage or "Status: SENT" in codex_usage
if not codex_used and codex_usage.strip().startswith("{"):
    try:
        codex_payload = json.loads(codex_usage)
        codex_used = bool(codex_payload.get("used")) or codex_payload.get("status") == "SENT"
    except Exception:
        pass
tests_passed = "Exit Code: 0" in test_output or status in {"PASSED", "PASSED_WITH_CODEX", "NO_CHANGES"}
files_changed = bool(changed_files)
blocked_with_changes = status in {"BLOCKED_LOCAL_WITH_CHANGES", "BLOCKED_CODEX"} and files_changed

def next_action():
    if status == "PLAN_ONLY":
        return "review plan"
    if status in {"PASSED", "PASSED_WITH_CODEX", "NO_CHANGES"}:
        return "commit changes or mark task complete"
    if status in {"BLOCKED_LOCAL", "BLOCKED_LOCAL_WITH_CHANGES", "BLOCKED_CODEX", "FAILED_TESTS", "SAFETY_BLOCKED", "NEEDS_USER_REVIEW", "FAILED_INTERNAL", "PATCH_INVALID", "BLOCKED_PATCH_INVALID"}:
        return "repair patch or fix task spec"
    if status == "TIMEOUT":
        return "rerun with a smaller scope or more time"
    return "inspect run artifacts"

report = f"""# Auto Run Final Report

## Summary
- Project: {project_key}
- Task: {task_title}
- Final Status: {status}
- Files Changed: {"yes" if files_changed else "no"}
- Tests Passed: {"yes" if tests_passed else "no"}
- Codex Used: {"yes" if codex_used else "no"}
- Branch: {branch}
- Run Folder: {run_dir}
{"- Blocked With Changes: yes" if blocked_with_changes else "- Blocked With Changes: no"}

## What Happened
{attempts.strip() or "No detailed attempt log was written."}

## Files Changed
{chr(10).join(f"- {x}" for x in changed_files) if changed_files else "- none"}

## Test Results
{test_output.strip() or "No test output recorded."}

## Local Model Usage
{model_roles.strip() or "No model role file recorded."}

## Codex Usage
{codex_usage.strip() or "Codex was not used."}

## Safety
{apply_guard.strip() or "No additional safety notes recorded."}

## Patch Validation
{patch_validation.strip() or "No patch validation notes recorded."}

## Rejected Patch
{rejected_patch.strip() or "No rejected patch recorded."}

## Internal Exception
{exception_log.strip() or "none"}

## Recommended Next Action
{next_action()}
"""

run_dir.joinpath("final_report.md").write_text(report, encoding="utf-8", newline="\n")
print(run_dir / "final_report.md")
PY

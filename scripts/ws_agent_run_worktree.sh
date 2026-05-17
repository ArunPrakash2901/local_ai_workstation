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

PROJECT_KEY=""
TASK_FILE=""
DRY_RUN=0
APPLY=0
WORKTREE_PATH=""
FROM_DRY_RUN=""
MAX_FILES=""
MAX_MINUTES=""
STOP_ON_FAIL=0

# Parse arguments
# We expect project_key and task_file as first two positional args if they don't start with --
if [[ $# -gt 0 ]] && [[ "$1" != --* ]]; then
    PROJECT_KEY="$1"
    shift
fi
if [[ $# -gt 0 ]] && [[ "$1" != --* ]]; then
    TASK_FILE="$1"
    shift
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --apply)
            APPLY=1
            shift
            ;;
        --worktree)
            WORKTREE_PATH="${2:-}"
            shift 2
            ;;
        --from-dry-run)
            FROM_DRY_RUN="${2:-}"
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
    echo "Usage: ws agent-run-worktree <project_key> <task_file> [--dry-run | --apply --from-dry-run <packet>] [flags]"
    exit 1
fi

if [ "$DRY_RUN" -eq 0 ] && [ "$APPLY" -eq 0 ]; then
    echo "Error: Must specify either --dry-run or --apply --from-dry-run <packet>."
    exit 1
fi

if [ "$DRY_RUN" -eq 1 ] && [ "$APPLY" -eq 1 ]; then
    echo "Error: Cannot combine --dry-run and --apply."
    exit 1
fi

if [ "$APPLY" -eq 1 ]; then
    if [ -z "$FROM_DRY_RUN" ]; then
        echo "Error: --apply requires --from-dry-run <dry_run_packet_or_report>."
        exit 1
    fi
    if [ -z "$WORKTREE_PATH" ]; then
        # If not provided, we might try to extract it from the dry-run packet later, 
        # but the prompt says --worktree is mandatory in requirements.
        echo "Error: --worktree <path> is mandatory."
        exit 1
    fi
fi

if [ "$DRY_RUN" -eq 1 ] && [ -z "$WORKTREE_PATH" ]; then
    echo "Error: --worktree <path> is mandatory for dry-run."
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
FROM_DRY_RUN_WSL=""
[ -n "$FROM_DRY_RUN" ] && FROM_DRY_RUN_WSL=$(to_wsl_path "$FROM_DRY_RUN")

NOW_TS=$(date +"%Y%m%d_%H%M%S")

if [ ! -x "$PYTHON" ]; then
    PYTHON="python3"
fi

# We use Python for all validation and packet prep to ensure consistency
RESULT_INFO=$( "$PYTHON" - "$PROJECT_KEY" "$TASK_WSL" "$WORKTREE_WSL" "$WS_HOME" "$NOW_TS" "$DRY_RUN" "$APPLY" "$FROM_DRY_RUN_WSL" "$MAX_FILES" "$MAX_MINUTES" "$STOP_ON_FAIL" << 'PY'
import sys
import json
import os
import yaml
import subprocess
import time
from pathlib import Path

project_key = sys.argv[1]
task_path = Path(sys.argv[2])
worktree_path = Path(sys.argv[3])
ws_home = Path(sys.argv[4])
now_ts = sys.argv[5]
is_dry_run = sys.argv[6] == "1"
is_apply = sys.argv[7] == "1"
from_dry_run_path = Path(sys.argv[8]) if sys.argv[8] else None
max_files = sys.argv[9]
max_minutes = sys.argv[10]
stop_on_fail = sys.argv[11] == "1"

def to_win(p):
    if not p: return ""
    try:
        return subprocess.check_output(["wslpath", "-w", str(p)]).decode("utf-8").strip()
    except:
        return str(p)

checks = []
def add_check(name: str, passed: bool, detail: str) -> None:
    checks.append((name, passed, detail))

# 1. Project exists
projects_yaml = ws_home / "registry" / "projects.yaml"
project_found = False
if projects_yaml.is_file():
    with open(projects_yaml, "r") as f:
        data = yaml.safe_load(f)
        project_found = project_key in data.get("projects", {})
add_check("project exists in registry", project_found, project_key if project_found else "not found")

# 2. Task file exists
add_check("task file exists", task_path.is_file(), str(task_path))

# 3. Task has explicit Allowed Files
allowed_files = []
if task_path.is_file():
    content = task_path.read_text(encoding="utf-8")
    import re
    match = re.search(r"## Allowed Files\s*\n(.*?)(?:\n##|$)", content, re.DOTALL | re.IGNORECASE)
    if not match:
        match = re.search(r"Allowed Files:\s*\n(.*?)(?:\n[A-Z]|$)", content, re.DOTALL | re.IGNORECASE)
    if match:
        allowed_files = [f.strip("- ").strip() for f in match.group(1).strip().split("\n") if f.strip()]
add_check("task has explicit Allowed Files", len(allowed_files) > 0, f"{len(allowed_files)} files")

# 4. Worktree path exists
wt_exists = worktree_path.is_dir()
add_check("worktree path exists", wt_exists, str(worktree_path))
add_check("worktree path is under approved root", str(worktree_path).startswith(str(ws_home / "worktrees")), str(worktree_path))

# 5. Worktree is listed
wt_listed = False
if wt_exists:
    res = subprocess.run(["git", "-C", str(ws_home), "worktree", "list"], capture_output=True, text=True)
    if str(worktree_path) in res.stdout:
        wt_listed = True
add_check("worktree is listed by git worktree list", wt_listed, "Yes" if wt_listed else "No")

# 6. READY status
wt_ready = False
wt_branch = "unknown"
wt_head = "unknown"
main_head = "unknown"
if wt_exists:
    wt_branch = subprocess.run(["git", "-C", str(worktree_path), "branch", "--show-current"], capture_output=True, text=True).stdout.strip()
    wt_head = subprocess.run(["git", "-C", str(worktree_path), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    main_head = subprocess.run(["git", "-C", str(ws_home), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    
    reports_dir = ws_home / "reports"
    review_mds = sorted(list(reports_dir.glob("WORKTREE_REVIEW_*.md")), reverse=True)
    for rmd in review_mds:
        rc = rmd.read_text(encoding="utf-8")
        if wt_branch in rc and "Classification**: READY" in rc:
            wt_ready = True
            break
add_check("ws worktree-review returns READY", wt_ready, "READY" if wt_ready else "not ready")

# 7. Clean status
wt_clean = False
if wt_exists:
    res = subprocess.run(["git", "-C", str(worktree_path), "status", "--porcelain"], capture_output=True, text=True)
    wt_clean = not res.stdout.strip()
add_check("worktree git status is clean", wt_clean, "clean" if wt_clean else "dirty")

main_clean = False
res = subprocess.run(["git", "-C", str(ws_home), "status", "--porcelain"], capture_output=True, text=True)
main_clean = not res.stdout.strip()
add_check("main repo git status is clean", main_clean, "clean" if main_clean else "dirty")

# Apply-specific checks
if is_apply:
    packet_valid = False
    if from_dry_run_path:
        # Check if it's a directory or a file
        meta_path = from_dry_run_path / "metadata.json" if from_dry_run_path.is_dir() else None
        if meta_path and meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if meta.get("classification") == "WORKTREE_AGENT_DRY_RUN_READY":
                    # Check matching
                    if (meta.get("project") == project_key and 
                        Path(meta.get("task_file")).resolve() == task_path.resolve() and
                        Path(meta.get("worktree_path")).resolve() == worktree_path.resolve() and
                        meta.get("branch") == wt_branch and
                        meta.get("wt_head") == wt_head):
                        
                        # Recency check (15 mins)
                        try:
                            mtime = meta_path.stat().st_mtime
                            if (time.time() - mtime) < 900: # 15 mins
                                packet_valid = True
                            else:
                                add_check("dry-run packet is recent", False, "stale (> 15 mins)")
                        except:
                            add_check("dry-run packet is recent", False, "unknown age")
                    else:
                        add_check("dry-run packet matches current context", False, "mismatch detected")
            except:
                add_check("dry-run packet is valid", False, "corrupt metadata")
        else:
            add_check("dry-run packet exists", False, "missing metadata.json")
    add_check("dry-run packet is ready and matching", packet_valid, "Yes" if packet_valid else "No")

passed = all(item[1] for item in checks)

if is_dry_run:
    classification = "WORKTREE_AGENT_DRY_RUN_READY" if passed else "WORKTREE_AGENT_DRY_RUN_BLOCKED"
    run_name = f"{now_ts}_{project_key}_{task_path.stem}_worktree_agent_dry_run"
    run_dir = ws_home / "auto_runs" / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    
    (run_dir / "status.txt").write_text(classification, encoding="utf-8")
    (run_dir / "task.md").write_text(task_path.read_text(encoding="utf-8"), encoding="utf-8")
    (run_dir / "worktree_context.md").write_text(f"Path: {worktree_path}\nBranch: {wt_branch}\nHEAD: {wt_head}\nMain HEAD: {main_head}\n", encoding="utf-8")
    (run_dir / "allowed_files.md").write_text("# Allowed Files\n" + "\n".join(f"- {f}" for f in allowed_files), encoding="utf-8")
    (run_dir / "agent_prompt.md").write_text(f"Run implementation for {task_path.name} in {worktree_path}", encoding="utf-8")
    
    metadata = {
        "timestamp": now_ts, "project": project_key, "task_file": str(task_path),
        "worktree_path": str(worktree_path), "branch": wt_branch, "wt_head": wt_head,
        "main_head": main_head, "classification": classification,
        "max_files": max_files, "max_minutes": max_minutes, "stop_on_fail": stop_on_fail,
        "allowed_files": allowed_files
    }
    (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    
    check_rows = "\n".join(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |" for name, ok, detail in checks)
    dry_run_report = f"""# Worktree Agent Dry-Run Report\n\n- Timestamp: {now_ts}\n- Classification: {classification}\n\n## Preflight Gates\n{check_rows}\n\n**No files were mutated.**"""
    (run_dir / "dry_run_report.md").write_text(dry_run_report, encoding="utf-8")
    
    print(f"{classification}|{to_win(run_dir)}|ws agent-run-worktree {project_key} {task_path.name} --worktree {worktree_path} --apply --from-dry-run {run_dir}")
    sys.exit(0)

if is_apply:
    if not passed:
        classification = "WORKTREE_AGENT_APPLY_BLOCKED"
        print(f"{classification}|NONE|Resolve blockers: " + ", ".join(n for n, ok, _ in checks if not ok))
        sys.exit(1)
    
    # Return signal to Bash to proceed with execution
    # Output: SIGNAL|WORKTREE_PATH_WIN|TASK_FILE_WIN|MAX_FILES|MAX_MINUTES|STOP_ON_FAIL|ALLOWED_FILES_JSON
    print(f"PROCEED|{to_win(worktree_path)}|{to_win(task_path)}|{max_files}|{max_minutes}|{stop_on_fail}|{json.dumps(allowed_files)}")
    sys.exit(0)
PY
)

if [[ "$RESULT_INFO" == PROCEED* ]]; then
    IFS="|" read -r SIGNAL WT_WIN TASK_WIN MFILES MMINS SOF ALLOWED_JSON <<< "$RESULT_INFO"
    
    # We are ready to execute
    echo "Preflight PASS. Starting worktree agent execution..."
    
    # Construct runner arguments
    AGENT_ARGS=( -NoProfile -ExecutionPolicy Bypass -File "$(wslpath -w "$WS_HOME/scripts/ws_agent_run.ps1")" -Command Run -ProjectKey "$PROJECT_KEY" -TaskFile "$TASK_WIN" -RepoOverride "$WT_WIN" )
    [ -n "$MFILES" ] && AGENT_ARGS+=( -MaxFiles "$MFILES" )
    [ -n "$MMINS" ] && AGENT_ARGS+=( -MaxMinutes "$MMINS" )
    [ "$SOF" -eq 1 ] && AGENT_ARGS+=( -StopOnFail )
    
    START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # Capture pre-run status
    GIT_STATUS_BEFORE=$(git -C "$WORKTREE_WSL" status --short --branch)
    
    # RUN IT
    set +e
    powershell.exe "${AGENT_ARGS[@]}" > /tmp/codex_stdout.log 2> /tmp/codex_stderr.log
    EXIT_CODE=$?
    set -e
    
    END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # Extract the run folder from stdout
    # ws_agent_run.ps1 outputs: STATUS \n RUN_FOLDER \n REPORT_PATH
    RUN_DIR_WIN=$(tail -n 2 /tmp/codex_stdout.log | head -n 1 | tr -d '\r')
    RUN_DIR_WSL=$(to_wsl_path "$RUN_DIR_WIN")
    
    # Post-process artifacts
    mv /tmp/codex_stdout.log "$RUN_DIR_WSL/codex_stdout.md"
    mv /tmp/codex_stderr.log "$RUN_DIR_WSL/codex_stderr.md"
    echo "$EXIT_CODE" > "$RUN_DIR_WSL/codex_exit_code.txt"
    echo "$GIT_STATUS_BEFORE" > "$RUN_DIR_WSL/git_status_before.md"
    git -C "$WORKTREE_WSL" status --short --branch > "$RUN_DIR_WSL/git_status_after.md"
    git -C "$WORKTREE_WSL" diff --stat > "$RUN_DIR_WSL/git_diff_stat.md"
    
    # Resolve Changed Files
    CHANGED_FILES=$(git -C "$WORKTREE_WSL" status --porcelain | cut -c 4-)
    echo "$CHANGED_FILES" > "$RUN_DIR_WSL/changed_files.md"
    
    # Enforce Allowed Files
    CLASSIFICATION="CODEX_COMPLETED_SAFE_DIFF"
    UNSAFE_FILES=""
    
    # Use Python for strict set intersection logic
    $PYTHON -c "
import json
import sys
allowed = set(json.loads(sys.argv[1]))
changed = set(sys.argv[2].splitlines())
unsafe = changed - allowed
if unsafe:
    print('UNSAFE|' + ','.join(unsafe))
elif not changed:
    print('NODIFF')
else:
    print('SAFE')
" "$ALLOWED_JSON" "$CHANGED_FILES" > /tmp/check_result.txt
    
    VAL_RES=$(cat /tmp/check_result.txt)
    if [[ "$VAL_RES" == UNSAFE* ]]; then
        CLASSIFICATION="CODEX_COMPLETED_UNSAFE_DIFF"
        UNSAFE_FILES=${VAL_RES#UNSAFE|}
    elif [ "$VAL_RES" == "NODIFF" ]; then
        CLASSIFICATION="CODEX_COMPLETED_NO_DIFF"
    fi
    
    if [ "$EXIT_CODE" -ne 0 ]; then
        CLASSIFICATION="CODEX_FAILED_PROVIDER"
    fi
    
    echo "$CLASSIFICATION" > "$RUN_DIR_WSL/status.txt"
    
    # Final Report
    cat <<EOF > "$RUN_DIR_WSL/final_report.md"
# Worktree Agent Execution Report

- Timestamp: $NOW_TS
- Project: $PROJECT_KEY
- Task: $TASK_FILE
- Worktree: $WORKTREE_PATH
- Classification: $CLASSIFICATION
- Start: $START_TIME
- End: $END_TIME
- Exit Code: $EXIT_CODE

## Differential Analysis
- Files Changed:
$([ -n "$CHANGED_FILES" ] && echo "$CHANGED_FILES" | sed 's/^/- /' || echo "- none")

- Unsafe Changes:
$([ -n "$UNSAFE_FILES" ] && echo "$UNSAFE_FILES" | tr ',' '\n' | sed 's/^/- /' || echo "- none")

## Artifacts
- [stdout](codex_stdout.md)
- [stderr](codex_stderr.md)
- [diff stat](git_diff_stat.md)

## Next Action
Review changes in worktree using \`ws worktree-review $WORKTREE_PATH\`.
EOF

    echo "Classification: $CLASSIFICATION"
    echo "Run directory: $RUN_DIR_WIN"
    echo "Final report: $RUN_DIR_WIN\\final_report.md"
    
else
    # Dry run or blocked apply
    IFS="|" read -r CLASSIFICATION RUN_DIR_PATH NEXT_ACTION <<< "$RESULT_INFO"
    echo "Classification: $CLASSIFICATION"
    echo "Run directory: $RUN_DIR_PATH"
    echo "Next safe action: $NEXT_ACTION"
fi

#!/bin/bash

set -euo pipefail

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
FEATURES_DIR="$WS_HOME/features"
RUNS_DIR="$WS_HOME/runs"
REPORTS_DIR="$WS_HOME/reports"
HANDOFFS_DIR="$WS_HOME/handoffs"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

FEATURE_INPUT=${1:-}
DRY_RUN=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        *)
            if [ -z "$FEATURE_INPUT" ] || [[ "$1" != --* ]]; then
                FEATURE_INPUT="$1"
            fi
            shift
            ;;
    esac
done

if [ -z "$FEATURE_INPUT" ]; then
    echo "Usage: ws feature-run <feature_id_or_path> --dry-run"
    exit 1
fi

if [ "$DRY_RUN" -eq 0 ]; then
    echo "Error: --dry-run is mandatory in this MVP."
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

resolve_feature_dir() {
    local candidate
    candidate=$(to_wsl_path "$FEATURE_INPUT")
    if [ -d "$candidate" ]; then
        printf '%s\n' "$candidate"
        return
    fi
    
    if [ -d "$FEATURES_DIR" ]; then
        for proj_dir in "$FEATURES_DIR"/*; do
            if [ -d "$proj_dir" ] && [ -d "$proj_dir/$FEATURE_INPUT" ]; then
                printf '%s\n' "$proj_dir/$FEATURE_INPUT"
                return
            fi
        done
    fi
    
    return 1
}

FEATURE_DIR=$(resolve_feature_dir) || {
    echo "Error: Feature not found: $FEATURE_INPUT"
    exit 1
}

if [ ! -x "$PYTHON" ]; then
    PYTHON="python3"
fi

NOW_TS=$(date +"%Y%m%d_%H%M%S")

RESULT_INFO=$( "$PYTHON" - "$FEATURE_DIR" "$WS_HOME" "$NOW_TS" << 'PY'
import sys
import json
import subprocess
import glob
from pathlib import Path

feature_dir = Path(sys.argv[1])
ws_home = Path(sys.argv[2])
now_ts = sys.argv[3]

state_path = feature_dir / "state.json"
state = {}
if state_path.is_file():
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        pass

checks = []

def add_check(name: str, passed: bool, detail: str) -> None:
    checks.append((name, passed, detail))

# Gates
current_state = state.get("current_state", "")
add_check("feature state is VALIDATED_LOCAL", current_state == "VALIDATED_LOCAL", current_state or "missing")

validation_result = state.get("validation_result", "")
if not validation_result:
    validation_mds = sorted(feature_dir.glob("evidence/validation_*.md"), reverse=True)
    if validation_mds:
        content = validation_mds[0].read_text(encoding="utf-8")
        if "Result: PASS" in content:
            validation_result = "PASS"

add_check("latest validation result is PASS", validation_result == "PASS", validation_result or "missing")

# Latest handoff review
feature_id = feature_dir.name
handoffs_dir = ws_home / "handoffs"
handoff_review_status = "UNKNOWN"
if handoffs_dir.is_dir():
    matched_handoffs = []
    for hd in handoffs_dir.iterdir():
        if hd.is_dir():
            meta_path = hd / "metadata.json"
            if meta_path.is_file():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    if meta.get("feature_id") == feature_id:
                        matched_handoffs.append(hd)
                except Exception:
                    pass
    matched_handoffs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    if matched_handoffs:
        latest_handoff = matched_handoffs[0]
        review_file = latest_handoff / "review.md"
        if review_file.is_file():
            content = review_file.read_text(encoding="utf-8").lower()
            if "status: accepted" in content or "review_accepted" in content or "status: review_accepted" in content:
                handoff_review_status = "REVIEW_ACCEPTED"
            else:
                handoff_review_status = "REVIEW_REJECTED"
        else:
            handoff_review_status = "NO_REVIEW_FILE"
    else:
        handoff_review_status = "NO_HANDOFF_DIR"

add_check("latest handoff review is REVIEW_ACCEPTED", handoff_review_status == "REVIEW_ACCEPTED", handoff_review_status)

# Repo is clean
repo_path = state.get("repo_path", "")
repo_is_git = False
repo_status = "unknown"
if repo_path and Path(repo_path).is_dir():
    repo_is_git = subprocess.run(
        ["git", "-C", repo_path, "rev-parse", "--is-inside-work-tree"],
        check=False, capture_output=True, text=True
    ).returncode == 0
    if repo_is_git:
        repo_status = subprocess.run(
            ["git", "-C", repo_path, "status", "--short"],
            check=False, capture_output=True, text=True
        ).stdout.strip()

add_check("repo is clean", repo_is_git and not repo_status, repo_status or "clean")

# Allowed files are explicit
allowed_files = state.get("allowed_files", [])
add_check("allowed files are explicit", len(allowed_files) > 0, f"{len(allowed_files)} files")

# ws ready evidence
reports_dir = ws_home / "reports"
ready_mds = sorted(list(reports_dir.glob("readiness_*.md")) + list(reports_dir.glob("READINESS_*.md")), reverse=True)
ready_exists = len(ready_mds) > 0
add_check("ws ready evidence exists", ready_exists, ready_mds[0].name if ready_exists else "missing")

# ws agent-hygiene evidence
hygiene_mds = sorted(list(reports_dir.glob("agent_hygiene_*.md")) + list(reports_dir.glob("AGENT_HYGIENE_*.md")), reverse=True)
hygiene_exists = len(hygiene_mds) > 0
add_check("ws agent-hygiene evidence exists", hygiene_exists, hygiene_mds[0].name if hygiene_exists else "missing")

# final_report.md exists
report_path = feature_dir / "final_report.md"
report_exists = report_path.is_file()
add_check("final_report.md exists", report_exists, "found" if report_exists else "missing")

passed = all(item[1] for item in checks)

classification = "FEATURE_RUN_DRY_READY"
if not passed:
    if current_state != "VALIDATED_LOCAL":
        classification = "FEATURE_RUN_REQUIRES_VALIDATED_LOCAL"
    elif handoff_review_status != "REVIEW_ACCEPTED":
        classification = "FEATURE_RUN_REQUIRES_REVIEW_ACCEPTED"
    elif repo_status != "" and repo_status != "unknown":
        classification = "FEATURE_RUN_REQUIRES_CLEAN_REPO"
    elif not report_exists:
        classification = "FEATURE_RUN_REQUIRES_REPORT"
    else:
        classification = "FEATURE_RUN_BLOCKED"

next_action = "Feature is ready for future supervised execution lane (dry-run passed)" if passed else "Resolve blocked gates before feature run"

worktree_status = "missing"
worktrees_dir = ws_home / "worktrees"
if worktrees_dir.is_dir():
    worktrees = [d for d in worktrees_dir.iterdir() if d.is_dir() and feature_id in d.name]
    if worktrees:
        worktree_status = "exists"

# Write run report
runs_dir = feature_dir / "runs"
runs_dir.mkdir(parents=True, exist_ok=True)
run_report_path = runs_dir / f"feature_run_dry_run_{now_ts}.md"

def status_mark(value: bool) -> str:
    return "PASS" if value else "FAIL"

check_rows = "\n".join(f"| {name} | {status_mark(ok)} | {detail} |" for name, ok, detail in checks)

report_content = f"""# Feature Run Dry-Run Report

- Timestamp: {now_ts}
- Feature ID: {feature_id}
- Feature Path: {feature_dir}
- Classification: {classification}

## Preflight Gates

| Check | Result | Detail |
| --- | --- | --- |
{check_rows}

## Execution Status
- Reviewed Worktree: {worktree_status}
- Next Safe Action: {next_action}
"""

run_report_path.write_text(report_content, encoding="utf-8", newline="\n")

# Append to loop_log.md
loop_log_path = feature_dir / "loop_log.md"
loop_entry = f"""
## {now_ts} - Feature Run Dry-Run Evaluated
- Actor: local
- Classification: {classification}
- Preflight: {"PASS" if passed else "FAIL"}
- Report: {run_report_path}
"""
if loop_log_path.is_file():
    with loop_log_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(loop_entry)

blockers = [name for name, ok, _ in checks if not ok]
blocker_str = ", ".join(blockers) if blockers else "none"

print(classification)
print(run_report_path)
print(blocker_str)
print(next_action)

PY
)

mapfile -t RESULT_FIELDS <<< "$RESULT_INFO"
CLASSIFICATION=${RESULT_FIELDS[0]:-UNKNOWN}
REPORT_PATH=${RESULT_FIELDS[1]:-}
BLOCKERS=${RESULT_FIELDS[2]:-none}
NEXT_ACTION=${RESULT_FIELDS[3]:-}

echo "Classification: $CLASSIFICATION"
echo "Feature path: $(to_windows_path "$FEATURE_DIR")"
echo "Run report path: $(to_windows_path "$REPORT_PATH")"
echo "Blockers: $BLOCKERS"
echo "Next safe action: $NEXT_ACTION"

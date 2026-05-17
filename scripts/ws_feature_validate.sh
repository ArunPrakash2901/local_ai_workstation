#!/bin/bash

set -euo pipefail

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
FEATURES_DIR="$WS_HOME/features"
REPORTS_DIR="$WS_HOME/reports"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

FEATURE_INPUT=${1:-}
if [ -z "$FEATURE_INPUT" ]; then
    echo "Usage: ws feature-validate <feature_id_or_path>"
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

latest_report() {
    local pattern=$1
    find "$REPORTS_DIR" -maxdepth 1 -type f -name "$pattern" -printf '%T@ %p\n' 2>/dev/null \
        | sort -nr \
        | head -n 1 \
        | cut -d' ' -f2-
}

resolve_feature_dir() {
    local candidate
    candidate=$(to_wsl_path "$FEATURE_INPUT")
    if [ -d "$candidate" ]; then
        printf '%s\n' "$candidate"
        return
    fi

    if [ ! -d "$FEATURES_DIR" ]; then
        echo "Feature stronghold root not found: $FEATURES_DIR" >&2
        return 1
    fi

    mapfile -t matches < <(
        find "$FEATURES_DIR" -mindepth 2 -maxdepth 2 -type d -name "$FEATURE_INPUT" 2>/dev/null | sort
    )

    case "${#matches[@]}" in
        0)
            echo "Feature stronghold not found: $FEATURE_INPUT" >&2
            return 1
            ;;
        1)
            printf '%s\n' "${matches[0]}"
            ;;
        *)
            echo "Feature id is ambiguous: $FEATURE_INPUT" >&2
            printf 'Matches:\n' >&2
            printf '  %s\n' "${matches[@]}" >&2
            return 1
            ;;
    esac
}

FEATURE_DIR=$(resolve_feature_dir)
VALIDATED_AT=$(date +%Y%m%d_%H%M%S)
LATEST_READINESS=$(latest_report 'READINESS_*.md')

RESULT_INFO=$(
    "$PYTHON" - \
        "$FEATURE_DIR" \
        "$VALIDATED_AT" \
        "$LATEST_READINESS" <<'PY'
import json
import re
import subprocess
import sys
from pathlib import Path

feature_dir = Path(sys.argv[1])
validated_at = sys.argv[2]
latest_readiness = sys.argv[3]

required_files = [
    "state.json",
    "feature_contract.md",
    "acceptance_criteria.md",
    "allowed_files.md",
    "validation_plan.md",
    "current_plan.md",
]

checks = []

def add_check(name: str, passed: bool, detail: str) -> None:
    checks.append((name, passed, detail))

for name in required_files:
    add_check(
        f"required file: {name}",
        feature_dir.joinpath(name).is_file(),
        str(feature_dir / name),
    )

state_path = feature_dir / "state.json"
state = {}
state_error = ""
if state_path.is_file():
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        state_error = str(exc)
add_check("state.json readable", bool(state) and not state_error, state_error or "parsed")

current_state = state.get("current_state", "")
add_check(
    "state allowed for validation",
    current_state in {"CREATED", "LOCAL_PLAN_READY"},
    current_state or "missing",
)

allowed_files = state.get("allowed_files") or []
allowed_file_entries = []
allowed_path = feature_dir / "allowed_files.md"
if allowed_path.is_file():
    allowed_text = allowed_path.read_text(encoding="utf-8")
    match = re.search(r"(?ms)^## Allowed\s*\n(.*?)(?=^## |\Z)", allowed_text)
    if match:
        allowed_file_entries = [
            line.strip()
            for line in match.group(1).splitlines()
            if line.strip().startswith("- ")
        ]
add_check(
    "allowed files explicit",
    bool(allowed_files) and bool(allowed_file_entries),
    f"state_count={len(allowed_files)}, markdown_count={len(allowed_file_entries)}",
)

source_task = state.get("source_task", "")
add_check("source task exists", bool(source_task) and Path(source_task).is_file(), source_task or "missing")

repo_path = state.get("repo_path", "")
repo_exists = bool(repo_path) and Path(repo_path).is_dir()
add_check("repo path exists", repo_exists, repo_path or "missing")

repo_is_git = False
repo_status = ""
actual_branch = ""
actual_commit = ""
if repo_exists:
    repo_is_git = subprocess.run(
        ["git", "-C", repo_path, "rev-parse", "--is-inside-work-tree"],
        check=False,
        capture_output=True,
        text=True,
    ).returncode == 0
    if repo_is_git:
        repo_status = subprocess.run(
            ["git", "-C", repo_path, "status", "--short"],
            check=False,
            capture_output=True,
            text=True,
        ).stdout.strip()
        actual_branch = subprocess.run(
            ["git", "-C", repo_path, "branch", "--show-current"],
            check=False,
            capture_output=True,
            text=True,
        ).stdout.strip()
        actual_commit = subprocess.run(
            ["git", "-C", repo_path, "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        ).stdout.strip()
add_check("repo is a Git repo", repo_is_git, repo_path or "missing")
add_check("repo status is clean", repo_is_git and not repo_status, repo_status or "clean")

recorded_branch = state.get("current_branch", "")
recorded_commit = state.get("current_commit", "")
add_check("current branch recorded", bool(recorded_branch), recorded_branch or "missing")
add_check("current commit recorded", bool(recorded_commit), recorded_commit or "missing")

readiness_exists = bool(latest_readiness) and Path(latest_readiness).is_file()
add_check("local readiness report exists", readiness_exists, latest_readiness or "not found")
add_check(
    "provider invocation disabled",
    state.get("provider_invocation") is False,
    str(state.get("provider_invocation")),
)
add_check(
    "browser automation disabled",
    state.get("browser_automation") is False,
    str(state.get("browser_automation")),
)

passed = all(item[1] for item in checks)
validation_result = "PASS" if passed else "FAIL"
next_state = "VALIDATED_LOCAL" if passed else "BLOCKED"
next_action = (
    "review the evidence; execution commands remain disabled."
    if passed
    else "resolve the failed checks, run `ws feature-plan` again, then re-run `ws feature-validate`."
)

evidence_dir = feature_dir / "evidence"
evidence_dir.mkdir(parents=True, exist_ok=True)
evidence_path = evidence_dir / f"validation_{validated_at}.md"

def status_mark(value: bool) -> str:
    return "PASS" if value else "FAIL"

check_rows = "\n".join(
    f"| {name} | {status_mark(ok)} | {detail} |"
    for name, ok, detail in checks
)
failed_checks = [name for name, ok, _ in checks if not ok]
failed_md = "\n".join(f"- {name}" for name in failed_checks) if failed_checks else "- none"
repo_status_block = repo_status or "clean"

evidence = f"""# Local Feature Validation

- Timestamp: {validated_at}
- Feature ID: {state.get("feature_id", "unknown")}
- Title: {state.get("title", "unknown")}
- Project: {state.get("project_key", "unknown")}
- Result: {validation_result}
- Prior State: {current_state or "missing"}
- Next State: {next_state}
- Provider Invocation: false
- Browser Automation: false

## Checks

| Check | Result | Detail |
| --- | --- | --- |
{check_rows}

## Failed Checks

{failed_md}

## Local Evidence

- Source Task: {source_task or "missing"}
- Repository Path: {repo_path or "missing"}
- Recorded Branch: {recorded_branch or "missing"}
- Recorded Commit: {recorded_commit or "missing"}
- Actual Branch: {actual_branch or "unavailable"}
- Actual Commit: {actual_commit or "unavailable"}
- Latest Readiness Report: {latest_readiness or "not found"}

### Current Git Status

```text
{repo_status_block}
```

## Safety Statement

- `ws feature-validate` inspected local files, Git metadata, and local readiness evidence only.
- No provider, browser automation, agent, apply path, worktree creation, or project mutation was run.

## Next Safe Action

{next_action}
"""

if state:
    state["current_state"] = next_state
    state["last_validated_at"] = validated_at
    state["validation_result"] = validation_result
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8", newline="\n")

loop_log_path = feature_dir / "loop_log.md"
loop_entry = f"""
## {validated_at} - Local Validation
- Actor: local
- Prior state: {current_state or "missing"}
- State: {next_state}
- Validation result: {validation_result}
- Evidence: {evidence_path}
- Provider invocation: false
- Browser automation: false
- Next safe action: {next_action}
"""
with loop_log_path.open("a", encoding="utf-8", newline="\n") as handle:
    handle.write(loop_entry)

evidence_path.write_text(evidence, encoding="utf-8", newline="\n")

print(validation_result)
print(next_state)
print(evidence_path)
print(next_action)
PY
)

mapfile -t RESULT_FIELDS <<< "$RESULT_INFO"
VALIDATION_RESULT=${RESULT_FIELDS[0]:-UNKNOWN}
NEXT_STATE=${RESULT_FIELDS[1]:-UNKNOWN}
EVIDENCE_PATH=${RESULT_FIELDS[2]:-}
NEXT_ACTION=${RESULT_FIELDS[3]:-"inspect validation evidence"}

echo "Validation result: $VALIDATION_RESULT"
echo "Feature path: $(to_windows_path "$FEATURE_DIR")"
echo "Evidence path: $(to_windows_path "$EVIDENCE_PATH")"
echo "State: $NEXT_STATE"
echo "Next safe action: $NEXT_ACTION"

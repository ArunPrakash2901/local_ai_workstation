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
    echo "Usage: ws feature-plan <feature_id_or_path>"
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
REQUIRED_FILES=(
    "state.json"
    "feature_contract.md"
    "acceptance_criteria.md"
    "allowed_files.md"
    "validation_plan.md"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$FEATURE_DIR/$file" ]; then
        echo "Feature stronghold is missing required file: $FEATURE_DIR/$file"
        exit 1
    fi
done

STATE_INFO=$(
    "$PYTHON" - "$FEATURE_DIR/state.json" <<'PY'
import json
import sys
from pathlib import Path

state = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(state.get("repo_path", ""))
print(state.get("feature_id", ""))
print(state.get("title", ""))
print(state.get("project_key", ""))
print(state.get("source_task", ""))
print(state.get("current_state", ""))
PY
)
mapfile -t STATE_FIELDS <<< "$STATE_INFO"
REPO_PATH=${STATE_FIELDS[0]:-}
FEATURE_ID=${STATE_FIELDS[1]:-}
TITLE=${STATE_FIELDS[2]:-}
PROJECT_KEY=${STATE_FIELDS[3]:-}
SOURCE_TASK=${STATE_FIELDS[4]:-}
PRIOR_STATE=${STATE_FIELDS[5]:-UNKNOWN}

if [ -z "$REPO_PATH" ] || [ ! -d "$REPO_PATH" ]; then
    echo "Repository path from state.json is unavailable: $REPO_PATH"
    exit 1
fi

if ! git -C "$REPO_PATH" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Repository path from state.json is not a Git repository: $REPO_PATH"
    exit 1
fi

PLANNED_AT=$(date +%Y%m%d_%H%M%S)
BRANCH=$(git -C "$REPO_PATH" branch --show-current 2>/dev/null || true)
COMMIT=$(git -C "$REPO_PATH" rev-parse HEAD 2>/dev/null || true)
GIT_STATUS=$(git -C "$REPO_PATH" status --short --branch 2>/dev/null || true)
LATEST_READINESS=$(latest_report 'READINESS_*.md')
LATEST_HYGIENE=$(latest_report 'AGENT_HYGIENE_*.md')
LATEST_WORKTREE_STATUS=$(latest_report 'WORKTREE_STATUS_*.md')

"$PYTHON" - \
    "$FEATURE_DIR" \
    "$PLANNED_AT" \
    "$BRANCH" \
    "$COMMIT" \
    "$GIT_STATUS" \
    "$LATEST_READINESS" \
    "$LATEST_HYGIENE" \
    "$LATEST_WORKTREE_STATUS" \
    "$PRIOR_STATE" <<'PY'
import json
import re
import sys
from pathlib import Path

(
    feature_dir,
    planned_at,
    branch,
    commit,
    git_status,
    latest_readiness,
    latest_hygiene,
    latest_worktree_status,
    prior_state,
) = sys.argv[1:]

feature_dir = Path(feature_dir)
state_path = feature_dir / "state.json"
contract_path = feature_dir / "feature_contract.md"
acceptance_path = feature_dir / "acceptance_criteria.md"
allowed_path = feature_dir / "allowed_files.md"
validation_path = feature_dir / "validation_plan.md"
current_plan_path = feature_dir / "current_plan.md"
loop_log_path = feature_dir / "loop_log.md"

state = json.loads(state_path.read_text(encoding="utf-8"))
contract_text = contract_path.read_text(encoding="utf-8")
acceptance_text = acceptance_path.read_text(encoding="utf-8").strip()
allowed_text = allowed_path.read_text(encoding="utf-8").strip()
validation_text = validation_path.read_text(encoding="utf-8").strip()

def section(text: str, heading: str) -> str:
    pattern = rf"(?ms)^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else "not specified"

def display_path(path: str) -> str:
    return path if path else "not found"

objective = section(contract_text, "Objective")
acceptance_items = [
    line.strip()
    for line in acceptance_text.splitlines()
    if line.strip().startswith("- ")
]
acceptance = "\n".join(acceptance_items) if acceptance_items else "not specified"
allowed = section(allowed_text, "Allowed")
git_status_display = git_status.strip() or "clean"

current_plan = f"""# Current Plan

## Feature
- Feature ID: {state.get("feature_id", "unknown")}
- Title: {state.get("title", "unknown")}
- Project: {state.get("project_key", "unknown")}
- Source Task: {state.get("source_task", "unknown")}

## Objective
{objective}

## Acceptance Criteria
{acceptance}

## Allowed Files
{allowed}

## Local Evidence Used
- Current Branch: {branch or "unknown"}
- Current Commit: {commit or "unknown"}
- Source Task: {state.get("source_task", "unknown")}
- Latest Readiness Report: {display_path(latest_readiness)}
- Latest Agent Hygiene Report: {display_path(latest_hygiene)}
- Latest Worktree Status Report: {display_path(latest_worktree_status)}
- Feature inputs read: `state.json`, `feature_contract.md`, `acceptance_criteria.md`, `allowed_files.md`, `validation_plan.md`

### Current Git Status
```text
{git_status_display}
```

## Validation Boundary Consulted
{validation_text}

## Recommended Next Safe Action
Review this local plan against the feature contract and acceptance criteria. No execution path is enabled by `ws feature-plan`; remain in the local-only lane until a later supervised feature command is added.

## Safety Statement
- Provider invocation: false
- Browser automation: false
- Apply run: false
- `ws feature-plan` used local files and Git metadata only; no provider or apply command was run.
"""

state["current_state"] = "LOCAL_PLAN_READY"
state["last_planned_at"] = planned_at
state["current_branch"] = branch
state["current_commit"] = commit
state["provider_invocation"] = False
state["browser_automation"] = False

loop_entry = f"""
## {planned_at} - Local Plan Generated
- Actor: local
- Prior state: {prior_state or "UNKNOWN"}
- State: LOCAL_PLAN_READY
- Current branch: {branch or "unknown"}
- Current commit: {commit or "unknown"}
- Readiness report: {display_path(latest_readiness)}
- Agent hygiene report: {display_path(latest_hygiene)}
- Worktree status report: {display_path(latest_worktree_status)}
- Provider invocation: false
- Browser automation: false
- Apply run: false
- Next safe action: review `current_plan.md`; no execution path has been enabled.
"""

current_plan_path.write_text(current_plan, encoding="utf-8", newline="\n")
with loop_log_path.open("a", encoding="utf-8", newline="\n") as handle:
    handle.write(loop_entry)
state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8", newline="\n")
PY

echo "Feature plan updated: $(to_windows_path "$FEATURE_DIR/current_plan.md")"
echo "Feature ID: $FEATURE_ID"
echo "Project: $PROJECT_KEY"
echo "State: LOCAL_PLAN_READY"
echo "Branch: ${BRANCH:-unknown}"
echo "Commit: ${COMMIT:-unknown}"
echo "Provider invocation: false"
echo "Browser automation: false"
echo "Next safe action: review current_plan.md; no apply or provider path was run."

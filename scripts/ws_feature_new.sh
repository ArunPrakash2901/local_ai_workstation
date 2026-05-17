#!/bin/bash

set -euo pipefail

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
FEATURES_DIR="$WS_HOME/features"
PROJECTS_YAML="$WS_HOME/registry/projects.yaml"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

PROJECT_KEY=${1:-}
shift || true

TITLE=""
TASK_FILE_INPUT=""

while [ $# -gt 0 ]; do
    case "$1" in
        --title)
            TITLE=${2:-}
            shift 2
            ;;
        --from-task)
            TASK_FILE_INPUT=${2:-}
            shift 2
            ;;
        *)
            echo "Usage: ws feature-new <project_key> --title \"<title>\" --from-task <task_file>"
            exit 1
            ;;
    esac
done

if [ -z "$PROJECT_KEY" ] || [ -z "$TITLE" ] || [ -z "$TASK_FILE_INPUT" ]; then
    echo "Usage: ws feature-new <project_key> --title \"<title>\" --from-task <task_file>"
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

safe_slug() {
    printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//'
}

TASK_FILE=$(to_wsl_path "$TASK_FILE_INPUT")
if [ ! -f "$TASK_FILE" ]; then
    echo "Task file not found: $TASK_FILE"
    exit 1
fi

PROJECT_INFO=$(
    "$PYTHON" - "$PROJECT_KEY" "$PROJECTS_YAML" <<'PY'
import sys
from pathlib import Path

import yaml

project_key, projects_yaml = sys.argv[1:]
projects = yaml.safe_load(Path(projects_yaml).read_text(encoding="utf-8")) or {}
project = (projects.get("projects") or {}).get(project_key)
if not project:
    raise SystemExit(1)
print(project.get("wsl_path", ""))
print(project.get("windows_path", ""))
print(project.get("display_name", project_key))
PY
)
if [ -z "$PROJECT_INFO" ]; then
    echo "Project not found in registry: $PROJECT_KEY"
    exit 1
fi

mapfile -t PROJECT_FIELDS <<< "$PROJECT_INFO"
REPO_PATH=${PROJECT_FIELDS[0]:-}
REPO_PATH_WINDOWS=${PROJECT_FIELDS[1]:-}
PROJECT_NAME=${PROJECT_FIELDS[2]:-$PROJECT_KEY}

if [ -z "$REPO_PATH" ] || [ ! -d "$REPO_PATH" ]; then
    echo "Repository path not found for project '$PROJECT_KEY': $REPO_PATH"
    exit 1
fi

if ! git -C "$REPO_PATH" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Project path is not a Git repository: $REPO_PATH"
    exit 1
fi

FEATURE_ID=$(safe_slug "$TITLE")
if [ -z "$FEATURE_ID" ]; then
    echo "Title must contain at least one letter or number."
    exit 1
fi

FEATURE_DIR="$FEATURES_DIR/$PROJECT_KEY/$FEATURE_ID"
if [ -e "$FEATURE_DIR" ]; then
    echo "Feature stronghold already exists: $(to_windows_path "$FEATURE_DIR")"
    exit 1
fi

CREATED_AT=$(date +%Y%m%d_%H%M%S)
BRANCH=$(git -C "$REPO_PATH" branch --show-current 2>/dev/null || true)
COMMIT=$(git -C "$REPO_PATH" rev-parse HEAD 2>/dev/null || true)

mkdir -p \
    "$FEATURE_DIR/evidence" \
    "$FEATURE_DIR/prompts" \
    "$FEATURE_DIR/responses" \
    "$FEATURE_DIR/runs" \
    "$FEATURE_DIR/handoffs"

"$PYTHON" - \
    "$FEATURE_ID" \
    "$TITLE" \
    "$PROJECT_KEY" \
    "$PROJECT_NAME" \
    "$TASK_FILE" \
    "$CREATED_AT" \
    "$REPO_PATH" \
    "$REPO_PATH_WINDOWS" \
    "$BRANCH" \
    "$COMMIT" \
    "$FEATURE_DIR" <<'PY'
import json
import re
import sys
from pathlib import Path

(
    feature_id,
    title,
    project_key,
    project_name,
    source_task,
    created_at,
    repo_path,
    repo_path_windows,
    current_branch,
    current_commit,
    feature_dir,
) = sys.argv[1:]

feature_dir = Path(feature_dir)
task_path = Path(source_task)
task_text = task_path.read_text(encoding="utf-8", errors="replace").strip()

def section(name: str) -> str:
    pattern = rf"(?ms)^{re.escape(name)}:\s*\n(.*?)(?=^[A-Za-z][A-Za-z ]*:\s*$|^Original Task Content:\s*$|\Z)"
    match = re.search(pattern, task_text)
    return match.group(1).strip() if match else ""

def bullets(text: str) -> list[str]:
    values = []
    for line in text.splitlines():
        value = re.sub(r"^\s*-\s*", "", line).strip()
        if value:
            values.append(value)
    return values

objective = section("Goal")
acceptance_criteria = bullets(section("Acceptance Criteria"))
allowed_files = bullets(section("Allowed Files"))
denied_files = bullets(section("Denied Files"))
risk = section("Risk") or "not specified"

if not objective:
    raise SystemExit("Task is missing a Goal section.")
if not acceptance_criteria:
    raise SystemExit("Task is missing Acceptance Criteria entries.")
if not allowed_files:
    raise SystemExit("Task is missing Allowed Files entries.")

def bullets_md(values: list[str]) -> str:
    return "\n".join(f"- {value}" for value in values) if values else "- none specified"

stop_conditions = [
    "max attempts reached",
    "repeated same failure without materially new plan",
    "dirty repo conflict",
    "quota blocked or provider unavailable",
    "validation failure unresolved",
    "human approval required before any apply path",
]

feature_contract = f"""# Feature Contract

## Feature
- Title: {title}
- Feature ID: {feature_id}
- Project: {project_key} ({project_name})
- Source Task: {source_task}

## Objective
{objective}

## Acceptance Criteria
{bullets_md(acceptance_criteria)}

## Allowed Files
{bullets_md(allowed_files)}

## Denied Files
{bullets_md(denied_files)}

## Risk
{risk}

## Stop Conditions
{bullets_md(stop_conditions)}
"""

acceptance_md = f"""# Acceptance Criteria

{bullets_md(acceptance_criteria)}
"""

allowed_md = f"""# Allowed Files

## Allowed
{bullets_md(allowed_files)}

## Denied
{bullets_md(denied_files)}
"""

validation_plan = """# Validation Plan

## Current MVP Boundary
- No apply behavior in this feature stronghold MVP.
- No agents are launched.
- No cloud providers are called.
- No browser automation is used.

## Future Checks To Enable Later
- syntax and shell checks for changed scripts
- targeted tests or compile commands from the source task
- changed-file allowlist enforcement
- git diff size and file-count review
- acceptance-criteria evidence collection
- final human review before any apply path
"""

state = {
    "feature_id": feature_id,
    "title": title,
    "project_key": project_key,
    "source_task": source_task,
    "current_state": "CREATED",
    "created_at": created_at,
    "repo_path": repo_path,
    "repo_path_windows": repo_path_windows,
    "current_branch": current_branch,
    "current_commit": current_commit,
    "allowed_files": allowed_files,
    "acceptance_criteria": acceptance_criteria,
    "provider_invocation": False,
    "browser_automation": False,
}

loop_log = f"""# Feature Loop Log

## {created_at} - Feature Created
- Actor: local
- Prior state: none
- State: CREATED
- Source task: {source_task}
- Provider invocation: false
- Browser automation: false
- Next safe action: inspect the feature stronghold; execution loops come later.
"""

current_plan = """# Current Plan

No feature plan has been created yet. Phase 3.1 creates the feature stronghold only.
"""

final_report = """# Final Report

Feature not complete. No execution, validation, or final evidence has been recorded yet.
"""

feature_dir.joinpath("feature_contract.md").write_text(feature_contract, encoding="utf-8", newline="\n")
feature_dir.joinpath("acceptance_criteria.md").write_text(acceptance_md, encoding="utf-8", newline="\n")
feature_dir.joinpath("allowed_files.md").write_text(allowed_md, encoding="utf-8", newline="\n")
feature_dir.joinpath("validation_plan.md").write_text(validation_plan, encoding="utf-8", newline="\n")
feature_dir.joinpath("state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8", newline="\n")
feature_dir.joinpath("loop_log.md").write_text(loop_log, encoding="utf-8", newline="\n")
feature_dir.joinpath("current_plan.md").write_text(current_plan, encoding="utf-8", newline="\n")
feature_dir.joinpath("final_report.md").write_text(final_report, encoding="utf-8", newline="\n")
PY

echo "Feature stronghold created: $(to_windows_path "$FEATURE_DIR")"
echo "Feature ID: $FEATURE_ID"
echo "Project: $PROJECT_KEY"
echo "State: CREATED"
echo "Provider invocation: false"
echo "Browser automation: false"

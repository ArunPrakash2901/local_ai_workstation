#!/bin/bash

set -euo pipefail

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
REPORTS_DIR="$WS_HOME/reports"
HANDOFFS_DIR="$WS_HOME/handoffs"
PROJECTS_YAML="$WS_HOME/registry/projects.yaml"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

PROJECT_KEY=${1:-}
TASK_FILE_INPUT=${2:-}
shift 2 || true

TARGET=""
PURPOSE=""

while [ $# -gt 0 ]; do
    case "$1" in
        --target)
            TARGET=${2:-}
            shift 2
            ;;
        --purpose)
            PURPOSE=${2:-}
            shift 2
            ;;
        *)
            echo "Usage: ws handoff-new <project_key> <task_file> --target chatgpt|gemini-browser|codex-cli|gemini-cli|local --purpose <purpose>"
            exit 1
            ;;
    esac
done

if [ -z "$PROJECT_KEY" ] || [ -z "$TASK_FILE_INPUT" ] || [ -z "$TARGET" ] || [ -z "$PURPOSE" ]; then
    echo "Usage: ws handoff-new <project_key> <task_file> --target chatgpt|gemini-browser|codex-cli|gemini-cli|local --purpose <purpose>"
    exit 1
fi

case "$TARGET" in
    chatgpt|gemini-browser|codex-cli|gemini-cli|local) ;;
    *)
        echo "Unsupported target: $TARGET"
        echo "Supported targets: chatgpt, gemini-browser, codex-cli, gemini-cli, local"
        exit 1
        ;;
esac

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
    printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9._-]+/-/g; s/^-+//; s/-+$//'
}

latest_report() {
    local pattern=$1
    find "$REPORTS_DIR" -maxdepth 1 -type f -name "$pattern" -printf '%T@ %p\n' 2>/dev/null \
        | sort -nr \
        | head -n 1 \
        | cut -d' ' -f2-
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

STAMP=$(date +%Y%m%d_%H%M%S)
SAFE_TARGET=$(safe_slug "$TARGET")
SAFE_PURPOSE=$(safe_slug "$PURPOSE")
if [ -z "$SAFE_PURPOSE" ]; then
    echo "Purpose must contain at least one letter or number."
    exit 1
fi
HANDOFF_DIR="$HANDOFFS_DIR/${STAMP}_${SAFE_TARGET}_${SAFE_PURPOSE}"
mkdir -p "$HANDOFF_DIR"

LATEST_READINESS=$(latest_report 'READINESS_*.md')
LATEST_HYGIENE=$(latest_report 'AGENT_HYGIENE_*.md')
LATEST_WORKTREE_STATUS=$(latest_report 'WORKTREE_STATUS_*.md')

if [ -z "$LATEST_READINESS" ]; then
    LOCAL_READINESS_STATE="UNKNOWN"
elif grep -q '\[FAIL\]' "$LATEST_READINESS"; then
    LOCAL_READINESS_STATE="DEGRADED"
else
    LOCAL_READINESS_STATE="READY"
fi

BRANCH=$(git -C "$REPO_PATH" branch --show-current 2>/dev/null || true)
COMMIT=$(git -C "$REPO_PATH" rev-parse HEAD 2>/dev/null || true)
GIT_STATUS=$(git -C "$REPO_PATH" status --short --branch 2>/dev/null || true)
GIT_DIFF_STAT=$(git -C "$REPO_PATH" diff --stat 2>/dev/null || true)

case "$TARGET" in
    chatgpt|gemini-browser) CURRENT_STATE="BROWSER_MANUAL_REQUIRED" ;;
    local|codex-cli|gemini-cli) CURRENT_STATE="PROMPT_READY" ;;
esac

"$PYTHON" - \
    "$STAMP" \
    "$TARGET" \
    "$PURPOSE" \
    "$PROJECT_KEY" \
    "$PROJECT_NAME" \
    "$TASK_FILE" \
    "$REPO_PATH" \
    "$REPO_PATH_WINDOWS" \
    "$BRANCH" \
    "$COMMIT" \
    "$GIT_STATUS" \
    "$GIT_DIFF_STAT" \
    "$LATEST_READINESS" \
    "$LATEST_HYGIENE" \
    "$LATEST_WORKTREE_STATUS" \
    "$LOCAL_READINESS_STATE" \
    "$CURRENT_STATE" \
    "$HANDOFF_DIR" <<'PY'
import json
import re
import sys
from pathlib import Path

(
    timestamp,
    target,
    purpose,
    project_key,
    project_name,
    task_file,
    repo_path,
    repo_path_windows,
    branch,
    commit,
    git_status,
    git_diff_stat,
    latest_readiness,
    latest_hygiene,
    latest_worktree_status,
    local_readiness_state,
    current_state,
    handoff_dir,
) = sys.argv[1:]

handoff_dir = Path(handoff_dir)
task_path = Path(task_file)
task_text = task_path.read_text(encoding="utf-8", errors="replace").strip()

def section(name: str) -> str:
    pattern = rf"(?ms)^{re.escape(name)}:\s*\n(.*?)(?=^[A-Za-z][A-Za-z ]*:\s*$|^Original Task Content:\s*$|\Z)"
    match = re.search(pattern, task_text)
    return match.group(1).strip() if match else ""

title_match = re.search(r"(?m)^#\s+(.*)$", task_text)
task_title = title_match.group(1).strip() if title_match else task_path.name
goal = section("Goal")
acceptance = section("Acceptance Criteria")
allowed_lines = []
for line in section("Allowed Files").splitlines():
    value = re.sub(r"^\s*-\s*", "", line).strip()
    if value:
        allowed_lines.append(value)

if not allowed_lines:
    raise SystemExit("Task is missing explicit Allowed Files entries.")

def display_path(path: str) -> str:
    return path if path else "not found"

git_status_display = git_status.strip() or "clean"
git_diff_display = git_diff_stat.strip() or "no unstaged diff"
allowed_md = "\n".join(f"- {item}" for item in allowed_lines)

context_pack = f"""# Handoff Context Pack

## Project Summary
- Project Key: {project_key}
- Project Name: {project_name}
- Repository Path: {repo_path}
- Repository Path (Windows): {repo_path_windows}

## Task Summary
- Task File: {task_file}
- Task: {task_title}

### Goal
{goal or "not specified"}

### Acceptance Criteria
{acceptance or "not specified"}

## Allowed Files
{allowed_md}

## Latest Local Reports
- Readiness: {display_path(latest_readiness)}
- Agent Hygiene: {display_path(latest_hygiene)}
- Worktree Status: {display_path(latest_worktree_status)}

## Current Git State
- Branch: {branch or "unknown"}
- Commit: {commit or "unknown"}

```text
{git_status_display}
```

### Git Diff Stat
```text
{git_diff_display}
```

## Local Safety Boundary
- Local readiness state: {local_readiness_state}
- No provider was invoked while creating this packet.
- No browser automation was used.
- Do not include secrets, credentials, raw datasets, model files, archives, `.env` files, or private keys in downstream handoffs.
"""

prompt = f"""# Handoff Prompt

Target: {target}
Purpose: {purpose}
Project: {project_key}

Use the local context below to help with the requested handoff. Do not assume permission to modify files or call tools.

## Task
````markdown
{task_text}
````

## Allowed Files
{allowed_md}

## Current Branch And Status
- Branch: {branch or "unknown"}
- Commit: {commit or "unknown"}

```text
{git_status_display}
```

## Latest Relevant Reports
- Readiness: {display_path(latest_readiness)}
- Agent Hygiene: {display_path(latest_hygiene)}
- Worktree Status: {display_path(latest_worktree_status)}

## Constraints
- Treat this as a handoff/review request only.
- Do not modify files.
- Do not exceed the explicit Allowed Files boundary in any recommendation.
- Do not request secrets, credentials, raw datasets, model files, archives, `.env` files, or private keys.
- Local readiness state is `{local_readiness_state}`. Do not assume a cloud fallback if local readiness is degraded.
- Browser targets remain manual; no provider has been invoked by this packet.

## Requested Output Format
## Assessment
## Risks Or Blockers
## Recommended Next Action
## Evidence Used
## Suggested Command Or Prompt
"""

metadata = {
    "timestamp": timestamp,
    "target": target,
    "purpose": purpose,
    "project_key": project_key,
    "task_file": task_file,
    "repo_path": repo_path,
    "repo_path_windows": repo_path_windows,
    "current_branch": branch,
    "current_commit": commit,
    "git_status_summary": git_status_display,
    "allowed_files": allowed_lines,
    "local_readiness_state": local_readiness_state,
    "provider_invocation": False,
    "browser_automation": False,
    "current_state": current_state,
    "latest_reports": {
        "readiness": latest_readiness or None,
        "agent_hygiene": latest_hygiene or None,
        "worktree_status": latest_worktree_status or None,
    },
}

if local_readiness_state == "DEGRADED":
    readiness_note = "Local readiness is degraded. The packet was still created locally; no cloud provider was called automatically."
elif local_readiness_state == "READY":
    readiness_note = "Local readiness is currently healthy based on the latest readiness report."
else:
    readiness_note = "Local readiness is unknown because no readiness report was found."

handoff_report = f"""# Handoff Report

- Timestamp: {timestamp}
- Target: {target}
- Purpose: {purpose}
- Project: {project_key}
- State: {current_state}
- Provider Invocation: false
- Browser Automation: false

## Summary
Created a local-only handoff packet for `{task_title}`.

## Local Readiness
{readiness_note}

## Artifacts
- Prompt: prompt.md
- Context Pack: context_pack.md
- Metadata: metadata.json
- Response Placeholder: response.md
- Transcript: transcript.md

## Latest Local Reports
- Readiness: {display_path(latest_readiness)}
- Agent Hygiene: {display_path(latest_hygiene)}
- Worktree Status: {display_path(latest_worktree_status)}

## Next Safe Action
Review `prompt.md` manually. For browser targets, paste it manually only if you decide to use that lane. No provider has been invoked by this command.
"""

response = """# Handoff Response

No response has been imported. Phase 2.1 creates local packet artifacts only.
"""

transcript = f"""# Handoff Transcript

## {timestamp} - Prompt Created
- Target: {target}
- Purpose: {purpose}
- State: {current_state}
- Provider invocation: false
- Browser automation: false
"""

handoff_dir.joinpath("context_pack.md").write_text(context_pack, encoding="utf-8", newline="\n")
handoff_dir.joinpath("prompt.md").write_text(prompt, encoding="utf-8", newline="\n")
handoff_dir.joinpath("metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8", newline="\n")
handoff_dir.joinpath("response.md").write_text(response, encoding="utf-8", newline="\n")
handoff_dir.joinpath("transcript.md").write_text(transcript, encoding="utf-8", newline="\n")
handoff_dir.joinpath("handoff_report.md").write_text(handoff_report, encoding="utf-8", newline="\n")
PY

echo "Handoff packet created: $(to_windows_path "$HANDOFF_DIR")"
echo "State: $CURRENT_STATE"
echo "Prompt: $(to_windows_path "$HANDOFF_DIR/prompt.md")"
echo "Context: $(to_windows_path "$HANDOFF_DIR/context_pack.md")"
echo "Metadata: $(to_windows_path "$HANDOFF_DIR/metadata.json")"
echo "Provider invocation: false"
echo "Browser automation: false"

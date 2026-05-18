#!/bin/bash

set -euo pipefail

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
FEATURES_DIR="$WS_HOME/features"
HANDOFFS_DIR="$WS_HOME/handoffs"
REPORTS_DIR="$WS_HOME/reports"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

FEATURE_INPUT=${1:-}
shift || true

TARGET=""
PURPOSE="master-plan"

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
            echo "Usage: ws feature-architect-handoff <feature_id_or_path> --target chatgpt|gemini-browser [--purpose master-plan]"
            exit 1
            ;;
    esac
done

if [ -z "$FEATURE_INPUT" ] || [ -z "$TARGET" ]; then
    echo "Usage: ws feature-architect-handoff <feature_id_or_path> --target chatgpt|gemini-browser [--purpose master-plan]"
    exit 1
fi

case "$TARGET" in
    chatgpt|gemini-browser) ;;
    *)
        echo "Unsupported target: $TARGET"
        echo "Supported targets: chatgpt, gemini-browser"
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
    "current_plan.md"
    "loop_log.md"
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
print(state.get("feature_id", ""))
print(state.get("title", ""))
print(state.get("project_key", ""))
print(state.get("source_task", ""))
print(state.get("current_state", ""))
print(state.get("repo_path", ""))
print(state.get("repo_path_windows", ""))
PY
)
mapfile -t STATE_FIELDS <<< "$STATE_INFO"
FEATURE_ID=${STATE_FIELDS[0]:-}
TITLE=${STATE_FIELDS[1]:-}
PROJECT_KEY=${STATE_FIELDS[2]:-}
SOURCE_TASK=${STATE_FIELDS[3]:-}
FEATURE_STATE=${STATE_FIELDS[4]:-}
REPO_PATH=${STATE_FIELDS[5]:-}
REPO_PATH_WINDOWS=${STATE_FIELDS[6]:-}

STAMP=$(date +%Y%m%d_%H%M%S)
SAFE_TARGET=$(safe_slug "$TARGET")
SAFE_PURPOSE=$(safe_slug "$PURPOSE")

HANDOFF_DIR="$HANDOFFS_DIR/${STAMP}_${SAFE_TARGET}_${SAFE_PURPOSE}"
mkdir -p "$HANDOFF_DIR"

LATEST_VALIDATION=$(find "$FEATURE_DIR/evidence" -maxdepth 1 -type f -name 'validation_*.md' -printf '%T@ %p\n' 2>/dev/null \
    | sort -nr \
    | head -n 1 \
    | cut -d' ' -f2-)
LATEST_LOCAL_REVIEW=$(find "$FEATURE_DIR/responses" -maxdepth 1 -type f -name 'local_review_*.md' -printf '%T@ %p\n' 2>/dev/null \
    | sort -nr \
    | head -n 1 \
    | cut -d' ' -f2-)
LATEST_DRY_RUN=$(find "$FEATURE_DIR/runs" -maxdepth 1 -type f -name 'feature_run_dry_run_*.md' -printf '%T@ %p\n' 2>/dev/null \
    | sort -nr \
    | head -n 1 \
    | cut -d' ' -f2-)
LATEST_READINESS=$(latest_report 'READINESS_*.md')

BRANCH=$(git -C "$REPO_PATH" branch --show-current 2>/dev/null || true)
COMMIT=$(git -C "$REPO_PATH" rev-parse HEAD 2>/dev/null || true)

"$PYTHON" - \
    "$STAMP" \
    "$TARGET" \
    "$PURPOSE" \
    "$FEATURE_DIR" \
    "$HANDOFF_DIR" \
    "$FEATURE_ID" \
    "$TITLE" \
    "$PROJECT_KEY" \
    "$SOURCE_TASK" \
    "$FEATURE_STATE" \
    "$REPO_PATH" \
    "$REPO_PATH_WINDOWS" \
    "$BRANCH" \
    "$COMMIT" \
    "$LATEST_VALIDATION" \
    "$LATEST_LOCAL_REVIEW" \
    "$LATEST_DRY_RUN" \
    "$LATEST_READINESS" <<'PY'
import json
import re
import sys
from pathlib import Path

(
    timestamp,
    target,
    purpose,
    feature_dir,
    handoff_dir,
    feature_id,
    title,
    project_key,
    source_task,
    feature_state,
    repo_path,
    repo_path_windows,
    branch,
    commit,
    latest_validation,
    latest_local_review,
    latest_dry_run,
    latest_readiness,
) = sys.argv[1:]

feature_dir = Path(feature_dir)
handoff_dir = Path(handoff_dir)

def get_content(p, fallback="not found"):
    if p and Path(p).is_file():
        return Path(p).read_text(encoding="utf-8").strip()
    return fallback

contract_path = feature_dir / "feature_contract.md"
acceptance_path = feature_dir / "acceptance_criteria.md"
allowed_path = feature_dir / "allowed_files.md"
current_plan_path = feature_dir / "current_plan.md"
loop_log_path = feature_dir / "loop_log.md"
state_path = feature_dir / "state.json"

contract_text = get_content(contract_path)
acceptance_text = get_content(acceptance_path)
allowed_text = get_content(allowed_path)
current_plan_text = get_content(current_plan_path)
loop_log_text = get_content(loop_log_path)
state = json.loads(state_path.read_text(encoding="utf-8"))

def recent_loop_events(text: str, limit: int = 5) -> list[str]:
    events = re.findall(r"(?m)^##\s+(.+)$", text)
    return events[-limit:]

loop_events = recent_loop_events(loop_log_text)
loop_summary = "\n".join(f"- {event}" for event in loop_events) if loop_events else "- no loop events found"

context_pack = f"""# Feature Architect Handoff Context Pack

## Feature Summary
- Feature ID: {feature_id}
- Title: {title}
- Feature State: {feature_state}
- Feature Path: {feature_dir}
- Project Key: {project_key}
- Source Task: {source_task}

## Feature Inputs
- Feature Contract: {contract_path}
- Acceptance Criteria: {acceptance_path}
- Allowed Files: {allowed_path}
- Current Plan: {current_plan_path}
- Loop Log: {loop_log_path}
- Latest Validation Evidence: {latest_validation or "none"}
- Latest Local Review: {latest_local_review or "none"}
- Latest Dry Run: {latest_dry_run or "none"}

## Current Plan Content
```markdown
{current_plan_text}
```

## Recent History
{loop_summary}

## Git State
- Repository: {repo_path}
- Branch: {branch}
- Commit: {commit}
"""

prompt = f"""# Senior Architect Master Plan Request

You are a Senior Technical Architect for an AI Workstation development team. 
I have a Feature Stronghold that has passed initial local validation. 
I need you to review the following context and provide a **Master Implementation Plan**.

## Objective
Provide a strategic roadmap for implementation. Do NOT provide direct code edits or patches. 
Focus on architecture, sequencing, and risk management.

## Feature Stronghold Context

### Feature Contract
```markdown
{contract_text}
```

### Acceptance Criteria
```markdown
{acceptance_text}
```

### Allowed Files
```markdown
{allowed_text}
```

### Initial Local Plan
This is a deterministic plan generated by the workstation. Use it as a base to build the master plan.
```markdown
{current_plan_text}
```

### Evidence and History
- Latest Validation Evidence Path: {latest_validation or "none"}
- Latest Local Review Path: {latest_local_review or "none"}
- Latest Feature-Run Dry-Run Path: {latest_dry_run or "none"}
- Recent Loop Events:
{loop_summary}

## Current Git State
- Branch: {branch}
- Commit: {commit}

## Your Task
Analyze the objective and constraints, then provide a response in the following format:

### 1. Implementation Strategy
Describe the overall architectural approach.

### 2. Implementation Sequencing
Provide a step-by-step list of tasks. Distinguish between:
- **Intern Tasks**: Routine tasks suitable for a small local model (Ollama).
- **Agent Tasks**: Bounded implementation tasks suitable for Codex or Gemini CLI.
- **Human Gates**: Steps requiring manual operator verification or approval.

### 3. Risk Assessment
Identify potential blockers, edge cases, or side effects.

### 4. Next Safe Workstation Command
Recommend the exact next `ws` command the operator should run (e.g., `ws feature-plan-import`, `ws feature-local-review`, etc.).

## Constraints
- Do not exceed the explicit Allowed Files boundary.
- Do not request secrets or credentials.
- Browser targets remain manual; no provider has been invoked.
"""

metadata = {
    "timestamp": timestamp,
    "feature_id": feature_id,
    "feature_path": str(feature_dir),
    "feature_state": feature_state,
    "project_key": project_key,
    "target": target,
    "purpose": "master-plan",
    "role": "senior_architect",
    "provider_invocation": False,
    "browser_automation": False,
    "current_state": "ARCHITECT_REVIEW_READY",
    "source_task": source_task,
    "repo_path": repo_path,
    "repo_path_windows": repo_path_windows,
    "current_branch": branch,
    "current_commit": commit,
    "latest_validation_evidence": latest_validation or None,
    "latest_local_review": latest_local_review or None,
    "latest_dry_run": latest_dry_run or None,
}

handoff_report = f"""# Feature Architect Handoff Report

- Timestamp: {timestamp}
- Target: {target}
- Purpose: master-plan
- Role: senior_architect
- Feature ID: {feature_id}
- State: ARCHITECT_REVIEW_READY

## Summary
Generated a Senior Architect prompt requesting a master implementation plan for feature `{feature_id}`.

## Artifacts
- Prompt: prompt.md
- Context Pack: context_pack.md
- Metadata: metadata.json

## Next Safe Action
1. Review `prompt.md`.
2. Paste it manually into {target}.
3. Once you receive the master plan, import it using `ws feature-plan-import`.
"""

response_md = "# Handoff Response\n\nNo response has been imported yet.\n"
transcript_md = f"# Handoff Transcript\n\n## {timestamp} - Architect Prompt Created\n- Role: senior_architect\n- Target: {target}\n"

loop_entry = f"""
## {timestamp} - Architect Handoff Created
- Actor: local
- Target: {target}
- Purpose: master-plan
- Role: senior_architect
- Handoff: {handoff_dir}
- Provider invocation: false
- Browser automation: false
- Next safe action: review `prompt.md` and obtain master plan from architect.
"""

handoff_dir.joinpath("context_pack.md").write_text(context_pack, encoding="utf-8", newline="\n")
handoff_dir.joinpath("prompt.md").write_text(prompt, encoding="utf-8", newline="\n")
handoff_dir.joinpath("metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8", newline="\n")
handoff_dir.joinpath("response.md").write_text(response_md, encoding="utf-8", newline="\n")
handoff_dir.joinpath("transcript.md").write_text(transcript_md, encoding="utf-8", newline="\n")
handoff_dir.joinpath("handoff_report.md").write_text(handoff_report, encoding="utf-8", newline="\n")

with loop_log_path.open("a", encoding="utf-8", newline="\n") as handle:
    handle.write(loop_entry)
PY

echo "Architect handoff packet created: $(to_windows_path "$HANDOFF_DIR")"
echo "Feature ID: $FEATURE_ID"
echo "Target: $TARGET"
echo "State: ARCHITECT_REVIEW_READY"
echo "Prompt: $(to_windows_path "$HANDOFF_DIR/prompt.md")"
echo "Next safe action: review prompt.md and paste it manually into $TARGET."

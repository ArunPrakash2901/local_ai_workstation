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
            echo "Usage: ws feature-handoff <feature_id_or_path> --target chatgpt|gemini-browser|local|codex-cli|gemini-cli --purpose <purpose>"
            exit 1
            ;;
    esac
done

if [ -z "$FEATURE_INPUT" ] || [ -z "$TARGET" ] || [ -z "$PURPOSE" ]; then
    echo "Usage: ws feature-handoff <feature_id_or_path> --target chatgpt|gemini-browser|local|codex-cli|gemini-cli --purpose <purpose>"
    exit 1
fi

case "$TARGET" in
    chatgpt|gemini-browser|local|codex-cli|gemini-cli) ;;
    *)
        echo "Unsupported target: $TARGET"
        echo "Supported targets: chatgpt, gemini-browser, local, codex-cli, gemini-cli"
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
    "validation_plan.md"
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
print(str(state.get("provider_invocation", "")))
print(str(state.get("browser_automation", "")))
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
PROVIDER_INVOCATION=${STATE_FIELDS[7]:-}
BROWSER_AUTOMATION=${STATE_FIELDS[8]:-}

case "$FEATURE_STATE" in
    LOCAL_PLAN_READY|VALIDATED_LOCAL|HUMAN_APPROVAL_REQUIRED) ;;
    *)
        echo "Feature handoff blocked: state '$FEATURE_STATE' is not eligible."
        echo "Allowed states: LOCAL_PLAN_READY, VALIDATED_LOCAL, HUMAN_APPROVAL_REQUIRED"
        exit 1
        ;;
esac

if [ "$PROVIDER_INVOCATION" != "False" ] || [ "$BROWSER_AUTOMATION" != "False" ]; then
    echo "Feature handoff blocked: state.json indicates provider invocation or browser automation is already enabled."
    exit 1
fi

if [ -z "$REPO_PATH" ] || [ ! -d "$REPO_PATH" ]; then
    echo "Repository path from state.json is unavailable: $REPO_PATH"
    exit 1
fi

if ! git -C "$REPO_PATH" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Repository path from state.json is not a Git repository: $REPO_PATH"
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

LATEST_VALIDATION=$(find "$FEATURE_DIR/evidence" -maxdepth 1 -type f -name 'validation_*.md' -printf '%T@ %p\n' 2>/dev/null \
    | sort -nr \
    | head -n 1 \
    | cut -d' ' -f2-)
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
    "$GIT_STATUS" \
    "$GIT_DIFF_STAT" \
    "$LATEST_VALIDATION" \
    "$LATEST_READINESS" \
    "$LATEST_HYGIENE" \
    "$LATEST_WORKTREE_STATUS" \
    "$LOCAL_READINESS_STATE" \
    "$CURRENT_STATE" <<'PY'
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
    git_status,
    git_diff_stat,
    latest_validation,
    latest_readiness,
    latest_hygiene,
    latest_worktree_status,
    local_readiness_state,
    current_state,
) = sys.argv[1:]

feature_dir = Path(feature_dir)
handoff_dir = Path(handoff_dir)

contract_path = feature_dir / "feature_contract.md"
acceptance_path = feature_dir / "acceptance_criteria.md"
allowed_path = feature_dir / "allowed_files.md"
validation_plan_path = feature_dir / "validation_plan.md"
current_plan_path = feature_dir / "current_plan.md"
loop_log_path = feature_dir / "loop_log.md"
state_path = feature_dir / "state.json"

state = json.loads(state_path.read_text(encoding="utf-8"))
contract_text = contract_path.read_text(encoding="utf-8").strip()
acceptance_text = acceptance_path.read_text(encoding="utf-8").strip()
allowed_text = allowed_path.read_text(encoding="utf-8").strip()
validation_plan_text = validation_plan_path.read_text(encoding="utf-8").strip()
current_plan_text = current_plan_path.read_text(encoding="utf-8").strip()
loop_log_text = loop_log_path.read_text(encoding="utf-8").strip()

def display_path(path: str) -> str:
    return path if path else "not found"

def section(text: str, heading: str) -> str:
    pattern = rf"(?ms)^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else "not specified"

def recent_loop_events(text: str, limit: int = 3) -> list[str]:
    events = re.findall(r"(?m)^##\s+(.+)$", text)
    return events[-limit:]

objective = section(contract_text, "Objective")
allowed = section(allowed_text, "Allowed")
git_status_display = git_status.strip() or "clean"
git_diff_display = git_diff_stat.strip() or "no unstaged diff"
loop_events = recent_loop_events(loop_log_text)
loop_summary = "\n".join(f"- {event}" for event in loop_events) if loop_events else "- no loop events found"

context_pack = f"""# Feature Handoff Context Pack

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
- Validation Plan: {validation_plan_path}
- Current Plan: {current_plan_path}
- Loop Log: {loop_log_path}
- Latest Validation Evidence: {display_path(latest_validation)}

## Objective
{objective}

## Acceptance Criteria
{acceptance_text}

## Allowed Files
{allowed}

## Latest Feature Plan
```markdown
{current_plan_text}
```

## Validation Evidence
- Latest Validation Evidence: {display_path(latest_validation)}

## Recent Loop Log Events
{loop_summary}

## Latest Local Reports
- Readiness: {display_path(latest_readiness)}
- Agent Hygiene: {display_path(latest_hygiene)}
- Worktree Status: {display_path(latest_worktree_status)}

## Current Git State
- Repository Path: {repo_path}
- Repository Path (Windows): {repo_path_windows}
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
- Feature handoff packet only; no provider was invoked.
- Browser automation was not used.
- Do not include secrets, credentials, raw datasets, model files, archives, `.env` files, or private keys in downstream handoffs.
"""

prompt = f"""# Feature Handoff Prompt

Target: {target}
Purpose: {purpose}
Project: {project_key}
Feature: {feature_id}
Feature State: {feature_state}

Use this feature stronghold context for a review-only handoff. Do not assume permission to modify files or call tools.

## Feature Contract
```markdown
{contract_text}
```

## Acceptance Criteria
```markdown
{acceptance_text}
```

## Allowed Files
```markdown
{allowed_text}
```

## Validation Plan
```markdown
{validation_plan_text}
```

## Current Plan
```markdown
{current_plan_text}
```

## Feature Evidence
- Source Task: {source_task}
- Latest Validation Evidence: {display_path(latest_validation)}
- Loop Log: {loop_log_path}
- Recent Loop Events:
{loop_summary}

## Current Git State
- Branch: {branch or "unknown"}
- Commit: {commit or "unknown"}

```text
{git_status_display}
```

## Constraints
- Treat this as a review/handoff request only.
- Do not modify files.
- Do not exceed the explicit Allowed Files boundary in any recommendation.
- Do not request secrets, credentials, raw datasets, model files, archives, `.env` files, or private keys.
- Feature state is `{feature_state}`.
- Local readiness state is `{local_readiness_state}`.
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
    "feature_id": feature_id,
    "feature_path": str(feature_dir),
    "feature_state": feature_state,
    "project_key": project_key,
    "target": target,
    "purpose": purpose,
    "provider_invocation": False,
    "browser_automation": False,
    "current_state": current_state,
    "source_task": source_task,
    "repo_path": repo_path,
    "repo_path_windows": repo_path_windows,
    "current_branch": branch,
    "current_commit": commit,
    "git_status_summary": git_status_display,
    "allowed_files": state.get("allowed_files", []),
    "latest_validation_evidence": latest_validation or None,
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

handoff_report = f"""# Feature Handoff Report

- Timestamp: {timestamp}
- Target: {target}
- Purpose: {purpose}
- Project: {project_key}
- Feature ID: {feature_id}
- Feature State: {feature_state}
- State: {current_state}
- Provider Invocation: false
- Browser Automation: false

## Summary
Created a local-only feature-aware handoff packet for `{title}`.

## Feature Inputs
- Feature Contract: {contract_path}
- Acceptance Criteria: {acceptance_path}
- Allowed Files: {allowed_path}
- Validation Plan: {validation_plan_path}
- Current Plan: {current_plan_path}
- Loop Log: {loop_log_path}
- Latest Validation Evidence: {display_path(latest_validation)}

## Local Readiness
{readiness_note}

## Artifacts
- Prompt: prompt.md
- Context Pack: context_pack.md
- Metadata: metadata.json
- Response Placeholder: response.md
- Transcript: transcript.md

## Next Safe Action
Review `prompt.md` manually. For browser targets, paste it manually only if you decide to use that lane. No provider has been invoked by this command.
"""

response = """# Handoff Response

No response has been imported. Phase 3.4 creates local feature-aware packet artifacts only.
"""

transcript = f"""# Handoff Transcript

## {timestamp} - Feature Prompt Created
- Feature ID: {feature_id}
- Feature State: {feature_state}
- Target: {target}
- Purpose: {purpose}
- State: {current_state}
- Provider invocation: false
- Browser automation: false
"""

loop_entry = f"""
## {timestamp} - Feature Handoff Created
- Actor: local
- State: {feature_state}
- Target: {target}
- Purpose: {purpose}
- Handoff: {handoff_dir}
- Latest validation evidence: {display_path(latest_validation)}
- Provider invocation: false
- Browser automation: false
- Next safe action: review `prompt.md`; browser targets remain manual.
"""

handoff_dir.joinpath("context_pack.md").write_text(context_pack, encoding="utf-8", newline="\n")
handoff_dir.joinpath("prompt.md").write_text(prompt, encoding="utf-8", newline="\n")
handoff_dir.joinpath("metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8", newline="\n")
handoff_dir.joinpath("response.md").write_text(response, encoding="utf-8", newline="\n")
handoff_dir.joinpath("transcript.md").write_text(transcript, encoding="utf-8", newline="\n")
handoff_dir.joinpath("handoff_report.md").write_text(handoff_report, encoding="utf-8", newline="\n")
with loop_log_path.open("a", encoding="utf-8", newline="\n") as handle:
    handle.write(loop_entry)
PY

echo "Feature handoff packet created: $(to_windows_path "$HANDOFF_DIR")"
echo "Feature ID: $FEATURE_ID"
echo "Feature state: $FEATURE_STATE"
echo "Packet state: $CURRENT_STATE"
echo "Prompt: $(to_windows_path "$HANDOFF_DIR/prompt.md")"
echo "Metadata: $(to_windows_path "$HANDOFF_DIR/metadata.json")"
echo "Provider invocation: false"
echo "Browser automation: false"
if [ "$CURRENT_STATE" = "BROWSER_MANUAL_REQUIRED" ]; then
    echo "Next safe action: review prompt.md and paste it manually into the browser lane if you choose to use it."
else
    echo "Next safe action: review prompt.md; no provider path was run."
fi

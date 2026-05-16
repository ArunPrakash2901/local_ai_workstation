#!/bin/bash

set -u

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
REPORTS_DIR="$WS_HOME/reports"
REGISTRY_DIR="$WS_HOME/registry"
PROJECTS_YAML="$REGISTRY_DIR/projects.yaml"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

PROJECT_KEY=${1:-}
TASK_FILE=${2:-}

if [ -z "$PROJECT_KEY" ] || [ -z "$TASK_FILE" ]; then
    echo "Usage: ws loop-plan <project_key> <task_file>"
    exit 1
fi

STAMP=$(date +%Y%m%d_%H%M%S)
REPORT="$REPORTS_DIR/LOOP_PLAN_$STAMP.md"

# 1. Check Project Path
PROJECT_PATH=$($PYTHON -c "
import yaml
try:
    with open('$PROJECTS_YAML', 'r') as f:
        data = yaml.safe_load(f)
        p = data.get('projects', {}).get('$PROJECT_KEY')
        if p and p.get('windows_path'):
            print(p.get('windows_path'))
except:
    pass
")

if [ -z "$PROJECT_PATH" ]; then
    PROJECT_PATH=$($PYTHON -c "
import yaml
try:
    with open('$PROJECTS_YAML', 'r') as f:
        data = yaml.safe_load(f)
        p = data.get('$PROJECT_KEY')
        if p and p.get('windows_path'):
            print(p.get('windows_path'))
except:
    pass
")
fi

CLASSIFICATION="UNKNOWN"
REASON=""

if [ -z "$PROJECT_PATH" ]; then
    CLASSIFICATION="BLOCKED_PROJECT_NOT_FOUND"
    REASON="Project '$PROJECT_KEY' not found in registry."
else
    # 2. Check Repo Path Exists
    WSL_PROJECT_PATH=$(wslpath -u "$PROJECT_PATH" 2>/dev/null || echo "")
    if [ -z "$WSL_PROJECT_PATH" ] || [ ! -d "$WSL_PROJECT_PATH" ]; then
        CLASSIFICATION="BLOCKED_PROJECT_NOT_FOUND"
        REASON="Directory for project '$PROJECT_KEY' not found at '$PROJECT_PATH'."
    else
        # 3. Check Task File
        WSL_TASK_FILE=$(wslpath -u "$TASK_FILE" 2>/dev/null || echo "$TASK_FILE")
        if [ ! -f "$WSL_TASK_FILE" ]; then
             CLASSIFICATION="BLOCKED_MISSING_ALLOWED_FILES"
             REASON="Task file not found."
        else
            if ! grep -q 'Allowed Files:' "$WSL_TASK_FILE"; then
                CLASSIFICATION="BLOCKED_MISSING_ALLOWED_FILES"
                REASON="Task is missing explicit 'Allowed Files:' section."
            else
                # 4. Check Dirty Repo
                if ! git -C "$WSL_PROJECT_PATH" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
                    CLASSIFICATION="BLOCKED_DIRTY_REPO"
                    REASON="Project path is not a valid git repository."
                else
                    if [ -n "$(git -C "$WSL_PROJECT_PATH" status --porcelain)" ]; then
                        CLASSIFICATION="BLOCKED_DIRTY_REPO"
                        REASON="Repository has uncommitted changes."
                    else
                        # 5. Check Canary
                        CANARY_JSON="$REPORTS_DIR/agent_canary_status.json"
                        CANARY_STATUS="NOT_RUN"
                        if [ -f "$CANARY_JSON" ]; then
                            CANARY_STATUS=$(grep -oP '"status"\s*:\s*"\K[^"]+' "$CANARY_JSON" || echo "UNKNOWN")
                        fi
                        if [ "$CANARY_STATUS" != "AGENT_CANARY_PASSED" ]; then
                            CLASSIFICATION="BLOCKED_CLOUD_QUOTA"
                            REASON="Cloud canary status is $CANARY_STATUS. Only LOCAL_PLAN_ONLY or HANDOFF_ONLY are available."
                        else
                            CLASSIFICATION="CLOUD_APPLY_ELIGIBLE"
                            REASON="All preflight checks passed. Local plan and cloud apply loops are eligible."
                        fi
                    fi
                fi
            fi
        fi
    fi
fi

cat <<EOF > "$REPORT"
# Independent Loop Plan

- **Timestamp**: $STAMP
- **Project**: $PROJECT_KEY
- **Task**: $TASK_FILE
- **Classification**: $CLASSIFICATION

## Analysis
$REASON

## Context Checks
- Project found: $(if [ -n "${WSL_PROJECT_PATH:-}" ]; then echo "Yes ($WSL_PROJECT_PATH)"; else echo "No"; fi)
- Task file exists: $(if [ -f "${WSL_TASK_FILE:-}" ]; then echo "Yes"; else echo "No"; fi)
- Canary status: ${CANARY_STATUS:-UNKNOWN}
- Stale runs: unchecked in v1 read-only planner

## Execution Strategy
If execution were enabled, this task would:
1. Formulate a local plan using Graphify and Hermes 3 8B.
2. If CLOUD_APPLY_ELIGIBLE: create a git worktree, branch, apply changes via Codex, and commit.
3. If BLOCKED_CLOUD_QUOTA: degrade to HANDOFF_ONLY.
EOF

echo "Classification: $CLASSIFICATION"
echo "Report: $(wslpath -w "$REPORT" 2>/dev/null || echo "$REPORT")"
echo "Reason: $REASON"
if [ "$CLASSIFICATION" = "CLOUD_APPLY_ELIGIBLE" ] || [ "$CLASSIFICATION" = "BLOCKED_CLOUD_QUOTA" ]; then
    echo "Next safe command: ws agent-run $PROJECT_KEY \"$TASK_FILE\" --mode detect --branch"
else
    echo "Next safe command: resolve blockers before proceeding."
fi

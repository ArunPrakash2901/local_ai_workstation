#!/bin/bash

set -u

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
SCRIPTS_DIR="$WS_HOME/scripts"
REPORTS_DIR="$WS_HOME/reports"
REGISTRY_DIR="$WS_HOME/registry"
PROJECTS_YAML="$REGISTRY_DIR/projects.yaml"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

PROJECT_KEY=${1:-}
TASK_FILE=${2:-}

if [ -z "$PROJECT_KEY" ] || [ -z "$TASK_FILE" ]; then
    echo "Usage: ws apply-ready <project_key> <task_file>"
    exit 1
fi

STAMP=$(date +%Y%m%d_%H%M%S)
REPORT="$REPORTS_DIR/APPLY_READY_$STAMP.md"

CLASSIFICATION="UNKNOWN"
REASON=""

to_wsl_path() {
    case "$1" in
        /*) printf '%s' "$1" ;;
        *) wslpath -u "$1" 2>/dev/null || printf '%s' "$1" ;;
    esac
}

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

HAS_LOCAL_PLAN="No"

if [ -z "$PROJECT_PATH" ]; then
    CLASSIFICATION="BLOCKED_PROJECT_NOT_FOUND"
    REASON="Project '$PROJECT_KEY' not found in registry."
else
    WSL_PROJECT_PATH=$(to_wsl_path "$PROJECT_PATH")
    if [ -z "$WSL_PROJECT_PATH" ] || [ ! -d "$WSL_PROJECT_PATH" ]; then
        CLASSIFICATION="BLOCKED_PROJECT_NOT_FOUND"
        REASON="Directory for project '$PROJECT_KEY' not found at '$PROJECT_PATH'."
    else
        WSL_TASK_FILE=$(to_wsl_path "$TASK_FILE")
        if [ ! -f "$WSL_TASK_FILE" ]; then
             CLASSIFICATION="BLOCKED_TASK_NOT_FOUND"
             REASON="Task file not found at '$WSL_TASK_FILE'."
        else
            if ! grep -q 'Allowed Files:' "$WSL_TASK_FILE"; then
                CLASSIFICATION="BLOCKED_MISSING_ALLOWED_FILES"
                REASON="Task is missing explicit 'Allowed Files:' section."
            else
                if ! git -C "$WSL_PROJECT_PATH" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
                    CLASSIFICATION="BLOCKED_DIRTY_REPO"
                    REASON="Project path is not a valid git repository."
                else
                    if [ -n "$(git -C "$WSL_PROJECT_PATH" status --porcelain)" ]; then
                        CLASSIFICATION="BLOCKED_DIRTY_REPO"
                        REASON="Repository has uncommitted changes."
                    else
                        # Check Canary
                        CANARY_JSON="$REPORTS_DIR/agent_canary_status.json"
                        CANARY_STATUS="NOT_RUN"
                        if [ -f "$CANARY_JSON" ]; then
                            CANARY_STATUS=$(grep -oP '"status"\s*:\s*"\K[^"]+' "$CANARY_JSON" || echo "UNKNOWN")
                        fi
                        if [ "$CANARY_STATUS" != "AGENT_CANARY_PASSED" ]; then
                            CLASSIFICATION="BLOCKED_CANARY_FAILED"
                            REASON="Cloud canary status is $CANARY_STATUS. Supervised cloud apply is blocked."
                        else
                            STALE_RUNS=()
                            HISTORICAL_RUNS=()
                            now=$(date +%s)
                            for d in "$WS_HOME/auto_runs"/*; do
                                if [ -d "$d" ] && [ -f "$d/status.txt" ]; then
                                    if grep -q "CODEX_RUNNING" "$d/status.txt"; then
                                        if [ ! -f "$d/stale_reviewed.md" ]; then
                                            # Parse project and task title from task.md
                                            run_project=$(grep -A 1 "Project:" "$d/task.md" 2>/dev/null | tail -n 1 | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                                            original_title=$(grep -m 1 "^# Task" "$WSL_TASK_FILE" 2>/dev/null | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                                            run_title=$(grep -m 1 "^# Task" "$d/task.md" 2>/dev/null | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

                                            is_match=false
                                            d_base=$(basename "$d")
                                            
                                            if [ "$run_project" = "$PROJECT_KEY" ] && [ "$original_title" = "$run_title" ] && [ -n "$run_project" ]; then
                                                is_match=true
                                            elif [[ "$d_base" == *"_$PROJECT_KEY_"* ]] && [ -z "$run_project" ]; then
                                                # Conservative fallback
                                                is_match=true
                                            fi
                                            
                                            if $is_match; then
                                                mtime=$(stat -c %Y "$d/heartbeat.log" 2>/dev/null || stat -c %Y "$d/status.txt" 2>/dev/null || echo 0)
                                                age=$(( now - mtime ))
                                                
                                                if [ "$age" -lt 7200 ]; then
                                                    STALE_RUNS+=("$d_base")
                                                else
                                                    HISTORICAL_RUNS+=("$d_base")
                                                fi
                                            fi
                                        fi
                                    fi
                                fi
                            done
                            
                            if [ ${#STALE_RUNS[@]} -gt 0 ]; then
                                CLASSIFICATION="BLOCKED_STALE_RUNNING_RUN"
                                REASON="Recent active/stale CODEX_RUNNING folder(s) found for this task: $(printf '%s ' "${STALE_RUNS[@]}")"
                                REASON="${REASON% }"
                            else
                                BUILD_LATEST=$(find "$WS_HOME/build_runs" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n 1 | cut -d' ' -f2-)
                                if [ -n "$BUILD_LATEST" ] && [ -d "$BUILD_LATEST" ] && [ -f "$BUILD_LATEST/local_plan.md" ]; then
                                    HAS_LOCAL_PLAN="Yes ($BUILD_LATEST/local_plan.md)"
                                fi
                                
                                if [ "$HAS_LOCAL_PLAN" = "No" ]; then
                                    CLASSIFICATION="BLOCKED_NO_LOCAL_PLAN"
                                    REASON="No recent local_plan.md found. You must run a local planning loop first."
                                else
                                    CLASSIFICATION="APPLY_READY"
                                    REASON="All preflight checks passed. Task is ready for supervised cloud apply."
                                    if [ ${#HISTORICAL_RUNS[@]} -gt 0 ]; then
                                        REASON="$REASON (Note: ${#HISTORICAL_RUNS[@]} historical unresolved runs found for this task, but they are older than 2 hours and ignored.)"
                                    fi
                                fi
                            fi
                        fi
                    fi
                fi
            fi
        fi
    fi
fi

cat <<EOF > "$REPORT"
# Supervised Apply Readiness

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
- Local Plan Evidence: $HAS_LOCAL_PLAN

EOF

echo "Classification: $CLASSIFICATION"
echo "Report: $(wslpath -w "$REPORT" 2>/dev/null || echo "$REPORT")"
echo "Reason: $REASON"
if [ "$CLASSIFICATION" = "APPLY_READY" ]; then
    echo "Next safe command: ws agent-run $PROJECT_KEY \"$TASK_FILE\" --mode detect --branch --max-files 5 --max-minutes 10 --stop-on-fail"
else
    echo "Next safe command: resolve blockers before proceeding."
fi

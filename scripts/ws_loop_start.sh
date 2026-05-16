#!/bin/bash

set -u

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
SCRIPTS_DIR="$WS_HOME/scripts"
REPORTS_DIR="$WS_HOME/reports"

PROJECT_KEY=${1:-}
TASK_FILE=${2:-}
shift 2 || true

MODE=""

while [ $# -gt 0 ]; do
    case "$1" in
        --mode) 
            MODE="$2"
            shift 2 
            ;;
        --parallel|--night) 
            echo "Terminal State: BLOCKED_UNSUPPORTED_MODE"
            echo "Reason: Parallel and night loops are not implemented."
            exit 1 
            ;;
        *) 
            echo "Terminal State: BLOCKED_UNSUPPORTED_MODE"
            echo "Reason: Unknown argument '$1'"
            exit 1 
            ;;
    esac
done

if [ -z "$PROJECT_KEY" ] || [ -z "$TASK_FILE" ]; then
    echo "Usage: ws loop-start <project_key> <task_file> --mode local-plan"
    exit 1
fi

if [ "$MODE" != "local-plan" ]; then
    echo "Terminal State: BLOCKED_UNSUPPORTED_MODE"
    echo "Reason: Only '--mode local-plan' is currently supported. Cloud apply remains deferred."
    exit 1
fi

STAMP=$(date +%Y%m%d_%H%M%S)
REPORT="$REPORTS_DIR/LOOP_START_$STAMP.md"

# 1. Run Preflight Checks via loop-plan
PLAN_OUT=$(bash "$SCRIPTS_DIR/ws_loop_plan.sh" "$PROJECT_KEY" "$TASK_FILE")
CLASS=$(echo "$PLAN_OUT" | grep "^Classification:" | cut -d' ' -f2- || echo "UNKNOWN")
REASON=$(echo "$PLAN_OUT" | grep "^Reason:" | cut -d' ' -f2- || echo "UNKNOWN")

if [[ "$CLASS" == "BLOCKED_PROJECT_NOT_FOUND" ]] || \
   [[ "$CLASS" == "BLOCKED_MISSING_ALLOWED_FILES" ]] || \
   [[ "$CLASS" == "BLOCKED_DIRTY_REPO" ]]; then
    TERMINAL_STATE="$CLASS"
else
    TERMINAL_STATE="LOCAL_PLAN_COMPLETED"
fi

cat <<EOF > "$REPORT"
# Independent Loop Start

- **Timestamp**: $STAMP
- **Project**: $PROJECT_KEY
- **Task**: $TASK_FILE
- **Mode**: $MODE
- **Terminal State**: $TERMINAL_STATE

## Preflight
- Plan Classification: $CLASS
- Plan Reason: $REASON

EOF

if [[ "$TERMINAL_STATE" == BLOCKED_* ]]; then
    echo "Terminal State: $TERMINAL_STATE"
    echo "Report: $(wslpath -w "$REPORT" 2>/dev/null || echo "$REPORT")"
    echo "Next safe operator action: resolve blockers before proceeding."
    exit 1
fi

echo "Preflight passed ($CLASS). Starting local-plan loop..."

# 2. Run Local Plan Build
bash "$SCRIPTS_DIR/ws_build.sh" "$PROJECT_KEY" "$TASK_FILE" --plan-only

BUILD_LATEST=$(find "$WS_HOME/build_runs" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n 1 | cut -d' ' -f2-)

cat <<EOF >> "$REPORT"
## Execution
- Build Run: $BUILD_LATEST
EOF

echo "Terminal State: $TERMINAL_STATE"
echo "Report: $(wslpath -w "$REPORT" 2>/dev/null || echo "$REPORT")"
if [ -n "$BUILD_LATEST" ]; then
    echo "Build Output: $(wslpath -w "$BUILD_LATEST" 2>/dev/null || echo "$BUILD_LATEST")"
fi
echo "Next safe operator action: review local plan and proceed to ws agent-run if ready."

#!/bin/bash
set -euo pipefail

WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
MODEL_HOME="${MODEL_HOME:-/mnt/d/ollama/models}"
if [ -f "$WS_HOME/scripts/ws_env.sh" ]; then
    source "$WS_HOME/scripts/ws_env.sh"
fi
WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
MODEL_HOME="${MODEL_HOME:-/mnt/d/ollama/models}"

RUN_DIR=${1:-}
STATUS=${2:-unknown}

if [ -z "$RUN_DIR" ]; then
    echo "Usage: ws_build_report.sh <run_dir> [status]"
    exit 1
fi

REPORT="$RUN_DIR/build_report.md"
{
    echo "# Build Report"
    echo ""
    echo "- Status: $STATUS"
    echo "- Run Folder: $RUN_DIR"
    echo "- Generated: $(date -Is)"
    echo ""
    echo "## Artifacts"
    for f in task.md project_metadata.md graph_context.md context_pack.md local_plan.md attempts.md test_output.md codex_packet.md codex_response.md final_diff.patch status.txt; do
        if [ -e "$RUN_DIR/$f" ]; then
            echo "- $f"
        fi
    done
    echo ""
    echo "## Status"
    if [ -f "$RUN_DIR/status.txt" ]; then
        cat "$RUN_DIR/status.txt"
    else
        echo "$STATUS"
    fi
    echo ""
    echo "## Task Lifecycle Recommendation"
    case "$STATUS" in
        COMPLETE|PASSED|passed)
            echo "Recommended next step: review the diff/tests, then run \`ws task-complete <task_file>\` if the task is done."
            ;;
        BLOCKED|FAILED|failed)
            echo "Recommended next step: inspect attempts/test output, then run \`ws task-block <task_file> \"reason\"\` or create a review packet."
            ;;
        PLAN_ONLY|planned|PLANNED)
            echo "Recommended next step: review \`local_plan.md\`; do not mark complete until an apply/test cycle succeeds."
            ;;
        *)
            echo "Recommended next step: review artifacts before changing task lifecycle status."
            ;;
    esac
} > "$REPORT"

echo "$REPORT"

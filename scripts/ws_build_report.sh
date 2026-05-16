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
    echo "## Summary"
    echo "- Status: $STATUS"
    echo "- Project: $([ -f "$RUN_DIR/project_metadata.md" ] && grep "^- Key:" "$RUN_DIR/project_metadata.md" | cut -d: -f2 | xargs || echo "unknown")"
    echo "- Generated: $(date -Is)"
    echo "- Run Folder: $RUN_DIR"
    echo ""
    echo "## Artifacts"
    for f in task.md project_metadata.md graph_context.md context_pack.md local_plan.md attempts.md test_output.md codex_packet.md codex_response.md final_diff.patch status.txt; do
        if [ -e "$RUN_DIR/$f" ]; then
            echo "- $f"
        fi
    done
    echo ""
    echo "## Final Status"
    if [ -f "$RUN_DIR/status.txt" ]; then
        echo "\`$(cat "$RUN_DIR/status.txt")\`"
    else
        echo "\`$STATUS\`"
    fi
    echo ""
    echo "## Proposed Plan"
    if [ -f "$RUN_DIR/local_plan.md" ]; then
        # Extract the first paragraph or non-code block text as summary
        (grep -v "^#" "$RUN_DIR/local_plan.md" | grep -v "^ " | grep -v "^$" | head -n 3 | sed 's/^/> /') || echo "> (no plan summary available)"
    else
        echo "No local plan generated."
    fi
    echo ""
    echo "## Task Lifecycle Recommendation"
    case "$STATUS" in
        passed|PASSED)
            echo "Recommended next step: review the diff/tests, then run \`ws task-complete <task_file>\` if the task is done."
            ;;
        failed|FAILED)
            echo "Recommended next step: inspect attempts/test output, then run \`ws task-block <task_file> \"reason\"\` or create a review packet."
            ;;
        planned|PLANNED)
            echo "Recommended next step: review \`local_plan.md\`; do not mark complete until an apply/test cycle succeeds."
            ;;
        blocked|BLOCKED)
            echo "Recommended next step: check if Ollama is running, check context limits, or clarify task goals."
            ;;
        *)
            echo "Recommended next step: review artifacts before changing task lifecycle status."
            ;;
    esac
} > "$REPORT"

echo "$REPORT"

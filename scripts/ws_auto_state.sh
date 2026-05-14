#!/bin/bash
set -euo pipefail

WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
if [ -f "$WS_HOME/scripts/ws_env.sh" ]; then
    source "$WS_HOME/scripts/ws_env.sh"
fi
WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"

ROOT="$WS_HOME/auto_runs"
MODE=${1:-status}
ARG=${2:-}

mkdir -p "$ROOT"

if [ "$MODE" = "runs" ]; then
    if find "$ROOT" -mindepth 1 -maxdepth 1 -type d | grep -q .; then
        find "$ROOT" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' | sort -nr | head -n 20 | cut -d' ' -f2-
    else
        echo "No auto runs found."
    fi
    exit 0
fi

if [ "$MODE" = "open" ]; then
    RUN_ID=${ARG:-}
    if [ -z "$RUN_ID" ]; then
        echo "Usage: ws_auto_state.sh open <latest|run_id>"
        exit 1
    fi
    if [ "$RUN_ID" = "latest" ]; then
        TARGET=$(find "$ROOT" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n 1 | cut -d' ' -f2-)
    else
        TARGET=$(find "$ROOT" -mindepth 1 -maxdepth 1 -type d -name "*$RUN_ID*" -print 2>/dev/null | head -n 1)
    fi
    if [ -z "$TARGET" ] || [ ! -d "$TARGET" ]; then
        echo "Auto run not found: $RUN_ID"
        exit 1
    fi
    echo "Auto Run:      $TARGET"
    echo "Status:        $TARGET/status.txt"
    echo "Task:          $TARGET/task.md"
    echo "Config:        $TARGET/run_config.md"
    echo "Models:        $TARGET/model_roles.md"
    echo "Context:       $TARGET/context_pack.md"
    echo "Plan:          $TARGET/local_plan.md"
    echo "Attempts:      $TARGET/local_attempts.md"
    echo "Tests:         $TARGET/test_output.md"
    echo "Guard:         $TARGET/apply_guard.md"
    echo "Codex Packet:  $TARGET/codex_packet.md"
    echo "Codex Usage:   $TARGET/codex_usage.md"
    echo "Codex Reply:   $TARGET/codex_response.md"
    echo "Codex Patch:   $TARGET/codex_patch.diff"
    echo "Patch Validation: $TARGET/codex_patch_validation.md"
    echo "Patch Apply:   $TARGET/codex_patch_apply.md"
    echo "Diff:          $TARGET/final_diff.patch"
    echo "Report:        $TARGET/final_report.md"
    exit 0
fi

if [ "$MODE" = "status" ] || [ -z "$MODE" ]; then
    echo "Auto Loop Status"
    echo "----------------"
    for status in PLAN_ONLY PASSED PASSED_WITH_CODEX BLOCKED_LOCAL BLOCKED_LOCAL_WITH_CHANGES BLOCKED_CODEX BLOCKED_CODEX_ADVICE_ONLY BLOCKED_CODEX_PATCH_INVALID FAILED_TESTS SAFETY_BLOCKED TIMEOUT NO_CHANGES NEEDS_USER_REVIEW FAILED_INTERNAL PATCH_INVALID BLOCKED_PATCH_INVALID PATCH_INVALID_APPROXIMATE BLOCKED_PATCH_INVALID_APPROXIMATE; do
        count=$(python3 - "$ROOT" "$status" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
wanted = sys.argv[2]
total = 0
for status_file in root.glob("*/status.txt"):
    try:
        if status_file.read_text(encoding="utf-8", errors="replace").strip() == wanted:
            total += 1
    except Exception:
        pass
print(total)
PY
)
        printf "%-18s %s\n" "$status:" "$count"
    done
    echo ""
    echo "Recent auto runs:"
    find "$ROOT" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n 12 | cut -d' ' -f2-
    exit 0
fi

echo "Usage: ws_auto_state.sh [status|runs|open]"
exit 1

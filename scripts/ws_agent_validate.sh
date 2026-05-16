#!/bin/bash

set -u

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
SCRIPTS_DIR="$WS_HOME/scripts"
REPORTS_DIR="$WS_HOME/reports"
TASK_FILE="$WS_HOME/tasks/generated/workstation_control_plane_task_001_stabilize_ws_command_documentation.md"
STAMP=$(date +%Y%m%d_%H%M%S)
REPORT="$REPORTS_DIR/AGENT_CONTRACT_VALIDATION_$STAMP.md"

mkdir -p "$REPORTS_DIR"

PASS_COUNT=0
FAIL_COUNT=0
CHECK_LINES=()
DETAIL_LINES=()

record_pass() {
    PASS_COUNT=$((PASS_COUNT + 1))
    CHECK_LINES+=("- PASS: $1")
}

record_fail() {
    FAIL_COUNT=$((FAIL_COUNT + 1))
    CHECK_LINES+=("- FAIL: $1")
}

record_detail() {
    DETAIL_LINES+=("- $1")
}

WS_SCRIPT="$SCRIPTS_DIR/ws"
AGENT_RUN_PS1="$SCRIPTS_DIR/ws_agent_run.ps1"
CANARY_STATUS="$REPORTS_DIR/agent_canary_status.json"

if [ -f "$WS_SCRIPT" ]; then
    record_pass "scripts/ws exists"
else
    record_fail "scripts/ws exists"
fi

for cmd in build agent-status agent-canary agent-run agent-import agent-validate; do
    if grep -q "^[[:space:]]*$cmd)" "$WS_SCRIPT"; then
        record_pass "scripts/ws dispatches $cmd"
    else
        record_fail "scripts/ws dispatches $cmd"
    fi
done

PS_PARSE_OUTPUT=$(
    powershell.exe -NoProfile -Command \
        "[scriptblock]::Create((Get-Content -Raw 'D:\_ai_brain\scripts\ws_agent_run.ps1')) | Out-Null; \
         [scriptblock]::Create((Get-Content -Raw 'D:\_ai_brain\scripts\ws_agent_status.ps1')) | Out-Null; \
         [scriptblock]::Create((Get-Content -Raw 'D:\_ai_brain\scripts\ws_agent_canary.ps1')) | Out-Null; \
         [scriptblock]::Create((Get-Content -Raw 'D:\_ai_brain\scripts\ws_agent_import.ps1')) | Out-Null; \
         Write-Output 'PS_PARSE_OK'" 2>&1
)
if printf '%s\n' "$PS_PARSE_OUTPUT" | grep -q 'PS_PARSE_OK'; then
    record_pass "PowerShell agent scripts parse"
else
    record_fail "PowerShell agent scripts parse"
    record_detail "PowerShell parse output: ${PS_PARSE_OUTPUT//$'\n'/ | }"
fi

STATUS_OUTPUT=$(bash "$WS_SCRIPT" agent-status 2>&1)
if printf '%s\n' "$STATUS_OUTPUT" | grep -q 'Windows Agent Orchestrator Status' &&
   printf '%s\n' "$STATUS_OUTPUT" | grep -q 'Selected launcher:'; then
    record_pass "ws agent-status returns usable output"
else
    record_fail "ws agent-status returns usable output"
fi
record_detail "agent-status output: ${STATUS_OUTPUT//$'\n'/ | }"

CANARY_BEFORE=$(cat "$CANARY_STATUS" 2>/dev/null || true)
CANARY_OUTPUT=$(bash "$WS_SCRIPT" agent-canary 2>&1)
CANARY_AFTER=$(cat "$CANARY_STATUS" 2>/dev/null || true)
if printf '%s\n' "$CANARY_OUTPUT" | grep -q 'Agent canary starting:'; then
    record_pass "ws agent-canary prints visible startup output"
else
    record_fail "ws agent-canary prints visible startup output"
fi
if [ -n "$CANARY_AFTER" ] && [ "$CANARY_AFTER" != "$CANARY_BEFORE" ]; then
    record_pass "ws agent-canary refreshes canary status"
else
    record_fail "ws agent-canary refreshes canary status"
fi
if printf '%s\n' "$CANARY_OUTPUT" | grep -q 'AGENT_CANARY_PASSED:'; then
    record_pass "ws agent-canary passes"
else
    record_fail "ws agent-canary passes"
fi
record_detail "agent-canary output: ${CANARY_OUTPUT//$'\n'/ | }"

DRY_RUN_OUTPUT=$(
    bash "$WS_SCRIPT" agent-run workstation_control_plane "$TASK_FILE" \
        --dry-run --mode detect --branch --max-files 5 --max-minutes 10 --stop-on-fail 2>&1
)
DRY_RUN_NORMALIZED=$(printf '%s\n' "$DRY_RUN_OUTPUT" | tr -d '\r')
RUN_WIN=$(printf '%s\n' "$DRY_RUN_NORMALIZED" | grep -E '^[A-Za-z]:\\.*_agent_run$' | tail -n 1 || true)
RUN_WSL=''
if [ -n "$RUN_WIN" ]; then
    RUN_WSL=$(wslpath -u "$RUN_WIN")
fi
if printf '%s\n' "$DRY_RUN_NORMALIZED" | grep -q '^PLAN_ONLY$'; then
    record_pass "ws agent-run dry-run returns PLAN_ONLY"
else
    record_fail "ws agent-run dry-run returns PLAN_ONLY"
fi
if [ -n "$RUN_WSL" ] && [ -f "$RUN_WSL/status.txt" ] && [ -f "$RUN_WSL/final_report.md" ]; then
    record_pass "dry-run writes status.txt and final_report.md"
else
    record_fail "dry-run writes status.txt and final_report.md"
fi
if [ -n "$RUN_WSL" ] && [ "$(tr -d '\r\n' < "$RUN_WSL/status.txt" 2>/dev/null)" != "CODEX_RUNNING" ]; then
    record_pass "dry-run does not leave CODEX_RUNNING"
else
    record_fail "dry-run does not leave CODEX_RUNNING"
fi
record_detail "dry-run output: ${DRY_RUN_NORMALIZED//$'\n'/ | }"

if grep -q 'if (-not \$task.HasAllowed)' "$AGENT_RUN_PS1" &&
   grep -q 'Task is missing explicit Allowed Files\.' "$AGENT_RUN_PS1"; then
    record_pass "apply path requires explicit Allowed Files"
else
    record_fail "apply path requires explicit Allowed Files"
fi
if grep -q '^Allowed Files:$' "$TASK_FILE" &&
   ! grep -A3 '^Allowed Files:$' "$TASK_FILE" | grep -q 'not specified'; then
    record_pass "canonical sample task has explicit Allowed Files"
else
    record_fail "canonical sample task has explicit Allowed Files"
fi

if git -C "$WS_HOME" check-ignore -q auto_runs/; then
    record_pass "auto_runs/ is ignored by Git"
else
    record_fail "auto_runs/ is ignored by Git"
fi

RESULT="PASS"
if [ "$FAIL_COUNT" -gt 0 ]; then
    RESULT="FAIL"
fi

{
    echo "# Agent Contract Validation"
    echo
    echo "## Summary"
    echo "- Result: $RESULT"
    echo "- Timestamp: $STAMP"
    echo "- Passed: $PASS_COUNT"
    echo "- Failed: $FAIL_COUNT"
    echo "- Dry-run folder: ${RUN_WIN:-not created}"
    echo
    echo "## Checks"
    printf '%s\n' "${CHECK_LINES[@]}"
    echo
    echo "## Details"
    printf '%s\n' "${DETAIL_LINES[@]}"
} > "$REPORT"

echo "$RESULT"
echo "$REPORT"

if [ "$FAIL_COUNT" -gt 0 ]; then
    exit 1
fi

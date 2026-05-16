#!/bin/bash
set -euo pipefail

WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
if [ -f "$WS_HOME/scripts/ws_env.sh" ]; then
    source "$WS_HOME/scripts/ws_env.sh"
fi

REPORT_DIR="$WS_HOME/reports"
mkdir -p "$REPORT_DIR"
TS=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="$REPORT_DIR/READINESS_$TS.md"

echo "Running daily readiness check..."

{
    echo "# Daily Readiness Report - $TS"
    echo ""

    echo "## 1. Workstation Health"
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(wslpath -w "$WS_HOME/scripts/check_health.ps1")"

    echo ""
    echo "## 2. Model & KV Configuration"
    bash "$WS_HOME/scripts/ai_model_current.sh"

    echo ""
    echo "## 3. Project Registry"
    if [ -f "$WS_HOME/registry/projects.yaml" ]; then
        COUNT=$(grep -E "^  [a-z0-9_]+:" "$WS_HOME/registry/projects.yaml" | wc -l)
        echo "Registry: $COUNT projects detected."
    else
        echo "Registry: FAILED (projects.yaml missing)"
    fi

    echo ""
    echo "## 4. Frontier Status"
    bash "$WS_HOME/scripts/ws_frontier_status.sh"

} > "$REPORT_FILE" 2>&1

# Print a concise summary to stdout
echo "-----------------------------------------"
echo " Readiness Summary"
echo "-----------------------------------------"
grep -E "\[OK\]|\[FAIL\]|\[INFO\]|Model Profile|KV Profile|Registry:|DETECTED|NOT FOUND" "$REPORT_FILE" | sed 's/^[[:space:]]*//'
echo "-----------------------------------------"
echo "Report: $REPORT_FILE"

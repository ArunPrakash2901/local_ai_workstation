#!/bin/bash
set -euo pipefail

WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
if [ -f "$WS_HOME/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "$WS_HOME/scripts/ws_env.sh"
fi
WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"

PROJECT_KEY=${1:-}
TASK_FILE=${2:-}
shift 2 || true

if [ -z "$PROJECT_KEY" ] || [ -z "$TASK_FILE" ]; then
    echo "Usage: ws codex-work <project_key> <task_file> [--mode auto|handoff|detect] [flags]"
    exit 1
fi

MODE="detect"
ARGS=()
while [ $# -gt 0 ]; do
    case "$1" in
        --mode)
            MODE=${2:-detect}
            shift 2
            ;;
        --mode=*)
            MODE="${1#*=}"
            shift
            ;;
        *)
            ARGS+=("$1")
            shift
            ;;
    esac
done

TASK_FILE=${TASK_FILE//\\//}
if [[ "$TASK_FILE" =~ ^([A-Za-z]):/(.*)$ ]]; then
    drive=$(echo "${BASH_REMATCH[1]}" | tr 'A-Z' 'a-z')
    TASK_FILE="/mnt/$drive/${BASH_REMATCH[2]}"
fi

PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"
CACHE_FILE="$WS_HOME/reports/codex_canary_status.json"

CANARY_STATUS="FAIL"
CANARY_RECOMMENDED="handoff"
if [ -f "$CACHE_FILE" ]; then
    read -r CANARY_STATUS CANARY_RECOMMENDED <<EOF
$(python3 - "$CACHE_FILE" <<'PY'
import json, sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    print("FAIL handoff")
    raise SystemExit(0)
data = json.loads(path.read_text(encoding="utf-8"))
status = data.get("status", "FAIL")
mode = "handoff"
ts = data.get("timestamp_utc", "")
try:
    if status == "PASS" and ts:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - dt).total_seconds()
        if age <= 86400:
            mode = "cli-auto"
        else:
            status = "STALE"
except Exception:
    if status == "PASS":
        mode = "cli-auto"
print(status, mode)
PY
)
EOF
fi

case "$MODE" in
    auto)
        if [ "$CANARY_STATUS" != "PASS" ] || [ "$CANARY_RECOMMENDED" != "cli-auto" ]; then
            echo "CODEX_CLI_AUTO_UNAVAILABLE"
            echo "Recommended mode: handoff"
            exit 2
        fi
        exec "$PYTHON" "$WS_HOME/scripts/ws_codex_work_impl.py" "$PROJECT_KEY" "$TASK_FILE" "${ARGS[@]}"
        ;;
    handoff)
        exec "$PYTHON" "$WS_HOME/scripts/ws_codex_flow.py" handoff "$PROJECT_KEY" "$TASK_FILE" "${ARGS[@]}"
        ;;
    detect)
        if [ "$CANARY_STATUS" = "PASS" ] && [ "$CANARY_RECOMMENDED" = "cli-auto" ]; then
            exec "$PYTHON" "$WS_HOME/scripts/ws_codex_work_impl.py" "$PROJECT_KEY" "$TASK_FILE" "${ARGS[@]}"
        fi
        exec "$PYTHON" "$WS_HOME/scripts/ws_codex_flow.py" handoff "$PROJECT_KEY" "$TASK_FILE" "${ARGS[@]}"
        ;;
    *)
        echo "Usage: ws codex-work <project_key> <task_file> [--mode auto|handoff|detect] [flags]"
        exit 1
        ;;
esac

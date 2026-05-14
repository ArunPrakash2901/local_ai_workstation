#!/bin/bash
set -euo pipefail

WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
MODEL_HOME="${MODEL_HOME:-/mnt/d/ollama/models}"
if [ -f "$WS_HOME/scripts/ws_env.sh" ]; then
    source "$WS_HOME/scripts/ws_env.sh"
fi
WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
MODEL_HOME="${MODEL_HOME:-/mnt/d/ollama/models}"

TASK_FILE=${1:-}
shift || true
REASON="$*"

if [ -z "$TASK_FILE" ] || [ -z "$REASON" ]; then
    echo "Usage: ws task-block <task_file> <reason>"
    exit 1
fi

TASK_FILE=${TASK_FILE//\\//}
if [[ "$TASK_FILE" =~ ^([A-Za-z]):/(.*)$ ]]; then
    drive=$(echo "${BASH_REMATCH[1]}" | tr 'A-Z' 'a-z')
    TASK_FILE="/mnt/$drive/${BASH_REMATCH[2]}"
fi

if [ ! -f "$TASK_FILE" ]; then
    echo "Task file not found: $TASK_FILE"
    exit 1
fi

BASE="$WS_HOME"
DEST_DIR="$BASE/tasks/blocked"
mkdir -p "$DEST_DIR"
DEST="$DEST_DIR/$(basename "$TASK_FILE")"
{
    echo ""
    echo "Block Reason:"
    echo "$REASON"
    echo ""
    echo "Blocked At:"
    date -Is
} >> "$TASK_FILE"
python3 - "$TASK_FILE" <<'PY'
import re, sys
from pathlib import Path
p=Path(sys.argv[1])
t=p.read_text(encoding="utf-8")
t=re.sub(r"(?ms)^Status:\s*\n.*?(?=^\w|^\Z)", "Status:\nblocked\n\n", t, count=1)
t=re.sub(r"(?ms)^Escalation:\s*\n.*?(?=^\w|^\Z)", "Escalation:\nblocked\n\n", t, count=1)
p.write_text(t, encoding="utf-8", newline="\n")
PY
mv "$TASK_FILE" "$DEST"
echo "$DEST"

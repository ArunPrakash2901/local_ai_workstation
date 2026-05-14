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
WITH_FLAG=${2:-}
PROVIDER=${3:-}

if [ -z "$TASK_FILE" ] || [ "$WITH_FLAG" != "--with" ] || [ "$PROVIDER" != "codex" ]; then
    echo "Usage: ws task-review <task_file> --with codex"
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
PACKETS="$BASE/frontier/packets"
PYTHON="$BASE/runtimes/workstation_venv/bin/python3"
mkdir -p "$PACKETS" "$BASE/tasks/reviewed"

PACKET="$PACKETS/$(date +%Y%m%d_%H%M%S)_task_review_codex.md"
"$PYTHON" - "$TASK_FILE" "$PACKET" <<'PY'
import re
import sys
from pathlib import Path

task = Path(sys.argv[1])
packet = Path(sys.argv[2])
text = task.read_text(encoding="utf-8", errors="replace")
project = re.search(r"(?ms)^Project:\s*\n(.+?)(?=^\w|^\Z)", text)
project = project.group(1).strip().splitlines()[0] if project else "unknown"
packet.write_text(f"""# Escalation Packet

## Target
{project}

## Intended Provider
codex

## Reason for Escalation
task review requested; packet only, no automatic send

## User Question
Review this task for clarity, safety, scope, and readiness for ws build.

## Project Metadata
- Project Key: {project}
- Task File: {task}

## Local Context
Task content:

```markdown
{text}
```

## Local Model Notes
Not applicable. This is a task review packet.

## Relevant Error or Test Output
blank unless provided

## Specific Question for Frontier Model
Is this task atomic, safe, and clear enough for a bounded ws build run? If not, what should be changed?

## Safety Notice
Secrets, raw datasets, credentials, .env files, private keys, and broker keys were excluded.
""", encoding="utf-8", newline="\n")
print(packet)
PY

bash "$BASE/scripts/ws_redact_packet.sh" "$PACKET"
echo "Review packet: $PACKET"
echo "Not sent. To send explicitly, run: ws escalate codex $PACKET"

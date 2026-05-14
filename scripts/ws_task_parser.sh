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
OUT_JSON=${2:-}

if [ -z "$TASK_FILE" ] || [ -z "$OUT_JSON" ]; then
    echo "Usage: ws_task_parser.sh <task_file> <out_json>"
    exit 1
fi

TASK_FILE=${TASK_FILE//\\//}
if [[ "$TASK_FILE" =~ ^([A-Za-z]):/(.*)$ ]]; then
    drive=$(echo "${BASH_REMATCH[1]}" | tr 'A-Z' 'a-z')
    TASK_FILE="/mnt/$drive/${BASH_REMATCH[2]}"
fi

PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

"$PYTHON" - "$TASK_FILE" "$OUT_JSON" <<'PY'
import json
import re
import sys
from pathlib import Path

task_file = Path(sys.argv[1])
out_json = Path(sys.argv[2])

if not task_file.is_file():
    print(f"Task file not found: {task_file}", file=sys.stderr)
    sys.exit(1)

text = task_file.read_text(encoding="utf-8", errors="replace")
matches = list(re.finditer(r"(?m)^##\s+Task\s+([A-Za-z0-9_.-]+)\s*:\s*(.+?)\s*$", text))
if not matches:
    print("Could not parse tasks. Expected headings like: ## Task 001: Title", file=sys.stderr)
    sys.exit(2)

def section(body, name):
    pat = re.compile(rf"(?ms)^{re.escape(name)}:\s*\n(.*?)(?=^[A-Za-z][A-Za-z ]+:\s*$|\Z)")
    m = pat.search(body)
    return m.group(1).strip() if m else ""

def bullets(value):
    out = []
    for line in value.splitlines():
        line = line.strip()
        if line.startswith("- "):
            out.append(line[2:].strip())
        elif line:
            out.append(line)
    return out

tasks = []
for i, m in enumerate(matches):
    start = m.end()
    end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
    body = text[start:end].strip()
    task = {
        "id": m.group(1).strip(),
        "title": m.group(2).strip(),
        "goal": section(body, "Goal"),
        "acceptance_criteria": bullets(section(body, "Acceptance Criteria")),
        "allowed_files": bullets(section(body, "Allowed Files")),
        "test_command": section(body, "Test Command").splitlines()[0].strip() if section(body, "Test Command") else "",
        "risk": section(body, "Risk").splitlines()[0].strip() if section(body, "Risk") else "unspecified",
        "raw": f"## Task {m.group(1).strip()}: {m.group(2).strip()}\n\n{body}\n",
    }
    if not task["goal"] or not task["acceptance_criteria"]:
        print(f"Task {task['id']} is missing Goal or Acceptance Criteria.", file=sys.stderr)
        sys.exit(3)
    tasks.append(task)

out_json.parent.mkdir(parents=True, exist_ok=True)
out_json.write_text(json.dumps({"source": str(task_file), "tasks": tasks}, indent=2), encoding="utf-8")
print(out_json)
PY

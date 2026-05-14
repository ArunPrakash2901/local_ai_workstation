#!/bin/bash
set -euo pipefail

WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
MODEL_HOME="${MODEL_HOME:-/mnt/d/ollama/models}"
if [ -f "$WS_HOME/scripts/ws_env.sh" ]; then
    source "$WS_HOME/scripts/ws_env.sh"
fi
WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
MODEL_HOME="${MODEL_HOME:-/mnt/d/ollama/models}"

PROJECT_FILTER=${1:-}
ROOT="$WS_HOME/tasks"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

mkdir -p "$ROOT/inbox" "$ROOT/active" "$ROOT/generated"

"$PYTHON" - "$ROOT" "$PROJECT_FILTER" <<'PY'
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
project_filter = sys.argv[2]
risk_rank = {"low": 0, "medium": 1, "high": 2}
candidates = []
for folder, status_rank in [("active", 0), ("inbox", 1), ("generated", 2)]:
    for path in (root / folder).glob("*.md"):
        text = path.read_text(encoding="utf-8", errors="replace")
        project = re.search(r"(?ms)^Project:\s*\n(.+?)(?=^\w|^\Z)", text)
        project = project.group(1).strip().splitlines()[0] if project else ""
        if project_filter and project != project_filter:
            continue
        risk = re.search(r"(?ms)^Risk:\s*\n(.+?)(?=^\w|^\Z)", text)
        risk = risk.group(1).strip().splitlines()[0].lower() if risk else "medium"
        candidates.append((folder, status_rank, risk_rank.get(risk, 1), path.stat().st_mtime, path))
if not candidates:
    print("No matching task found.", file=sys.stderr)
    sys.exit(1)
candidates.sort(key=lambda x: (x[1], x[2], x[3]))
folder, _, _, _, path = candidates[0]
print(f"Selected task from {folder}:")
print(path)
PY

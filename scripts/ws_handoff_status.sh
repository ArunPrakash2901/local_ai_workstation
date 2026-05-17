#!/bin/bash

set -euo pipefail

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
HANDOFFS_DIR="$WS_HOME/handoffs"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

if [ ! -d "$HANDOFFS_DIR" ]; then
    echo "No handoff folders found."
    exit 0
fi

"$PYTHON" - "$HANDOFFS_DIR" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

handoffs_dir = Path(sys.argv[1])
rows = []

for handoff_dir in sorted((p for p in handoffs_dir.iterdir() if p.is_dir()), reverse=True):
    metadata_path = handoff_dir / "metadata.json"
    if not metadata_path.is_file():
        continue
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        continue
    try:
        path_display = subprocess.run(
            ["wslpath", "-w", str(handoff_dir)],
            check=False,
            capture_output=True,
            text=True,
        ).stdout.strip() or str(handoff_dir)
    except FileNotFoundError:
        path_display = str(handoff_dir)
    rows.append(
        (
            metadata.get("timestamp", "unknown"),
            metadata.get("target", "unknown"),
            metadata.get("purpose", "unknown"),
            metadata.get("current_state", "unknown"),
            path_display,
        )
    )

if not rows:
    print("No handoff folders found.")
    raise SystemExit(0)

print("Recent Handoffs")
print("---------------")
for timestamp, target, purpose, state, path in rows[:20]:
    print(f"{timestamp} | {target} | {purpose} | {state} | {path}")
PY

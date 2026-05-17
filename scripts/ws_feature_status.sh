#!/bin/bash

set -euo pipefail

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
FEATURES_DIR="$WS_HOME/features"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

if [ ! -d "$FEATURES_DIR" ]; then
    echo "No feature strongholds found."
    exit 0
fi

"$PYTHON" - "$FEATURES_DIR" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

features_dir = Path(sys.argv[1])
rows = []

for state_path in features_dir.glob("*/*/state.json"):
    try:
        metadata = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        continue
    feature_dir = state_path.parent
    try:
        path_display = subprocess.run(
            ["wslpath", "-w", str(feature_dir)],
            check=False,
            capture_output=True,
            text=True,
        ).stdout.strip() or str(feature_dir)
    except FileNotFoundError:
        path_display = str(feature_dir)
    rows.append(
        (
            metadata.get("created_at", ""),
            metadata.get("feature_id", "unknown"),
            metadata.get("project_key", "unknown"),
            metadata.get("title", "unknown"),
            metadata.get("current_state", "unknown"),
            path_display,
        )
    )

if not rows:
    print("No feature strongholds found.")
    raise SystemExit(0)

print("Recent Feature Strongholds")
print("--------------------------")
for _, feature_id, project, title, state, path in sorted(rows, reverse=True)[:20]:
    print(f"{feature_id} | {project} | {title} | {state} | {path}")
PY

#!/bin/bash

set -euo pipefail

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
STRONGHOLDS_DIR="$WS_HOME/strongholds"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

if [ ! -d "$STRONGHOLDS_DIR" ]; then
    echo "No strongholds found."
    exit 0
fi

echo "Recent Strongholds"
echo "-------------------"

# We use Python to parse state.json files and format output
"$PYTHON" - "$STRONGHOLDS_DIR" << 'PY'
import sys
import json
from pathlib import Path

strongholds_dir = Path(sys.argv[1])
if not strongholds_dir.exists():
    sys.exit(0)

# Find all state.json files
state_files = sorted(strongholds_dir.glob("**/state.json"), key=lambda x: x.stat().st_mtime, reverse=True)

if not state_files:
    print("No strongholds found.")
    sys.exit(0)

print(f"{'TYPE':<15} | {'TITLE':<40} | {'STATE':<20} | {'ID'}")
print("-" * 100)

for sf in state_files:
    try:
        state = json.loads(sf.read_text(encoding="utf-8"))
        stype = state.get("type", "unknown")
        title = state.get("title", "unknown")
        curr_state = state.get("current_state", "unknown")
        sid = state.get("stronghold_id", "unknown")
        
        # Truncate title if too long
        if len(title) > 40:
            title = title[:37] + "..."
            
        print(f"{stype:<15} | {title:<40} | {curr_state:<20} | {sid}")
    except Exception as e:
        # print(f"Error reading {sf}: {e}")
        pass
PY

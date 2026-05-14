#!/bin/bash
set -euo pipefail

WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
if [ -f "$WS_HOME/scripts/ws_env.sh" ]; then
    source "$WS_HOME/scripts/ws_env.sh"
fi
MODEL_HOME="${MODEL_HOME:-/mnt/d/ollama/models}"

PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"
PATHS_YAML="${WS_PATHS_YAML:-$WS_HOME/registry/paths.yaml}"

if [ ! -f "$PATHS_YAML" ]; then
    echo "Path registry missing: $PATHS_YAML"
    echo "WS_HOME=$WS_HOME"
    echo "MODEL_HOME=$MODEL_HOME"
    exit 1
fi

"$PYTHON" - "$PATHS_YAML" <<'PY'
import os
import sys
from pathlib import Path

import yaml

paths_yaml = Path(sys.argv[1])
data = yaml.safe_load(paths_yaml.read_text(encoding="utf-8")) or {}
live = data.get("live", {})
future = data.get("future", {})
active = data.get("active", {})

def exists_wsl(path):
    return "yes" if path and Path(path).exists() else "no"

rows = [
    ("live control plane", live.get("control_plane_wsl"), live.get("control_plane_windows")),
    ("parent folder", live.get("parent_wsl"), live.get("parent_windows")),
    ("live Ollama models", live.get("ollama_models_wsl"), live.get("ollama_models_windows")),
    ("future control plane", future.get("control_plane_wsl"), future.get("control_plane_windows")),
    ("future Ollama models", future.get("ollama_models_wsl"), future.get("ollama_models_windows")),
]

print("Workstation Path Status")
print("-----------------------")
for label, wsl_path, win_path in rows:
    print(f"{label:22} | exists={exists_wsl(wsl_path):3} | WSL={wsl_path} | Windows={win_path}")
print("")
print(f"WS_HOME:           {os.environ.get('WS_HOME', active.get('ws_home', ''))}")
print(f"WS_PARENT:         {os.environ.get('WS_PARENT', active.get('ws_parent', ''))}")
print(f"MODEL_HOME:        {os.environ.get('MODEL_HOME', active.get('model_home', ''))}")
print(f"WS_PATHS_YAML:     {os.environ.get('WS_PATHS_YAML', str(paths_yaml))}")
print(f"Migration mode:    {active.get('migration_mode', os.environ.get('WS_MIGRATION_MODE', 'unknown'))}")
print(f"Using live paths:  {'yes' if active.get('migration_mode') == 'live_paths' and active.get('ws_home') == live.get('control_plane_wsl') else 'no'}")
PY

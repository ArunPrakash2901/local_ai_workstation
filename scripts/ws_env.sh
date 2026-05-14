#!/bin/bash

# Sourceable path environment for the local AI workstation.
# This file must stay safe for `source` from any bash script.

if [ -z "${WS_HOME:-}" ]; then
    export WS_HOME="/mnt/d/_ai_brain"
fi

if [ -z "${WS_PARENT:-}" ]; then
    export WS_PARENT="/mnt/d/Local_AI_Workstation"
fi

if [ -z "${MODEL_HOME:-}" ]; then
    export MODEL_HOME="/mnt/d/ollama/models"
fi

if [ -z "${WS_PATHS_YAML:-}" ]; then
    export WS_PATHS_YAML="$WS_HOME/registry/paths.yaml"
fi

if [ -f "$WS_PATHS_YAML" ]; then
    _ws_python="$WS_HOME/runtimes/workstation_venv/bin/python3"
    if [ -x "$_ws_python" ]; then
        _ws_exports=$("$_ws_python" - "$WS_PATHS_YAML" <<'PY' 2>/dev/null
import shlex
import sys
import yaml

with open(sys.argv[1], "r", encoding="utf-8") as f:
    data = yaml.safe_load(f) or {}
active = data.get("active", {})
for key, env_name in [
    ("ws_home", "WS_HOME"),
    ("ws_parent", "WS_PARENT"),
    ("model_home", "MODEL_HOME"),
    ("migration_mode", "WS_MIGRATION_MODE"),
]:
    value = active.get(key)
    if value:
        print(f"export {env_name}={shlex.quote(str(value))}")
PY
)
        if [ -n "$_ws_exports" ]; then
            eval "$_ws_exports"
            export WS_PATHS_YAML="$WS_HOME/registry/paths.yaml"
        fi
    fi
    unset _ws_python _ws_exports
fi

if [ -z "${WS_MIGRATION_MODE:-}" ]; then
    export WS_MIGRATION_MODE="live_paths"
fi

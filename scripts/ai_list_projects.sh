#!/bin/bash

WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
if [ -f "$WS_HOME/scripts/ws_env.sh" ]; then
    source "$WS_HOME/scripts/ws_env.sh"
fi

REGISTRY_DIR="$WS_HOME/registry"
PROJECTS_YAML="$REGISTRY_DIR/projects.yaml"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

echo "Registered Projects:"
echo "-------------------"

$PYTHON -c "
import yaml
with open('$PROJECTS_YAML', 'r') as f:
    data = yaml.safe_load(f)
    for key, info in data['projects'].items():
        print(f'[{info.get(\"status\", \"unknown\")}] {key:20} | {info.get(\"display_name\", \"\")}')
"

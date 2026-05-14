#!/bin/bash

WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
if [ -f "$WS_HOME/scripts/ws_env.sh" ]; then
    source "$WS_HOME/scripts/ws_env.sh"
fi

REGISTRY_DIR="$WS_HOME/registry"
ACTIVE_MODEL="$REGISTRY_DIR/active_model.yaml"
ACTIVE_KV="$REGISTRY_DIR/active_kv_profile.yaml"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

echo "Current Active Configuration:"
echo "----------------------------"

$PYTHON -c "
import yaml
with open('$ACTIVE_MODEL', 'r') as f:
    am = yaml.safe_load(f)
with open('$ACTIVE_KV', 'r') as f:
    ak = yaml.safe_load(f)

print(f'Model Profile:  {am.get(\"active_profile\")}')
print(f'Ollama Model:   {am.get(\"active_model\")}')
print(f'Mode:           {am.get(\"mode\")}')
print(f'KV Profile:     {ak.get(\"active_profile\")}')
print(f'KV Type:        {ak.get(\"kv_cache_type\")}')
print(f'Context:        {am.get(\"context_length\")} (Model) / {ak.get(\"context\")} (KV)')
"

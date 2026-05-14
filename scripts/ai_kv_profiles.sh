#!/bin/bash

WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
if [ -f "$WS_HOME/scripts/ws_env.sh" ]; then
    source "$WS_HOME/scripts/ws_env.sh"
fi

REGISTRY_DIR="$WS_HOME/registry"
KV_YAML="$REGISTRY_DIR/kv_profiles.yaml"
ACTIVE_KV="$REGISTRY_DIR/active_kv_profile.yaml"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

echo "KV Cache Profiles:"
echo "--------------------------------------------------------------------------------"
printf "%-25s %-10s %-10s %-10s\n" "Profile Key" "Type" "Flash" "Context"
echo "--------------------------------------------------------------------------------"

$PYTHON -c "
import yaml
with open('$KV_YAML', 'r') as f:
    profiles = yaml.safe_load(f)
with open('$ACTIVE_KV', 'r') as f:
    active = yaml.safe_load(f)

for key, info in profiles.items():
    active_marker = '*' if key == active.get('active_profile') else ' '
    print(f\"{active_marker}{key:<24} {info.get('kv_cache_type'):<10} {str(info.get('flash_attention')):<10} {info.get('context'):<10}\")
"

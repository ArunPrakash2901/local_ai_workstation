#!/bin/bash

PROFILE_KEY=$1
if [ -z "$PROFILE_KEY" ]; then
    echo "Usage: ai_kv_use <profile_key>"
    exit 1
fi

REGISTRY_DIR="/mnt/d/_ai_brain/registry"
KV_YAML="$REGISTRY_DIR/kv_profiles.yaml"
ACTIVE_KV="$REGISTRY_DIR/active_kv_profile.yaml"
PYTHON="/mnt/d/_ai_brain/runtimes/workstation_venv/bin/python3"

$PYTHON -c "
import yaml
import sys

profile_key = sys.argv[1]
with open('$KV_YAML', 'r') as f:
    profiles = yaml.safe_load(f)

if profile_key not in profiles:
    print(f'Error: Profile \"{profile_key}\" not found.')
    sys.exit(1)

kv_info = profiles[profile_key]
with open('$ACTIVE_KV', 'r') as f:
    active = yaml.safe_load(f)

active['active_profile'] = profile_key
active['kv_cache_type'] = kv_info.get('kv_cache_type')
active['flash_attention'] = kv_info.get('flash_attention')
active['context'] = kv_info.get('context')

with open('$ACTIVE_KV', 'w') as f:
    yaml.dump(active, f)

print(f'Switched to KV profile: {profile_key}')
print(f'KV Type:                {active[\"kv_cache_type\"]}')
print(f'Flash Attention:        {active[\"flash_attention\"]}')
print(f'Note: Run ai_apply_ollama_profile.ps1 in PowerShell to apply changes.')
" "$PROFILE_KEY"

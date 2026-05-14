#!/bin/bash

PROFILE_KEY=$1
if [ -z "$PROFILE_KEY" ]; then
    echo "Usage: ai_model_use <profile_key>"
    exit 1
fi

REGISTRY_DIR="/mnt/d/_ai_brain/registry"
MODELS_YAML="$REGISTRY_DIR/models.yaml"
ACTIVE_YAML="$REGISTRY_DIR/active_model.yaml"
PYTHON="/mnt/d/_ai_brain/runtimes/workstation_venv/bin/python3"

$PYTHON -c "
import yaml
import sys

profile_key = sys.argv[1]
with open('$MODELS_YAML', 'r') as f:
    models = yaml.safe_load(f)

if profile_key not in models:
    print(f'Error: Profile \"{profile_key}\" not found.')
    sys.exit(1)

model_info = models[profile_key]
with open('$ACTIVE_YAML', 'r') as f:
    active = yaml.safe_load(f)

active['active_profile'] = profile_key
active['active_model'] = model_info.get('model_name')
active['context_length'] = model_info.get('default_context', 8192)
active['mode'] = 'lab' if model_info.get('lab_only') else 'daily'

with open('$ACTIVE_YAML', 'w') as f:
    yaml.dump(active, f)

print(f'Switched to profile: {profile_key}')
print(f'Model:               {active[\"active_model\"]}')
print(f'Mode:                {active[\"mode\"]}')
" "$PROFILE_KEY"

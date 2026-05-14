#!/bin/bash

WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
if [ -f "$WS_HOME/scripts/ws_env.sh" ]; then
    source "$WS_HOME/scripts/ws_env.sh"
fi
MODEL_HOME="${MODEL_HOME:-/mnt/d/ollama/models}"

REGISTRY_DIR="$WS_HOME/registry"
MODELS_YAML="$REGISTRY_DIR/models.yaml"
ACTIVE_YAML="$REGISTRY_DIR/active_model.yaml"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

echo "Model Profiles:"
echo "--------------------------------------------------------------------------------"
printf "%-25s %-15s %-10s %-10s %-10s\n" "Profile Key" "Model Name" "Daily" "Lab" "Status"
echo "--------------------------------------------------------------------------------"

# Get installed models from ollama
if command -v ollama &> /dev/null; then
    INSTALLED=$(ollama list | awk '{print $1}' | tail -n +2)
elif command -v ollama.exe &> /dev/null; then
    INSTALLED=$(ollama.exe list | awk '{print $1}' | tail -n +2)
else
    echo "Warning: ollama command not found. Status will show MISSING. MODEL_HOME=$MODEL_HOME"
    INSTALLED=""
fi

$PYTHON -c "
import yaml
import sys

installed = sys.argv[1].split()
with open('$MODELS_YAML', 'r') as f:
    models = yaml.safe_load(f)

with open('$ACTIVE_YAML', 'r') as f:
    active = yaml.safe_load(f)

for key, info in models.items():
    active_marker = '*' if key == active.get('active_profile') else ' '
    name = info.get('model_name', 'unknown')
    daily = 'YES' if info.get('daily_safe') else 'NO'
    lab = 'YES' if info.get('lab_only') else 'NO'
    status = 'INSTALLED' if name in installed or any(name.startswith(i) for i in installed) else 'MISSING'
    
    printf_str = f'{active_marker}{key:<24} {name:<15} {daily:<10} {lab:<10} {status:<10}'
    print(printf_str)
" "$INSTALLED"

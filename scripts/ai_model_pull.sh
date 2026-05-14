#!/bin/bash

PROFILE_KEY=$1
if [ -z "$PROFILE_KEY" ]; then
    echo "Usage: ai_model_pull <profile_key>"
    exit 1
fi

REGISTRY_DIR="/mnt/d/_ai_brain/registry"
MODELS_YAML="$REGISTRY_DIR/models.yaml"
PYTHON="/mnt/d/_ai_brain/runtimes/workstation_venv/bin/python3"

# Check free space on D:
FREE_GB=$(df -BG /mnt/d | tail -n 1 | awk '{print $4}' | sed 's/G//')

$PYTHON -c "
import yaml
import sys
import subprocess

profile_key = sys.argv[1]
free_gb = int(sys.argv[2])

with open('$MODELS_YAML', 'r') as f:
    models = yaml.safe_load(f)

if profile_key not in models:
    print(f'Error: Profile \"{profile_key}\" not found.')
    sys.exit(1)

model_name = models[profile_key].get('model_name')
print(f'Pulling model for profile {profile_key}: {model_name}')

# Estimate size (very rough)
size_est = 30 if '32b' in model_name else 5
if free_gb - size_est < 80:
    print(f'Warning: Low disk space! Estimated {size_est}GB needed, only {free_gb}GB available. Target safety is 80GB free.')
    if free_gb - size_est < 10:
         print('Critical: Insufficient space. Aborting.')
         sys.exit(1)

# Use curl to pull via API
ollama_host = subprocess.check_output(['bash', '-c', 'echo ${OLLAMA_HOST:-http://localhost:11434}']).decode().strip()
print(f'Using Ollama Host: {ollama_host}')

subprocess.run(['curl', '-X', 'POST', f'{ollama_host}/api/pull', '-d', f'{{\"name\": \"{model_name}\"}}'])
" "$PROFILE_KEY" "$FREE_GB"

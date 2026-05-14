#!/bin/bash

QUESTION=""
PROFILE_OVERRIDE=""
MODEL_OVERRIDE=""
KV_OVERRIDE=""
CONTEXT_OVERRIDE=""

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --profile) PROFILE_OVERRIDE="$2"; shift ;;
        --model) MODEL_OVERRIDE="$2"; shift ;;
        --kv) KV_OVERRIDE="$2"; shift ;;
        --context) CONTEXT_OVERRIDE="$2"; shift ;;
        *) 
            if [ -z "$QUESTION" ]; then QUESTION="$1"; fi 
            ;;
    esac
    shift
done

if [ -z "$QUESTION" ]; then
    echo "Usage: ai_global_ask \"<question>\" [--profile <p>] [--model <m>] [--kv <k>] [--context <c>]"
    exit 1
fi

MODELS_YAML="/mnt/d/_ai_brain/registry/models.yaml"
KV_YAML="/mnt/d/_ai_brain/registry/kv_profiles.yaml"
ACTIVE_MODEL_YAML="/mnt/d/_ai_brain/registry/active_model.yaml"
ACTIVE_KV_YAML="/mnt/d/_ai_brain/registry/active_kv_profile.yaml"
RUNS_DIR="/mnt/d/_ai_brain/runs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RUN_DIR="$RUNS_DIR/${TIMESTAMP}_global_ask"
PYTHON="/mnt/d/_ai_brain/runtimes/workstation_venv/bin/python3"

mkdir -p "$RUN_DIR"

# Determine active model and KV
$PYTHON -c "
import yaml
import sys

def load_yaml(path):
    with open(path, 'r') as f: return yaml.safe_load(f)

am = load_yaml('$ACTIVE_MODEL_YAML')
ak = load_yaml('$ACTIVE_KV_YAML')
models = load_yaml('$MODELS_YAML')
kvs = load_yaml('$KV_YAML')

profile_key = '$PROFILE_OVERRIDE' or am['active_profile']
model_name = '$MODEL_OVERRIDE' or (models[profile_key]['model_name'] if '$PROFILE_OVERRIDE' else am['active_model'])
kv_profile = '$KV_OVERRIDE' or ak['active_profile']
kv_type = kvs[kv_profile]['kv_cache_type'] if '$KV_OVERRIDE' else ak['kv_cache_type']
context = int('$CONTEXT_OVERRIDE' or ak['context'])
mode = am['mode']
arch = models.get(profile_key, {}).get('architecture', 'unknown')

with open('$RUN_DIR/run_summary.yaml', 'w') as f:
    yaml.dump({
        'profile': profile_key,
        'model_name': model_name,
        'architecture': arch,
        'kv_profile': kv_profile,
        'kv_cache_type': kv_type,
        'context_length': context,
        'mode': mode,
        'timestamp': '$TIMESTAMP'
    }, f)

print(f'{model_name}|{context}|{profile_key}|{kv_profile}')
" > "$RUN_DIR/active_config.txt"

IFS='|' read -r MODEL CTX_SIZE PROF KV_PROF < "$RUN_DIR/active_config.txt"

# Global Graph Context
GRAPH_PATH="$HOME/.graphify/global-graph.json"

if [ -f "$GRAPH_PATH" ]; then
    VENV_PATH="/mnt/d/_ai_brain/runtimes/graphify_venv/bin/activate"
    source "$VENV_PATH"
    graphify query "$QUESTION" --graph "$GRAPH_PATH" > "$RUN_DIR/graph_context.md"
    deactivate
else
    echo "Warning: Global graph not found at $GRAPH_PATH."
    echo "No global graph context available." > "$RUN_DIR/graph_context.md"
fi

# Build Prompts
SYSTEM_PROMPT_PATH="/mnt/d/_ai_brain/prompts/global_system.md"
USER_PROMPT_PATH="$RUN_DIR/user_prompt.md"
echo -e "Global Question: $QUESTION\n\nGlobal Graph Context:\n$(cat "$RUN_DIR/graph_context.md")" > "$USER_PROMPT_PATH"

# Call Ollama
OLLAMA_HOST=${OLLAMA_HOST:-"http://localhost:11434"}

echo "Asking $MODEL globally (Profile: $PROF, KV: $KV_PROF, CTX: $CTX_SIZE)..."

$PYTHON /mnt/d/_ai_brain/scripts/ollama_call.py "$OLLAMA_HOST" "$MODEL" "$SYSTEM_PROMPT_PATH" "$USER_PROMPT_PATH" > "$RUN_DIR/answer.md"

echo "-----------------------------------"
cat "$RUN_DIR/answer.md"
echo "-----------------------------------"
echo "Run artifacts saved to $RUN_DIR"

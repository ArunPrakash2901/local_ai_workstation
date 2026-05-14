#!/bin/bash

# Default model
DEFAULT_MODEL="hermes3:8b"
PROFILE_KEY=""
ALLOW_LAB=false

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --allow-lab) ALLOW_LAB=true ;;
        *) PROFILE_KEY="$1" ;;
    esac
    shift
done

MODELS_YAML="/mnt/d/_ai_brain/registry/models.yaml"
ACTIVE_MODEL_YAML="/mnt/d/_ai_brain/registry/active_model.yaml"
PYTHON="/mnt/d/_ai_brain/runtimes/workstation_venv/bin/python3"

# Resolve Model Name
if [ -z "$PROFILE_KEY" ]; then
    MODEL_NAME=$($PYTHON -c "import yaml; print(yaml.safe_load(open('$ACTIVE_MODEL_YAML')).get('active_model', '$DEFAULT_MODEL'))")
    PROFILE_KEY=$($PYTHON -c "import yaml; print(yaml.safe_load(open('$ACTIVE_MODEL_YAML')).get('active_profile', 'unknown'))")
else
    MODEL_NAME=$($PYTHON -c "import yaml; models=yaml.safe_load(open('$MODELS_YAML')); print(models['$PROFILE_KEY']['model_name'] if '$PROFILE_KEY' in models else '$PROFILE_KEY')")
fi

# Safety Check
IS_LAB=$($PYTHON -c "import yaml; models=yaml.safe_load(open('$MODELS_YAML')); print('true' if '$PROFILE_KEY' in models and models['$PROFILE_KEY'].get('lab_only') else ('true' if '32b' in '$MODEL_NAME'.lower() else 'false'))")

if [ "$IS_LAB" == "true" ] && [ "$ALLOW_LAB" == false ]; then
    echo "ERROR: Refusing to warm lab/big model '$MODEL_NAME' without --allow-lab."
    exit 1
fi

echo "Warming model: $MODEL_NAME (Profile: $PROFILE_KEY)..."

OLLAMA_HOST=${OLLAMA_HOST:-"http://localhost:11434"}

# Use a non-blocking fast call
RESPONSE=$(curl -s -m 120 -X POST "$OLLAMA_HOST/api/generate" -d "{
  \"model\": \"$MODEL_NAME\",
  \"prompt\": \"Reply with only READY\",
  \"stream\": false,
  \"options\": {
    \"num_predict\": 5
  },
  \"keep_alive\": \"30m\"
}")

if [ $? -eq 0 ]; then
    echo "Warm-up request sent to $MODEL_NAME."
    # Check if we got a valid response
    TEXT=$(echo "$RESPONSE" | $PYTHON -c "import sys, json; print(json.load(sys.stdin).get('response', 'Error: No response'))")
    echo "Response: $TEXT"
else
    echo "ERROR: Warm-up timed out or failed."
fi

echo "-----------------------------------"
if command -v ollama &> /dev/null; then
    ollama ps
elif command -v ollama.exe &> /dev/null; then
    ollama.exe ps
fi
echo "-----------------------------------"

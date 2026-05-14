#!/bin/bash

PROFILE_KEY=${1:-"hermes_default"}
REGISTRY_DIR="/mnt/d/_ai_brain/registry"
MODELS_YAML="$REGISTRY_DIR/models.yaml"
ACTIVE_KV="$REGISTRY_DIR/active_kv_profile.yaml"
RUNS_DIR="/mnt/d/_ai_brain/runs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BENCH_DIR="$RUNS_DIR/${TIMESTAMP}_bench_${PROFILE_KEY}"
PYTHON="/mnt/d/_ai_brain/runtimes/workstation_venv/bin/python3"

mkdir -p "$BENCH_DIR"

MODEL_NAME=$($PYTHON -c "import yaml; print(yaml.safe_load(open('$MODELS_YAML'))['$PROFILE_KEY']['model_name'])")
KV_TYPE=$($PYTHON -c "import yaml; print(yaml.safe_load(open('$ACTIVE_KV'))['kv_cache_type'])")
CTX=$($PYTHON -c "import yaml; print(yaml.safe_load(open('$ACTIVE_KV'))['context'])")

echo "Benchmarking Profile: $PROFILE_KEY ($MODEL_NAME)"
echo "KV Type: $KV_TYPE, Context: $CTX"

PROMPTS=("hi" "Write a fast Fibonacci in Python" "Explain the concept of MoE (Mixture of Experts)")

for i in "${!PROMPTS[@]}"; do
    PROMPT="${PROMPTS[$i]}"
    echo "Test $((i+1)): $PROMPT"
    
    START=$(date +%s%N)
    RESPONSE=$(curl -s -X POST http://localhost:11434/api/generate -d "{
      \"model\": \"$MODEL_NAME\",
      \"prompt\": \"$PROMPT\",
      \"stream\": false,
      \"options\": {
        \"num_ctx\": $CTX
      }
    }")
    END=$(date +%s%N)
    
    DURATION_NS=$((END-START))
    DURATION_SEC=$(echo "scale=3; $DURATION_NS / 1000000000" | bc)
    
    TEXT=$(echo "$RESPONSE" | $PYTHON -c "import sys, json; print(json.load(sys.stdin).get('response', ''))")
    TOKENS=$(echo "$RESPONSE" | $PYTHON -c "import sys, json; print(json.load(sys.stdin).get('eval_count', 0))")
    TPS=$(echo "scale=2; $TOKENS / $DURATION_SEC" | bc)
    
    echo "Duration: ${DURATION_SEC}s, Tokens: $TOKENS, TPS: $TPS"
    echo -e "Prompt: $PROMPT\nResponse: $TEXT\nTPS: $TPS\n" >> "$BENCH_DIR/results.md"
done

echo "Benchmark complete. Results in $BENCH_DIR/results.md"

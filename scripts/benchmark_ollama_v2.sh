#!/bin/bash
# Fixed benchmark with proper long prompts (no raw chat tokens)
set -e

OLLAMA_URL="${OLLAMA_HOST:-http://localhost:11434}"
MODEL="${1:-hermes3:8b}"
NUM_CONTEXT="${2:-8192}"
REPORT_DIR="/mnt/d/_ai_brain/benchmarks"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="$REPORT_DIR/benchmark_${MODEL//[:\/]/_}_ctx${NUM_CONTEXT}_${TIMESTAMP}.md"

mkdir -p "$REPORT_DIR"

echo "# Ollama Benchmark Report" > "$REPORT_FILE"
echo "**Model**: $MODEL | **Context**: $NUM_CONTEXT | **Time**: $(date)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

run_bench() {
    local label="$1"
    local prompt="$2"
    local num_ctx="${3:-$NUM_CONTEXT}"
    
    echo "Running: $label..."
    
    local gpu_before=$(nvidia-smi.exe --query-gpu=memory.used,temperature.gpu --format=csv,noheader,nounits 2>/dev/null || echo "?,?")
    
    local payload=$(/mnt/d/_ai_brain/runtimes/workstation_venv/bin/python3 -c "
import json
print(json.dumps({
    'model': '$MODEL',
    'prompt': '''$prompt''',
    'stream': False,
    'options': {'num_ctx': $num_ctx, 'num_predict': 200}
}))
" 2>/dev/null)
    
    local start_time=$(date +%s%N)
    local result=$(curl -s "$OLLAMA_URL/api/generate" -d "$payload" 2>&1)
    local end_time=$(date +%s%N)
    
    local wall_ms=$(( (end_time - start_time) / 1000000 ))
    
    local gpu_after=$(nvidia-smi.exe --query-gpu=memory.used,temperature.gpu --format=csv,noheader,nounits 2>/dev/null || echo "?,?")
    
    local eval_count=$(echo "$result" | /mnt/d/_ai_brain/runtimes/workstation_venv/bin/python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('eval_count',0))" 2>/dev/null || echo "0")
    local eval_dur=$(echo "$result" | /mnt/d/_ai_brain/runtimes/workstation_venv/bin/python3 -c "import sys,json; d=json.load(sys.stdin); print(round(d.get('eval_duration',0)/1e9,3))" 2>/dev/null || echo "0")
    local prompt_eval_dur=$(echo "$result" | /mnt/d/_ai_brain/runtimes/workstation_venv/bin/python3 -c "import sys,json; d=json.load(sys.stdin); print(round(d.get('prompt_eval_duration',0)/1e9,3))" 2>/dev/null || echo "0")
    local prompt_eval_count=$(echo "$result" | /mnt/d/_ai_brain/runtimes/workstation_venv/bin/python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('prompt_eval_count',0))" 2>/dev/null || echo "0")
    local tps="0"
    if [ "$eval_dur" != "0" ] && [ "$eval_count" != "0" ]; then
        tps=$(/mnt/d/_ai_brain/runtimes/workstation_venv/bin/python3 -c "print(round($eval_count / $eval_dur, 1))" 2>/dev/null || echo "?")
    fi
    
    echo "  Wall: ${wall_ms}ms | Prompt: ${prompt_eval_dur}s (${prompt_eval_count}t) | Gen: ${eval_dur}s (${eval_count}t) | ${tps} t/s"
    echo "  GPU: $gpu_before -> $gpu_after"
    
    echo "### $label" >> "$REPORT_FILE"
    echo "| Metric | Value |" >> "$REPORT_FILE"
    echo "|--------|-------|" >> "$REPORT_FILE"
    echo "| Wall time | ${wall_ms}ms |" >> "$REPORT_FILE"
    echo "| Prompt eval | ${prompt_eval_dur}s (${prompt_eval_count} tokens) |" >> "$REPORT_FILE"
    echo "| Generation | ${eval_dur}s (${eval_count} tokens) |" >> "$REPORT_FILE"
    echo "| Tokens/sec | ${tps} |" >> "$REPORT_FILE"
    echo "| GPU VRAM (before/after) | ${gpu_before} / ${gpu_after} MiB |" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    
    sleep 2
}

echo "=========================================="
echo "Ollama Benchmark - Model: $MODEL | Context: $NUM_CONTEXT"
echo "=========================================="

# Test 1: Short prompt
run_bench "1. Short Prompt" "What is 2+2? Answer in one word."

# Test 2: Medium prompt  
run_bench "2. Medium Prompt" "Explain the key differences between REST and GraphQL APIs. Cover query flexibility, over-fetching, versioning, caching, and type system."

# Test 3: Graphify-style analysis
run_bench "3. Graphify-style Analysis" "Analyze this codebase structure: app/page.tsx imports NavBar, Hero, Features from components/. lib/utils.ts exports cn, formatDate, parseMarkdown, calculateScore. lib/hooks/useScroll.ts is a React hook. lib/constants.ts exports NAV_ITEMS, ROUTES, API_ENDPOINTS. Identify the entry point, utility hub, dependency depth, circular dependencies, and refactoring risks."

# Test 4: Repeated prefix (first call)
run_bench "4a. Repeated Prefix (Q1)" "You are working on a Python data pipeline using pandas, DuckDB, and Apache Arrow. The pipeline has ingestion, transformation, and output stages. What validation checks should the ingestion stage have?"

# Test 5: Repeated prefix (second call, same prefix)
run_bench "4b. Repeated Prefix (Q2)" "You are working on a Python data pipeline using pandas, DuckDB, and Apache Arrow. The pipeline has ingestion, transformation, and output stages. How should schema evolution be handled in the transformation stage?"

# Test 6: Agent-style coding prompt
run_bench "5. Agent-style Coding" "You are a coding assistant. A user asks: Add input validation to an Express.js POST endpoint. The endpoint accepts name (string, required, max 100 chars), email (string, required, valid format), and age (number, optional, 0-150). Write the validation middleware with proper error messages and 400 responses."

echo ""
echo "Report: $REPORT_FILE"
echo "GPU final: $(nvidia-smi.exe --query-gpu=memory.used,temperature.gpu --format=csv,noheader 2>/dev/null)"

echo "---" >> "$REPORT_FILE"
echo "GPU final: $(nvidia-smi.exe --query-gpu=memory.used,temperature.gpu,power.draw --format=csv,noheader 2>/dev/null)" >> "$REPORT_FILE"

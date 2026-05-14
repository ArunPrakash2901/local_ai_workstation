#!/bin/bash
# =============================================================
# Ollama Benchmark Suite for AI Workstation
# Tests: short, medium, long, repeated-prefix, agent-style prompts
# Measures: latency, tokens/sec, VRAM, stability
# =============================================================
set -e

OLLAMA_URL="${OLLAMA_HOST:-http://localhost:11434}"
MODEL="${1:-hermes3:8b}"
NUM_CONTEXT="${2:-4096}"
REPORT_DIR="/mnt/d/_ai_brain/benchmarks"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="$REPORT_DIR/benchmark_${MODEL//[:\/]/_}_ctx${NUM_CONTEXT}_${TIMESTAMP}.md"

mkdir -p "$REPORT_DIR"

echo "# Ollama Benchmark Report" > "$REPORT_FILE"
echo "**Model**: $MODEL | **Context**: $NUM_CONTEXT | **Time**: $(date)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Helper function to run a benchmark
run_bench() {
    local label="$1"
    local prompt="$2"
    local num_ctx="${3:-$NUM_CONTEXT}"
    
    echo "Running: $label..."
    
    # Get GPU state before
    local gpu_before=$(nvidia-smi.exe --query-gpu=memory.used,temperature.gpu --format=csv,noheader,nounits 2>/dev/null || echo "?,?")
    
    local start_time=$(date +%s%N)
    local result=$(curl -s "$OLLAMA_URL/api/generate" -d "{
        \"model\": \"$MODEL\",
        \"prompt\": \"$prompt\",
        \"stream\": false,
        \"options\": { \"num_ctx\": $num_ctx, \"num_predict\": 200 }
    }" 2>&1)
    local end_time=$(date +%s%N)
    
    local wall_ms=$(( (end_time - start_time) / 1000000 ))
    
    # Get GPU state after
    local gpu_after=$(nvidia-smi.exe --query-gpu=memory.used,temperature.gpu --format=csv,noheader,nounits 2>/dev/null || echo "?,?")
    
    # Parse response
    local response=$(echo "$result" | /mnt/d/_ai_brain/runtimes/workstation_venv/bin/python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('response','ERROR')[:100])" 2>/dev/null || echo "PARSE_ERROR")
    local eval_count=$(echo "$result" | /mnt/d/_ai_brain/runtimes/workstation_venv/bin/python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('eval_count',0))" 2>/dev/null || echo "0")
    local eval_dur=$(echo "$result" | /mnt/d/_ai_brain/runtimes/workstation_venv/bin/python3 -c "import sys,json; d=json.load(sys.stdin); print(round(d.get('eval_duration',0)/1e9,3))" 2>/dev/null || echo "0")
    local prompt_eval_dur=$(echo "$result" | /mnt/d/_ai_brain/runtimes/workstation_venv/bin/python3 -c "import sys,json; d=json.load(sys.stdin); print(round(d.get('prompt_eval_duration',0)/1e9,3))" 2>/dev/null || echo "0")
    local prompt_eval_count=$(echo "$result" | /mnt/d/_ai_brain/runtimes/workstation_venv/bin/python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('prompt_eval_count',0))" 2>/dev/null || echo "0")
    local tps="0"
    if [ "$eval_dur" != "0" ] && [ "$eval_count" != "0" ]; then
        tps=$(/mnt/d/_ai_brain/runtimes/workstation_venv/bin/python3 -c "print(round($eval_count / $eval_dur, 1))" 2>/dev/null || echo "?")
    fi
    
    echo "  Wall: ${wall_ms}ms | Prompt eval: ${prompt_eval_dur}s (${prompt_eval_count} tokens) | Gen: ${eval_dur}s (${eval_count} tokens) | ${tps} tok/s"
    echo "  GPU before: $gpu_before | GPU after: $gpu_after"
    
    # Write to report
    echo "### $label" >> "$REPORT_FILE"
    echo "| Metric | Value |" >> "$REPORT_FILE"
    echo "|--------|-------|" >> "$REPORT_FILE"
    echo "| Wall time | ${wall_ms}ms |" >> "$REPORT_FILE"
    echo "| Prompt eval | ${prompt_eval_dur}s (${prompt_eval_count} tokens) |" >> "$REPORT_FILE"
    echo "| Generation | ${eval_dur}s (${eval_count} tokens) |" >> "$REPORT_FILE"
    echo "| Tokens/sec | ${tps} |" >> "$REPORT_FILE"
    echo "| GPU VRAM (before) | ${gpu_before} MiB |" >> "$REPORT_FILE"
    echo "| GPU VRAM (after) | ${gpu_after} MiB |" >> "$REPORT_FILE"
    echo "| Response preview | ${response:0:80}... |" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    
    # Small delay between benchmarks
    sleep 2
}

echo "=========================================="
echo "Ollama Benchmark Suite"
echo "Model: $MODEL | Context: $NUM_CONTEXT"
echo "=========================================="
echo ""

# --- Test 1: Short prompt (cold if first call) ---
run_bench "1. Short Prompt" "What is 2+2? Answer in one word."

# --- Test 2: Short prompt (warm/repeat) ---
run_bench "2. Short Prompt (Repeat)" "What is 2+2? Answer in one word."

# --- Test 3: Medium prompt ---
run_bench "3. Medium Prompt" "You are a senior software engineer. Explain the key differences between REST and GraphQL APIs. Cover at least 5 specific technical differences including query flexibility, over-fetching, versioning, caching, and type system. Keep your answer concise but technical."

# --- Test 4: Graphify-style long prompt ---
LONG_PROMPT="You are analyzing a codebase knowledge graph. The graph contains the following nodes and relationships:

Node: app/page.tsx (React component, 45 lines) -> imports from: components/NavBar, components/Hero, components/Features, lib/utils
Node: components/NavBar.tsx (React component, 120 lines) -> imports from: lib/hooks/useScroll, lib/constants
Node: components/Hero.tsx (React component, 80 lines) -> imports from: framer-motion, lib/animations
Node: lib/utils.ts (utility module, 200 lines) -> exports: cn, formatDate, parseMarkdown, calculateScore
Node: lib/hooks/useScroll.ts (custom hook, 30 lines) -> imports from: react
Node: lib/constants.ts (constants, 50 lines) -> exports: NAV_ITEMS, ROUTES, API_ENDPOINTS
Node: lib/animations.ts (animation config, 40 lines) -> exports: fadeIn, slideUp, staggerContainer

Based on this graph structure, answer these questions:
1. What is the entry point and what does it depend on?
2. Which module has the most exports and is likely a utility hub?
3. What is the dependency depth from page.tsx to useScroll?
4. Are there any circular dependencies?
5. What would break if lib/constants.ts was refactored?"

run_bench "4. Graphify-style Long Prompt" "$LONG_PROMPT"

# --- Test 5: Repeated prefix prompt (same prefix, different question) ---
REPEATED_PREFIX="You are a helpful AI assistant working on a data engineering project. The project uses Python with pandas, DuckDB, and Apache Arrow for ETL pipelines. The team follows a modular architecture with separate ingestion, transformation, and output stages."

run_bench "5a. Repeated Prefix (Question 1)" "${REPEATED_PREFIX} What validation checks should we add to the ingestion stage?"
run_bench "5b. Repeated Prefix (Question 2)" "${REPEATED_PREFIX} How should we handle schema evolution in the transformation stage?"

# --- Test 6: Agent-style prompt ---
AGENT_PROMPT="<|im_start|>system
You are a coding agent. You have access to tools: read_file, write_file, run_command, search_codebase.
When asked to make changes, first analyze the request, then propose a plan, then execute it step by step.
Always explain your reasoning before acting.
<|im_end|>
<|im_start|>user
I need you to add input validation to the API endpoint in routes/api.ts. The endpoint accepts a POST request with fields: name (string, required, max 100 chars), email (string, required, valid email format), and age (number, optional, 0-150). Add proper error messages and return 400 for validation failures.
<|im_end|>
<|im_start|>assistant
"

run_bench "6. Agent-style Prompt" "$AGENT_PROMPT"

# --- Summary ---
echo "" >> "$REPORT_FILE"
echo "---" >> "$REPORT_FILE"
echo "## System Info at Benchmark Time" >> "$REPORT_FILE"
echo "- GPU: $(nvidia-smi.exe --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo 'N/A')" >> "$REPORT_FILE"
echo "- GPU Temp: $(nvidia-smi.exe --query-gpu=temperature.gpu --format=csv,noheader 2>/dev/null || echo 'N/A')°C" >> "$REPORT_FILE"
echo "- Context: $NUM_CONTEXT" >> "$REPORT_FILE"
echo "- Model: $MODEL" >> "$REPORT_FILE"

echo ""
echo "=========================================="
echo "Benchmark complete!"
echo "Report saved to: $REPORT_FILE"
echo "=========================================="

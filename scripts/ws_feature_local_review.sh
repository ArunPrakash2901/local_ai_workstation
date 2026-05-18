#!/bin/bash

set -euo pipefail

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
FEATURES_DIR="$WS_HOME/features"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"
OLLAMA_CALL_PY="$WS_HOME/scripts/ollama_call.py"

FEATURE_INPUT=""
MODEL="hermes3:8b"
PURPOSE="general"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --model)
            MODEL="$2"
            shift 2
            ;;
        --purpose)
            PURPOSE="$2"
            shift 2
            ;;
        *)
            if [ -z "$FEATURE_INPUT" ] || [[ "$1" != --* ]]; then
                FEATURE_INPUT="$1"
            fi
            shift
            ;;
    esac
done

if [ -z "$FEATURE_INPUT" ]; then
    echo "Usage: ws feature-local-review <feature_id_or_path> [--model <model>] [--purpose <purpose>]"
    exit 1
fi

to_wsl_path() {
    case "$1" in
        /*) printf '%s' "$1" ;;
        *) wslpath -u "$1" 2>/dev/null || printf '%s' "$1" ;;
    esac
}

to_windows_path() {
    wslpath -w "$1" 2>/dev/null || printf '%s' "$1"
}

resolve_feature_dir() {
    local candidate
    candidate=$(to_wsl_path "$FEATURE_INPUT")
    if [ -d "$candidate" ]; then
        printf '%s\n' "$candidate"
        return
    fi
    
    if [ ! -d "$FEATURES_DIR" ]; then
        echo "Feature stronghold root not found: $FEATURES_DIR" >&2
        return 1
    fi

    mapfile -t matches < <(
        find "$FEATURES_DIR" -mindepth 2 -maxdepth 2 -type d -name "$FEATURE_INPUT" 2>/dev/null | sort
    )

    case "${#matches[@]}" in
        0)
            echo "Feature stronghold not found: $FEATURE_INPUT" >&2
            return 1
            ;;
        1)
            printf '%s\n' "${matches[0]}"
            ;;
        *)
            echo "Feature id is ambiguous: $FEATURE_INPUT" >&2
            printf 'Matches:\n' >&2
            printf '  %s\n' "${matches[@]}" >&2
            return 1
            ;;
    esac
}

FEATURE_DIR=$(resolve_feature_dir) || exit 1

# Verify required files
REQUIRED_FILES=(
    "state.json"
    "feature_contract.md"
    "current_plan.md"
)
for f in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$FEATURE_DIR/$f" ]; then
        echo "Error: Missing required file $f in $FEATURE_DIR"
        exit 1
    fi
done

NOW_TS=$(date +"%Y%m%d_%H%M%S")

# Check Ollama
if ! curl -s -f "http://localhost:11434/api/tags" > /dev/null; then
    echo "Error: Ollama is not reachable at localhost:11434."
    exit 1
fi

# Check model
if ! curl -s "http://localhost:11434/api/tags" | grep -q "\"$MODEL\""; then
    echo "Error: Model '$MODEL' is not available in Ollama."
    echo "Available models:"
    curl -s "http://localhost:11434/api/tags" | grep -o "\"name\":\"[^\"]*\"" | cut -d'"' -f4
    exit 1
fi

# Call Python to handle prompt building and model call
RESULT_JSON=$( "$PYTHON" - "$FEATURE_DIR" "$WS_HOME" "$MODEL" "$PURPOSE" "$NOW_TS" "$OLLAMA_CALL_PY" << 'PY'
import sys
import json
import subprocess
from pathlib import Path

feature_dir = Path(sys.argv[1])
ws_home = Path(sys.argv[2])
model = sys.argv[3]
purpose = sys.argv[4]
now_ts = sys.argv[5]
ollama_call_script = sys.argv[6]

def get_content(p):
    if p.is_file():
        return p.read_text(encoding="utf-8")
    return ""

state_path = feature_dir / "state.json"
state = {}
if state_path.is_file():
    state = json.loads(state_path.read_text(encoding="utf-8"))

# Artifacts
artifacts = {
    "contract": get_content(feature_dir / "feature_contract.md"),
    "plan": get_content(feature_dir / "current_plan.md"),
    "report": get_content(feature_dir / "final_report.md")
}

# Validation evidence
val_mds = sorted(feature_dir.glob("evidence/validation_*.md"), reverse=True)
artifacts["validation"] = get_content(val_mds[0]) if val_mds else ""

# Latest handoff review
latest_handoff_review = ""
handoffs_dir = ws_home / "handoffs"
if handoffs_dir.is_dir():
    matched = []
    for hd in handoffs_dir.iterdir():
        if hd.is_dir():
            meta_path = hd / "metadata.json"
            if meta_path.is_file():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    if meta.get("feature_id") == feature_dir.name:
                        matched.append(hd)
                except: pass
    if matched:
        matched.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        rev_path = matched[0] / "review.md"
        if rev_path.is_file():
            latest_handoff_review = rev_path.read_text(encoding="utf-8")

# Latest feature-run dry-run
latest_dry_run = ""
dry_run_mds = sorted(feature_dir.glob("runs/feature_run_dry_run_*.md"), reverse=True)
if dry_run_mds:
    latest_dry_run = dry_run_mds[0].read_text(encoding="utf-8")

# Latest worktree agent run
latest_agent_run = ""
agent_runs = sorted(list(ws_home.glob("auto_runs/*_worktree_agent_run")), key=lambda x: x.stat().st_mtime, reverse=True)
for ar in agent_runs:
    meta_path = ar / "metadata.json"
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta.get("feature_id") == feature_dir.name or feature_dir.name in ar.name:
                rep_path = ar / "final_report.md"
                if rep_path.is_file():
                    latest_agent_run = rep_path.read_text(encoding="utf-8")
                    break
        except: pass

# Prompt building
system_prompt = """You are a senior technical architect and local reasoning gate for an AI Workstation.
Your goal is to review a Feature Stronghold and provide a conservative assessment of its readiness for implementation/execution.

Classify your response with EXACTLY ONE of the following tags on the first line:
LOCAL_REVIEW_ACCEPTED - Plan is robust, aligns with contract, and deterministic checks passed.
LOCAL_REVIEW_NEEDS_FIX - Specific gaps or safety risks detected.
LOCAL_REVIEW_RECOMMENDS_CLOUD - Task complexity or context requires higher-reasoning (GPT-4/Claude 3.5).
LOCAL_REVIEW_BLOCKED - Major missing information or contract violations.

Be critical and conservative. If in doubt, choose NEEDS_FIX or RECOMMENDS_CLOUD."""

user_prompt = f"""Review Feature: {feature_dir.name}
Purpose: {purpose}

### Feature Contract
{artifacts['contract']}

### Current Implementation Plan
{artifacts['plan']}

### Latest Validation Evidence
{artifacts['validation']}

### Final Feature Report (if available)
{artifacts['report']}

### Latest Handoff Review (if available)
{latest_handoff_review}

### Latest Feature-Run Dry-Run (if available)
{latest_dry_run}

### Latest Worktree Agent Run (if available)
{latest_agent_run}

Analyze the above and provide your classification and reasoning."""

# Write temporary prompts for ollama_call.py
evid_dir = feature_dir / "evidence"
evid_dir.mkdir(parents=True, exist_ok=True)
sys_prompt_path = evid_dir / f"local_model_{now_ts}_sys.txt"
sys_prompt_path.write_text(system_prompt, encoding="utf-8")

user_prompt_path = evid_dir / f"local_model_{now_ts}_user.txt"
user_prompt_path.write_text(user_prompt, encoding="utf-8")

# Call Ollama
try:
    res = subprocess.check_output([
        sys.executable, ollama_call_script,
        "http://localhost:11434", model,
        str(sys_prompt_path), str(user_prompt_path)
    ], text=True).strip()
except subprocess.CalledProcessError as e:
    print(json.dumps({"error": f"Ollama call failed: {e.output}"}))
    sys.exit(1)

# Write response and evidence
resp_dir = feature_dir / "responses"
resp_dir.mkdir(parents=True, exist_ok=True)
resp_path = resp_dir / f"local_review_{now_ts}.md"
resp_path.write_text(res, encoding="utf-8")

evid_path = evid_dir / f"local_model_{now_ts}.md"
evid_path.write_text(f"# Local Model Review Evidence\n\n- Model: {model}\n- Purpose: {purpose}\n\n## System Prompt\n{system_prompt}\n\n## User Prompt\n{user_prompt}\n\n## Response\n{res}", encoding="utf-8")

# Classify
classification = "LOCAL_REVIEW_NEEDS_FIX"
lines = res.splitlines()
first_line = lines[0] if lines else ""
if "LOCAL_REVIEW_ACCEPTED" in first_line: classification = "LOCAL_REVIEW_ACCEPTED"
elif "LOCAL_REVIEW_RECOMMENDS_CLOUD" in first_line: classification = "LOCAL_REVIEW_RECOMMENDS_CLOUD"
elif "LOCAL_REVIEW_BLOCKED" in first_line: classification = "LOCAL_REVIEW_BLOCKED"

# Update state.json
state["last_local_review_at"] = now_ts
state["local_review_result"] = classification
state["local_review_model"] = model
state["provider_invocation"] = False
state["browser_automation"] = False
state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

# Append loop log
loop_log_path = feature_dir / "loop_log.md"
loop_entry = f"""
## {now_ts} - Local Model Review
- Actor: {model}
- Result: {classification}
- Response: {resp_path}
"""
if loop_log_path.is_file():
    with loop_log_path.open("a", encoding="utf-8") as f:
        f.write(loop_entry)

print(json.dumps({
    "classification": classification,
    "resp_path": str(resp_path),
    "evid_path": str(evid_path)
}))

# Cleanup temporary prompts
sys_prompt_path.unlink()
user_prompt_path.unlink()
PY
)

# Output results
echo "$RESULT_JSON" | $PYTHON -c "
import json
import sys
try:
    data = json.loads(sys.stdin.read())
    if 'error' in data:
        print(data['error'])
        sys.exit(1)
    print(f\"Classification: {data['classification']}\")
    print(f\"Response:      {data['resp_path']}\")
    print(f\"Evidence:      {data['evid_path']}\")
except Exception as e:
    print(f\"Error parsing result: {e}\")
    sys.exit(1)
"

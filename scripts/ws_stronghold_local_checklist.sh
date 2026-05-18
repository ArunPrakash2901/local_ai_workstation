#!/bin/bash

set -euo pipefail

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
STRONGHOLDS_DIR="$WS_HOME/strongholds"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"
OLLAMA_CALL_PY="$WS_HOME/scripts/ollama_call.py"

STRONGHOLD_INPUT=""
MODEL="hermes3:8b"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --model)
            MODEL="$2"
            shift 2
            ;;
        *)
            if [ -z "$STRONGHOLD_INPUT" ] || [[ "$1" != --* ]]; then
                STRONGHOLD_INPUT="$1"
            fi
            shift
            ;;
    esac
done

if [ -z "$STRONGHOLD_INPUT" ]; then
    echo "Usage: ws stronghold-local-checklist <stronghold_id_or_path> [--model <model>]"
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

resolve_stronghold_dir() {
    local candidate
    candidate=$(to_wsl_path "$STRONGHOLD_INPUT")
    if [ -d "$candidate" ] && [ -f "$candidate/state.json" ]; then
        printf '%s\n' "$candidate"
        return
    fi

    if [ ! -d "$STRONGHOLDS_DIR" ]; then
        echo "Stronghold root not found: $STRONGHOLDS_DIR" >&2
        return 1
    fi

    mapfile -t matches < <(
        find "$STRONGHOLDS_DIR" -mindepth 2 -maxdepth 2 -type d -name "$STRONGHOLD_INPUT" 2>/dev/null | sort
    )

    case "${#matches[@]}" in
        0)
            echo "Stronghold not found: $STRONGHOLD_INPUT" >&2
            return 1
            ;;
        1)
            printf '%s\n' "${matches[0]}"
            ;;
        *)
            echo "Stronghold id is ambiguous: $STRONGHOLD_INPUT" >&2
            printf 'Matches:\n' >&2
            printf '  %s\n' "${matches[@]}" >&2
            return 1
            ;;
    esac
}

STRONGHOLD_DIR=$(resolve_stronghold_dir) || exit 1

# 1. Verify state
STATE_JSON="$STRONGHOLD_DIR/state.json"
CURRENT_STATE=$( "$PYTHON" - "$STATE_JSON" <<'PY'
import json
import sys
from pathlib import Path
state = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(state.get("current_state", ""))
PY
)

if [ "$CURRENT_STATE" != "ARCHITECT_PLAN_IMPORTED" ]; then
    echo "Error: Stronghold must be in ARCHITECT_PLAN_IMPORTED state. Current state: $CURRENT_STATE"
    exit 1
fi

# 2. Verify artifacts
REQUIRED_FILES=(
    "architect_plan.md"
    "contract.md"
    "goals.md"
    "constraints.md"
    "success_criteria.md"
)
for f in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$STRONGHOLD_DIR/$f" ]; then
        echo "Error: Missing required file $f in $STRONGHOLD_DIR"
        exit 1
    fi
done

# 3. Check Ollama
if ! curl -s -f "http://localhost:11434/api/tags" > /dev/null; then
    echo "Error: Ollama is not reachable at localhost:11434."
    exit 1
fi

if ! curl -s "http://localhost:11434/api/tags" | grep -q "\"$MODEL\""; then
    echo "Error: Model '$MODEL' is not available in Ollama."
    exit 1
fi

NOW_TS=$(date +"%Y%m%d_%H%M%S")

# 4. Generate checklist using Python to build prompt and call model
RESULT_JSON=$( "$PYTHON" - "$STRONGHOLD_DIR" "$MODEL" "$NOW_TS" "$OLLAMA_CALL_PY" << 'PY'
import sys
import json
import subprocess
from pathlib import Path

stronghold_dir = Path(sys.argv[1])
model = sys.argv[2]
now_ts = sys.argv[3]
ollama_call_script = sys.argv[4]

def get_content(filename):
    p = stronghold_dir / filename
    if p.is_file():
        return p.read_text(encoding="utf-8").strip()
    return "[Artifact not found]"

state = json.loads((stronghold_dir / "state.json").read_text(encoding="utf-8"))
stype = state.get("type", "unknown")
title = state.get("title", "unknown")

system_prompt = """You are a senior technical intern and operator for an AI Workstation.
Your goal is to take a Master Plan from a Senior Architect and convert it into a granular, step-by-step operational checklist.

Focus on tactical execution, dependencies, and validation.
BE CONSERVATIVE. If a step is risky, flag it for human review.

Structure your response as a Markdown checklist.
"""

domain_focus = ""
if stype == "learning":
    domain_focus = "Emphasize specific study sessions, practice exercises, and assessment milestones."
elif stype == "product":
    domain_focus = "Emphasize feature breakdown, implementation tasks, and strategic review gates."
elif stype == "research":
    domain_focus = "Emphasize source collection, hypothesis evaluation steps, and evidence matrix updates."
elif stype == "trading-research":
    domain_focus = """**SAFETY MANDATE**: RESEARCH ONLY. No live trading. 
Emphasize backtest parameters, overfitting controls, and paper-trading validation.
DO NOT include any steps for live brokerage execution."""

user_prompt = f"""Review the following Stronghold context and the Senior Architect's Master Plan.
Generate a granular, step-by-step operational checklist.

{domain_focus}

### Stronghold: {title} ({stype})
#### Contract
{get_content('contract.md')}

#### Goals
{get_content('goals.md')}

#### Constraints
{get_content('constraints.md')}

#### Master Plan (Architect)
{get_content('architect_plan.md')}

### Your Task
Provide an Operational Checklist that includes:
1. Step-by-step tasks.
2. Dependencies between tasks.
3. Assignment Recommendation:
   - **Human**: Manual steps or critical reviews.
   - **Local Model**: Routine analysis or checklist generation.
   - **Codex/Gemini CLI**: Code mutation or data processing.
4. Validation Checkpoints for each major step.
5. Critical Questions or Blockers for the Human Operator.
"""

# Write temporary prompts
evid_dir = stronghold_dir / "evidence"
evid_dir.mkdir(parents=True, exist_ok=True)
sys_p_path = evid_dir / f"local_model_checklist_{now_ts}_sys.txt"
sys_p_path.write_text(system_prompt, encoding="utf-8")
usr_p_path = evid_dir / f"local_model_checklist_{now_ts}_user.txt"
usr_p_path.write_text(user_prompt, encoding="utf-8")

# Call Ollama
try:
    res = subprocess.check_output([
        sys.executable, ollama_call_script,
        "http://localhost:11434", model,
        str(sys_p_path), str(usr_p_path)
    ], text=True).strip()
except subprocess.CalledProcessError as e:
    print(json.dumps({"error": f"Ollama call failed: {e.output}"}))
    sys.exit(1)

# Write results
(stronghold_dir / "local_checklist.md").write_text(res, encoding="utf-8", newline="\n")

resp_dir = stronghold_dir / "responses"
resp_dir.mkdir(parents=True, exist_ok=True)
resp_path = resp_dir / f"local_checklist_{now_ts}.md"
resp_path.write_text(res, encoding="utf-8", newline="\n")

evid_path = evid_dir / f"local_model_checklist_{now_ts}.md"
evid_content = f"# Local Model Checklist Evidence\n\n- Model: {model}\n- Timestamp: {now_ts}\n\n## Response\n{res}"
evid_path.write_text(evid_content, encoding="utf-8", newline="\n")

# Update state.json
state["current_state"] = "LOCAL_CHECKLIST_READY"
state["last_local_checklist_at"] = now_ts
state["local_checklist_model"] = model
state["provider_invocation"] = False
state["browser_automation"] = False
(stronghold_dir / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8", newline="\n")

# Update loop log
loop_log_path = stronghold_dir / "loop_log.md"
loop_entry = f"""
## {now_ts} - Local Intern Checklist Generated
- Actor: {model}
- State: LOCAL_CHECKLIST_READY
- Output: local_checklist.md
"""
with loop_log_path.open("a", encoding="utf-8", newline="\n") as f:
    f.write(loop_entry)

print(json.dumps({
    "checklist_path": str(stronghold_dir / "local_checklist.md"),
    "report_path": str(resp_path)
}))

# Cleanup
sys_p_path.unlink()
usr_p_path.unlink()
PY
)

echo "Local intern checklist generated."
echo "$RESULT_JSON" | $PYTHON -c "
import json
import sys
try:
    data = json.loads(sys.stdin.read())
    if 'error' in data:
        print(data['error'])
        sys.exit(1)
    print(f\"Checklist: {data['checklist_path']}\")
    print(f\"Report:    {data['report_path']}\")
except Exception as e:
    print(f\"Error parsing result: {e}\")
    sys.exit(1)
"

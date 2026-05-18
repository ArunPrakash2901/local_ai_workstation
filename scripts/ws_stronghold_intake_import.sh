#!/bin/bash

set -euo pipefail

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
STRONGHOLDS_DIR="$WS_HOME/strongholds"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

STRONGHOLD_INPUT=${1:-}
ANSWERS_FILE=""

# Parse arguments
shift || true
while [[ $# -gt 0 ]]; do
    case "$1" in
        --from-file)
            ANSWERS_FILE="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

if [ -z "$STRONGHOLD_INPUT" ] || [ -z "$ANSWERS_FILE" ]; then
    echo "Usage: ws stronghold-intake-import <stronghold_id_or_path> --from-file <answers_file>"
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
ANSWERS_FILE_WSL=$(to_wsl_path "$ANSWERS_FILE")

if [ ! -f "$ANSWERS_FILE_WSL" ]; then
    echo "Error: Answers file not found: $ANSWERS_FILE"
    exit 1
fi

if [ ! -s "$ANSWERS_FILE_WSL" ]; then
    echo "Error: Answers file is empty: $ANSWERS_FILE"
    exit 1
fi

NOW_TS=$(date +"%Y%m%d_%H%M%S")

# Use Python to handle deterministic extraction and artifact updates
"$PYTHON" - "$STRONGHOLD_DIR" "$ANSWERS_FILE_WSL" "$NOW_TS" << 'PY'
import sys
import json
import re
import shutil
from pathlib import Path

stronghold_dir = Path(sys.argv[1])
answers_file = Path(sys.argv[2])
now_ts = sys.argv[3]

state_path = stronghold_dir / "state.json"
state = json.loads(state_path.read_text(encoding="utf-8"))
stype = state.get("type", "unknown")

answers_text = answers_file.read_text(encoding="utf-8")
(stronghold_dir / "intake_response.md").write_text(answers_text, encoding="utf-8", newline="\n")

# Simple section extraction logic
# We look for markdown headers and the text between them
def get_sections(text):
    sections = {}
    current_header = None
    current_content = []
    
    for line in text.splitlines():
        if line.startswith("#"):
            if current_header:
                sections[current_header] = "\n".join(current_content).strip()
            current_header = line.lstrip("#").strip()
            # Clean up number if present (e.g., "1. What is...")
            current_header = re.sub(r"^\d+\.\s*", "", current_header)
            current_content = []
        elif current_header:
            current_content.append(line)
            
    if current_header:
        sections[current_header] = "\n".join(current_content).strip()
        
    return sections

sections = get_sections(answers_text)

# Update core artifacts
def update_md(filename, title, content_map):
    p = stronghold_dir / filename
    text = f"# {title}\n\n"
    for k, v in content_map.items():
        text += f"## {k}\n{v}\n\n"
    p.write_text(text, encoding="utf-8", newline="\n")

# Helper to find answer by key fragment
def find_answer(fragments):
    for k, v in sections.items():
        if any(f.lower() in k.lower() for f in fragments):
            if v and v.lower() != "[answer here]":
                return v
    return ""

contract_data = {
    "Objective": find_answer(["objective", "problem", "solving", "research question", "target outcome", "hypothesis"]),
    "Acceptance Criteria": find_answer(["acceptance criteria", "success metrics", "evidence standard", "progress be assessed", "paper-trading validation"]),
    "Allowed Files": find_answer(["allowed files", "instruments", "sources", "data sources", "specific projects"]),
}
update_md("contract.md", f"Stronghold Contract: {state.get('title')}", contract_data)

goals_data = {
    "Primary Goal": find_answer(["target outcome", "desired outcome", "north star", "research question", "alpha signal", "target outcome"]),
}
update_md("goals.md", f"Goals: {state.get('title')}", goals_data)

constraints_data = {
    "Safety and Limits": find_answer(["constraints", "risk level", "risk limits", "deadline", "weekly time", "time available"]),
}
if stype == "trading-research":
    safety_confirm = find_answer(["acknowledge", "confirmation required", "disabled"])
    confirmed = False
    if safety_confirm and any(word in safety_confirm.lower() for word in ["yes", "confirm", "acknowledge", "i do", "i acknowledge"]):
        confirmed = True
    
    warn = "> **SAFETY WARNING**: This stronghold is for RESEARCH ONLY. Live trading, brokerage API execution, and capital deployment are STRICTORLY DISABLED.\n\n"
    constraints_data["Trading Safety"] = warn + (f"Confirmed: {safety_confirm}" if confirmed else "NOT CONFIRMED")
    state["safety_confirmed"] = confirmed
else:
    state["safety_confirmed"] = True

update_md("constraints.md", f"Constraints: {state.get('title')}", constraints_data)

success_data = {
    "Conditions": find_answer(["success criteria", "deliverable", "target outcome"]),
}
update_md("success_criteria.md", f"Success Criteria: {state.get('title')}", success_data)

# State update
all_filled = all(v for v in contract_data.values()) and state.get("safety_confirmed")
state["current_state"] = "CONTRACT_READY" if all_filled else "NEEDS_HUMAN_REVIEW"
state["last_intake_imported_at"] = now_ts
state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

# Loop log
loop_log_path = stronghold_dir / "loop_log.md"
loop_entry = f"\n## {now_ts} - Stronghold Intake Imported\n- Actor: local\n- State: {state['current_state']}\n- Source: {answers_file}\n"
with loop_log_path.open("a", encoding="utf-8", newline="\n") as f:
    f.write(loop_entry)

# Report
report_path = stronghold_dir / "reports" / f"intake_import_report_{now_ts}.md"
report_text = f"# Stronghold Intake Import Report\n\n- Timestamp: {now_ts}\n- Result State: {state['current_state']}\n- Source: {answers_file}\n"
report_path.write_text(report_text, encoding="utf-8", newline="\n")

print(f"Import complete. New state: {state['current_state']}")
print(f"Report: {report_path}")
PY

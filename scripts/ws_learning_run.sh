#!/bin/bash

set -euo pipefail

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
STRONGHOLDS_DIR="$WS_HOME/strongholds"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

STRONGHOLD_INPUT=""
SESSION=0
DRY_RUN=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --session)
            SESSION=1
            shift
            ;;
        --dry-run)
            DRY_RUN=1
            shift
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
    echo "Usage: ws learning-run <stronghold_id_or_path> --session --dry-run"
    exit 1
fi

if [ "$SESSION" -eq 0 ]; then
    echo "Error: --session is mandatory in this MVP."
    exit 1
fi

if [ "$DRY_RUN" -eq 0 ]; then
    echo "Error: --dry-run is mandatory in this MVP."
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

    # Search in learning subfolder specifically
    mapfile -t matches < <(
        find "$STRONGHOLDS_DIR/learning" -mindepth 1 -maxdepth 1 -type d -name "$STRONGHOLD_INPUT" 2>/dev/null | sort
    )

    case "${#matches[@]}" in
        0)
            echo "Learning stronghold not found: $STRONGHOLD_INPUT" >&2
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

STRONGHOLD_DIR=$(resolve_stronghold_dir) || {
    # If not found in learning/, check if it's a generic path but invalid type
    echo "Error: Target is not a learning stronghold or not found."
    exit 1
}

NOW_TS=$(date +"%Y%m%d_%H%M%S")

# Use Python for logic
RESULT_JSON=$( "$PYTHON" - "$STRONGHOLD_DIR" "$NOW_TS" << 'PY'
import sys
import json
import re
from pathlib import Path

stronghold_dir = Path(sys.argv[1])
now_ts = sys.argv[2]

state_path = stronghold_dir / "state.json"
if not state_path.is_file():
    print(json.dumps({"error": f"Missing state.json in {stronghold_dir}", "classification": "LEARNING_SESSION_INVALID_STRONGHOLD"}))
    sys.exit(0)

state = json.loads(state_path.read_text(encoding="utf-8"))
stype = state.get("type", "")
if stype != "learning":
    print(json.dumps({"error": f"Stronghold type must be 'learning', found '{stype}'", "classification": "LEARNING_SESSION_INVALID_STRONGHOLD"}))
    sys.exit(0)

curr_state = state.get("current_state", "unknown")
allowed_states = ["LOCAL_CHECKLIST_READY", "ARCHITECT_PLAN_IMPORTED", "READY_FOR_LOCAL_WORK"]
if curr_state not in allowed_states:
    # We might still allow it if it's been manually updated, but let's be strict for MVP
    print(json.dumps({"error": f"Stronghold is in state '{curr_state}'. Must be one of: {', '.join(allowed_states)}", "classification": "LEARNING_SESSION_BLOCKED"}))
    sys.exit(0)

checklist_path = stronghold_dir / "local_checklist.md"
if not checklist_path.is_file() or checklist_path.stat().st_size == 0:
    print(json.dumps({"error": "Missing or empty local_checklist.md", "classification": "LEARNING_SESSION_BLOCKED"}))
    sys.exit(0)

# Identify next task from checklist (simple heuristic: first unchecked box)
checklist_text = checklist_path.read_text(encoding="utf-8")
match = re.search(r"(?:-|\d+\.)\s*\[\s*\]\s*(.+)", checklist_text)
next_task = match.group(1).strip() if match else "No pending tasks found in checklist."

# Generate session plan
sessions_dir = stronghold_dir / "sessions"
sessions_dir.mkdir(parents=True, exist_ok=True)
plan_path = sessions_dir / f"{now_ts}_session_plan.md"

plan_content = f"""# Learning Session Plan: {state.get('title')}

- Timestamp: {now_ts}
- Stronghold ID: {state.get('stronghold_id')}
- Classification: LEARNING_SESSION_DRY_READY

## Session Objective
Implement or study the next tactical task:
> {next_task}

## Prerequisites
- Review `contract.md`
- Review `architect_plan.md`
- Ensure local model `hermes3:8b` is warm (if applicable)

## Topics to Study
[Heuristic: Extracting from syllabus based on task]
- Refer to `syllabus.md` for relevant sections.

## Practice Exercises
- [Draft 1]: Verbal explanation of the concept.
- [Draft 2]: Minimal code reproduction or diagram.

## Self-Assessment Questions
1. How does this task align with the primary goal?
2. What are the key risks identified by the architect for this phase?

## Estimated Time Blocks
- Prep: 10m
- Active Study/Practice: 40m
- Assessment: 10m

## Human Role
- Actively engage with the material.
- Complete the exercises in `intake_response.md` or a new session file.
- Log progress in `practice_log.md`.

## Local Tutor Role (Later Phase)
- Provide clarifications.
- Evaluate exercise results.
- Update `skill_map.md`.

## Next Safe Action
Run the actual session once implemented, or begin manual study based on this plan.
"""
plan_path.write_text(plan_content, encoding="utf-8", newline="\n")

# Update practice_log.md
log_path = stronghold_dir / "practice_log.md"
log_entry = f"\n## {now_ts} - Planned Session\n- Focus: {next_task}\n- Plan: sessions/{plan_path.name}\n"
with log_path.open("a", encoding="utf-8", newline="\n") as f:
    f.write(log_entry)

# Update loop_log.md
loop_log_path = stronghold_dir / "loop_log.md"
loop_entry = f"\n## {now_ts} - Learning Session Dry-Run Generated\n- Actor: local\n- State: {curr_state}\n- Plan: sessions/{plan_path.name}\n"
with loop_log_path.open("a", encoding="utf-8", newline="\n") as f:
    f.write(loop_entry)

# Update state.json
state["last_learning_session_plan_at"] = now_ts
state["last_learning_session_plan_path"] = str(plan_path)
state["provider_invocation"] = False
state["browser_automation"] = False
state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

def to_win(p):
    try:
        import subprocess
        return subprocess.check_output(["wslpath", "-w", str(p)]).decode("utf-8").strip()
    except:
        return str(p)

print(json.dumps({
    "classification": "LEARNING_SESSION_DRY_READY",
    "stronghold_path": to_win(stronghold_dir),
    "plan_path": to_win(plan_path),
    "next_action": "Review the session plan and begin manual study."
}))
PY
)

# Output results
echo "$RESULT_JSON" | $PYTHON -c "
import json
import sys
try:
    data = json.loads(sys.stdin.read())
    if 'error' in data:
        print(f\"Error: {data['error']}\")
        print(f\"Classification: {data['classification']}\")
        sys.exit(1)
    print(f\"Classification: {data['classification']}\")
    print(f\"Stronghold:     {data['stronghold_path']}\")
    print(f\"Session Plan:   {data['plan_path']}\")
    print(f\"Next Action:    {data['next_action']}\")
except Exception as e:
    print(f\"Error parsing result: {e}\")
    sys.exit(1)
"

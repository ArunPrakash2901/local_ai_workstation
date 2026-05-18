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

if [ -z "$STRONGHOLD_INPUT" ]; then
    echo "Usage: ws learning-advance <stronghold_id_or_path>"
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

STRONGHOLD_DIR=$(resolve_stronghold_dir) || exit 1

NOW_TS=$(date +"%Y%m%d_%H%M%S")

# Use Python for advancement logic
RESULT_JSON=$( "$PYTHON" - "$STRONGHOLD_DIR" "$NOW_TS" << 'PY'
import sys
import json
import re
from pathlib import Path

stronghold_dir = Path(sys.argv[1])
now_ts = sys.argv[2]

def to_win(p):
    try:
        import subprocess
        return subprocess.check_output(["wslpath", "-w", str(p)]).decode("utf-8").strip()
    except:
        return str(p)

state_path = stronghold_dir / "state.json"
if not state_path.is_file():
    print(json.dumps({"error": "Missing state.json", "classification": "LEARNING_ADVANCE_BLOCKED"}))
    sys.exit(0)

state = json.loads(state_path.read_text(encoding="utf-8"))
if state.get("type") != "learning":
    print(json.dumps({"error": "Not a learning stronghold", "classification": "LEARNING_ADVANCE_BLOCKED"}))
    sys.exit(0)

# 1. Verify decision
last_decision = state.get("last_learning_review_decision")
if last_decision != "ADVANCE_TO_NEXT_TASK":
    print(json.dumps({
        "error": f"Requires 'ADVANCE_TO_NEXT_TASK' decision. Current decision: {last_decision}",
        "classification": "LEARNING_ADVANCE_REQUIRES_ADVANCE_DECISION"
    }))
    sys.exit(0)

# 2. Determine completed task from latest plan
completed_task = "Unknown Task"
plan_path_str = state.get("last_learning_session_plan_path")
if plan_path_str:
    plan_path = Path(plan_path_str)
    if plan_path.is_file():
        plan_text = plan_path.read_text(encoding="utf-8")
        # More robust match for the blockquote line
        match = re.search(r"^>\s*(.+)", plan_text, re.MULTILINE)
        if match:
            completed_task = match.group(1).strip()

# 3. Read progress.md to track what's already done
progress_path = stronghold_dir / "progress.md"
completed_tasks_set = set()
if progress_path.is_file():
    prog_text = progress_path.read_text(encoding="utf-8")
    # Heuristic: Find tasks in progress.md
    for line in prog_text.splitlines():
        if line.startswith("- [x]") or line.startswith("- Completed:"):
            completed_tasks_set.add(line.split(":", 1)[-1].strip())

# 4. Find next task from local_checklist.md
checklist_path = stronghold_dir / "local_checklist.md"
if not checklist_path.is_file():
    print(json.dumps({"error": "Missing local_checklist.md", "classification": "LEARNING_ADVANCE_BLOCKED"}))
    sys.exit(0)

checklist_text = checklist_path.read_text(encoding="utf-8")
tasks = re.findall(r"(?:-|\d+\.)\s*\[\s*\]\s*(.+)", checklist_text)

next_task = "No pending tasks found in checklist."
found_next = False
for t in tasks:
    t_clean = t.strip()
    if t_clean != completed_task and t_clean not in completed_tasks_set:
        next_task = t_clean
        found_next = True
        break

# 5. Update progress.md
if not progress_path.is_file():
    progress_path.write_text("# Learning Progress\n\n", encoding="utf-8", newline="\n")

evidence_path = state.get("last_learning_review_assessment_path") or state.get("last_learning_assessment_path", "unknown")

progress_entry = f"""
## {now_ts} - Task Completed
- Completed: {completed_task}
- Evidence: {evidence_path}
- Advancement Reason: Positive review assessment and ADVANCE decision.
- Next Task: {next_task}
"""

with progress_path.open("a", encoding="utf-8", newline="\n") as f:
    f.write(progress_entry)

# 6. Update state.json
state["last_learning_advanced_at"] = now_ts
state["last_completed_learning_task"] = completed_task
state["next_learning_task"] = next_task
state["learning_session_status"] = "ready_for_next_session"
state["provider_invocation"] = False
state["browser_automation"] = False
state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

# 7. Update logs
with (stronghold_dir / "practice_log.md").open("a", encoding="utf-8", newline="\n") as f:
    f.write(f"\n## {now_ts} - Learning Task Advanced\n- Completed: {completed_task}\n- Next: {next_task}\n")

with (stronghold_dir / "loop_log.md").open("a", encoding="utf-8", newline="\n") as f:
    f.write(f"\n## {now_ts} - Learning Task Advanced\n- Completed: {completed_task}\n- Next: {next_task}\n")

classification = "LEARNING_ADVANCED"
if not found_next:
    classification = "LEARNING_ADVANCE_NO_NEXT_TASK"

print(json.dumps({
    "classification": classification,
    "completed_task": completed_task,
    "next_task": next_task,
    "progress_path": to_win(progress_path),
    "next_safe_action": "Run `ws learning-run --session --dry-run` to plan the next session." if found_next else "Stronghold tasks complete. Run `ws stronghold-report`."
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
    print(f\"Classification:   {data['classification']}\")
    print(f\"Completed Task:   {data['completed_task']}\")
    print(f\"Next Task:        {data['next_task']}\")
    print(f\"Progress Path:    {data['progress_path']}\")
    print(f\"Next Action:      {data['next_safe_action']}\")
except Exception as e:
    print(f\"Error parsing result: {e}\")
    sys.exit(1)
"

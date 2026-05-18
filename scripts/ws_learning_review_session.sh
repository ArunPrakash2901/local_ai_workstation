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
DRY_RUN=0

# Parse arguments
shift || true
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        *)
            shift
            ;;
    esac
done

if [ -z "$STRONGHOLD_INPUT" ]; then
    echo "Usage: ws learning-review-session <stronghold_id_or_path> --dry-run"
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

STRONGHOLD_DIR=$(resolve_stronghold_dir) || exit 1

NOW_TS=$(date +"%Y%m%d_%H%M%S")

# Use Python for logic
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
    print(json.dumps({"error": "Missing state.json", "classification": "LEARNING_REVIEW_SESSION_BLOCKED"}))
    sys.exit(0)

state = json.loads(state_path.read_text(encoding="utf-8"))
if state.get("type") != "learning":
    print(json.dumps({"error": "Not a learning stronghold", "classification": "LEARNING_REVIEW_SESSION_BLOCKED"}))
    sys.exit(0)

# Check for latest decision
last_decision = state.get("last_learning_decision")
if last_decision not in ["REVIEW_CURRENT_TASK", "REPEAT_SESSION"]:
    print(json.dumps({
        "error": f"Stronghold decision is '{last_decision}'. Review session not required.",
        "classification": "LEARNING_REVIEW_NOT_NEEDED"
    }))
    sys.exit(0)

# Read latest assessment to extract gaps
last_assessment_path = state.get("last_learning_assessment_path")
gaps = "Manual review required to identify specific gaps."
if last_assessment_path and Path(last_assessment_path).is_file():
    assessment_text = Path(last_assessment_path).read_text(encoding="utf-8")
    # Simple heuristic to extract gaps
    match = re.search(r"Areas for Improvement:(.*?)(?:\n##|\n[A-Z]|$)", assessment_text, re.DOTALL | re.IGNORECASE)
    if match:
        gaps = match.group(1).strip()

# Generate review session plan
sessions_dir = stronghold_dir / "sessions"
sessions_dir.mkdir(parents=True, exist_ok=True)
plan_path = sessions_dir / f"{now_ts}_review_session_plan.md"

plan_content = f"""# Targeted Learning Review Plan: {state.get('title')}

- Timestamp: {now_ts}
- Stronghold ID: {state.get('stronghold_id')}
- Classification: LEARNING_REVIEW_SESSION_READY
- Base Assessment: {last_assessment_path}

## Review Objective
Address identified gaps and misconceptions to achieve proficiency.

## Gaps to Address
{gaps}

## Focused Study Topics
- Refer to sections in `syllabus.md` related to the identified gaps.
- Deep dive into concepts marked as 'Needs Improvement' in the assessment.

## Practice Tasks
- [Review 1]: Re-read the technical explanation for the difficult concepts.
- [Review 2]: Correct and re-submit the failed exercises from the previous template.
- [Review 3]: Complete a new, similar exercise provided by the local tutor.

## Self-Assessment Questions
1. Can I now explain the identified gaps without referring to external notes?
2. Does my updated practice work demonstrate proficiency in the previously failed areas?

## Criteria to Advance
- Successful completion of all Review Practice Tasks.
- Qualitative assessment score of 8/10 or higher.
- "ADVANCE" recommendation from local assessor.

## Next Safe Action
Run `ws learning-run --session --model <m> --from-plan {plan_path.name}` (once review sessions supported by runner).
"""
plan_path.write_text(plan_content, encoding="utf-8", newline="\n")

# Update logs
with (stronghold_dir / "practice_log.md").open("a", encoding="utf-8", newline="\n") as f:
    f.write(f"\n## {now_ts} - Review Session Planned\n- Focus: Address assessment gaps\n- Plan: sessions/{plan_path.name}\n")

with (stronghold_dir / "loop_log.md").open("a", encoding="utf-8", newline="\n") as f:
    f.write(f"\n## {now_ts} - Learning Review Session Dry-Run Generated\n- Plan: sessions/{plan_path.name}\n")

# Update state.json
state["last_learning_review_plan_at"] = now_ts
state["last_learning_review_plan_path"] = str(plan_path)
state["provider_invocation"] = False
state["browser_automation"] = False
state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

print(json.dumps({
    "classification": "LEARNING_REVIEW_SESSION_READY",
    "plan_path": to_win(plan_path),
    "next_action": "Review the targeted plan and prepare for a model-backed review session."
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
    print(f\"Plan Path:      {data['plan_path']}\")
    print(f\"Next Action:    {data['next_action']}\")
except Exception as e:
    print(f\"Error parsing result: {e}\")
    sys.exit(1)
"

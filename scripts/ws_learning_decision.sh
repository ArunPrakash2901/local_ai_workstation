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
REVIEW=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --review)
            REVIEW=1
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
    echo "Usage: ws learning-decision <stronghold_id_or_path> [--review]"
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

# Use Python for classification logic
RESULT_JSON=$( "$PYTHON" - "$STRONGHOLD_DIR" "$NOW_TS" "$REVIEW" << 'PY'
import sys
import json
import re
from pathlib import Path

stronghold_dir = Path(sys.argv[1])
now_ts = sys.argv[2]
is_review = sys.argv[3] == "1"

state_path = stronghold_dir / "state.json"
if not state_path.is_file():
    print(json.dumps({"error": "Missing state.json", "classification": "BLOCKED"}))
    sys.exit(0)

state = json.loads(state_path.read_text(encoding="utf-8"))
if state.get("type") != "learning":
    print(json.dumps({"error": "Not a learning stronghold", "classification": "BLOCKED"}))
    sys.exit(0)

# Check requirements
if is_review:
    last_assessment_path = state.get("last_learning_review_assessment_path")
    decision_type = "Learning Review Decision"
    log_subject = "Learning Review Decision Generated"
    file_prefix = "learning_review_decision"
    status_val = "review_decision_recorded"
    state_key_at = "last_learning_review_decision_at"
    state_key_val = "last_learning_review_decision"
else:
    last_assessment_path = state.get("last_learning_assessment_path")
    decision_type = "Learning Progress Decision"
    log_subject = "Learning Decision Generated"
    file_prefix = "learning_decision"
    status_val = "decision_recorded"
    state_key_at = "last_learning_decision_at"
    state_key_val = "last_learning_decision"

if not last_assessment_path or not Path(last_assessment_path).is_file():
    print(json.dumps({"error": f"Latest {'review ' if is_review else ''}assessment not found", "classification": "BLOCKED"}))
    sys.exit(0)

assessment_text = Path(last_assessment_path).read_text(encoding="utf-8")

classification = "NEEDS_HUMAN_REVIEW"
next_action = "Manually review the latest assessment."

# Heuristics
rec_match = re.search(r"Recommendation:\s*(ADVANCE|REVIEW|REPEAT)", assessment_text, re.IGNORECASE)
explicit_rec = rec_match.group(1).upper() if rec_match else None

score_match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*10", assessment_text)
score = float(score_match.group(1)) if score_match else None

if not score:
    score_match = re.search(r"Score:\s*(\d+(?:\.\d+)?)", assessment_text, re.IGNORECASE)
    score = float(score_match.group(1)) if score_match else None

has_major_gaps = "major gaps" in assessment_text.lower() or "significant improvement" in assessment_text.lower()
gaps_fixed = bool(re.search(r"(?:gaps fixed|gaps were fixed|prior gaps fixed|gaps were successfully addressed)\s*[:\*]*\s*(?:yes|true)", assessment_text, re.IGNORECASE | re.DOTALL))

# Decision Tree
if explicit_rec == "ADVANCE" or (score and score >= 8 and (not is_review or gaps_fixed)):
    classification = "ADVANCE_TO_NEXT_TASK"
    next_action = "Run `ws stronghold-decision` to identify next task or generate next session plan."
elif explicit_rec == "REVIEW" or (score and 5 <= score < 8):
    classification = "REVIEW_CURRENT_TASK"
    next_action = "Review misconceptions in the assessment and retry relevant exercises."
elif explicit_rec == "REPEAT" or (score and score < 5):
    classification = "REPEAT_SESSION"
    next_action = "Regenerate tutor session for the current task and repeat the study session."
else:
    if "pass" in assessment_text.lower() and "fail" not in assessment_text.lower():
        classification = "ADVANCE_TO_NEXT_TASK"
        next_action = "Proceed based on positive qualitative feedback."

# Decision report assembly
report_content = f"""# {decision_type}: {state.get('title')}

- Timestamp: {now_ts}
- Classification: {classification}
- Base Assessment: {last_assessment_path}

## Logic Summary
- Explicit Recommendation: {explicit_rec or "none detected"}
- Detected Score: {score if score else "none detected"}
- Major Gaps Detected: {"Yes" if has_major_gaps else "No"}
"""

if is_review:
    report_content += f"- Prior Gaps Fixed: {'Yes' if gaps_fixed else 'No'}\n"

report_content += f"""
## Next Safe Action
{next_action}
"""

reports_dir = stronghold_dir / "reports"
reports_dir.mkdir(parents=True, exist_ok=True)
decision_report_path = reports_dir / f"{file_prefix}_{now_ts}.md"
decision_report_path.write_text(report_content, encoding="utf-8", newline="\n")

# Update logs
with (stronghold_dir / "practice_log.md").open("a", encoding="utf-8", newline="\n") as f:
    f.write(f"\n## {now_ts} - {log_subject}\n- Result: {classification}\n- Action: {next_action}\n")

with (stronghold_dir / "loop_log.md").open("a", encoding="utf-8", newline="\n") as f:
    f.write(f"\n## {now_ts} - {log_subject}\n- Classification: {classification}\n- Report: reports/{decision_report_path.name}\n")

# Update state.json
state[state_key_at] = now_ts
state[state_key_val] = classification
state["learning_session_status"] = status_val
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
    "classification": classification,
    "report_path": to_win(decision_report_path),
    "next_action": next_action
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
    print(f\"Report Path:    {data['report_path']}\")
    print(f\"Next Action:    {data['next_action']}\")
except Exception as e:
    print(f\"Error parsing result: {e}\")
    sys.exit(1)
"

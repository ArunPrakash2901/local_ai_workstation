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
ANSWERS_FILE=""
REVIEW=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --from-file)
            ANSWERS_FILE="$2"
            shift 2
            ;;
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

if [ -z "$STRONGHOLD_INPUT" ] || [ -z "$ANSWERS_FILE" ]; then
    echo "Usage: ws learning-import-answers <stronghold_id_or_path> --from-file <answers_file> [--review]"
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
    echo "Error: Target is not a learning stronghold or not found."
    exit 1
}

ANSWERS_FILE_WSL=$(to_wsl_path "$ANSWERS_FILE")
if [ ! -f "$ANSWERS_FILE_WSL" ]; then
    echo "Error: Answers file not found: $ANSWERS_FILE"
    exit 1
fi

if [ ! -s "$ANSWERS_FILE_WSL" ]; then
    echo "Error: Answers file is empty."
    exit 1
fi

NOW_TS=$(date +"%Y%m%d_%H%M%S")

# Use Python for logic
RESULT_JSON=$( "$PYTHON" - "$STRONGHOLD_DIR" "$ANSWERS_FILE_WSL" "$NOW_TS" "$REVIEW" << 'PY'
import sys
import json
import shutil
from pathlib import Path

stronghold_dir = Path(sys.argv[1])
answers_file = Path(sys.argv[2])
now_ts = sys.argv[3]
is_review = sys.argv[4] == "1"

def to_win(p):
    try:
        import subprocess
        return subprocess.check_output(["wslpath", "-w", str(p)]).decode("utf-8").strip()
    except:
        return str(p)

state_path = stronghold_dir / "state.json"
if not state_path.is_file():
    print(json.dumps({"error": "Missing state.json", "classification": "LEARNING_ANSWERS_INVALID_STRONGHOLD"}))
    sys.exit(0)

state = json.loads(state_path.read_text(encoding="utf-8"))
if state.get("type") != "learning":
    print(json.dumps({"error": "Not a learning stronghold", "classification": "LEARNING_ANSWERS_INVALID_STRONGHOLD"}))
    sys.exit(0)

if is_review:
    status = state.get("learning_session_status", "")
    if status != "awaiting_review_answers":
         # Warning only, don't necessarily block if user wants to override
         pass
    
    cl_base = "LEARNING_REVIEW_ANSWERS"
    file_suffix = "human_review_answers"
    log_subject = "Learning Review Answers Imported"
    status_msg = "Human review answers imported"
    next_status = "awaiting_review_assessment"
else:
    cl_base = "LEARNING_ANSWERS"
    file_suffix = "human_answers"
    log_subject = "Learning Answers Imported"
    status_msg = "Human answers imported"
    next_status = "awaiting_assessment"

# Import artifacts
sessions_dir = stronghold_dir / "sessions"
sessions_dir.mkdir(parents=True, exist_ok=True)
imported_answers_path = sessions_dir / f"{now_ts}_{file_suffix}.md"
shutil.copy2(answers_file, imported_answers_path)

evidence_dir = stronghold_dir / "evidence"
evidence_dir.mkdir(parents=True, exist_ok=True)
evidence_path = evidence_dir / f"{file_suffix}_{now_ts}.md"
shutil.copy2(answers_file, evidence_path)

# Update practice_log.md
log_path = stronghold_dir / "practice_log.md"
log_entry = f"""
## {now_ts} - {status_msg}
- Source: {to_win(answers_file)}
- Imported: sessions/{imported_answers_path.name}
- Status: {next_status}
"""
with log_path.open("a", encoding="utf-8", newline="\n") as f:
    f.write(log_entry)

# Update loop_log.md
loop_log_path = stronghold_dir / "loop_log.md"
loop_entry = f"\n## {now_ts} - {log_subject}\n- Imported: sessions/{imported_answers_path.name}\n"
with loop_log_path.open("a", encoding="utf-8", newline="\n") as f:
    f.write(loop_entry)

# Update state.json
if is_review:
    state["last_learning_review_answers_imported_at"] = now_ts
    state["last_learning_review_answers_path"] = str(imported_answers_path)
else:
    state["last_learning_answers_imported_at"] = now_ts
    state["last_learning_answers_path"] = str(imported_answers_path)

state["learning_session_status"] = next_status
state["provider_invocation"] = False
state["browser_automation"] = False
state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

print(json.dumps({
    "classification": f"{cl_base}_IMPORTED",
    "imported_path": to_win(imported_answers_path),
    "next_action": "Run `ws learning-run --session --model <m> --evaluate` (once implemented) or manually review progress."
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
    print(f\"Imported Answers: {data['imported_path']}\")
    print(f\"Next Action:      {data['next_action']}\")
except Exception as e:
    print(f\"Error parsing result: {e}\")
    sys.exit(1)
"

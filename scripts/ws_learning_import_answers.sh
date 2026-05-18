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

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --from-file)
            ANSWERS_FILE="$2"
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

if [ -z "$STRONGHOLD_INPUT" ] || [ -z "$ANSWERS_FILE" ]; then
    echo "Usage: ws learning-import-answers <stronghold_id_or_path> --from-file <answers_file>"
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
RESULT_JSON=$( "$PYTHON" - "$STRONGHOLD_DIR" "$ANSWERS_FILE_WSL" "$NOW_TS" << 'PY'
import sys
import json
import shutil
from pathlib import Path

stronghold_dir = Path(sys.argv[1])
answers_file = Path(sys.argv[2])
now_ts = sys.argv[3]

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

# Import artifacts
sessions_dir = stronghold_dir / "sessions"
sessions_dir.mkdir(parents=True, exist_ok=True)
imported_answers_path = sessions_dir / f"{now_ts}_human_answers.md"
shutil.copy2(answers_file, imported_answers_path)

evidence_dir = stronghold_dir / "evidence"
evidence_dir.mkdir(parents=True, exist_ok=True)
evidence_path = evidence_dir / f"human_answers_{now_ts}.md"
shutil.copy2(answers_file, evidence_path)

# Update practice_log.md
log_path = stronghold_dir / "practice_log.md"
log_entry = f"""
## {now_ts} - Human Answers Imported
- Source: {to_win(answers_file)}
- Imported: sessions/{imported_answers_path.name}
- Status: awaiting assessment
"""
with log_path.open("a", encoding="utf-8", newline="\n") as f:
    f.write(log_entry)

# Update loop_log.md
loop_log_path = stronghold_dir / "loop_log.md"
loop_entry = f"\n## {now_ts} - Learning Answers Imported\n- Imported: sessions/{imported_answers_path.name}\n"
with loop_log_path.open("a", encoding="utf-8", newline="\n") as f:
    f.write(loop_entry)

# Update state.json
state["last_learning_answers_imported_at"] = now_ts
state["last_learning_answers_path"] = str(imported_answers_path)
state["learning_session_status"] = "awaiting_assessment"
state["provider_invocation"] = False
state["browser_automation"] = False
state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

print(json.dumps({
    "classification": "LEARNING_ANSWERS_IMPORTED",
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

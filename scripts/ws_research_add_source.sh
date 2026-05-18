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
SOURCE_TEXT=""
LABEL=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --source-text)
            SOURCE_TEXT="$2"
            shift 2
            ;;
        --label)
            LABEL="$2"
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

if [ -z "$STRONGHOLD_INPUT" ] || [ -z "$SOURCE_TEXT" ] || [ -z "$LABEL" ]; then
    echo "Usage: ws research-add-source <stronghold_id_or_path> --source-text <text_file> --label \"<source_label>\""
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

    # Search in research subfolder specifically
    mapfile -t matches < <(
        find "$STRONGHOLDS_DIR/research" -mindepth 1 -maxdepth 1 -type d -name "$STRONGHOLD_INPUT" 2>/dev/null | sort
    )

    case "${#matches[@]}" in
        0)
            echo "Research stronghold not found: $STRONGHOLD_INPUT" >&2
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
SOURCE_TEXT_WSL=$(to_wsl_path "$SOURCE_TEXT")

if [ ! -f "$SOURCE_TEXT_WSL" ]; then
    echo "Error: Source text file not found: $SOURCE_TEXT_WSL"
    exit 1
fi

if [ ! -s "$SOURCE_TEXT_WSL" ]; then
    echo "Error: Source text file is empty: $SOURCE_TEXT_WSL"
    exit 1
fi

# Use Python for logic
RESULT_JSON=$( "$PYTHON" - "$STRONGHOLD_DIR" "$NOW_TS" "$SOURCE_TEXT_WSL" "$LABEL" << 'PY'
import sys
import json
import re
import shutil
from pathlib import Path

stronghold_dir = Path(sys.argv[1])
now_ts = sys.argv[2]
source_text_path = Path(sys.argv[3])
label = sys.argv[4]

def to_win(p):
    try:
        import subprocess
        return subprocess.check_output(["wslpath", "-w", str(p)]).decode("utf-8").strip()
    except:
        return str(p)

def slugify(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")

# 0. Check core state
state_path = stronghold_dir / "state.json"
if not state_path.is_file():
    print(json.dumps({"error": f"Missing state.json in {stronghold_dir}", "classification": "RESEARCH_BLOCKED"}))
    sys.exit(0)

state = json.loads(state_path.read_text(encoding="utf-8"))
stype = state.get("type", "")
if stype != "research":
    print(json.dumps({"error": f"Stronghold type must be 'research', found '{stype}'", "classification": "RESEARCH_BLOCKED"}))
    sys.exit(0)

lm_path = stronghold_dir / "literature_map.md"
if not lm_path.is_file():
    print(json.dumps({"error": f"Missing literature_map.md in {stronghold_dir}", "classification": "RESEARCH_BLOCKED"}))
    sys.exit(0)

# 1. Create sources folder
sources_dir = stronghold_dir / "sources"
sources_dir.mkdir(parents=True, exist_ok=True)

# 2. Copy source
label_slug = slugify(label)
dest_path = sources_dir / f"{now_ts}_{label_slug}.txt"
shutil.copy2(source_text_path, dest_path)

# 3. Update literature_map.md
with lm_path.open("a", encoding="utf-8", newline="\n") as f:
    # Check if table exists, if not add header (already handled by research-run but safe)
    content = lm_path.read_text(encoding="utf-8")
    if "| Source |" not in content:
        f.write("# Literature Map\n\n| Source | Title | Key Theme | Relevance | Status | Stored Path | Added |\n| --- | --- | --- | --- | --- | --- | --- |\n")
    
    relative_path = f"sources/{dest_path.name}"
    f.write(f"| {label} | [Pending] | [Pending] | [Pending] | registered_unreviewed | {relative_path} | {now_ts} |\n")

# 4. Update state.json
state["last_research_source_added_at"] = now_ts
state["last_research_source_path"] = str(dest_path)
state["provider_invocation"] = False
state["browser_automation"] = False
state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

# 5. Update loop_log.md
with (stronghold_dir / "loop_log.md").open("a", encoding="utf-8", newline="\n") as f:
    f.write(f"\n## {now_ts} - Research Source Added\n- Label: {label}\n- Path: sources/{dest_path.name}\n")

latest_plan_path = state.get("last_research_review_plan_path", "[path_to_plan]")

print(json.dumps({
    "classification": "RESEARCH_SOURCE_REGISTERED",
    "stronghold_path": to_win(stronghold_dir),
    "stored_source_path": to_win(dest_path),
    "next_action": f"run ws research-run {state.get('stronghold_id', 'id')} --review-paper --model hermes3:8b --source-text {to_win(dest_path)} --from-plan {to_win(latest_plan_path)}"
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
        sys.exit(1)
    print(f\"Classification:  {data['classification']}\")
    print(f\"Stored Source:   {data['stored_source_path']}\")
    print(f\"Next Action:     {data['next_action']}\")
except Exception as e:
    print(f\"Error parsing result: {e}\")
    sys.exit(1)
"

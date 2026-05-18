#!/bin/bash

set -euo pipefail

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
STRONGHOLDS_DIR="$WS_HOME/strongholds"
HANDOFFS_DIR="$WS_HOME/handoffs"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

STRONGHOLD_INPUT=${1:-}
shift || true

HANDOFF_INPUT=""

while [ $# -gt 0 ]; do
    case "$1" in
        --from-handoff)
            HANDOFF_INPUT=${2:-}
            shift 2
            ;;
        *)
            echo "Usage: ws stronghold-plan-import <stronghold_id_or_path> --from-handoff latest|<handoff_id_or_path>"
            exit 1
            ;;
    esac
done

if [ -z "$STRONGHOLD_INPUT" ] || [ -z "$HANDOFF_INPUT" ]; then
    echo "Usage: ws stronghold-plan-import <stronghold_id_or_path> --from-handoff latest|<handoff_id_or_path>"
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

resolve_handoff_dir() {
    local candidate
    candidate=$(to_wsl_path "$HANDOFF_INPUT")
    if [ -d "$candidate" ] && [ -f "$candidate/metadata.json" ]; then
        printf '%s\n' "$candidate"
        return
    fi

    if [ "$HANDOFF_INPUT" = "latest" ]; then
        ls -dt "$HANDOFFS_DIR"/* 2>/dev/null | head -n 1
        return
    fi

    if [ -d "$HANDOFFS_DIR" ]; then
        local match
        match=$(find "$HANDOFFS_DIR" -maxdepth 1 -type d -name "*$HANDOFF_INPUT*" | sort -r | head -n 1)
        if [ -n "$match" ]; then
            printf '%s\n' "$match"
            return
        fi
    fi

    return 1
}

STRONGHOLD_DIR=$(resolve_stronghold_dir) || exit 1
HANDOFF_DIR=$(resolve_handoff_dir) || {
    echo "Error: Handoff not found: $HANDOFF_INPUT"
    exit 1
}

STAMP=$(date +%Y%m%d_%H%M%S)

"$PYTHON" - "$STRONGHOLD_DIR" "$HANDOFF_DIR" "$STAMP" << 'PY'
import sys
import json
import shutil
import re
from pathlib import Path

stronghold_dir = Path(sys.argv[1])
handoff_dir = Path(sys.argv[2])
stamp = sys.argv[3]

# 1. Verify files
state_path = stronghold_dir / "state.json"
if not state_path.is_file():
    print(f"Error: state.json not found in {stronghold_dir}")
    sys.exit(1)

meta_path = handoff_dir / "metadata.json"
if not meta_path.is_file():
    print(f"Error: metadata.json not found in {handoff_dir}")
    sys.exit(1)

resp_path = handoff_dir / "response.md"
if not resp_path.is_file():
    print(f"Error: response.md not found in {handoff_dir}")
    sys.exit(1)

resp_content = resp_path.read_text(encoding="utf-8").strip()
if not resp_content or "No response has been imported yet" in resp_content or "Response pending" in resp_content:
    print(f"Error: response.md is empty or placeholder in {handoff_dir}")
    sys.exit(1)

# 2. Verify metadata
state = json.loads(state_path.read_text(encoding="utf-8"))
meta = json.loads(meta_path.read_text(encoding="utf-8"))

if meta.get("role") != "senior_architect":
    print(f"Error: Handoff role must be 'senior_architect', found '{meta.get('role')}'")
    sys.exit(1)

h_state = meta.get("current_state", "")
# Allow ARCHITECT_REVIEW_READY if response is actually there (useful for manual testing or overrides)
# but normally we expect RESPONSE_IMPORTED or REVIEW_ACCEPTED
if h_state not in ["RESPONSE_IMPORTED", "REVIEW_ACCEPTED", "ARCHITECT_REVIEW_READY"]:
    print(f"Error: Handoff state must be RESPONSE_IMPORTED or REVIEW_ACCEPTED, found '{h_state}'")
    sys.exit(1)

# ID matching
sid = state.get("stronghold_id")
h_sid = meta.get("stronghold_id") or meta.get("feature_id") # support legacy feature_id if needed
if sid != h_sid:
    print(f"Error: Stronghold ID mismatch. Stronghold: {sid}, Handoff: {h_sid}")
    sys.exit(1)

# 3. Import
target_plan = stronghold_dir / "architect_plan.md"
target_plan.write_text(resp_content, encoding="utf-8", newline="\n")

# 4. Safety check for trading-research
safety_warning = ""
stype = state.get("type")
if stype == "trading-research":
    # Heuristic for live trading recommendations
    keywords = ["live trading", "deploy capital", "brokerage", "api key", "execute trades", "real money"]
    found = [k for k in keywords if k in resp_content.lower()]
    if found:
        safety_warning = f"WARNING: Plan appears to recommend prohibited actions: {', '.join(found)}"

# 5. Update state.json
state["current_state"] = "ARCHITECT_PLAN_IMPORTED"
if safety_warning:
    state["current_state"] = "NEEDS_HUMAN_REVIEW"

state["last_architect_plan_imported_at"] = stamp
state["architect_handoff_path"] = str(handoff_dir)
state["architect_plan_path"] = str(target_plan)
state["provider_invocation"] = False
state["browser_automation"] = False
state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

# 6. Append loop log
loop_log_path = stronghold_dir / "loop_log.md"
loop_entry = f"""
## {stamp} - Architect Plan Imported
- Actor: local
- State: {state["current_state"]}
- Handoff: {handoff_dir}
- Plan: architect_plan.md
"""
if safety_warning:
    loop_entry += f"- Safety: {safety_warning}\n"

with loop_log_path.open("a", encoding="utf-8", newline="\n") as f:
    f.write(loop_entry)

# 7. Write report
report_path = stronghold_dir / "reports" / f"architect_plan_import_{stamp}.md"
report_content = f"""# Architect Plan Import Report

- Timestamp: {stamp}
- Stronghold ID: {sid}
- Type: {stype}
- Result State: {state["current_state"]}
- Handoff Path: {handoff_dir}

## Import Summary
Successfully imported Senior Architect response into `architect_plan.md`.

"""
if safety_warning:
    report_content += f"## Safety Violations Detected\n{safety_warning}\n\n"

report_path.write_text(report_content, encoding="utf-8", newline="\n")

print(f"Import complete. New state: {state['current_state']}")
if safety_warning:
    print(safety_warning)
PY

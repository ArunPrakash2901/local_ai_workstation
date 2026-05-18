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
    echo "Usage: ws stronghold-report <stronghold_id_or_path>"
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

NOW_TS=$(date +"%Y%m%d_%H%M%S")

# Use Python to aggregate data and write final_report.md
"$PYTHON" - "$STRONGHOLD_DIR" "$NOW_TS" << 'PY'
import sys
import json
import re
from pathlib import Path

stronghold_dir = Path(sys.argv[1])
now_ts = sys.argv[2]

def get_content(filename, fallback="[Not found]"):
    p = stronghold_dir / filename
    if p.is_file():
        return p.read_text(encoding="utf-8").strip()
    return fallback

state_path = stronghold_dir / "state.json"
state = json.loads(state_path.read_text(encoding="utf-8"))
stype = state.get("type", "unknown")
title = state.get("title", "unknown")
sid = state.get("stronghold_id", "unknown")
curr_state = state.get("current_state", "unknown")

# Aggregating information
contract = get_content("contract.md")
goals = get_content("goals.md")
constraints = get_content("constraints.md")
success_criteria = get_content("success_criteria.md")
intake_response = get_content("intake_response.md")
architect_plan = get_content("architect_plan.md")
local_checklist = get_content("local_checklist.md")
loop_log = get_content("loop_log.md")

# Evidence paths
evidence_dir = stronghold_dir / "evidence"
evidence_list = []
if evidence_dir.is_dir():
    evidence_list = sorted([f.name for f in evidence_dir.iterdir() if f.is_file()])

# Extract timeline
timeline = []
for line in loop_log.splitlines():
    if line.startswith("## "):
        timeline.append(line.lstrip("#").strip())

# Determine next safe action
next_action = "Consult the operational checklist or Senior Architect for next steps."
if curr_state == "CREATED":
    next_action = "Run `ws stronghold-intake` to begin discovery."
elif curr_state == "INTAKE_IN_PROGRESS":
    next_action = "Import human answers using `ws stronghold-intake-import`."
elif curr_state == "CONTRACT_READY":
    next_action = "Create an architect handoff using `ws stronghold-architect-handoff`."
elif curr_state == "ARCHITECT_REVIEW_READY":
    next_action = "Paste the prompt into a browser model and import the response using `ws stronghold-plan-import`."
elif curr_state == "ARCHITECT_PLAN_IMPORTED":
    next_action = "Generate an operational checklist using `ws stronghold-local-checklist`."
elif curr_state == "LOCAL_CHECKLIST_READY":
    if stype == "learning":
        next_action = "Begin the first study/practice session defined in the checklist."
    elif stype == "product":
        next_action = "Execute the first build/implementation task in the checklist."
    elif stype == "research":
        next_action = "Start source collection and hypothesis evaluation."
    elif stype == "feature":
        next_action = "Run `ws feature-run --dry-run` to verify execution environment."

# Final report assembly
report_content = f"""# Stronghold Report: {title}

- Timestamp: {now_ts}
- Stronghold ID: {sid}
- Type: {stype}
- Current State: {curr_state}

## 1. Objectives & Goals
{goals}

## 2. Contract & Scope
{contract}

## 3. Constraints & Safety
{constraints}

"""

if stype == "trading-research":
    report_content += """> **STRICT SAFETY REMINDER**: 
> - NO LIVE TRADING
> - NO CAPITAL DEPLOYMENT
> - NO BROKERAGE/API EXECUTION
> - Backtest and paper-trading only until explicitly redesigned.

"""

report_content += f"""## 4. Success Criteria
{success_criteria}

## 5. Planning Status
- **Architect Plan**: {"Imported" if architect_plan != "[Not found]" else "Pending"}
- **Local Checklist**: {"Generated" if local_checklist != "[Not found]" else "Pending"}

## 6. Execution Evidence
- **Evidence Files**:
{chr(10).join(f"  - {e}" for e in evidence_list) if evidence_list else "  - none"}

## 7. Timeline Summary
{chr(10).join(f"- {t}" for t in timeline[-10:]) if timeline else "- none"}

## 8. Next Safe Action
{next_action}
"""

final_report_path = stronghold_dir / "final_report.md"
final_report_path.write_text(report_content, encoding="utf-8", newline="\n")

# Update state.json
state["last_reported_at"] = now_ts
state["report_path"] = str(final_report_path)
state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

# Append loop log
loop_log_path = stronghold_dir / "loop_log.md"
loop_entry = f"\n## {now_ts} - Stronghold Report Generated\n- Actor: local\n- Report: final_report.md\n"
if loop_log_path.is_file():
    with loop_log_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(loop_entry)

def to_win(p):
    try:
        import subprocess
        return subprocess.check_output(["wslpath", "-w", str(p)]).decode("utf-8").strip()
    except:
        return str(p)

print(f"Report generated: {to_win(final_report_path)}")
PY

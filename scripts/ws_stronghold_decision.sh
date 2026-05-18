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
    echo "Usage: ws stronghold-decision <stronghold_id_or_path>"
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

# Use Python for classification logic
RESULT_JSON=$( "$PYTHON" - "$STRONGHOLD_DIR" "$NOW_TS" << 'PY'
import sys
import json
from pathlib import Path

stronghold_dir = Path(sys.argv[1])
now_ts = sys.argv[2]

def has_artifact(filename):
    p = stronghold_dir / filename
    return p.is_file() and p.stat().st_size > 0

state_path = stronghold_dir / "state.json"
state = json.loads(state_path.read_text(encoding="utf-8"))
stype = state.get("type", "unknown")
title = state.get("title", "unknown")
curr_state = state.get("current_state", "unknown")

# Required file checks
intake_ready = has_artifact("intake_response.md")
contract_ready = has_artifact("contract.md")
plan_imported = has_artifact("architect_plan.md")
checklist_ready = has_artifact("local_checklist.md")
report_ready = has_artifact("final_report.md")

# Default classification
classification = "NEEDS_HUMAN_REVIEW"
reason = "Unclassified state."
next_action = "Review stronghold state manually."

# Logic
if curr_state == "CREATED":
    classification = "NEEDS_INTAKE"
    next_action = "Run `ws stronghold-intake`."
elif curr_state == "INTAKE_IN_PROGRESS":
    if intake_ready:
        classification = "READY_FOR_HUMAN_REVIEW"
        next_action = "Import answers with `ws stronghold-intake-import`."
    else:
        classification = "NEEDS_INTAKE"
        next_action = "Complete `intake_response.md`."
elif curr_state == "CONTRACT_READY":
    classification = "NEEDS_ARCHITECT_PLAN"
    next_action = "Run `ws stronghold-architect-handoff`."
elif curr_state == "ARCHITECT_REVIEW_READY":
    classification = "NEEDS_ARCHITECT_PLAN"
    next_action = "Import plan with `ws stronghold-plan-import` after browser review."
elif curr_state == "ARCHITECT_PLAN_IMPORTED":
    classification = "NEEDS_LOCAL_CHECKLIST"
    next_action = "Run `ws stronghold-local-checklist`."
elif curr_state == "LOCAL_CHECKLIST_READY":
    if not report_ready:
        classification = "NEEDS_REPORT"
        next_action = "Run `ws stronghold-report`."
    else:
        # High-level domain-specific gating
        if stype == "learning":
            classification = "READY_FOR_LOCAL_WORK"
            next_action = "Start study/practice session defined in checklist."
        elif stype == "trading-research":
            classification = "READY_FOR_LOCAL_WORK"
            next_action = "Begin backtesting tasks; NO LIVE TRADING ALLOWED."
        elif stype == "research":
            classification = "READY_FOR_LOCAL_WORK"
            next_action = "Start evidence collection and synthesis."
        elif stype == "product":
            classification = "READY_FOR_SUPERVISED_AGENT"
            next_action = "Proceed to implementation task execution."
        elif stype == "feature":
            classification = "READY_FOR_SUPERVISED_AGENT"
            next_action = "Run `ws feature-run --dry-run`."
        else:
            classification = "READY_FOR_HUMAN_REVIEW"
            next_action = "Manually authorize next step."

if curr_state == "NEEDS_HUMAN_REVIEW":
    classification = "NEEDS_HUMAN_REVIEW"
    next_action = "Resolve blockers or safety warnings manually."

if curr_state == "COMPLETE":
    classification = "COMPLETE_CANDIDATE"
    next_action = "Archive stronghold or move to next dependency."

# Decision report assembly
decision_content = f"""# Stronghold Decision Gate: {title}

- Timestamp: {now_ts}
- Classification: {classification}
- Current State: {curr_state}
- Domain: {stype}

## Artifact Readiness
- Intake Response: {"PASS" if intake_ready else "PENDING"}
- Contract: {"PASS" if contract_ready else "PENDING"}
- Architect Plan: {"PASS" if plan_imported else "PENDING"}
- Local Checklist: {"PASS" if checklist_ready else "PENDING"}
- Final Report: {"PASS" if report_ready else "PENDING"}

## Safety Constraints
"""

if stype == "trading-research":
    decision_content += """> **MANDATORY**:
> - NO LIVE TRADING
> - NO CAPITAL DEPLOYMENT
> - RESEARCH / BACKTEST / PAPER-TRADING ONLY
"""
else:
    decision_content += "- Standard workstation safety rules apply.\n"

decision_content += f"""
## Next Safe Action
{next_action}
"""

reports_dir = stronghold_dir / "reports"
reports_dir.mkdir(parents=True, exist_ok=True)
decision_path = reports_dir / f"decision_{now_ts}.md"
decision_path.write_text(decision_content, encoding="utf-8", newline="\n")

# Update state.json
state["last_decision_at"] = now_ts
state["last_decision"] = classification
state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

# Update loop log
loop_log_path = stronghold_dir / "loop_log.md"
loop_entry = f"""
## {now_ts} - Stronghold Decision Generated
- Actor: local
- Classification: {classification}
- Report: reports/{decision_path.name}
"""
if loop_log_path.is_file():
    with loop_log_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(loop_entry)

def to_win(p):
    try:
        import subprocess
        return subprocess.check_output(["wslpath", "-w", str(p)]).decode("utf-8").strip()
    except:
        return str(p)

print(json.dumps({
    "classification": classification,
    "stronghold_path": to_win(stronghold_dir),
    "report_path": to_win(decision_path),
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
    print(f\"Classification: {data['classification']}\")
    print(f\"Stronghold:     {data['stronghold_path']}\")
    print(f\"Report:         {data['report_path']}\")
    print(f\"Next Action:    {data['next_action']}\")
except Exception as e:
    print(f\"Error parsing result: {e}\")
    sys.exit(1)
"

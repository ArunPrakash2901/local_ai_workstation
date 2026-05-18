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
    echo "Usage: ws stronghold-intake <stronghold_id_or_path>"
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

    # Search in all subdirectories of strongholds/
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

# Use Python to handle logic
"$PYTHON" - "$STRONGHOLD_DIR" "$NOW_TS" << 'PY'
import sys
import json
from pathlib import Path

stronghold_dir = Path(sys.argv[1])
now_ts = sys.argv[2]

state_path = stronghold_dir / "state.json"
if not state_path.is_file():
    print(f"Error: Missing state.json in {stronghold_dir}")
    sys.exit(1)

state = json.loads(state_path.read_text(encoding="utf-8"))
stype = state.get("type", "unknown")
title = state.get("title", "unknown")
sid = state.get("stronghold_id", "unknown")

questions = []

if stype == "learning":
    questions = [
        "What is your current level/background in this topic?",
        "What is the specific target outcome or skill you want to acquire?",
        "Do you have a deadline for this learning goal?",
        "What is your preferred learning style (reading, video, hands-on projects)?",
        "How many hours per week can you realistically dedicate to this?",
        "What is your desired balance between theory and practice (e.g., 20/80)?",
        "How should your progress be assessed (quizzes, project completion, peer review)?",
        "Are there specific projects or exercises you want to include?"
    ]
elif stype == "product":
    questions = [
        "Who is the primary user or customer for this product?",
        "What specific problem are you solving?",
        "What is the desired outcome or 'North Star' for this product?",
        "What are the absolute MVP boundaries (what is out of scope)?",
        "How will you measure success (metrics, user feedback)?",
        "What are the known constraints (technical, budget, legal)?",
        "What platforms or tools are required?",
        "What aspects do you want to review personally versus delegating to the AI?"
    ]
elif stype == "feature":
    questions = [
        "Which repository or project does this feature belong to?",
        "What is the expected behavior from the user's perspective?",
        "Which specific files are allowed to be modified?",
        "What are the detailed acceptance criteria?",
        "What existing tests should be run, or what new tests are needed?",
        "What is the risk level of these changes?",
        "What are the expectations for rollback if validation fails?"
    ]
elif stype == "research":
    questions = [
        "What is the core research question you are investigating?",
        "What are the primary sources or papers to be analyzed?",
        "What is your initial hypothesis?",
        "What standard of evidence is required for validation?",
        "What is the final intended deliverable (report, presentation, data)?",
        "What is the desired review cadence for findings?"
    ]
elif stype == "trading-research":
    questions = [
        "Which market and specific instruments are being researched?",
        "What is the target timeframe for the strategy (e.g., 1m, 1h, daily)?",
        "What academic paper or source material inspired this hypothesis?",
        "What is the formal description of the alpha signal/hypothesis?",
        "What data sources will be used (historical)?",
        "What is the desired backtest period?",
        "What assumptions should be made for transaction costs?",
        "What slippage model should be applied?",
        "What are the strict risk limits (stop loss, max drawdown, exposure)?",
        "What overfitting controls will be implemented (e.g., walk-forward, k-fold)?",
        "What are the requirements for paper-trading validation?",
        "CONFIRMATION REQUIRED: Do you acknowledge that live trading and capital deployment are DISABLED and out-of-scope for this stronghold?"
    ]
else:
    questions = ["No domain-specific questions defined for type: " + stype]

# Generate intake_questions.md
q_text = f"# Intake Questions: {title}\n\nType: {stype}\n\n"
if stype == "trading-research":
    q_text += "> **SAFETY WARNING**: This stronghold is for RESEARCH ONLY. Live trading, brokerage API execution, and capital deployment are STRICTORLY DISABLED.\n\n"

for i, q in enumerate(questions, 1):
    q_text += f"## {i}. {q}\n\n[Answer here]\n\n"

(stronghold_dir / "intake_questions.md").write_text(q_text, encoding="utf-8", newline="\n")

# Generate intake_response.md placeholder
r_text = f"# Intake Response: {title}\n\nCopy the questions from `intake_questions.md` and provide your answers here.\n"
(stronghold_dir / "intake_response.md").write_text(r_text, encoding="utf-8", newline="\n")

# Update state.json
state["current_state"] = "INTAKE_IN_PROGRESS"
state["last_intake_at"] = now_ts
state["provider_invocation"] = False
state["browser_automation"] = False
state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

# Append loop_log.md
loop_log_path = stronghold_dir / "loop_log.md"
loop_entry = f"\n## {now_ts} - Stronghold Intake Generated\n- Actor: local\n- State: INTAKE_IN_PROGRESS\n- Artifact: intake_questions.md\n"
if loop_log_path.is_file():
    with loop_log_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(loop_entry)

# Write report
reports_dir = stronghold_dir / "reports"
reports_dir.mkdir(parents=True, exist_ok=True)
report_path = reports_dir / f"intake_report_{now_ts}.md"
report_content = f"# Stronghold Intake Report\n\n- Timestamp: {now_ts}\n- Stronghold: {title}\n- ID: {sid}\n- Type: {stype}\n- State: INTAKE_IN_PROGRESS\n\nIntake questions have been generated in `intake_questions.md`."
report_path.write_text(report_content, encoding="utf-8", newline="\n")

def to_win(p):
    try:
        return subprocess.check_output(["wslpath", "-w", str(p)]).decode("utf-8").strip()
    except:
        return str(p)

print(f"Intake questions generated: {to_win(stronghold_dir / 'intake_questions.md')}")
print(f"Report: {to_win(report_path)}")
PY

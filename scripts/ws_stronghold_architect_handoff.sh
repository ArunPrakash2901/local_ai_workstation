#!/bin/bash

set -euo pipefail

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
STRONGHOLDS_DIR="$WS_HOME/strongholds"
HANDOFFS_DIR="$WS_HOME/handoffs"
REPORTS_DIR="$WS_HOME/reports"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

STRONGHOLD_INPUT=${1:-}
shift || true

TARGET=""
PURPOSE="master-plan"

while [ $# -gt 0 ]; do
    case "$1" in
        --target)
            TARGET=${2:-}
            shift 2
            ;;
        --purpose)
            PURPOSE=${2:-}
            shift 2
            ;;
        *)
            echo "Usage: ws stronghold-architect-handoff <stronghold_id_or_path> --target chatgpt|gemini-browser [--purpose master-plan]"
            exit 1
            ;;
    esac
done

if [ -z "$STRONGHOLD_INPUT" ] || [ -z "$TARGET" ]; then
    echo "Usage: ws stronghold-architect-handoff <stronghold_id_or_path> --target chatgpt|gemini-browser [--purpose master-plan]"
    exit 1
fi

case "$TARGET" in
    chatgpt|gemini-browser) ;;
    *)
        echo "Unsupported target: $TARGET"
        echo "Supported targets: chatgpt, gemini-browser"
        exit 1
        ;;
esac

to_wsl_path() {
    case "$1" in
        /*) printf '%s' "$1" ;;
        *) wslpath -u "$1" 2>/dev/null || printf '%s' "$1" ;;
    esac
}

to_windows_path() {
    wslpath -w "$1" 2>/dev/null || printf '%s' "$1"
}

safe_slug() {
    printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9._-]+/-/g; s/^-+//; s/-+$//'
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

STRONGHOLD_DIR=$(resolve_stronghold_dir)
STATE_JSON="$STRONGHOLD_DIR/state.json"

if [ ! -f "$STATE_JSON" ]; then
    echo "Error: Missing state.json in $STRONGHOLD_DIR"
    exit 1
fi

STATE_CHECK=$( "$PYTHON" - "$STATE_JSON" <<'PY'
import json
import sys
from pathlib import Path
state = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(state.get("current_state", ""))
PY
)

if [ "$STATE_CHECK" != "CONTRACT_READY" ]; then
    echo "Error: Stronghold must be in CONTRACT_READY state. Current state: $STATE_CHECK"
    exit 1
fi

STAMP=$(date +%Y%m%d_%H%M%S)
SAFE_TARGET=$(safe_slug "$TARGET")
SAFE_PURPOSE=$(safe_slug "$PURPOSE")

HANDOFF_DIR="$HANDOFFS_DIR/${STAMP}_${SAFE_TARGET}_stronghold_${SAFE_PURPOSE}"
mkdir -p "$HANDOFF_DIR"

"$PYTHON" - "$STRONGHOLD_DIR" "$HANDOFF_DIR" "$TARGET" "$PURPOSE" "$STAMP" <<'PY'
import json
import os
import sys
from pathlib import Path

stronghold_dir = Path(sys.argv[1])
handoff_dir = Path(sys.argv[2])
target = sys.argv[3]
purpose = sys.argv[4]
timestamp = sys.argv[5]

def get_content(filename, fallback="[Artifact not found]"):
    p = stronghold_dir / filename
    if p.is_file():
        return p.read_text(encoding="utf-8").strip()
    return fallback

state = json.loads((stronghold_dir / "state.json").read_text(encoding="utf-8"))
stype = state.get("type", "unknown")
title = state.get("title", "unknown")
sid = state.get("stronghold_id", "unknown")

# Collect domain files
domain_files = ""
if stype == "learning":
    domain_files += f"\n### Syllabus\n{get_content('syllabus.md')}\n"
    domain_files += f"\n### Skill Map\n{get_content('skill_map.md')}\n"
elif stype == "product":
    domain_files += f"\n### Product Brief\n{get_content('product_brief.md')}\n"
    domain_files += f"\n### Roadmap\n{get_content('roadmap.md')}\n"
elif stype == "research":
    domain_files += f"\n### Literature Map\n{get_content('literature_map.md')}\n"
elif stype == "trading-research":
    domain_files += f"\n### Paper Notes\n{get_content('paper_notes.md')}\n"
    domain_files += f"\n### Backtest Plan\n{get_content('backtest_plan.md')}\n"

# Domain specific requirements
domain_reqs = ""
if stype == "learning":
    domain_reqs = """Please provide:
- A detailed Syllabus structured by modules.
- A Practice Plan with specific exercises.
- An Assessment Method to verify skill acquisition.
- A Weekly Cadence for study and practice."""
elif stype == "product":
    domain_reqs = """Please provide:
- A clear MVP Scope.
- A strategic Roadmap with milestones.
- A Feature Breakdown.
- Implementation sequencing and key Review Gates."""
elif stype == "research":
    domain_reqs = """Please provide:
- A comprehensive Research Plan.
- A Source Strategy for gathering evidence.
- A Hypothesis/Evidence Matrix structure.
- A Deliverable Structure for the final findings."""
elif stype == "trading-research":
    domain_reqs = """**SAFETY MANDATE**: This is for RESEARCH ONLY. No live trading, capital deployment, or brokerage API execution.
Please provide:
- A Backtest Plan with strict gates.
- Paper-trading validation requirements.
- Robust Overfitting, Slippage, and Transaction Cost controls.
- Defined Risk Limits (Max Drawdown, Volatility, Exposure)."""

prompt = f"""# Senior Architect Master Plan Request: {title}

You are a Senior Technical Architect and Strategist. 
I have a Stronghold in the `{stype}` domain that is ready for master planning.
Review the context below and provide a comprehensive **Master Plan**.

## Stronghold Context
- **Type**: {stype}
- **Title**: {title}
- **Stronghold ID**: {sid}

### Contract
{get_content('contract.md')}

### Goals
{get_content('goals.md')}

### Constraints
{get_content('constraints.md')}

### Success Criteria
{get_content('success_criteria.md')}

### Intake Response
{get_content('intake_response.md')}
{domain_files}

## Your Task
Provide a Master Plan that defines the strategy and execution roadmap. Do NOT provide low-level code unless specifically requested as a snippet.

### 1. Master Strategy
Describe the overall approach to achieving the objectives.

### 2. Execution Phases
Break the work down into logical phases.

### 3. Task Sequencing
Provide a task list. Distinguish between:
- **Intern/Operator Tasks**: Routine work suitable for local small models (Ollama).
- **Agent Tasks**: Bounded implementation/calculation tasks for workers (Codex/Gemini CLI).
- **Architect Reviews**: Critical strategic gates requiring human or high-reasoning model input.

### 4. Validation & Safety
{domain_reqs}

### 5. Risk Assessment
Identify strategic risks, dependencies, or potential blockers.

### 6. Next Safe Workstation Command
Recommend the next `ws` command (e.g. `ws stronghold-import`, `ws stronghold-local-review`).
"""

metadata = {
    "timestamp": timestamp,
    "stronghold_id": sid,
    "stronghold_path": str(stronghold_dir),
    "stronghold_type": stype,
    "stronghold_state": state["current_state"],
    "target": target,
    "purpose": "master-plan",
    "role": "senior_architect",
    "provider_invocation": False,
    "browser_automation": False,
    "current_state": "ARCHITECT_REVIEW_READY"
}

handoff_report = f"""# Stronghold Architect Handoff Report

- Timestamp: {timestamp}
- Target: {target}
- Stronghold ID: {sid}
- Type: {stype}
- State: ARCHITECT_REVIEW_READY

Generated a Senior Architect prompt for a master plan.

## Next Safe Action
1. Review `prompt.md`.
2. Paste manually into {target}.
3. Import the result using `ws stronghold-import`.
"""

context_pack = f"""# Stronghold Context Pack: {sid}
Type: {stype}
Path: {stronghold_dir}

## Artifacts
- Contract: {stronghold_dir}/contract.md
- Goals: {stronghold_dir}/goals.md
- Constraints: {stronghold_dir}/constraints.md
- Success Criteria: {stronghold_dir}/success_criteria.md
- Intake Response: {stronghold_dir}/intake_response.md
"""

handoff_dir.joinpath("prompt.md").write_text(prompt, encoding="utf-8", newline="\n")
handoff_dir.joinpath("context_pack.md").write_text(context_pack, encoding="utf-8", newline="\n")
handoff_dir.joinpath("metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8", newline="\n")
handoff_dir.joinpath("response.md").write_text("# Response pending\n", encoding="utf-8", newline="\n")
handoff_dir.joinpath("transcript.md").write_text(f"# Handoff Transcript\n\n- {timestamp}: Architect Handoff Created\n", encoding="utf-8", newline="\n")
handoff_dir.joinpath("handoff_report.md").write_text(handoff_report, encoding="utf-8", newline="\n")

# Update loop log
loop_log_path = stronghold_dir / "loop_log.md"
loop_entry = f"""
## {timestamp} - Stronghold Architect Handoff Created
- Actor: local
- Target: {target}
- Handoff: {handoff_dir}
- Provider invocation: false
- Browser automation: false
"""
with loop_log_path.open("a", encoding="utf-8", newline="\n") as f:
    f.write(loop_entry)
PY

echo "Stronghold architect handoff created: $(to_windows_path "$HANDOFF_DIR")"
echo "Prompt: $(to_windows_path "$HANDOFF_DIR/prompt.md")"
echo "Next step: review prompt and paste into $TARGET"

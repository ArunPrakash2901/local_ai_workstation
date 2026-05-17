#!/bin/bash

set -euo pipefail

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
FEATURES_DIR="$WS_HOME/features"
HANDOFFS_DIR="$WS_HOME/handoffs"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

FEATURE_INPUT=${1:-}
if [ -z "$FEATURE_INPUT" ] || [ $# -ne 1 ]; then
    echo "Usage: ws feature-report <feature_id_or_path>"
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

resolve_feature_dir() {
    local candidate
    candidate=$(to_wsl_path "$FEATURE_INPUT")
    if [ -d "$candidate" ]; then
        printf '%s\n' "$candidate"
        return
    fi

    if [ ! -d "$FEATURES_DIR" ]; then
        echo "Feature stronghold root not found: $FEATURES_DIR" >&2
        return 1
    fi

    mapfile -t matches < <(
        find "$FEATURES_DIR" -mindepth 2 -maxdepth 2 -type d -name "$FEATURE_INPUT" 2>/dev/null | sort
    )

    case "${#matches[@]}" in
        0)
            echo "Feature stronghold not found: $FEATURE_INPUT" >&2
            return 1
            ;;
        1)
            printf '%s\n' "${matches[0]}"
            ;;
        *)
            echo "Feature id is ambiguous: $FEATURE_INPUT" >&2
            printf 'Matches:\n' >&2
            printf '  %s\n' "${matches[@]}" >&2
            return 1
            ;;
    esac
}

FEATURE_DIR=$(resolve_feature_dir)
REQUIRED_FILES=(
    "state.json"
    "feature_contract.md"
    "current_plan.md"
    "loop_log.md"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$FEATURE_DIR/$file" ]; then
        echo "Feature stronghold is missing required file: $FEATURE_DIR/$file"
        exit 1
    fi
done

REPORT_STAMP=$(date +%Y%m%d_%H%M%S)
FINAL_REPORT_PATH="$FEATURE_DIR/final_report.md"

REPORT_INFO=$(
    "$PYTHON" - \
        "$FEATURE_DIR" \
        "$HANDOFFS_DIR" \
        "$REPORT_STAMP" <<'PY'
import json
import re
import sys
from pathlib import Path

feature_dir = Path(sys.argv[1])
handoffs_dir = Path(sys.argv[2])
report_stamp = sys.argv[3]

state_path = feature_dir / "state.json"
contract_path = feature_dir / "feature_contract.md"
plan_path = feature_dir / "current_plan.md"
loop_log_path = feature_dir / "loop_log.md"
final_report_path = feature_dir / "final_report.md"

state = json.loads(state_path.read_text(encoding="utf-8"))
contract_text = contract_path.read_text(encoding="utf-8").strip()
plan_text = plan_path.read_text(encoding="utf-8").strip()
loop_text = loop_log_path.read_text(encoding="utf-8").strip()

def section(text: str, heading: str) -> str:
    pattern = rf"(?ms)^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else "not specified"

def latest_validation_path() -> Path | None:
    evidence_dir = feature_dir / "evidence"
    candidates = sorted(
        evidence_dir.glob("validation_*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None

def validation_result(path: Path | None) -> str:
    if not path:
        return "not found"
    match = re.search(r"(?m)^- Result:\s*(.+)$", path.read_text(encoding="utf-8"))
    return match.group(1).strip() if match else "unknown"

def discover_handoffs(feature_path: str, feature_id: str) -> list[tuple[Path, dict]]:
    rows = []
    if not handoffs_dir.is_dir():
        return rows
    for metadata_path in handoffs_dir.glob("*/metadata.json"):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if metadata.get("feature_path") == feature_path or metadata.get("feature_id") == feature_id:
            rows.append((metadata_path.parent, metadata))
    return sorted(rows, key=lambda item: item[0].stat().st_mtime, reverse=True)

def loop_events(text: str, limit: int = 8) -> list[str]:
    return re.findall(r"(?m)^##\s+(.+)$", text)[-limit:]

def summarize_plan(text: str) -> str:
    objective = section(text, "Objective")
    next_action = section(text, "Recommended Next Safe Action")
    return f"- Objective: {objective}\n- Plan next action: {next_action}"

objective = section(contract_text, "Objective")
acceptance = section(contract_text, "Acceptance Criteria")
allowed = section(contract_text, "Allowed Files")
latest_validation = latest_validation_path()
latest_validation_result = validation_result(latest_validation)
linked_handoffs = discover_handoffs(str(feature_dir), state.get("feature_id", ""))
latest_handoff_dir = linked_handoffs[0][0] if linked_handoffs else None
latest_handoff_metadata = linked_handoffs[0][1] if linked_handoffs else {}
latest_review_path = latest_handoff_dir / "review.md" if latest_handoff_dir else None
latest_review_result = latest_handoff_metadata.get("current_state", "not found") if latest_handoff_metadata else "not found"
if latest_review_path and not latest_review_path.is_file():
    latest_review_path = None

if state.get("validation_result") == "FAIL" or latest_validation_result == "FAIL":
    blockers = "- Latest validation failed."
elif latest_review_result == "REVIEW_NEEDS_ATTENTION":
    blockers = "- Latest handoff review needs attention."
else:
    blockers = "- none currently recorded"

if latest_validation_result == "PASS" and latest_review_result == "REVIEW_ACCEPTED":
    next_action = "Ready for next supervised implementation phase"
elif latest_validation_result == "FAIL":
    next_action = "Resolve validation blockers before any next phase."
elif latest_review_result == "REVIEW_NEEDS_ATTENTION":
    next_action = "Inspect the latest handoff review before any next phase."
else:
    next_action = "Continue local inspection; no execution path is enabled."

timeline = "\n".join(f"- {event}" for event in loop_events(loop_text)) or "- no loop events found"

report = f"""# Feature Final Report

- Generated At: {report_stamp}
- Feature ID: {state.get("feature_id", "unknown")}
- Title: {state.get("title", "unknown")}
- Project: {state.get("project_key", "unknown")}
- Current State: {state.get("current_state", "unknown")}
- Source Task: {state.get("source_task", "unknown")}
- Provider Invocation: {str(state.get("provider_invocation", False)).lower()}
- Browser Automation: {str(state.get("browser_automation", False)).lower()}

## Feature Summary

{objective}

## Acceptance Criteria

{acceptance}

## Allowed Files

{allowed}

## Latest Plan Summary

{summarize_plan(plan_text)}

## Latest Validation

- Result: {latest_validation_result}
- Evidence: {latest_validation or "not found"}

## Latest Handoff And Review

- Handoff: {latest_handoff_dir or "not found"}
- Handoff State: {latest_handoff_metadata.get("current_state", "not found") if latest_handoff_metadata else "not found"}
- Review Result: {latest_review_result}
- Review Evidence: {latest_review_path or "not found"}

## Evidence Paths

- Feature Contract: {contract_path}
- Current Plan: {plan_path}
- Latest Validation Evidence: {latest_validation or "not found"}
- Latest Handoff Metadata: {(latest_handoff_dir / "metadata.json") if latest_handoff_dir else "not found"}
- Latest Handoff Review: {latest_review_path or "not found"}
- Loop Log: {loop_log_path}

## Loop Timeline Summary

{timeline}

## Current Blockers

{blockers}

## Recommended Next Safe Action

{next_action}

## Safety Statement

- Local report generation only.
- No provider, browser automation, CLI execution, apply path, agent run, or worktree execution was invoked.
"""

final_report_path.write_text(report, encoding="utf-8", newline="\n")

with loop_log_path.open("a", encoding="utf-8", newline="\n") as handle:
    handle.write(
        f"\n## {report_stamp} - Feature Report Generated\n"
        "- Actor: local\n"
        f"- State: {state.get('current_state', 'unknown')}\n"
        f"- Report: {final_report_path}\n"
        f"- Recommended next safe action: {next_action}\n"
    )

print(final_report_path)
print(state.get("current_state", "unknown"))
print(latest_validation_result)
print(latest_review_result)
print(next_action)
PY
)

mapfile -t REPORT_FIELDS <<< "$REPORT_INFO"
REPORT_PATH=${REPORT_FIELDS[0]:-}
FEATURE_STATE=${REPORT_FIELDS[1]:-unknown}
VALIDATION_RESULT=${REPORT_FIELDS[2]:-unknown}
REVIEW_RESULT=${REPORT_FIELDS[3]:-unknown}
NEXT_ACTION=${REPORT_FIELDS[4]:-}

echo "Feature report generated: $(to_windows_path "$REPORT_PATH")"
echo "Feature state: $FEATURE_STATE"
echo "Latest validation result: $VALIDATION_RESULT"
echo "Latest review result: $REVIEW_RESULT"
echo "Next safe action: $NEXT_ACTION"

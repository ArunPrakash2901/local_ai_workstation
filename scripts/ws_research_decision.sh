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

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        *)
            if [ -z "$STRONGHOLD_INPUT" ] || [[ "$1" != --* ]]; then
                STRONGHOLD_INPUT="$1"
            fi
            shift
            ;;
    esac
done

if [ -z "$STRONGHOLD_INPUT" ]; then
    echo "Usage: ws research-decision <stronghold_id_or_path>"
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

# Use Python for logic
RESULT_JSON=$( "$PYTHON" - "$STRONGHOLD_DIR" "$NOW_TS" << 'PY'
import sys
import json
import re
from pathlib import Path

stronghold_dir = Path(sys.argv[1])
now_ts = sys.argv[2]

def to_win(p):
    try:
        import subprocess
        return subprocess.check_output(["wslpath", "-w", str(p)]).decode("utf-8").strip()
    except:
        return str(p)

def count_items(path, pattern):
    if not path.is_file():
        return 0
    content = path.read_text(encoding="utf-8")
    return len(re.findall(pattern, content, re.M))

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

# 1. Verify required artifacts
required_files = ["hypothesis_log.md", "evidence_matrix.md", "research_summary.md", "goals.md", "success_criteria.md"]
missing = [f for f in required_files if not (stronghold_dir / f).is_file()]
if missing:
    print(json.dumps({"error": f"Missing artifacts: {', '.join(missing)}", "classification": "RESEARCH_BLOCKED"}))
    sys.exit(0)

# 2. Check for source notes
papers_dir = stronghold_dir / "papers"
source_notes = list(papers_dir.glob("*_source_notes.md")) if papers_dir.is_dir() else []
if not source_notes:
    print(json.dumps({"error": "No source notes found in papers/", "classification": "NEEDS_MORE_SOURCES"}))
    sys.exit(0)

# 3. Analyze content for classification
num_sources = len(source_notes)
num_hypotheses = count_items(stronghold_dir / "hypothesis_log.md", r"### Candidate Hypotheses")
num_evidence = count_items(stronghold_dir / "evidence_matrix.md", r"^\|")
# Adjust evidence count if headers exist (usually 2 lines for header and separator)
if num_evidence >= 2:
    num_evidence -= 2

# Check for sample/demo content
has_sample = any("sample_source.txt" in f.read_text(encoding="utf-8") for f in source_notes)

# Classification Logic
classification = "NEEDS_MORE_SOURCES"
reason = ""

if num_sources >= 3 and num_hypotheses >= 2 and num_evidence >= 3:
    classification = "ENOUGH_FOR_SYNTHESIS"
    reason = f"Found {num_sources} sources, {num_hypotheses} hypotheses, and {num_evidence} evidence rows."
elif has_sample and num_sources == 1:
    classification = "NEEDS_MORE_SOURCES"
    reason = "Only one source found, and it appears to be a sample/demo."
elif num_sources < 3:
    classification = "NEEDS_MORE_SOURCES"
    reason = f"Insufficient sources ({num_sources}). Need at least 3 for synthesis."
elif num_evidence < 3:
    classification = "NEEDS_MORE_SOURCES"
    reason = f"Insufficient evidence ({num_evidence}). Need at least 3 entries."
else:
    classification = "NEEDS_HUMAN_REVIEW"
    reason = "Metadata thresholds met, but synthesis eligibility is unclear."

# 4. Generate report
reports_dir = stronghold_dir / "reports"
reports_dir.mkdir(parents=True, exist_ok=True)
report_path = reports_dir / f"research_decision_{now_ts}.md"

report_content = f"""# Research Decision: {state.get('title')}

- Timestamp: {now_ts}
- Classification: {classification}
- Reason: {reason}

## Metrics
- Sources Processed: {num_sources}
- Candidate Hypotheses: {num_hypotheses}
- Evidence Entries: {num_evidence}
- Sample Data Detected: {"Yes" if has_sample else "No"}

## Evidence Matrix Snapshot
{ (stronghold_dir / 'evidence_matrix.md').read_text(encoding='utf-8') }

## Next Safe Action
"""

if classification == "ENOUGH_FOR_SYNTHESIS":
    report_content += "Advance to Research Synthesis phase (Phase 7.4).\n"
elif classification == "NEEDS_MORE_SOURCES":
    report_content += "Gather and process more technical sources using `ws research-run`.\n"
elif classification == "NEEDS_HUMAN_REVIEW":
    report_content += "A human operator should review the evidence matrix and manually update the state if synthesis is ready.\n"
else:
    report_content += "Resolve missing artifacts or blocked state.\n"

report_path.write_text(report_content, encoding="utf-8", newline="\n")

# 5. Update state.json
state["last_research_decision_at"] = now_ts
state["last_research_decision"] = classification
state["provider_invocation"] = False
state["browser_automation"] = False
state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

# 6. Update loop_log.md
with (stronghold_dir / "loop_log.md").open("a", encoding="utf-8", newline="\n") as f:
    f.write(f"\n## {now_ts} - Research Decision Generated\n- Classification: {classification}\n- Report: reports/{report_path.name}\n")

print(json.dumps({
    "classification": classification,
    "stronghold_path": to_win(stronghold_dir),
    "report_path": to_win(report_path),
    "next_action": report_content.split("## Next Safe Action\n")[-1].strip()
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
    print(f\"Classification:  {data['classification']}\")
    print(f\"Stronghold:      {data['stronghold_path']}\")
    print(f\"Decision Report: {data['report_path']}\")
    print(f\"Next Action:     {data['next_action']}\")
except Exception as e:
    print(f\"Error parsing result: {e}\")
    sys.exit(1)
"

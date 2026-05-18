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
REVIEW_PAPER=0
DRY_RUN=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --review-paper)
            REVIEW_PAPER=1
            shift
            ;;
        --dry-run)
            DRY_RUN=1
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

if [ -z "$STRONGHOLD_INPUT" ]; then
    echo "Usage: ws research-run <stronghold_id_or_path> --review-paper --dry-run"
    exit 1
fi

if [ "$REVIEW_PAPER" -eq 0 ]; then
    echo "Error: --review-paper is mandatory in this MVP."
    exit 1
fi

if [ "$DRY_RUN" -eq 0 ]; then
    echo "Error: --dry-run is mandatory in this MVP."
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

# 0. Check core state
state_path = stronghold_dir / "state.json"
if not state_path.is_file():
    print(json.dumps({"error": f"Missing state.json in {stronghold_dir}", "classification": "RESEARCH_REVIEW_INVALID_STRONGHOLD"}))
    sys.exit(0)

state = json.loads(state_path.read_text(encoding="utf-8"))
stype = state.get("type", "")
if stype != "research":
    print(json.dumps({"error": f"Stronghold type must be 'research', found '{stype}'", "classification": "RESEARCH_REVIEW_INVALID_STRONGHOLD"}))
    sys.exit(0)

curr_state = state.get("current_state", "unknown")
# For Research MVP we allow initial planning states
allowed_states = ["CONTRACT_READY", "ARCHITECT_PLAN_IMPORTED", "LOCAL_CHECKLIST_READY", "RESEARCH_READY"]
if curr_state not in allowed_states and not curr_state.startswith("RESEARCH_"):
    print(json.dumps({"error": f"Stronghold is in state '{curr_state}'.", "classification": "RESEARCH_REVIEW_BLOCKED"}))
    sys.exit(0)

# 1. Read/Validate required artifacts
required_files = [
    "contract.md", "goals.md", "constraints.md", "success_criteria.md",
    "literature_map.md", "hypothesis_log.md", "evidence_matrix.md", "research_summary.md"
]
optional_files = ["architect_plan.md", "local_checklist.md", "final_report.md"]

artifact_status = {}
for f in required_files:
    path = stronghold_dir / f
    artifact_status[f] = path.is_file()

for f in optional_files:
    path = stronghold_dir / f
    artifact_status[f] = path.is_file()

# 2. Initialize placeholders if missing or empty
def init_file(path, content):
    if not path.is_file() or path.stat().st_size == 0:
        path.write_text(content, encoding="utf-8", newline="\n")
    else:
        existing = path.read_text(encoding="utf-8")
        if "# " not in existing:
             with path.open("a", encoding="utf-8", newline="\n") as f:
                 f.write("\n" + content)

init_file(stronghold_dir / "hypothesis_log.md", "# Hypothesis Log\n\n## Future Hypotheses\n- [ ] [Pending Hypothesis]\n")
init_file(stronghold_dir / "evidence_matrix.md", "# Evidence Matrix\n\n| Hypothesis ID | Source | Evidence Type | Detail | Confidence |\n| --- | --- | --- | --- | --- |\n")
init_file(stronghold_dir / "research_summary.md", "# Research Summary\n\n[Summary of research progress and findings]\n")
init_file(stronghold_dir / "literature_map.md", "# Literature Map\n\n| Source | Title | Key Theme | Relevance |\n| --- | --- | --- | --- |\n")

# Extra check for hypothesis log section
h_log_path = stronghold_dir / "hypothesis_log.md"
if "## Future Hypotheses" not in h_log_path.read_text(encoding="utf-8"):
    with h_log_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write("\n## Future Hypotheses\n- [ ] [Pending Hypothesis]\n")

# 3. Generate review plan
papers_dir = stronghold_dir / "papers"
papers_dir.mkdir(parents=True, exist_ok=True)
plan_path = papers_dir / f"{now_ts}_paper_review_plan.md"

title = state.get("title", "unknown")
sid = state.get("stronghold_id", "unknown")

# Try to extract research question from contract.md if not in state
research_q = state.get('research_question', '')
if not research_q and (stronghold_dir / "contract.md").is_file():
    contract_text = (stronghold_dir / "contract.md").read_text(encoding="utf-8")
    m = re.search(r"## Research Question\n(.*?)\n", contract_text, re.S)
    if m:
        research_q = m.group(1).strip()

if not research_q:
    research_q = "[Define research question in contract.md or intake]"

plan_content = f"""# Research Paper Review Plan: {title}

- Timestamp: {now_ts}
- Stronghold ID: {sid}
- Classification: RESEARCH_REVIEW_PLAN_READY

## Research Question
{research_q}

## Source/Paper Intake Checklist
- [ ] Source URL/Path verified
- [ ] Abstract reviewed
- [ ] Methodology section identified
- [ ] Results/Conclusion sections identified

## Sections to Extract
- Abstract/Summary
- Core Methodology
- Data Sources/Universe
- Key Findings/Claims
- Limitations/Risks

## Claim/Evidence/Speculation Separation Rules
- **Claim**: Direct statement by the author about the result or relationship.
- **Evidence**: Data points, charts, or statistical values supporting a claim.
- **Speculation**: Author's interpretations or future work ideas not directly proven in the paper.
- **Implementation Idea**: How this could be applied to our workstation/agent patterns.

## Hypothesis Extraction Template
```markdown
### Hypothesis [ID]
- **Description**: [Falsifiable statement]
- **Source Context**: [Where in the paper this came from]
- **Initial Confidence**: [Low/Med/High]
```

## Evidence Matrix Update Template
`| [Hypothesis ID] | [Source Ref] | [Supporting/Refuting] | [Data Point] | [High/Med/Low] |`

## Anti-Hallucination Rules
- DO NOT summarize sections you have not parsed.
- USE direct quotes for key technical definitions.
- FLAG sections with ambiguous language.
- RECORD exact page/paragraph numbers if available.

## Human Role
- Provide the paper content (or URL if using a web-aware agent later).
- Review extracted hypotheses for logical coherence.
- Approve matrix updates.

## Local Research Intern Role (Later Phase)
- Parse provided source text.
- Extract claims and evidence according to these rules.
- Draft updates for `hypothesis_log.md`.

## Next Safe Action
Begin source review based on this plan.
"""
plan_path.write_text(plan_content, encoding="utf-8", newline="\n")

# 4. Update logs
with (stronghold_dir / "loop_log.md").open("a", encoding="utf-8", newline="\n") as f:
    f.write(f"\n## {now_ts} - Research Paper Review Dry-Run Generated\n- Actor: local\n- Plan: papers/{plan_path.name}\n")

# 5. Update state.json
state["last_research_review_plan_at"] = now_ts
state["last_research_review_plan_path"] = str(plan_path)
state["provider_invocation"] = False
state["browser_automation"] = False
state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

print(json.dumps({
    "classification": "RESEARCH_REVIEW_PLAN_READY",
    "stronghold_path": to_win(stronghold_dir),
    "plan_path": to_win(plan_path),
    "next_action": "Review the paper review plan and begin manual analysis."
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
    print(f\"Review Plan:     {data['plan_path']}\")
    print(f\"Next Action:     {data['next_action']}\")
except Exception as e:
    print(f\"Error parsing result: {e}\")
    sys.exit(1)
"

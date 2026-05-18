#!/bin/bash

set -euo pipefail

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
STRONGHOLDS_DIR="$WS_HOME/strongholds"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"
OLLAMA_CALL_PY="$WS_HOME/scripts/ollama_call.py"

STRONGHOLD_INPUT=""
REVIEW_PAPER=0
DRY_RUN=0
MODEL=""
SOURCE_TEXT=""
FROM_PLAN=""

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
        --model)
            MODEL="$2"
            shift 2
            ;;
        --source-text)
            SOURCE_TEXT="$2"
            shift 2
            ;;
        --from-plan)
            FROM_PLAN="$2"
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

if [ -z "$STRONGHOLD_INPUT" ]; then
    echo "Usage: ws research-run <stronghold_id_or_path> --review-paper [--dry-run | --model <m> --source-text <f> --from-plan <p>]"
    exit 1
fi

if [ "$REVIEW_PAPER" -eq 0 ]; then
    echo "Error: --review-paper is mandatory."
    exit 1
fi

# Validation of combinations
if [ "$DRY_RUN" -eq 1 ]; then
    if [ -n "$MODEL" ] || [ -n "$SOURCE_TEXT" ] || [ -n "$FROM_PLAN" ]; then
        echo "Error: Cannot combine --dry-run with --model, --source-text, or --from-plan."
        exit 1
    fi
else
    if [ -z "$MODEL" ] || [ -z "$SOURCE_TEXT" ] || [ -z "$FROM_PLAN" ]; then
        echo "Error: Must specify either --dry-run or all of (--model, --source-text, --from-plan)."
        exit 1
    fi
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

if [ "$DRY_RUN" -eq 0 ]; then
    # Check Ollama
    if ! curl -s -f "http://localhost:11434/api/tags" > /dev/null; then
        echo "Error: Ollama is not reachable at localhost:11434. (RESEARCH_SOURCE_NOTES_REQUIRES_OLLAMA)"
        exit 1
    fi

    # Check model
    if ! curl -s "http://localhost:11434/api/tags" | grep -q "\"$MODEL\""; then
        echo "Error: Model '$MODEL' is not available in Ollama. (RESEARCH_SOURCE_NOTES_REQUIRES_MODEL)"
        exit 1
    fi
fi

NOW_TS=$(date +"%Y%m%d_%H%M%S")
SOURCE_TEXT_WSL=""
[ -n "$SOURCE_TEXT" ] && SOURCE_TEXT_WSL=$(to_wsl_path "$SOURCE_TEXT")
FROM_PLAN_WSL=""
[ -n "$FROM_PLAN" ] && FROM_PLAN_WSL=$(to_wsl_path "$FROM_PLAN")

# Use Python for logic
RESULT_JSON=$( "$PYTHON" - "$STRONGHOLD_DIR" "$NOW_TS" "$DRY_RUN" "$MODEL" "$SOURCE_TEXT_WSL" "$FROM_PLAN_WSL" "$OLLAMA_CALL_PY" << 'PY'
import sys
import json
import re
import subprocess
from pathlib import Path

stronghold_dir = Path(sys.argv[1])
now_ts = sys.argv[2]
is_dry_run = sys.argv[3] == "1"
model = sys.argv[4]
source_text_path = Path(sys.argv[5]) if sys.argv[5] else None
from_plan_path = Path(sys.argv[6]) if sys.argv[6] else None
ollama_call_script = sys.argv[7]

def to_win(p):
    try:
        return subprocess.check_output(["wslpath", "-w", str(p)]).decode("utf-8").strip()
    except:
        return str(p)

def get_content(filename):
    p = stronghold_dir / filename
    if p.is_file():
        return p.read_text(encoding="utf-8").strip()
    return "[Artifact not found]"

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

# 1. Initialize placeholders if missing or empty
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

if is_dry_run:
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
    sys.exit(0)

# --------------------------------------------------------------------------
# Model source notes mode
# --------------------------------------------------------------------------
if not source_text_path or not source_text_path.is_file():
    print(json.dumps({"error": f"Source text not found: {source_text_path}", "classification": "RESEARCH_SOURCE_NOTES_REQUIRES_SOURCE"}))
    sys.exit(0)

if not from_plan_path or not from_plan_path.is_file():
    print(json.dumps({"error": f"Paper review plan not found: {from_plan_path}", "classification": "RESEARCH_SOURCE_NOTES_REQUIRES_PLAN"}))
    sys.exit(0)

source_text = source_text_path.read_text(encoding="utf-8")
plan_text = from_plan_path.read_text(encoding="utf-8")
goals = get_content("goals.md")
success = get_content("success_criteria.md")
h_log = get_content("hypothesis_log.md")
e_matrix = get_content("evidence_matrix.md")

system_prompt = """You are a meticulous local Research Intern for an AI Workstation operator.
Your task is to analyze the provided source text and generate structured source notes based on the current paper review plan and stronghold goals.

Rules:
1. Ground every claim and piece of evidence directly in the source text.
2. Clearly distinguish between:
   - **Source-Grounded Claims**: Direct results or findings stated in the text.
   - **Evidence**: Data points, charts, or quotes supporting those claims.
   - **Hypotheses/Speculation**: Ideas suggested by the text or the author's own interpretations.
   - **Implementation Ideas**: How these findings could be applied to workstation or agent patterns.
3. Identify gaps or questions raised by the source.
4. Suggest updates for the evidence matrix and hypothesis log.
5. Do NOT hallucinate. If the information is not in the text, say so.
6. Use page or section numbers if available in the text.
7. Be concise, technical, and analytical.
"""

user_prompt = f"""Analyze the following source text according to the Research Paper Review Plan.

### Research Paper Review Plan
{plan_text}

### Stronghold Context
- Goals: {goals}
- Success Criteria: {success}
- Current Hypothesis Log: {h_log}
- Current Evidence Matrix: {e_matrix}

### Source Text
{source_text}

### Requested Output Structure
1. **Source Summary**: (One paragraph)
2. **Key Claims**: (List with grounding)
3. **Evidence Excerpts**: (Specific quotes or paraphrases)
4. **Candidate Hypotheses**: (Extracted or suggested by source)
5. **Speculation**: (Clearly separated author or intern speculation)
6. **Implementation Ideas**: (How this applies to our patterns)
7. **Questions & Gaps**: (What is missing or unclear)
8. **Suggested Evidence Matrix Updates**: (Markdown table rows)
"""

# Call Ollama via temporary files
evid_dir = stronghold_dir / "evidence"
evid_dir.mkdir(parents=True, exist_ok=True)
sys_p = evid_dir / f"local_research_{now_ts}_sys.txt"
usr_p = evid_dir / f"local_research_{now_ts}_user.txt"
sys_p.write_text(system_prompt, encoding="utf-8")
usr_p.write_text(user_prompt, encoding="utf-8")

try:
    res = subprocess.check_output([
        sys.executable, ollama_call_script,
        "http://localhost:11434", model,
        str(sys_p), str(usr_p)
    ], text=True).strip()
except subprocess.CalledProcessError as e:
    print(json.dumps({"error": f"Ollama call failed: {e.output}", "classification": "RESEARCH_SOURCE_NOTES_BLOCKED"}))
    sys.exit(0)

# Write outputs
papers_dir = stronghold_dir / "papers"
papers_dir.mkdir(parents=True, exist_ok=True)
notes_path = papers_dir / f"{now_ts}_source_notes.md"
notes_path.write_text(res, encoding="utf-8", newline="\n")

resp_dir = stronghold_dir / "responses"
resp_dir.mkdir(parents=True, exist_ok=True)
(resp_dir / f"local_research_notes_{now_ts}.md").write_text(res, encoding="utf-8", newline="\n")

evid_path = evid_dir / f"local_research_notes_{now_ts}.md"
evid_path.write_text(f"# Local Research Evidence\n- Model: {model}\n- Source: {source_text_path.name}\n\n## Response\n{res}", encoding="utf-8", newline="\n")

# Append to artifacts
# 1. Hypotheses
h_match = re.search(r"## Candidate Hypotheses\n(.*?)(?:\n##|$)", res, re.DOTALL | re.IGNORECASE)
if h_match:
    with (stronghold_dir / "hypothesis_log.md").open("a", encoding="utf-8", newline="\n") as f:
        f.write(f"\n### Candidate Hypotheses from {now_ts} ({source_text_path.name})\n")
        f.write(h_match.group(1).strip() + "\n")

# 2. Evidence Matrix
e_match = re.search(r"## Suggested Evidence Matrix Updates\n(.*?)(?:\n##|$)", res, re.DOTALL | re.IGNORECASE)
if e_match:
    rows = [l.strip() for l in e_match.group(1).strip().splitlines() if "|" in l and "---" not in l and "Hypothesis ID" not in l]
    if rows:
        with (stronghold_dir / "evidence_matrix.md").open("a", encoding="utf-8", newline="\n") as f:
            for r in rows:
                f.write(r + "\n")

# 3. Research Summary
s_match = re.search(r"## Source Summary\n(.*?)(?:\n##|$)", res, re.DOTALL | re.IGNORECASE)
if s_match:
    with (stronghold_dir / "research_summary.md").open("a", encoding="utf-8", newline="\n") as f:
        f.write(f"\n### {now_ts} - Source Review: {source_text_path.name}\n")
        f.write(s_match.group(1).strip() + "\n")

# Update logs
with (stronghold_dir / "loop_log.md").open("a", encoding="utf-8", newline="\n") as f:
    f.write(f"\n## {now_ts} - Local Research Source Notes Generated\n- Actor: {model}\n- Source: {source_text_path.name}\n- Notes: papers/{notes_path.name}\n")

# Update state.json
state["last_research_notes_at"] = now_ts
state["last_research_notes_path"] = str(notes_path)
state["research_model"] = model
state["provider_invocation"] = False
state["browser_automation"] = False
state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

print(json.dumps({
    "classification": "RESEARCH_SOURCE_NOTES_READY",
    "stronghold_path": to_win(stronghold_dir),
    "notes_path": to_win(notes_path),
    "next_action": "Review the source notes and update the literature map if needed."
}))

# Cleanup
sys_p.unlink()
usr_p.unlink()
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
        print(f\"Classification: {data.get('classification', 'BLOCKED')}\")
        sys.exit(1)
    print(f\"Classification:  {data.get('classification', 'unknown')}\")
    print(f\"Stronghold:      {data.get('stronghold_path', 'unknown')}\")
    print(f\"Source Notes:    {data.get('notes_path', 'unknown')}\")
    print(f\"Next Action:     {data.get('next_action', 'unknown')}\")
except Exception as e:
    print(f\"Error parsing result: {e}\")
    sys.exit(1)
"

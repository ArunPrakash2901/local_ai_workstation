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
MODEL="hermes3:8b"
REVIEW=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --model)
            MODEL="$2"
            shift 2
            ;;
        --review)
            REVIEW=1
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
    echo "Usage: ws learning-assess <stronghold_id_or_path> --model <model> [--review]"
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

    # Search in learning subfolder specifically
    mapfile -t matches < <(
        find "$STRONGHOLDS_DIR/learning" -mindepth 1 -maxdepth 1 -type d -name "$STRONGHOLD_INPUT" 2>/dev/null | sort
    )

    case "${#matches[@]}" in
        0)
            echo "Learning stronghold not found: $STRONGHOLD_INPUT" >&2
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

# Check Ollama
if ! curl -s -f "http://localhost:11434/api/tags" > /dev/null; then
    echo "Error: Ollama is not reachable at localhost:11434. (LEARNING_ASSESSMENT_REQUIRES_OLLAMA)"
    exit 1
fi

if ! curl -s "http://localhost:11434/api/tags" | grep -q "\"$MODEL\""; then
    echo "Error: Model '$MODEL' is not available in Ollama. (LEARNING_ASSESSMENT_REQUIRES_MODEL)"
    exit 1
fi

NOW_TS=$(date +"%Y%m%d_%H%M%S")

# Use Python for logic
RESULT_JSON=$( "$PYTHON" - "$STRONGHOLD_DIR" "$NOW_TS" "$MODEL" "$OLLAMA_CALL_PY" "$REVIEW" << 'PY'
import sys
import json
import re
import subprocess
from pathlib import Path

stronghold_dir = Path(sys.argv[1])
now_ts = sys.argv[2]
model = sys.argv[3]
ollama_call_script = sys.argv[4]
is_review = sys.argv[5] == "1"

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

state_path = stronghold_dir / "state.json"
if not state_path.is_file():
    print(json.dumps({"error": "Missing state.json", "classification": "LEARNING_ASSESSMENT_BLOCKED"}))
    sys.exit(0)

state = json.loads(state_path.read_text(encoding="utf-8"))
if state.get("type") != "learning":
    print(json.dumps({"error": "Not a learning stronghold", "classification": "LEARNING_ASSESSMENT_BLOCKED"}))
    sys.exit(0)

# Check requirements
if is_review:
    last_answers_path = state.get("last_learning_review_answers_path")
    cl_prefix = "LEARNING_REVIEW_ASSESSMENT"
    file_prefix = "review_assessment"
    log_msg = "Learning Review Assessment Generated"
    status_val = "review_assessed"
else:
    last_answers_path = state.get("last_learning_answers_path")
    cl_prefix = "LEARNING_ASSESSMENT"
    file_prefix = "assessment"
    log_msg = "Learning Assessment Generated"
    status_val = "assessed"

if not last_answers_path or not Path(last_answers_path).is_file():
    print(json.dumps({"error": f"Latest {'review ' if is_review else ''}answers not found", "classification": f"{cl_prefix}_REQUIRES_ANSWERS"}))
    sys.exit(0)

# Find latest tutor session
sessions_dir = stronghold_dir / "sessions"
if is_review:
    tutor_sessions = sorted(list(sessions_dir.glob("*_review_tutor_session.md")), reverse=True)
else:
    tutor_sessions = sorted(list(sessions_dir.glob("*_tutor_session.md")), reverse=True)

if not tutor_sessions:
    print(json.dumps({"error": f"Latest {'review ' if is_review else ''}tutor session not found", "classification": f"{cl_prefix}_BLOCKED"}))
    sys.exit(0)

tutor_session_path = tutor_sessions[0]
tutor_session = tutor_session_path.read_text(encoding="utf-8")

# Timestamp alignment check
answers_mtime = Path(last_answers_path).stat().st_mtime
tutor_mtime = tutor_session_path.stat().st_mtime

if answers_mtime < tutor_mtime:
    print(json.dumps({
        "error": f"Latest {'review ' if is_review else ''}answers are older than latest tutor session. (Contamination Risk)",
        "classification": f"{cl_prefix}_REQUIRES_CURRENT_ANSWERS",
        "tutor_session_path": to_win(tutor_session_path),
        "answers_path": to_win(last_answers_path)
    }))
    sys.exit(0)

human_answers = Path(last_answers_path).read_text(encoding="utf-8")

contract = get_content("contract.md")
goals = get_content("goals.md")
constraints = get_content("constraints.md")
success = get_content("success_criteria.md")
syllabus = get_content("syllabus.md")
skill_map = get_content("skill_map.md")
practice_log = get_content("practice_log.md")
assessment_history = get_content("assessment.md")
architect_plan = get_content("architect_plan.md")
local_checklist = get_content("local_checklist.md")

if is_review:
    system_prompt = """You are an expert technical tutor and targeted review assessor for an AI Workstation operator.
Your goal is to evaluate the human operator's remediated answers from a review session.

Assess whether the previously identified gaps and misconceptions have been successfully addressed.
Provide:
1. A qualitative rating or score (e.g. 1-10 or Pass/Needs Further Review).
2. Explicit confirmation on whether prior gaps were fixed.
3. Any remaining gaps or new misconceptions detected.
4. Recommended next practice or study task.
5. A definitive recommendation: ADVANCE to next task, REVIEW specific topics, or REPEAT review session.

Be supportive but rigorous. Focus on evidence of mastery for the specific gaps."""
    
    last_assessment_path = state.get("last_learning_assessment_path")
    last_assessment = get_content(Path(last_assessment_path).name) if last_assessment_path else "Not found"
    
    user_prompt = f"""Assess the following human review answers.

### Review Tutor Session Context
{tutor_session}

### Human Review Answers
{human_answers}

### Previous Assessment (Gaps identified here)
{last_assessment}

### Stronghold Context
- Goals: {goals}
- Syllabus: {syllabus}
- Skill Map: {skill_map}

Please provide your evaluation of the review session."""
else:
    system_prompt = """You are an expert technical tutor and assessor for an AI Workstation operator.
Your goal is to evaluate the human operator's answers from a learning session.

Assess the answers against the provided tutor session, goals, and syllabus.
Provide:
1. A qualitative rating or score (e.g. 1-10 or Pass/Needs Review).
2. What was correct and demonstrated understanding.
3. Specific areas for improvement or missing details.
4. Any misconceptions detected.
5. Recommended next practice or study task.
6. A definitive recommendation: REPEAT session, REVIEW specific topics, or ADVANCE to next task.

Be supportive but rigorous. Do NOT automatically mark everything as perfect."""

    user_prompt = f"""Assess the following human answers from a learning session.

### Tutor Session Context
{tutor_session}

### Human Answers
{human_answers}

### Stronghold Context
- Goals: {goals}
- Syllabus: {syllabus}
- Skill Map: {skill_map}
- Master Plan: {architect_plan}

### Assessment History
{assessment_history[-2000:]}

Please provide your evaluation."""

# Call Ollama via temporary files
evid_dir = stronghold_dir / "evidence"
evid_dir.mkdir(parents=True, exist_ok=True)
sys_p = evid_dir / f"local_assessment_{now_ts}_sys.txt"
usr_p = evid_dir / f"local_assessment_{now_ts}_user.txt"
sys_p.write_text(system_prompt, encoding="utf-8")
usr_p.write_text(user_prompt, encoding="utf-8")

try:
    res = subprocess.check_output([
        sys.executable, ollama_call_script,
        "http://localhost:11434", model,
        str(sys_p), str(usr_p)
    ], text=True).strip()
except subprocess.CalledProcessError as e:
    print(json.dumps({"error": f"Ollama call failed: {e.output}", "classification": f"{cl_prefix}_BLOCKED"}))
    sys.exit(0)

# Write outputs
assessments_dir = stronghold_dir / "assessments"
assessments_dir.mkdir(parents=True, exist_ok=True)
assessment_path = assessments_dir / f"{file_prefix}_{now_ts}.md"
assessment_path.write_text(res, encoding="utf-8", newline="\n")

resp_dir = stronghold_dir / "responses"
resp_dir.mkdir(parents=True, exist_ok=True)
(resp_dir / f"local_{file_prefix}_{now_ts}.md").write_text(res, encoding="utf-8", newline="\n")

evid_path = evid_dir / f"local_{file_prefix}_{now_ts}.md"
evid_path.write_text(f"# Local {'Review ' if is_review else ''}Assessment Evidence\n- Model: {model}\n\n## Prompt\n{user_prompt}\n\n## Response\n{res}", encoding="utf-8", newline="\n")

# Extract next action recommendation
next_action_match = re.search(r"(?:REPEAT|REVIEW|ADVANCE).*", res, re.IGNORECASE)
recommended_next = next_action_match.group(0).strip() if next_action_match else "Manually review assessment for next steps."

# Append assessment.md
with (stronghold_dir / "assessment.md").open("a", encoding="utf-8", newline="\n") as f:
    f.write(f"\n## {now_ts} - {'Review ' if is_review else ''}Session Assessment\n- Result: {recommended_next}\n- Report: assessments/{assessment_path.name}\n")

# Append practice_log.md
with (stronghold_dir / "practice_log.md").open("a", encoding="utf-8", newline="\n") as f:
    f.write(f"\n## {now_ts} - {'Review ' if is_review else ''}Assessment Completed\n- Result: {recommended_next}\n- Path: assessments/{assessment_path.name}\n")

# Update loop_log.md
with (stronghold_dir / "loop_log.md").open("a", encoding="utf-8", newline="\n") as f:
    f.write(f"\n## {now_ts} - {log_msg}\n- Actor: {model}\n- Result: {recommended_next}\n- Path: assessments/{assessment_path.name}\n")

# Update state.json
if is_review:
    state["last_learning_review_assessment_at"] = now_ts
    state["last_learning_review_assessment_path"] = str(assessment_path)
    state["learning_review_assessment_model"] = model
else:
    state["last_learning_assessment_at"] = now_ts
    state["last_learning_assessment_path"] = str(assessment_path)
    state["learning_assessment_model"] = model

state["learning_session_status"] = status_val
state["provider_invocation"] = False
state["browser_automation"] = False
state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

print(json.dumps({
    "classification": f"{cl_prefix}_COMPLETED",
    "assessment_path": to_win(assessment_path),
    "recommended_next": recommended_next
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
        print(f\"Classification: {data['classification']}\")
        if 'tutor_session_path' in data:
            print(f\"Tutor Session:   {data['tutor_session_path']}\")
        if 'answers_path' in data:
            print(f\"Latest Answers:  {data['answers_path']}\")
        if data['classification'].endswith('REQUIRES_CURRENT_ANSWERS'):
            print(f\"Next Safe Action: ws learning-import-answers <stronghold> --from-file <answers_file>\")
        sys.exit(1)
    print(f\"Classification:   {data['classification']}\")
    print(f\"Assessment:       {data['assessment_path']}\")
    print(f\"Next Action:      {data['recommended_next']}\")
except Exception as e:
    print(f\"Error parsing result: {e}\")
    sys.exit(1)
"

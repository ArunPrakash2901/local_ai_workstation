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
SESSION=0
REVIEW_SESSION=0
DRY_RUN=0
MODEL=""
FROM_PLAN=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --session)
            SESSION=1
            shift
            ;;
        --review-session)
            REVIEW_SESSION=1
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
    echo "Usage: ws learning-run <stronghold_id_or_path> [--session | --review-session] [--dry-run | --model <m> --from-plan <f>]"
    exit 1
fi

if [ "$SESSION" -eq 0 ] && [ "$REVIEW_SESSION" -eq 0 ]; then
    echo "Error: Either --session or --review-session is mandatory."
    exit 1
fi

if [ "$SESSION" -eq 1 ] && [ "$REVIEW_SESSION" -eq 1 ]; then
    echo "Error: Cannot combine --session and --review-session."
    exit 1
fi

if [ "$DRY_RUN" -eq 1 ] && [ -n "$MODEL" ]; then
    echo "Error: Cannot combine --dry-run and --model."
    exit 1
fi

if [ "$DRY_RUN" -eq 0 ]; then
    if [ -z "$MODEL" ] || [ -z "$FROM_PLAN" ]; then
        echo "Error: Must specify either --dry-run or both --model and --from-plan."
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

STRONGHOLD_DIR=$(resolve_stronghold_dir) || {
    echo "Error: Target is not a learning stronghold or not found."
    exit 1
}

if [ "$DRY_RUN" -eq 0 ]; then
    # Check Ollama
    if ! curl -s -f "http://localhost:11434/api/tags" > /dev/null; then
        echo "Error: Ollama is not reachable at localhost:11434. (LEARNING_TUTOR_REQUIRES_OLLAMA)"
        exit 1
    fi

    # Check model
    if ! curl -s "http://localhost:11434/api/tags" | grep -q "\"$MODEL\""; then
        echo "Error: Model '$MODEL' is not available in Ollama. (LEARNING_TUTOR_REQUIRES_MODEL)"
        exit 1
    fi
fi

NOW_TS=$(date +"%Y%m%d_%H%M%S")
FROM_PLAN_WSL=""
[ -n "$FROM_PLAN" ] && FROM_PLAN_WSL=$(to_wsl_path "$FROM_PLAN")

# Use Python for logic
RESULT_JSON=$( "$PYTHON" - "$STRONGHOLD_DIR" "$NOW_TS" "$DRY_RUN" "$MODEL" "$FROM_PLAN_WSL" "$OLLAMA_CALL_PY" "$SESSION" "$REVIEW_SESSION" << 'PY'
import sys
import json
import re
import subprocess
from pathlib import Path

stronghold_dir = Path(sys.argv[1])
now_ts = sys.argv[2]
is_dry_run = sys.argv[3] == "1"
model = sys.argv[4]
from_plan_path = Path(sys.argv[5]) if sys.argv[5] else None
ollama_call_script = sys.argv[6]
is_normal_session = sys.argv[7] == "1"
is_review_session = sys.argv[8] == "1"

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
    print(json.dumps({"error": f"Missing state.json in {stronghold_dir}", "classification": "LEARNING_SESSION_INVALID_STRONGHOLD"}))
    sys.exit(0)

state = json.loads(state_path.read_text(encoding="utf-8"))
stype = state.get("type", "")
if stype != "learning":
    print(json.dumps({"error": f"Stronghold type must be 'learning', found '{stype}'", "classification": "LEARNING_SESSION_INVALID_STRONGHOLD"}))
    sys.exit(0)

curr_state = state.get("current_state", "unknown")
# For MVP we allow a few ready states
allowed_states = ["LOCAL_CHECKLIST_READY", "ARCHITECT_PLAN_IMPORTED", "READY_FOR_LOCAL_WORK"]
if curr_state not in allowed_states:
    print(json.dumps({"error": f"Stronghold is in state '{curr_state}'. Must be one of: {', '.join(allowed_states)}", "classification": "LEARNING_SESSION_BLOCKED"}))
    sys.exit(0)

checklist_path = stronghold_dir / "local_checklist.md"
if not checklist_path.is_file() or checklist_path.stat().st_size == 0:
    print(json.dumps({"error": "Missing or empty local_checklist.md", "classification": "LEARNING_SESSION_BLOCKED"}))
    sys.exit(0)

if is_dry_run:
    # Identify next task (Progress Aware)
    # 1. Prefer state.json next_learning_task
    next_task = state.get("next_learning_task")
    
    # 2. Check progress.md for completed tasks
    progress_path = stronghold_dir / "progress.md"
    completed_tasks = set()
    if progress_path.is_file():
        prog_text = progress_path.read_text(encoding="utf-8")
        for line in prog_text.splitlines():
            if line.startswith("- Completed:"):
                completed_tasks.add(line.split(":", 1)[-1].strip())

    # 3. Fallback to checklist if next_task is missing or already done
    if not next_task or next_task in completed_tasks:
        checklist_text = checklist_path.read_text(encoding="utf-8")
        matches = re.findall(r"(?:-|\d+\.)\s*\[\s*\]\s*(.+)", checklist_text)
        found = False
        for m in matches:
            t = m.strip()
            if t not in completed_tasks:
                next_task = t
                found = True
                break
        if not found and not next_task:
            next_task = "No pending tasks found in checklist."

    # Generate session plan
    sessions_dir = stronghold_dir / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    plan_path = sessions_dir / f"{now_ts}_session_plan.md"

    plan_content = f"""# Learning Session Plan: {state.get('title')}

- Timestamp: {now_ts}
- Stronghold ID: {state.get('stronghold_id')}
- Classification: LEARNING_SESSION_DRY_READY

## Session Objective
Implement or study the next tactical task:
> {next_task}

## Prerequisites
- Review `contract.md`
- Review `architect_plan.md`
- Ensure local model `hermes3:8b` is warm (if applicable)

## Topics to Study
- Refer to `syllabus.md` for relevant sections.

## Practice Exercises
- [Draft 1]: Verbal explanation of the concept.
- [Draft 2]: Minimal code reproduction or diagram.

## Self-Assessment Questions
1. How does this task align with the primary goal?
2. What are the key risks identified by the architect for this phase?

## Estimated Time Blocks
- Prep: 10m
- Active Study/Practice: 40m
- Assessment: 10m

## Human Role
- Actively engage with the material.
- Complete the exercises in `intake_response.md` or a new session file.
- Log progress in `practice_log.md`.

## Local Tutor Role (Later Phase)
- Provide clarifications.
- Evaluate exercise results.
- Update `skill_map.md`.

## Next Safe Action
Run the actual session once implemented, or begin manual study based on this plan.
"""
    plan_path.write_text(plan_content, encoding="utf-8", newline="\n")

    # Update logs
    with (stronghold_dir / "practice_log.md").open("a", encoding="utf-8", newline="\n") as f:
        f.write(f"\n## {now_ts} - Planned Session\n- Focus: {next_task}\n- Plan: sessions/{plan_path.name}\n")
    with (stronghold_dir / "loop_log.md").open("a", encoding="utf-8", newline="\n") as f:
        f.write(f"\n## {now_ts} - Learning Session Dry-Run Generated\n- Actor: local\n- State: {curr_state}\n- Plan: sessions/{plan_path.name}\n")

    state["last_learning_session_plan_at"] = now_ts
    state["last_learning_session_plan_path"] = str(plan_path)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    print(json.dumps({
        "classification": "LEARNING_SESSION_DRY_READY",
        "stronghold_path": to_win(stronghold_dir),
        "plan_path": to_win(plan_path),
        "next_action": "Review the session plan and begin manual study."
    }))
    sys.exit(0)

# Model session mode
if not from_plan_path or not from_plan_path.is_file():
    cl = "LEARNING_TUTOR_REQUIRES_PLAN" if is_normal_session else "LEARNING_REVIEW_TUTOR_REQUIRES_PLAN"
    print(json.dumps({"error": f"Session plan not found: {from_plan_path}", "classification": cl}))
    sys.exit(0)

plan_text = from_plan_path.read_text(encoding="utf-8")
contract = get_content("contract.md")
goals = get_content("goals.md")
constraints = get_content("constraints.md")
success = get_content("success_criteria.md")
syllabus = get_content("syllabus.md")
skill_map = get_content("skill_map.md")
practice_log = get_content("practice_log.md")
assessment = get_content("assessment.md")
architect_plan = get_content("architect_plan.md")
local_checklist = get_content("local_checklist.md")

if is_normal_session:
    system_prompt = """You are a supportive and technical local tutor (Intern level) for an AI Workstation operator.
Your goal is to guide the user through a specific learning session defined in their plan.

Provide:
1. A clear, technical explanation of the topic.
2. A worked example or case study.
3. 2-3 specific practice exercises for the user to complete.
4. 3 self-assessment questions to check understanding.
5. A Markdown Answer Template for the user to use.
6. Instructions on what the human should do next.

Stay within the provided context. Do NOT suggest live trading or capital deployment.
Act as an assistant, not an architect. Focus on implementation and understanding.
"""
    cl_prefix = "LEARNING_TUTOR"
    session_suffix = "tutor_session"
    template_suffix = "answer_template"
    log_msg = "Local Tutor Session Generated"
else:
    # Review session
    last_decision = state.get("last_learning_decision")
    if last_decision not in ["REVIEW_CURRENT_TASK", "REPEAT_SESSION"]:
        print(json.dumps({
            "error": f"Stronghold decision is '{last_decision}'. Review session not required.",
            "classification": "LEARNING_REVIEW_TUTOR_REQUIRES_DECISION"
        }))
        sys.exit(0)

    last_assessment_path = state.get("last_learning_assessment_path")
    last_assessment = get_content(Path(last_assessment_path).name) if last_assessment_path else "Not found"

    system_prompt = """You are a supportive and targeted local review tutor for an AI Workstation operator.
Your goal is to help the user address specific gaps identified in their previous assessment.

Provide:
1. A focused explanation for each identified gap or misconception.
2. Corrected worked examples addressing the failed areas.
3. Targeted practice exercises specifically designed to demonstrate mastery of the gaps.
4. 3 self-assessment questions to verify the gaps are closed.
5. A Markdown Answer Template for the user to use.
6. Instructions on what the human should do next to advance.

Stay within the provided context. Do NOT suggest live trading or capital deployment.
Act as a review assistant. Focus on remediation and mastery.
"""
    cl_prefix = "LEARNING_REVIEW_TUTOR"
    session_suffix = "review_tutor_session"
    template_suffix = "review_answer_template"
    log_msg = "Local Review Tutor Session Generated"

user_prompt = f"""Conduct a {'review ' if is_review_session else ''}learning session based on the following plan.

### {'Review ' if is_review_session else ''}Session Plan
{plan_text}

### Stronghold Context
- Title: {state.get('title')}
- Contract: {contract}
- Goals: {goals}
- Constraints: {constraints}
- Syllabus: {syllabus}
- Skill Map: {skill_map}
- Master Plan (Architect): {architect_plan}
"""

if is_review_session:
    user_prompt += f"\n### Latest Assessment\n{last_assessment}\n"

user_prompt += f"\n### History\n{practice_log[-2000:]}\n\nPlease generate the tutor session content."

# Call Ollama via temporary files
evid_dir = stronghold_dir / "evidence"
evid_dir.mkdir(parents=True, exist_ok=True)
sys_p = evid_dir / f"local_tutor_{now_ts}_sys.txt"
usr_p = evid_dir / f"local_tutor_{now_ts}_user.txt"
sys_p.write_text(system_prompt, encoding="utf-8")
usr_p.write_text(user_prompt, encoding="utf-8")

try:
    res = subprocess.check_output([
        sys.executable, ollama_call_script,
        "http://localhost:11434", model,
        str(sys_p), str(usr_p)
    ], text=True).strip()
except subprocess.CalledProcessError as e:
    print(json.dumps({"error": f"Ollama call failed: {e.output}", "classification": f"{cl_prefix}_SESSION_BLOCKED"}))
    sys.exit(0)

# Write outputs
sessions_dir = stronghold_dir / "sessions"
tutor_session_path = sessions_dir / f"{now_ts}_{session_suffix}.md"
tutor_session_path.write_text(res, encoding="utf-8", newline="\n")

# Extract answer template
answer_template = "# Answer Template\n\n[Paste tutor session exercises here and provide answers]"
template_match = re.search(r"## Answer Template\n(.*?)(?:\n##|$)", res, re.DOTALL | re.IGNORECASE)
if template_match:
    answer_template = f"# Answer Template: {now_ts}\n\n{template_match.group(1).strip()}"

template_path = sessions_dir / f"{now_ts}_{template_suffix}.md"
template_path.write_text(answer_template, encoding="utf-8", newline="\n")

# Responses and evidence
resp_dir = stronghold_dir / "responses"
resp_dir.mkdir(parents=True, exist_ok=True)
(resp_dir / f"local_{session_suffix}_{now_ts}.md").write_text(res, encoding="utf-8", newline="\n")

evid_path = evid_dir / f"local_{session_suffix}_{now_ts}.md"
evid_path.write_text(f"# Local Tutor Evidence\n- Model: {model}\n\n## Prompt\n{user_prompt}\n\n## Response\n{res}", encoding="utf-8", newline="\n")

# Update logs
with (stronghold_dir / "practice_log.md").open("a", encoding="utf-8", newline="\n") as f:
    f.write(f"\n## {now_ts} - {log_msg}\n- Model: {model}\n- Session: sessions/{tutor_session_path.name}\n- Status: awaiting human answers\n")
with (stronghold_dir / "loop_log.md").open("a", encoding="utf-8", newline="\n") as f:
    f.write(f"\n## {now_ts} - {log_msg}\n- Actor: {model}\n- Plan: {from_plan_path.name}\n- Session: sessions/{tutor_session_path.name}\n")

# Update state.json
if is_normal_session:
    state["last_tutor_session_at"] = now_ts
    state["last_tutor_session_path"] = str(tutor_session_path)
    state["tutor_model"] = model
    state["learning_session_status"] = "awaiting_human_answers"
else:
    state["last_review_tutor_session_at"] = now_ts
    state["last_review_tutor_session_path"] = str(tutor_session_path)
    state["review_tutor_model"] = model
    state["learning_session_status"] = "awaiting_review_answers"

state["provider_invocation"] = False
state["browser_automation"] = False
state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

print(json.dumps({
    "classification": f"{cl_prefix}_READY",
    "stronghold_path": to_win(stronghold_dir),
    "tutor_session_path": to_win(tutor_session_path),
    "answer_template_path": to_win(template_path),
    "next_action": "Complete the answer template based on the tutor session."
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
    
    if 'plan_path' in data:
        print(f\"Session Plan:    {data['plan_path']}\")
    if 'tutor_session_path' in data:
        print(f\"Tutor Session:   {data['tutor_session_path']}\")
    if 'answer_template_path' in data:
        print(f\"Answer Template: {data['answer_template_path']}\")
        
    print(f\"Next Action:     {data.get('next_action', 'unknown')}\")
except Exception as e:
    print(f\"Error parsing result: {e}\")
    sys.exit(1)
"

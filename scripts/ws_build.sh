#!/bin/bash
set -euo pipefail

PROJECT_KEY=${1:-}
TASK_FILE=${2:-}
shift 2 || true

if [ -z "$PROJECT_KEY" ] || [ -z "$TASK_FILE" ]; then
    echo "Usage: ws build <project_key> <task_file> [flags]"
    exit 1
fi

BASE="/mnt/d/_ai_brain"
SCRIPTS="$BASE/scripts"
BUILD_RUNS="$BASE/build_runs"
TASKS_DIR="$BASE/tasks"
PYTHON="$BASE/runtimes/workstation_venv/bin/python3"
PROJECTS_YAML="$BASE/registry/projects.yaml"
ACTIVE_MODEL_YAML="$BASE/registry/active_model.yaml"
SYSTEM_PROMPT="$BASE/prompts/product_builder.md"

PLAN_ONLY=true
APPLY=false
BRANCH=false
MAX_TASKS=1
MAX_ATTEMPTS=3
MAX_FILES=5
MAX_MINUTES=60
ESCALATE="none"
STOP_ON_FAIL=false
TEST_OVERRIDE=""
DRY_RUN=false

while [ "$#" -gt 0 ]; do
    case "$1" in
        --plan-only) PLAN_ONLY=true; APPLY=false ;;
        --apply) APPLY=true; PLAN_ONLY=false ;;
        --branch) BRANCH=true ;;
        --max-tasks) MAX_TASKS="$2"; shift ;;
        --max-attempts) MAX_ATTEMPTS="$2"; shift ;;
        --max-files) MAX_FILES="$2"; shift ;;
        --max-minutes) MAX_MINUTES="$2"; shift ;;
        --escalate) ESCALATE="$2"; shift ;;
        --no-escalate) ESCALATE="none" ;;
        --stop-on-fail) STOP_ON_FAIL=true ;;
        --tests) TEST_OVERRIDE="$2"; shift ;;
        --dry-run) DRY_RUN=true ;;
        *) echo "Unknown build flag: $1"; exit 1 ;;
    esac
    shift
done

if [ "$ESCALATE" != "none" ] && [ "$ESCALATE" != "codex" ]; then
    echo "Only --escalate codex is supported. Gemini is manual packet review only for now."
    exit 1
fi

mkdir -p "$BUILD_RUNS" "$TASKS_DIR"
PARSED="$BUILD_RUNS/parsed_tasks_$(date +%Y%m%d_%H%M%S).json"
bash "$SCRIPTS/ws_task_parser.sh" "$TASK_FILE" "$PARSED" >/dev/null

PROJECT_DIR=$("$PYTHON" - "$PROJECT_KEY" "$PROJECTS_YAML" <<'PY'
import sys, yaml
project_key, projects_yaml = sys.argv[1:]
projects = yaml.safe_load(open(projects_yaml, encoding="utf-8"))["projects"]
p = projects.get(project_key)
if not p:
    print("")
    sys.exit(1)
print(p.get("wsl_path", ""))
PY
)

if [ -z "$PROJECT_DIR" ] || [ ! -d "$PROJECT_DIR" ]; then
    echo "Project path not found for $PROJECT_KEY"
    exit 1
fi

if [ "$APPLY" = true ] && ! git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Git is unavailable for $PROJECT_KEY. Refusing apply mode; rerun plan-only or initialize git explicitly."
    exit 1
fi

TASK_COUNT=$("$PYTHON" - "$PARSED" <<'PY'
import json, sys
print(len(json.load(open(sys.argv[1], encoding="utf-8"))["tasks"]))
PY
)
if [ "$MAX_TASKS" -gt "$TASK_COUNT" ]; then
    MAX_TASKS="$TASK_COUNT"
fi

echo "Build loop: project=$PROJECT_KEY mode=$([ "$APPLY" = true ] && echo apply || echo plan-only) max_tasks=$MAX_TASKS escalate=$ESCALATE"
if [ "$DRY_RUN" = true ]; then
    echo "Dry run: parsed $TASK_COUNT task(s); no run folders beyond parser output will be created."
    exit 0
fi

for ((idx=0; idx<MAX_TASKS; idx++)); do
    TASK_ID=$("$PYTHON" - "$PARSED" "$idx" <<'PY'
import json, re, sys
task = json.load(open(sys.argv[1], encoding="utf-8"))["tasks"][int(sys.argv[2])]
safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", task["id"]).strip("_")
print(safe or "task")
PY
)
    TS=$(date +%Y%m%d_%H%M%S)
    RUN_DIR="$BUILD_RUNS/${TS}_${PROJECT_KEY}_${TASK_ID}"
    mkdir -p "$RUN_DIR"
    echo "IN_PROGRESS" > "$RUN_DIR/status.txt"
    echo "# Attempts" > "$RUN_DIR/attempts.md"

    bash "$SCRIPTS/ws_context_pack.sh" "$PROJECT_KEY" "$PARSED" "$idx" "$RUN_DIR" >/dev/null

    TEST_COMMAND=$("$PYTHON" - "$PARSED" "$idx" "$TEST_OVERRIDE" <<'PY'
import json, sys
task = json.load(open(sys.argv[1], encoding="utf-8"))["tasks"][int(sys.argv[2])]
override = sys.argv[3]
print(override or task.get("test_command", ""))
PY
)
    "$PYTHON" - "$PARSED" "$idx" "$RUN_DIR/allowed_files.txt" <<'PY'
import json, sys
task = json.load(open(sys.argv[1], encoding="utf-8"))["tasks"][int(sys.argv[2])]
open(sys.argv[3], "w", encoding="utf-8").write("\n".join(task.get("allowed_files", [])) + "\n")
PY

    USER_PROMPT="$RUN_DIR/local_prompt.md"
    cat > "$USER_PROMPT" <<EOF
You are the local Hermes planning agent for a bounded engineering build loop.

Use the context pack below to produce a concise implementation plan.

Rules:
- Prefer plan-only guidance unless a unified diff is clearly safe.
- The build run folder already exists under D:\_ai_brain\build_runs; do not propose creating run folders inside the project.
- Focus the plan on satisfying the task acceptance criteria in the registered project.
- Do not touch secrets, raw data, generated dependency folders, graphify-out, models, archives, or project credentials.
- If apply mode is needed, include at most one fenced \`\`\`diff block and only for Allowed Files.
- Keep changed files under $MAX_FILES.
- If ambiguous, say BLOCKED and explain what needs clarification.

Context:

$(cat "$RUN_DIR/context_pack.md")
EOF

    MODEL=$("$PYTHON" - "$ACTIVE_MODEL_YAML" <<'PY'
import sys, yaml
active = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
print(active.get("active_model", "hermes3:8b"))
PY
)
    OLLAMA_HOST=${OLLAMA_HOST:-"http://localhost:11434"}
    timeout $((MAX_MINUTES * 60)) "$PYTHON" "$SCRIPTS/ollama_call.py" "$OLLAMA_HOST" "$MODEL" "$SYSTEM_PROMPT" "$USER_PROMPT" > "$RUN_DIR/local_plan.md" || {
        echo "BLOCKED: local Hermes planning failed or timed out." > "$RUN_DIR/status.txt"
        bash "$SCRIPTS/ws_build_report.sh" "$RUN_DIR" "BLOCKED" >/dev/null
        $STOP_ON_FAIL && exit 1 || continue
    }

    if [ "$PLAN_ONLY" = true ]; then
        echo "PLAN_ONLY" > "$RUN_DIR/status.txt"
        bash "$SCRIPTS/ws_build_report.sh" "$RUN_DIR" "PLAN_ONLY" >/dev/null
        echo "Plan-only run: $RUN_DIR"
        continue
    fi

    if [ "$BRANCH" = true ]; then
        BRANCH_NAME="ai-build/${PROJECT_KEY}/${TASK_ID}-${TS}"
        git -C "$PROJECT_DIR" switch -c "$BRANCH_NAME" >> "$RUN_DIR/attempts.md" 2>&1 || git -C "$PROJECT_DIR" switch "$BRANCH_NAME" >> "$RUN_DIR/attempts.md" 2>&1
    fi

    APPLIED=false
    for ((attempt=1; attempt<=MAX_ATTEMPTS; attempt++)); do
        echo "" >> "$RUN_DIR/attempts.md"
        echo "## Attempt $attempt" >> "$RUN_DIR/attempts.md"
        if ! "$PYTHON" - "$RUN_DIR/local_plan.md" "$RUN_DIR/proposed.patch" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8", errors="replace").read()
m = re.search(r"```(?:diff|patch)\s*\n(.*?)```", text, re.S)
if not m:
    sys.exit(1)
open(sys.argv[2], "w", encoding="utf-8", newline="\n").write(m.group(1).strip() + "\n")
PY
        then
            : > "$RUN_DIR/proposed.patch"
        fi
        if [ ! -s "$RUN_DIR/proposed.patch" ]; then
            echo "No machine-applicable unified diff found in local plan." >> "$RUN_DIR/attempts.md"
            break
        fi
        if ! bash "$SCRIPTS/ws_apply_guard.sh" "$PROJECT_DIR" "$RUN_DIR/proposed.patch" "$RUN_DIR/allowed_files.txt" "$MAX_FILES" >> "$RUN_DIR/attempts.md" 2>&1; then
            echo "Apply guard blocked proposed patch." >> "$RUN_DIR/attempts.md"
            break
        fi
        if ! git -C "$PROJECT_DIR" apply --check "$RUN_DIR/proposed.patch" >> "$RUN_DIR/attempts.md" 2>&1; then
            echo "Patch did not apply cleanly." >> "$RUN_DIR/attempts.md"
            break
        fi
        git -C "$PROJECT_DIR" apply "$RUN_DIR/proposed.patch"
        APPLIED=true
        if bash "$SCRIPTS/ws_test_runner.sh" "$PROJECT_DIR" "$RUN_DIR" "$TEST_COMMAND" "$MAX_MINUTES" >> "$RUN_DIR/attempts.md" 2>&1; then
            git -C "$PROJECT_DIR" diff > "$RUN_DIR/final_diff.patch"
            echo "COMPLETE" > "$RUN_DIR/status.txt"
            bash "$SCRIPTS/ws_build_report.sh" "$RUN_DIR" "COMPLETE" >/dev/null
            echo "Build run complete: $RUN_DIR"
            break
        fi
        echo "Tests failed after applied patch." >> "$RUN_DIR/attempts.md"
        break
    done

    if [ "$(cat "$RUN_DIR/status.txt")" != "COMPLETE" ]; then
        if [ "$ESCALATE" = "codex" ]; then
            cp "$RUN_DIR/context_pack.md" "$RUN_DIR/codex_packet.md"
            printf "\n## Local Plan\n\n" >> "$RUN_DIR/codex_packet.md"
            cat "$RUN_DIR/local_plan.md" >> "$RUN_DIR/codex_packet.md"
            printf "\n## Test Output\n\n" >> "$RUN_DIR/codex_packet.md"
            test -f "$RUN_DIR/test_output.md" && cat "$RUN_DIR/test_output.md" >> "$RUN_DIR/codex_packet.md" || true
            if bash "$SCRIPTS/ws_redact_packet.sh" "$RUN_DIR/codex_packet.md" | grep -qx "SAFE"; then
                bash "$SCRIPTS/ws_escalate.sh" codex "$RUN_DIR/codex_packet.md" >> "$RUN_DIR/attempts.md" 2>&1 || true
                latest_response=$(ls -t "$BASE/frontier/responses"/*codex* 2>/dev/null | head -n 1 || true)
                [ -n "$latest_response" ] && cp "$latest_response" "$RUN_DIR/codex_response.md"
            fi
        fi
        [ "$APPLIED" = true ] && git -C "$PROJECT_DIR" diff > "$RUN_DIR/final_diff.patch"
        echo "BLOCKED" > "$RUN_DIR/status.txt"
        bash "$SCRIPTS/ws_build_report.sh" "$RUN_DIR" "BLOCKED" >/dev/null
        echo "Build run blocked: $RUN_DIR"
        $STOP_ON_FAIL && exit 1
    fi
done

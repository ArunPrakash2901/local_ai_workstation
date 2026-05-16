#!/bin/bash

set -u

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
REPORTS_DIR="$WS_HOME/reports"
PROJECTS_YAML="$WS_HOME/registry/projects.yaml"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"
MAX_DRY_RUN_AGE_SECONDS=900

PROJECT_KEY=${1:-}
TASK_FILE=${2:-}

if [ -z "$PROJECT_KEY" ] || [ -z "$TASK_FILE" ]; then
    echo "Usage: ws worktree-create <project_key> <task_file> (--dry-run | --apply --from-report <report>)"
    exit 1
fi

shift 2
MODE=""
FROM_REPORT=""

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)
            if [ "$MODE" = "apply" ]; then
                MODE="conflict"
            else
                MODE="dry-run"
            fi
            shift
            ;;
        --apply)
            if [ "$MODE" = "dry-run" ]; then
                MODE="conflict"
            else
                MODE="apply"
            fi
            shift
            ;;
        --from-report)
            FROM_REPORT=${2:-}
            if [ -z "$FROM_REPORT" ]; then
                echo "Usage: ws worktree-create <project_key> <task_file> --apply --from-report <report>"
                exit 1
            fi
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

STAMP=$(date -u +%Y%m%d_%H%M%S)
REPORT_STAMP=$(date -u +%Y%m%d_%H%M%S_%N)
CLASSIFICATION="WORKTREE_CREATE_DRY_RUN_READY"
REASON="All dry-run worktree creation checks passed."

if [ "$MODE" = "apply" ]; then
    CLASSIFICATION="WORKTREE_CREATED"
    REASON="All supervised worktree creation checks passed."
fi

if [ "$MODE" = "apply" ]; then
    REPORT="$REPORTS_DIR/WORKTREE_CREATE_$REPORT_STAMP.md"
else
    REPORT="$REPORTS_DIR/WORKTREE_CREATE_DRY_RUN_$REPORT_STAMP.md"
fi

PROJECT_PATH=""
WSL_PROJECT_PATH=""
WSL_TASK_FILE=""
TASK_ID=""
TASK_TITLE=""
ALLOWED_FILES=()
CURRENT_BRANCH=""
REPO_STATUS="unknown"
WORKTREE_LIST=""
PROPOSED_WORKTREE_PATH_WSL=""
PROPOSED_WORKTREE_PATH_WINDOWS=""
PROPOSED_BRANCH=""
PATH_EXISTS="No"
BRANCH_EXISTS="No"
BRANCH_COMMAND=""
WORKTREE_COMMAND=""
BRANCH_COMMAND_OUTPUT=""
WORKTREE_COMMAND_OUTPUT=""
ROOT_CREATED="No"
ROLLBACK_PERFORMED="No"
ROLLBACK_REQUIRED="No"
SOURCE_REPORT=""
SOURCE_REPORT_WSL=""
SOURCE_REPORT_TIMESTAMP=""
SOURCE_REPORT_PROJECT=""
SOURCE_REPORT_TASK_FILE=""
SOURCE_REPORT_CLASSIFICATION=""
SOURCE_REPORT_BRANCH=""
SOURCE_REPORT_WORKTREE_PATH_WSL=""
SOURCE_REPORT_AGE_SECONDS=""

to_wsl_path() {
    case "$1" in
        /*) printf '%s' "$1" ;;
        *) wslpath -u "$1" 2>/dev/null || printf '%s' "$1" ;;
    esac
}

to_windows_path() {
    wslpath -w "$1" 2>/dev/null || printf '%s' "$1"
}

set_blocker() {
    if [ "$MODE" = "apply" ]; then
        if [ "$CLASSIFICATION" = "WORKTREE_CREATED" ]; then
            CLASSIFICATION="$1"
            REASON="$2"
        fi
    else
        if [ "$CLASSIFICATION" = "WORKTREE_CREATE_DRY_RUN_READY" ]; then
            CLASSIFICATION="$1"
            REASON="$2"
        fi
    fi
}

read_report_metadata() {
    "$PYTHON" - "$1" <<'PY'
import json
import re
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")

def one(pattern):
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1).strip() if match else ""

print(json.dumps({
    "timestamp": one(r"^- \*\*Timestamp\*\*: (.+)$"),
    "project": one(r"^- \*\*Project\*\*: (.+)$"),
    "task_file": one(r"^- \*\*Task File\*\*: (.+)$"),
    "classification": one(r"^- \*\*Classification\*\*: (.+)$"),
    "branch": one(r"^- Branch: (.+)$"),
    "worktree_path_wsl": one(r"^- Worktree path \(WSL\): (.+)$"),
}))
PY
}

if [ -z "$MODE" ] && [ -n "$FROM_REPORT" ]; then
    CLASSIFICATION="BLOCKED_REPORT_MISMATCH"
    REASON="--from-report requires --apply."
elif [ -z "$MODE" ]; then
    set_blocker "BLOCKED_MISSING_DRY_RUN" "Specify either --dry-run or --apply --from-report <report>."
elif [ "$MODE" = "conflict" ]; then
    CLASSIFICATION="BLOCKED_REPORT_MISMATCH"
    REASON="--dry-run and --apply cannot be combined."
elif [ "$MODE" = "dry-run" ] && [ -n "$FROM_REPORT" ]; then
    CLASSIFICATION="BLOCKED_REPORT_MISMATCH"
    REASON="--from-report requires --apply."
elif [ "$MODE" = "apply" ] && [ -z "$FROM_REPORT" ]; then
    set_blocker "BLOCKED_MISSING_FROM_REPORT" "--apply requires --from-report <dry_run_report>."
fi

PROJECT_PATH=$("$PYTHON" - "$PROJECTS_YAML" "$PROJECT_KEY" <<'PY'
import sys
import yaml

with open(sys.argv[1], "r", encoding="utf-8") as f:
    data = yaml.safe_load(f) or {}
project = (data.get("projects") or {}).get(sys.argv[2]) or data.get(sys.argv[2]) or {}
print(project.get("windows_path", ""))
PY
)

if [ -z "$PROJECT_PATH" ]; then
    set_blocker "BLOCKED_PROJECT_NOT_FOUND" "Project '$PROJECT_KEY' not found in registry."
else
    WSL_PROJECT_PATH=$(to_wsl_path "$PROJECT_PATH")
    if [ -z "$WSL_PROJECT_PATH" ] || [ ! -d "$WSL_PROJECT_PATH" ]; then
        set_blocker "BLOCKED_PROJECT_NOT_FOUND" "Directory for project '$PROJECT_KEY' not found at '$PROJECT_PATH'."
    fi
fi

WSL_TASK_FILE=$(to_wsl_path "$TASK_FILE")
if [ ! -f "$WSL_TASK_FILE" ]; then
    set_blocker "BLOCKED_TASK_NOT_FOUND" "Task file not found at '$WSL_TASK_FILE'."
else
    TASK_META=$("$PYTHON" - "$WSL_TASK_FILE" <<'PY'
import json
import re
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
heading = re.search(r"(?m)^#{1,2}\s+Task\s+([A-Za-z0-9_.-]+)\s*:\s*(.+?)\s*$", text)
allowed = re.search(r"(?ms)^Allowed Files:\s*\n(.*?)(?=^[A-Za-z][A-Za-z ]+:\s*$|\Z)", text)
allowed_files = []
if allowed:
    for line in allowed.group(1).splitlines():
        line = line.strip()
        if line.startswith("- "):
            allowed_files.append(line[2:].strip())
        elif line:
            allowed_files.append(line)
print(json.dumps({
    "id": heading.group(1).strip() if heading else "",
    "title": heading.group(2).strip() if heading else "",
    "allowed_files": allowed_files,
}))
PY
)
    TASK_ID=$("$PYTHON" -c 'import json,sys; print(json.loads(sys.argv[1])["id"])' "$TASK_META")
    TASK_TITLE=$("$PYTHON" -c 'import json,sys; print(json.loads(sys.argv[1])["title"])' "$TASK_META")
    mapfile -t ALLOWED_FILES < <("$PYTHON" -c 'import json,sys; print("\n".join(json.loads(sys.argv[1])["allowed_files"]))' "$TASK_META")
    if [ -z "$TASK_ID" ] || [ -z "$TASK_TITLE" ]; then
        set_blocker "BLOCKED_TASK_NOT_FOUND" "Task heading was not found in '$WSL_TASK_FILE'."
    fi
    if [ ${#ALLOWED_FILES[@]} -eq 0 ]; then
        set_blocker "BLOCKED_MISSING_ALLOWED_FILES" "Task is missing explicit Allowed Files entries."
    fi
fi

if [ "$MODE" = "apply" ] && [ -n "$FROM_REPORT" ]; then
    SOURCE_REPORT="$FROM_REPORT"
    SOURCE_REPORT_WSL=$(to_wsl_path "$FROM_REPORT")
    if [ ! -f "$SOURCE_REPORT_WSL" ]; then
        set_blocker "BLOCKED_MISSING_FROM_REPORT" "Dry-run report not found at '$SOURCE_REPORT_WSL'."
    else
        REPORT_META=$(read_report_metadata "$SOURCE_REPORT_WSL")
        SOURCE_REPORT_TIMESTAMP=$("$PYTHON" -c 'import json,sys; print(json.loads(sys.argv[1])["timestamp"])' "$REPORT_META")
        SOURCE_REPORT_PROJECT=$("$PYTHON" -c 'import json,sys; print(json.loads(sys.argv[1])["project"])' "$REPORT_META")
        SOURCE_REPORT_TASK_FILE=$("$PYTHON" -c 'import json,sys; print(json.loads(sys.argv[1])["task_file"])' "$REPORT_META")
        SOURCE_REPORT_CLASSIFICATION=$("$PYTHON" -c 'import json,sys; print(json.loads(sys.argv[1])["classification"])' "$REPORT_META")
        SOURCE_REPORT_BRANCH=$("$PYTHON" -c 'import json,sys; print(json.loads(sys.argv[1])["branch"])' "$REPORT_META")
        SOURCE_REPORT_WORKTREE_PATH_WSL=$("$PYTHON" -c 'import json,sys; print(json.loads(sys.argv[1])["worktree_path_wsl"])' "$REPORT_META")

        if [ "$SOURCE_REPORT_CLASSIFICATION" != "WORKTREE_CREATE_DRY_RUN_READY" ]; then
            set_blocker "BLOCKED_REPORT_MISMATCH" "Dry-run report is not WORKTREE_CREATE_DRY_RUN_READY."
        fi
        if [ "$SOURCE_REPORT_PROJECT" != "$PROJECT_KEY" ] || [ "$SOURCE_REPORT_TASK_FILE" != "$TASK_FILE" ]; then
            set_blocker "BLOCKED_REPORT_MISMATCH" "Dry-run report project or task file does not match this apply request."
        fi
        if [ -z "$SOURCE_REPORT_BRANCH" ] || [ -z "$SOURCE_REPORT_WORKTREE_PATH_WSL" ]; then
            set_blocker "BLOCKED_REPORT_MISMATCH" "Dry-run report is missing proposed branch or worktree path."
        fi

        SOURCE_REPORT_AGE_SECONDS=$("$PYTHON" - "$SOURCE_REPORT_TIMESTAMP" <<'PY'
from datetime import datetime, timezone
import sys

try:
    created = datetime.strptime(sys.argv[1], "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    print(int((now - created).total_seconds()))
except Exception:
    print("")
PY
)
        if [ -z "$SOURCE_REPORT_AGE_SECONDS" ]; then
            set_blocker "BLOCKED_REPORT_MISMATCH" "Dry-run report timestamp could not be parsed."
        elif [ "$SOURCE_REPORT_AGE_SECONDS" -gt "$MAX_DRY_RUN_AGE_SECONDS" ]; then
            set_blocker "BLOCKED_STALE_DRY_RUN_REPORT" "Dry-run report is older than $MAX_DRY_RUN_AGE_SECONDS seconds."
        fi

        if [ -n "$TASK_ID" ]; then
            case "$SOURCE_REPORT_BRANCH" in
                "loop/$PROJECT_KEY/$TASK_ID/"*) ;;
                *) set_blocker "BLOCKED_REPORT_MISMATCH" "Dry-run report branch is outside the approved task namespace." ;;
            esac
        fi
        case "$SOURCE_REPORT_WORKTREE_PATH_WSL" in
            "$WS_HOME/worktrees/$PROJECT_KEY/"*) ;;
            *) set_blocker "BLOCKED_REPORT_MISMATCH" "Dry-run report worktree path is outside the approved root." ;;
        esac
    fi
fi

if [ -n "$WSL_PROJECT_PATH" ] && [ -d "$WSL_PROJECT_PATH" ]; then
    if ! git -C "$WSL_PROJECT_PATH" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        set_blocker "BLOCKED_UNSUPPORTED_REPO_STATE" "Project path is not a supported git worktree."
    else
        CURRENT_BRANCH=$(git -C "$WSL_PROJECT_PATH" symbolic-ref --quiet --short HEAD 2>/dev/null || true)
        if [ -z "$CURRENT_BRANCH" ]; then
            set_blocker "BLOCKED_UNSUPPORTED_REPO_STATE" "Repository is in detached HEAD or another unsupported branch state."
        fi

        if [ -n "$(git -C "$WSL_PROJECT_PATH" status --porcelain)" ]; then
            REPO_STATUS="dirty"
            set_blocker "BLOCKED_DIRTY_REPO" "Repository has uncommitted changes."
        else
            REPO_STATUS="clean"
        fi

        WORKTREE_LIST=$(git -C "$WSL_PROJECT_PATH" worktree list --porcelain 2>/dev/null || true)
        if [ -z "$WORKTREE_LIST" ]; then
            set_blocker "BLOCKED_UNSUPPORTED_REPO_STATE" "Could not inspect existing git worktrees."
        fi
    fi
fi

if [ "$MODE" = "apply" ] && [ -n "$SOURCE_REPORT_BRANCH" ] && [ -n "$SOURCE_REPORT_WORKTREE_PATH_WSL" ]; then
    PROPOSED_BRANCH="$SOURCE_REPORT_BRANCH"
    PROPOSED_WORKTREE_PATH_WSL="$SOURCE_REPORT_WORKTREE_PATH_WSL"
    PROPOSED_WORKTREE_PATH_WINDOWS=$(to_windows_path "$PROPOSED_WORKTREE_PATH_WSL")
elif [ "$MODE" != "apply" ] && [ -n "$TASK_ID" ]; then
    PROPOSED_WORKTREE_PATH_WSL="$WS_HOME/worktrees/$PROJECT_KEY/${TASK_ID}_$STAMP"
    PROPOSED_WORKTREE_PATH_WINDOWS=$(to_windows_path "$PROPOSED_WORKTREE_PATH_WSL")
    PROPOSED_BRANCH="loop/$PROJECT_KEY/$TASK_ID/$STAMP"
fi

if [ -n "$PROPOSED_WORKTREE_PATH_WSL" ]; then
    if [ -e "$PROPOSED_WORKTREE_PATH_WSL" ]; then
        PATH_EXISTS="Yes"
        set_blocker "BLOCKED_WORKTREE_EXISTS" "Proposed worktree path already exists."
    fi
fi

if [ -n "$WSL_PROJECT_PATH" ] && [ -n "$PROPOSED_BRANCH" ]; then
    if git -C "$WSL_PROJECT_PATH" show-ref --verify --quiet "refs/heads/$PROPOSED_BRANCH"; then
        BRANCH_EXISTS="Yes"
        set_blocker "BLOCKED_BRANCH_EXISTS" "Proposed branch already exists."
    fi
fi

if [ "$MODE" = "dry-run" ] && [ -n "$WSL_PROJECT_PATH" ] && [ -n "$CURRENT_BRANCH" ] && [ -n "$PROPOSED_BRANCH" ] && [ -n "$PROPOSED_WORKTREE_PATH_WSL" ]; then
    BRANCH_COMMAND="git -C \"$WSL_PROJECT_PATH\" branch \"$PROPOSED_BRANCH\" \"main\""
    WORKTREE_COMMAND="git -C \"$WSL_PROJECT_PATH\" worktree add \"$PROPOSED_WORKTREE_PATH_WSL\" \"$PROPOSED_BRANCH\""
elif [ "$MODE" = "apply" ] && [ -n "$WSL_PROJECT_PATH" ] && [ -n "$PROPOSED_BRANCH" ] && [ -n "$PROPOSED_WORKTREE_PATH_WSL" ]; then
    BRANCH_COMMAND="git -C \"$WSL_PROJECT_PATH\" branch \"$PROPOSED_BRANCH\" \"main\""
    WORKTREE_COMMAND="git -C \"$WSL_PROJECT_PATH\" worktree add \"$PROPOSED_WORKTREE_PATH_WSL\" \"$PROPOSED_BRANCH\""
fi

if [ "$MODE" = "apply" ] && [ "$CLASSIFICATION" = "WORKTREE_CREATED" ]; then
    PROJECT_WORKTREE_ROOT="$WS_HOME/worktrees/$PROJECT_KEY"
    if [ ! -d "$PROJECT_WORKTREE_ROOT" ]; then
        if mkdir -p "$PROJECT_WORKTREE_ROOT"; then
            ROOT_CREATED="Yes"
        else
            CLASSIFICATION="FAILED_WORKTREE_ADD"
            REASON="Could not create approved worktree root '$PROJECT_WORKTREE_ROOT'."
        fi
    fi
fi

if [ "$MODE" = "apply" ] && [ "$CLASSIFICATION" = "WORKTREE_CREATED" ]; then
    if ! BRANCH_COMMAND_OUTPUT=$(git -C "$WSL_PROJECT_PATH" branch "$PROPOSED_BRANCH" main 2>&1); then
        CLASSIFICATION="FAILED_BRANCH_CREATE"
        REASON="git branch failed."
    fi
fi

if [ "$MODE" = "apply" ] && [ "$CLASSIFICATION" = "WORKTREE_CREATED" ]; then
    if ! WORKTREE_COMMAND_OUTPUT=$(git -C "$WSL_PROJECT_PATH" worktree add "$PROPOSED_WORKTREE_PATH_WSL" "$PROPOSED_BRANCH" 2>&1); then
        CLASSIFICATION="FAILED_WORKTREE_ADD"
        REASON="git worktree add failed."

        BASE_COMMIT=$(git -C "$WSL_PROJECT_PATH" rev-parse main 2>/dev/null || true)
        CREATED_BRANCH_COMMIT=$(git -C "$WSL_PROJECT_PATH" rev-parse "refs/heads/$PROPOSED_BRANCH" 2>/dev/null || true)
        ATTACHED_WORKTREE=$(git -C "$WSL_PROJECT_PATH" worktree list --porcelain 2>/dev/null | grep -F "branch refs/heads/$PROPOSED_BRANCH" || true)

        if [ -n "$BASE_COMMIT" ] \
            && [ "$BASE_COMMIT" = "$CREATED_BRANCH_COMMIT" ] \
            && [ -z "$ATTACHED_WORKTREE" ] \
            && [ ! -e "$PROPOSED_WORKTREE_PATH_WSL" ]; then
            if git -C "$WSL_PROJECT_PATH" branch -d "$PROPOSED_BRANCH" >/dev/null 2>&1; then
                ROLLBACK_PERFORMED="Yes"
            else
                CLASSIFICATION="FAILED_ROLLBACK_REQUIRED"
                ROLLBACK_REQUIRED="Yes"
                REASON="worktree add failed and automatic rollback could not remove the new branch safely."
            fi
        else
            CLASSIFICATION="FAILED_ROLLBACK_REQUIRED"
            ROLLBACK_REQUIRED="Yes"
            REASON="worktree add failed and rollback safety could not be proven."
        fi
    fi
fi

FINAL_WORKTREE_LIST=""
if [ -n "$WSL_PROJECT_PATH" ] && [ -d "$WSL_PROJECT_PATH" ]; then
    FINAL_WORKTREE_LIST=$(git -C "$WSL_PROJECT_PATH" worktree list --porcelain 2>/dev/null || true)
fi

{
    if [ "$MODE" = "apply" ]; then
        echo "# Worktree Create"
    else
        echo "# Worktree Create Dry Run"
    fi
    echo ""
    echo "- **Timestamp**: $STAMP"
    echo "- **Project**: $PROJECT_KEY"
    echo "- **Task File**: $TASK_FILE"
    echo "- **Mode**: ${MODE:-missing}"
    echo "- **Classification**: $CLASSIFICATION"
    echo ""
    echo "## Analysis"
    echo "$REASON"
    echo ""
    if [ "$MODE" = "apply" ]; then
        echo "## Source Dry Run"
        echo "- Report: ${SOURCE_REPORT:-missing}"
        echo "- Classification: ${SOURCE_REPORT_CLASSIFICATION:-unknown}"
        echo "- Age seconds: ${SOURCE_REPORT_AGE_SECONDS:-unknown}"
        echo ""
    fi
    echo "## Task"
    echo "- Task ID: ${TASK_ID:-unknown}"
    echo "- Task title: ${TASK_TITLE:-unknown}"
    echo "- Allowed Files:"
    if [ ${#ALLOWED_FILES[@]} -gt 0 ]; then
        printf '%s\n' "${ALLOWED_FILES[@]}" | sed 's/^/  - /'
    else
        echo "  - none"
    fi
    echo ""
    echo "## Project Repository"
    echo "- Registry path: ${PROJECT_PATH:-missing}"
    echo "- WSL path: ${WSL_PROJECT_PATH:-missing}"
    echo "- Current branch: ${CURRENT_BRANCH:-unknown}"
    echo "- Repository status: $REPO_STATUS"
    echo ""
    echo "## Existing Worktrees"
    if [ -n "$WORKTREE_LIST" ]; then
        echo '```text'
        printf '%s\n' "$WORKTREE_LIST"
        echo '```'
    else
        echo "Unable to inspect existing worktrees."
    fi
    echo ""
    echo "## Proposed Future Worktree"
    echo "- Worktree path (Windows): ${PROPOSED_WORKTREE_PATH_WINDOWS:-unavailable}"
    echo "- Worktree path (WSL): ${PROPOSED_WORKTREE_PATH_WSL:-unavailable}"
    echo "- Branch: ${PROPOSED_BRANCH:-unavailable}"
    echo "- Proposed path already exists: $PATH_EXISTS"
    echo "- Proposed branch already exists: $BRANCH_EXISTS"
    echo ""
    echo "## Commands"
    if [ -n "$BRANCH_COMMAND" ] && [ -n "$WORKTREE_COMMAND" ]; then
        echo '```bash'
        printf '%s\n' "$BRANCH_COMMAND"
        printf '%s\n' "$WORKTREE_COMMAND"
        echo '```'
    else
        echo "Unavailable until required inputs are valid."
    fi
    if [ "$MODE" = "apply" ]; then
        echo ""
        echo "## Execution"
        echo "- Worktree root created by this invocation: $ROOT_CREATED"
        echo "- Branch command output: ${BRANCH_COMMAND_OUTPUT:-none}"
        echo "- Worktree command output: ${WORKTREE_COMMAND_OUTPUT:-none}"
        echo "- Rollback performed: $ROLLBACK_PERFORMED"
        echo "- Manual rollback required: $ROLLBACK_REQUIRED"
        echo ""
        echo "## Final Worktrees"
        if [ -n "$FINAL_WORKTREE_LIST" ]; then
            echo '```text'
            printf '%s\n' "$FINAL_WORKTREE_LIST"
            echo '```'
        else
            echo "Unable to inspect final worktrees."
        fi
    fi
    echo ""
    echo "## Safety"
    if [ "$MODE" = "apply" ]; then
        echo "This command created isolation only when all supervised gates passed. It did not run tasks or modify project source files."
    else
        echo "This command is dry-run only. It did not create a branch or worktree."
    fi
    echo ""
    echo "## Next Safe Action"
    case "$CLASSIFICATION" in
        WORKTREE_CREATE_DRY_RUN_READY)
            echo "Review the dry-run report, then use supervised apply only if still appropriate."
            ;;
        WORKTREE_CREATED)
            echo "Run ws worktree-status and inspect the new isolated worktree before doing anything else."
            ;;
        FAILED_ROLLBACK_REQUIRED)
            echo "Inspect the branch and worktree state manually before any cleanup."
            ;;
        *)
            echo "Resolve the reported blocker before future worktree creation."
            ;;
    esac
} > "$REPORT"

echo "Classification: $CLASSIFICATION"
echo "Report: $(to_windows_path "$REPORT")"
echo "Proposed worktree path: ${PROPOSED_WORKTREE_PATH_WINDOWS:-unavailable}"
echo "Proposed branch name: ${PROPOSED_BRANCH:-unavailable}"
if [ "$MODE" = "apply" ]; then
    echo "Source dry-run report: ${SOURCE_REPORT:-missing}"
fi
echo "Commands:"
if [ -n "$BRANCH_COMMAND" ] && [ -n "$WORKTREE_COMMAND" ]; then
    printf '  %s\n' "$BRANCH_COMMAND"
    printf '  %s\n' "$WORKTREE_COMMAND"
else
    echo "  unavailable until required inputs are valid"
fi
case "$CLASSIFICATION" in
    WORKTREE_CREATE_DRY_RUN_READY)
        echo "Next safe action: review the dry-run report; actual creation remains supervised."
        ;;
    WORKTREE_CREATED)
        echo "Next safe action: run ws worktree-status and inspect the new worktree."
        ;;
    FAILED_ROLLBACK_REQUIRED)
        echo "Next safe action: inspect branch/worktree state manually before cleanup."
        ;;
    *)
        echo "Next safe action: resolve blockers before future worktree creation."
        ;;
esac

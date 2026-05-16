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

PROJECT_KEY=${1:-}
TASK_FILE=${2:-}

if [ -z "$PROJECT_KEY" ] || [ -z "$TASK_FILE" ]; then
    echo "Usage: ws worktree-plan <project_key> <task_file>"
    exit 1
fi

STAMP=$(date -u +%Y%m%d_%H%M%S)
REPORT="$REPORTS_DIR/WORKTREE_PLAN_$STAMP.md"
CLASSIFICATION="WORKTREE_PLAN_READY"
REASON="All read-only worktree planning checks passed."

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

to_wsl_path() {
    case "$1" in
        /*) printf '%s' "$1" ;;
        *) wslpath -u "$1" 2>/dev/null || printf '%s' "$1" ;;
    esac
}

set_blocker() {
    if [ "$CLASSIFICATION" = "WORKTREE_PLAN_READY" ]; then
        CLASSIFICATION="$1"
        REASON="$2"
    fi
}

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

if [ -n "$TASK_ID" ]; then
    PROPOSED_WORKTREE_PATH_WSL="$WS_HOME/worktrees/$PROJECT_KEY/${TASK_ID}_$STAMP"
    PROPOSED_WORKTREE_PATH_WINDOWS=$(wslpath -w "$PROPOSED_WORKTREE_PATH_WSL" 2>/dev/null || printf '%s' "$PROPOSED_WORKTREE_PATH_WSL")
    PROPOSED_BRANCH="loop/$PROJECT_KEY/$TASK_ID/$STAMP"

    if [ -e "$PROPOSED_WORKTREE_PATH_WSL" ]; then
        PATH_EXISTS="Yes"
        set_blocker "BLOCKED_WORKTREE_EXISTS" "Proposed worktree path already exists."
    fi

    if [ -n "$WSL_PROJECT_PATH" ] && git -C "$WSL_PROJECT_PATH" show-ref --verify --quiet "refs/heads/$PROPOSED_BRANCH"; then
        BRANCH_EXISTS="Yes"
        set_blocker "BLOCKED_BRANCH_EXISTS" "Proposed branch already exists."
    fi
fi

{
    echo "# Worktree Plan"
    echo ""
    echo "- **Timestamp**: $STAMP"
    echo "- **Project**: $PROJECT_KEY"
    echo "- **Task File**: $TASK_FILE"
    echo "- **Classification**: $CLASSIFICATION"
    echo ""
    echo "## Analysis"
    echo "$REASON"
    echo ""
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
    echo "## Next Safe Action"
    if [ "$CLASSIFICATION" = "WORKTREE_PLAN_READY" ]; then
        echo "Review this plan only. Worktree creation is not implemented."
    else
        echo "Resolve the reported blocker before any future worktree creation."
    fi
} > "$REPORT"

echo "Classification: $CLASSIFICATION"
echo "Report: $(wslpath -w "$REPORT" 2>/dev/null || echo "$REPORT")"
echo "Proposed worktree path: ${PROPOSED_WORKTREE_PATH_WINDOWS:-unavailable}"
echo "Proposed branch name: ${PROPOSED_BRANCH:-unavailable}"
if [ "$CLASSIFICATION" = "WORKTREE_PLAN_READY" ]; then
    echo "Next safe action: review the generated plan; no worktree creation is enabled."
else
    echo "Next safe action: resolve blockers before future worktree creation."
fi

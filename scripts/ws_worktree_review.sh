#!/bin/bash

set -u

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
REPORTS_DIR="$WS_HOME/reports"
WORKTREE_ROOT="$WS_HOME/worktrees"
TARGET_INPUT=${1:-}

if [ -z "$TARGET_INPUT" ]; then
    echo "Usage: ws worktree-review <worktree_path>"
    exit 1
fi

STAMP=$(date -u +%Y%m%d_%H%M%S)
REPORT="$REPORTS_DIR/WORKTREE_REVIEW_$STAMP.md"

CLASSIFICATION="REVIEW_NEEDED"
REASON="Unable to complete all review checks."
TARGET_PATH=""
TARGET_PATH_WINDOWS=""
MAIN_PATH=""
WORKTREE_ROOT_CANON=""
LISTED_WORKTREE="No"
APPROVED_PATH="No"
IS_GIT_WORKTREE="No"
BRANCH=""
HEAD_COMMIT=""
MAIN_COMMIT=""
BEHIND_COUNT=""
AHEAD_COUNT=""
DIRTY="unknown"
WORKTREE_LIST=""

to_wsl_path() {
    case "$1" in
        /*) printf '%s' "$1" ;;
        *) wslpath -u "$1" 2>/dev/null || printf '%s' "$1" ;;
    esac
}

to_windows_path() {
    wslpath -w "$1" 2>/dev/null || printf '%s' "$1"
}

next_safe_action() {
    case "$1" in
        READY)
            echo "Review complete. Worktree is aligned with main; task execution remains separately gated."
            ;;
        BEHIND_MAIN)
            echo "Review drift before use; use a future sync or recreate workflow before task execution."
            ;;
        DIRTY)
            echo "Review uncommitted changes in the worktree before any lifecycle action."
            ;;
        AHEAD_OF_MAIN)
            echo "Review branch-only commits before use or integration."
            ;;
        DIVERGED)
            echo "Manual review is required before any sync or use."
            ;;
        INVALID_WORKTREE)
            echo "Provide an active path from git worktree list."
            ;;
        OUTSIDE_APPROVED_ROOT)
            echo "Review the path manually; only the main worktree or worktrees under the approved root are expected."
            ;;
        *)
            echo "Inspect the reported metadata manually before relying on this worktree."
            ;;
    esac
}

TARGET_CANDIDATE=$(to_wsl_path "$TARGET_INPUT")
MAIN_PATH=$(readlink -f "$WS_HOME" 2>/dev/null || printf '%s' "$WS_HOME")
WORKTREE_ROOT_CANON=$(readlink -f "$WORKTREE_ROOT" 2>/dev/null || printf '%s' "$WORKTREE_ROOT")
WORKTREE_LIST=$(git -C "$WS_HOME" worktree list --porcelain 2>/dev/null || true)
MAIN_COMMIT=$(git -C "$WS_HOME" rev-parse main 2>/dev/null || true)

if [ ! -d "$TARGET_CANDIDATE" ]; then
    CLASSIFICATION="INVALID_WORKTREE"
    REASON="Path does not exist."
else
    TARGET_PATH=$(readlink -f "$TARGET_CANDIDATE" 2>/dev/null || printf '%s' "$TARGET_CANDIDATE")
    TARGET_PATH_WINDOWS=$(to_windows_path "$TARGET_PATH")

    if git -C "$TARGET_PATH" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        IS_GIT_WORKTREE="Yes"
    fi

    if [ "$IS_GIT_WORKTREE" != "Yes" ]; then
        CLASSIFICATION="INVALID_WORKTREE"
        REASON="Path is not a Git worktree."
    else
        while IFS= read -r listed_path; do
            [ -z "$listed_path" ] && continue
            listed_canon=$(readlink -f "$listed_path" 2>/dev/null || printf '%s' "$listed_path")
            if [ "$listed_canon" = "$TARGET_PATH" ]; then
                LISTED_WORKTREE="Yes"
                break
            fi
        done < <(printf '%s\n' "$WORKTREE_LIST" | sed -n 's/^worktree //p')

        if [ "$LISTED_WORKTREE" != "Yes" ]; then
            CLASSIFICATION="INVALID_WORKTREE"
            REASON="Path is not listed by git worktree list."
        else
            if [ "$TARGET_PATH" = "$MAIN_PATH" ]; then
                APPROVED_PATH="Yes"
            else
                case "$TARGET_PATH" in
                    "$WORKTREE_ROOT_CANON"/*) APPROVED_PATH="Yes" ;;
                esac
            fi

            BRANCH=$(git -C "$TARGET_PATH" symbolic-ref --quiet --short HEAD 2>/dev/null || true)
            HEAD_COMMIT=$(git -C "$TARGET_PATH" rev-parse HEAD 2>/dev/null || true)

            if [ -n "$(git -C "$TARGET_PATH" status --porcelain 2>/dev/null)" ]; then
                DIRTY="Yes"
            else
                DIRTY="No"
            fi

            if [ -n "$HEAD_COMMIT" ] && [ -n "$MAIN_COMMIT" ]; then
                COUNTS=$(git -C "$WS_HOME" rev-list --left-right --count "$MAIN_COMMIT...$HEAD_COMMIT" 2>/dev/null || true)
                BEHIND_COUNT=$(printf '%s' "$COUNTS" | awk '{print $1}')
                AHEAD_COUNT=$(printf '%s' "$COUNTS" | awk '{print $2}')
            fi

            if [ "$APPROVED_PATH" != "Yes" ]; then
                CLASSIFICATION="OUTSIDE_APPROVED_ROOT"
                REASON="Worktree path is outside the main worktree and approved worktree root."
            elif [ -z "$BRANCH" ] || [ -z "$HEAD_COMMIT" ] || [ -z "$MAIN_COMMIT" ] || [ -z "$BEHIND_COUNT" ] || [ -z "$AHEAD_COUNT" ]; then
                CLASSIFICATION="REVIEW_NEEDED"
                REASON="Worktree metadata could not be fully resolved."
            elif [ "$DIRTY" = "Yes" ]; then
                CLASSIFICATION="DIRTY"
                REASON="Worktree has uncommitted changes."
            elif [ "$BEHIND_COUNT" -gt 0 ] && [ "$AHEAD_COUNT" -gt 0 ]; then
                CLASSIFICATION="DIVERGED"
                REASON="Worktree branch and main both contain unique commits."
            elif [ "$BEHIND_COUNT" -gt 0 ]; then
                CLASSIFICATION="BEHIND_MAIN"
                REASON="Worktree branch is behind main."
            elif [ "$AHEAD_COUNT" -gt 0 ]; then
                CLASSIFICATION="AHEAD_OF_MAIN"
                REASON="Worktree branch is ahead of main."
            else
                CLASSIFICATION="READY"
                REASON="Worktree is clean, approved, and aligned with main."
            fi
        fi
    fi
fi

{
    echo "# Worktree Review"
    echo ""
    echo "- **Timestamp**: $STAMP"
    echo "- **Input Path**: $TARGET_INPUT"
    echo "- **Resolved Path**: ${TARGET_PATH:-unavailable}"
    echo "- **Resolved Path (Windows)**: ${TARGET_PATH_WINDOWS:-unavailable}"
    echo "- **Classification**: $CLASSIFICATION"
    echo ""
    echo "## Analysis"
    echo "$REASON"
    echo ""
    echo "## Checks"
    echo "- Path exists: $([ -d "$TARGET_CANDIDATE" ] && echo Yes || echo No)"
    echo "- Git worktree: $IS_GIT_WORKTREE"
    echo "- Listed by git worktree list: $LISTED_WORKTREE"
    echo "- Under approved root or main worktree: $APPROVED_PATH"
    echo "- Dirty: $DIRTY"
    echo ""
    echo "## Git State"
    echo "- Branch: ${BRANCH:-unknown}"
    echo "- HEAD commit: ${HEAD_COMMIT:-unknown}"
    echo "- Main commit: ${MAIN_COMMIT:-unknown}"
    echo "- Behind main: ${BEHIND_COUNT:-unknown}"
    echo "- Ahead of main: ${AHEAD_COUNT:-unknown}"
    echo ""
    echo "## Active Worktrees"
    if [ -n "$WORKTREE_LIST" ]; then
        echo '```text'
        printf '%s\n' "$WORKTREE_LIST"
        echo '```'
    else
        echo "Unable to inspect active worktrees."
    fi
    echo ""
    echo "## Next Safe Action"
    next_safe_action "$CLASSIFICATION"
    echo ""
    echo "## Safety"
    echo "This command is read-only. It does not create, sync, prune, remove, or modify worktrees."
} > "$REPORT"

echo "Classification: $CLASSIFICATION"
echo "Report: $(to_windows_path "$REPORT")"
echo "Branch: ${BRANCH:-unknown}"
echo "HEAD commit: ${HEAD_COMMIT:-unknown}"
echo "Main commit: ${MAIN_COMMIT:-unknown}"
echo "Next safe action: $(next_safe_action "$CLASSIFICATION")"

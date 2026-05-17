#!/bin/bash

set -euo pipefail

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
REPORTS_DIR="$WS_HOME/reports"
WORKTREE_ROOT="$WS_HOME/worktrees"

TARGET_INPUT=${1:-}
DRY_RUN=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        *)
            if [ -z "$TARGET_INPUT" ] || [[ "$1" != --* ]]; then
                TARGET_INPUT="$1"
            fi
            shift
            ;;
    esac
done

if [ -z "$TARGET_INPUT" ]; then
    echo "Usage: ws worktree-sync <worktree_path> --dry-run"
    exit 1
fi

if [ "$DRY_RUN" -eq 0 ]; then
    echo "Error: --dry-run is mandatory for worktree-sync MVP."
    exit 1
fi

STAMP=$(date -u +%Y%m%d_%H%M%S)
REPORT="$REPORTS_DIR/WORKTREE_SYNC_DRY_RUN_$STAMP.md"

CLASSIFICATION="BLOCKED_UNSUPPORTED_STATE"
REASON="Unable to complete dry-run checks."
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
AHEAD=0
BEHIND=0
DIRTY_STATUS=""

to_wsl_path() {
    case "$1" in
        /*) printf '%s' "$1" ;;
        *) wslpath -u "$1" 2>/dev/null || printf '%s' "$1" ;;
    esac
}

to_windows_path() {
    wslpath -w "$1" 2>/dev/null || printf '%s' "$1"
}

canon_path() {
    readlink -f "$1" 2>/dev/null || echo "$1"
}

TARGET_PATH=$(canon_path "$(to_wsl_path "$TARGET_INPUT")")
if [ -n "$TARGET_PATH" ]; then
    TARGET_PATH_WINDOWS=$(to_windows_path "$TARGET_PATH")
fi

WORKTREE_ROOT_CANON=$(canon_path "$WORKTREE_ROOT")
MAIN_PATH=$(canon_path "$WS_HOME")

check_dry_run() {
    if [ ! -d "$TARGET_PATH" ]; then
        CLASSIFICATION="BLOCKED_INVALID_WORKTREE"
        REASON="Path does not exist or is not a directory."
        return
    fi

    if [[ "$TARGET_PATH" != "$WORKTREE_ROOT_CANON"* ]]; then
        CLASSIFICATION="BLOCKED_OUTSIDE_APPROVED_ROOT"
        REASON="Path is not under $WORKTREE_ROOT"
        return
    fi
    APPROVED_PATH="Yes"

    if [ -f "$TARGET_PATH/.git" ]; then
        IS_GIT_WORKTREE="Yes"
    else
        CLASSIFICATION="BLOCKED_INVALID_WORKTREE"
        REASON="Path does not contain a .git file indicating a worktree."
        return
    fi

    if git -C "$MAIN_PATH" worktree list | grep -qF "$TARGET_PATH"; then
        LISTED_WORKTREE="Yes"
    else
        CLASSIFICATION="BLOCKED_INVALID_WORKTREE"
        REASON="Path is not listed by 'git worktree list'."
        return
    fi

    # Read Git state
    DIRTY_STATUS=$(git -C "$TARGET_PATH" status --porcelain 2>/dev/null)
    if [ -n "$DIRTY_STATUS" ]; then
        CLASSIFICATION="BLOCKED_DIRTY"
        REASON="Worktree has uncommitted changes."
        return
    fi

    BRANCH=$(git -C "$TARGET_PATH" branch --show-current 2>/dev/null)
    HEAD_COMMIT=$(git -C "$TARGET_PATH" rev-parse HEAD 2>/dev/null)
    MAIN_COMMIT=$(git -C "$MAIN_PATH" rev-parse HEAD 2>/dev/null)

    if [ -z "$BRANCH" ] || [ -z "$HEAD_COMMIT" ] || [ -z "$MAIN_COMMIT" ]; then
        CLASSIFICATION="BLOCKED_INVALID_WORKTREE"
        REASON="Failed to determine branch or commit hashes."
        return
    fi

    # Check ahead/behind vs main
    # Ensure tracking information is updated (we assume main is local and up-to-date)
    AHEAD=$(git -C "$MAIN_PATH" rev-list --count "$MAIN_COMMIT..$HEAD_COMMIT" 2>/dev/null || echo 0)
    BEHIND=$(git -C "$MAIN_PATH" rev-list --count "$HEAD_COMMIT..$MAIN_COMMIT" 2>/dev/null || echo 0)

    if [ "$AHEAD" -gt 0 ] && [ "$BEHIND" -gt 0 ]; then
        CLASSIFICATION="BLOCKED_DIVERGED"
        REASON="Worktree has diverged from main (ahead $AHEAD, behind $BEHIND)."
        return
    fi

    if [ "$AHEAD" -gt 0 ]; then
        CLASSIFICATION="BLOCKED_AHEAD_OF_MAIN"
        REASON="Worktree is ahead of main ($AHEAD commits)."
        return
    fi

    if [ "$BEHIND" -eq 0 ] && [ "$AHEAD" -eq 0 ]; then
        CLASSIFICATION="WORKTREE_SYNC_NOT_NEEDED"
        REASON="Worktree is already in sync with main."
        return
    fi

    if [ "$BEHIND" -gt 0 ] && [ "$AHEAD" -eq 0 ]; then
        CLASSIFICATION="WORKTREE_SYNC_DRY_RUN_READY"
        REASON="Worktree can cleanly fast-forward."
        return
    fi
}

check_dry_run

echo "Classification: $CLASSIFICATION"
echo "Report: $(to_windows_path "$REPORT")"
echo "Branch: ${BRANCH:-none}"
echo "Ahead: $AHEAD, Behind: $BEHIND"

PREVIEW_COMMAND="None"
if [ "$CLASSIFICATION" = "WORKTREE_SYNC_DRY_RUN_READY" ]; then
    PREVIEW_COMMAND="git -C $TARGET_PATH_WINDOWS merge --ff-only main"
    echo "Next safe action: A future sync path would run '$PREVIEW_COMMAND'."
elif [ "$CLASSIFICATION" = "WORKTREE_SYNC_NOT_NEEDED" ]; then
    echo "Next safe action: No sync needed."
else
    echo "Next safe action: Resolve blockers before sync."
fi

cat <<EOF > "$REPORT"
# Worktree Sync Dry-Run

- Timestamp: $STAMP
- Target Path: $TARGET_PATH
- Target Path (Windows): $TARGET_PATH_WINDOWS
- Main Path: $MAIN_PATH

## Classification
- Result: $CLASSIFICATION
- Reason: $REASON
- Preview Command: $PREVIEW_COMMAND

## Git State
- Approved Root: $APPROVED_PATH
- Listed Worktree: $LISTED_WORKTREE
- Has .git file: $IS_GIT_WORKTREE
- Branch: ${BRANCH:-none}
- HEAD commit: ${HEAD_COMMIT:-none}
- Main commit: ${MAIN_COMMIT:-none}
- Ahead: $AHEAD
- Behind: $BEHIND
- Dirty Status: ${DIRTY_STATUS:-clean}

## Next Safe Action
$(if [ "$CLASSIFICATION" = "WORKTREE_SYNC_DRY_RUN_READY" ]; then echo "A future sync path would run '$PREVIEW_COMMAND'."; elif [ "$CLASSIFICATION" = "WORKTREE_SYNC_NOT_NEEDED" ]; then echo "No sync needed."; else echo "Resolve blockers before sync."; fi)
EOF

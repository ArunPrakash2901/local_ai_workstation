#!/bin/bash

set -u

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
REPORTS_DIR="$WS_HOME/reports"
WORKTREE_ROOT="$WS_HOME/worktrees"
WORKTREE_ROOT_WINDOWS=$(wslpath -w "$WORKTREE_ROOT" 2>/dev/null || printf '%s' "$WORKTREE_ROOT")

STAMP=$(date -u +%Y%m%d_%H%M%S)
REPORT="$REPORTS_DIR/WORKTREE_STATUS_$STAMP.md"

ACTIVE_WORKTREE_RAW=$(git -C "$WS_HOME" worktree list --porcelain 2>/dev/null || true)
ACTIVE_WORKTREES=()
if [ -n "$ACTIVE_WORKTREE_RAW" ]; then
    mapfile -t ACTIVE_WORKTREES < <(printf '%s\n' "$ACTIVE_WORKTREE_RAW" | sed -n 's/^worktree //p')
fi
ACTIVE_COUNT=${#ACTIVE_WORKTREES[@]}

if [ -d "$WORKTREE_ROOT" ]; then
    ROOT_EXISTS="Yes"
else
    ROOT_EXISTS="No"
fi

mapfile -t PLAN_REPORTS < <(
    find "$REPORTS_DIR" -maxdepth 1 -name "WORKTREE_PLAN_*.md" -type f -printf '%T@ %p\n' 2>/dev/null \
        | sort -nr \
        | head -n 10 \
        | cut -d' ' -f2-
)

READY_PLAN_COUNT=0
BLOCKED_PLAN_COUNT=0
PLAN_ROWS=()

for plan_file in "${PLAN_REPORTS[@]}"; do
    timestamp=$(grep -oP -- '^- \*\*Timestamp\*\*: \K.*' "$plan_file" || true)
    project=$(grep -oP -- '^- \*\*Project\*\*: \K.*' "$plan_file" || true)
    classification=$(grep -oP -- '^- \*\*Classification\*\*: \K.*' "$plan_file" || true)
    proposed_path=$(grep -oP -- '^- Worktree path \(Windows\): \K.*' "$plan_file" || true)
    proposed_branch=$(grep -oP -- '^- Branch: \K.*' "$plan_file" || true)

    if [ "$classification" = "WORKTREE_PLAN_READY" ]; then
        READY_PLAN_COUNT=$((READY_PLAN_COUNT + 1))
    elif [[ "$classification" == BLOCKED_* ]]; then
        BLOCKED_PLAN_COUNT=$((BLOCKED_PLAN_COUNT + 1))
    fi

    PLAN_ROWS+=("${timestamp:-unknown}|${project:-unknown}|${classification:-unknown}|${proposed_path:-unavailable}|${proposed_branch:-unavailable}|$(basename "$plan_file")")
done

STALE_DIRS=()
if [ "$ROOT_EXISTS" = "Yes" ]; then
    mapfile -t CANDIDATE_DIRS < <(find "$WORKTREE_ROOT" -mindepth 2 -maxdepth 2 -type d 2>/dev/null | sort)
    for dir in "${CANDIDATE_DIRS[@]}"; do
        is_active="No"
        for active in "${ACTIVE_WORKTREES[@]}"; do
            if [ "$dir" = "$active" ]; then
                is_active="Yes"
                break
            fi
        done
        if [ "$is_active" = "No" ]; then
            STALE_DIRS+=("$dir")
        fi
    done
fi
STALE_COUNT=${#STALE_DIRS[@]}

{
    echo "# Worktree Status"
    echo ""
    echo "- **Timestamp**: $STAMP"
    echo "- **Configured future worktree root**: $WORKTREE_ROOT_WINDOWS"
    echo "- **Worktree root exists**: $ROOT_EXISTS"
    echo "- **Active worktrees**: $ACTIVE_COUNT"
    echo "- **Recent worktree-plan reports inspected**: ${#PLAN_REPORTS[@]}"
    echo "- **Planned worktrees**: $READY_PLAN_COUNT"
    echo "- **Blocked plans**: $BLOCKED_PLAN_COUNT"
    echo "- **Stale-looking worktree directories**: $STALE_COUNT"
    echo ""
    echo "## Active Worktrees"
    if [ -n "$ACTIVE_WORKTREE_RAW" ]; then
        echo '```text'
        printf '%s\n' "$ACTIVE_WORKTREE_RAW"
        echo '```'
    else
        echo "Unable to inspect active worktrees."
    fi
    echo ""
    echo "## Recent Worktree Plans"
    if [ ${#PLAN_ROWS[@]} -eq 0 ]; then
        echo "No recent worktree-plan reports found."
    else
        for row in "${PLAN_ROWS[@]}"; do
            IFS='|' read -r timestamp project classification proposed_path proposed_branch file_name <<< "$row"
            echo "### Plan: $timestamp"
            echo "- Project: $project"
            echo "- Classification: $classification"
            echo "- Proposed worktree path: $proposed_path"
            echo "- Proposed branch: $proposed_branch"
            echo "- Report: $file_name"
            echo ""
        done
    fi
    echo "## Stale-Looking Worktree Directories"
    if [ $STALE_COUNT -eq 0 ]; then
        echo "None found."
    else
        for dir in "${STALE_DIRS[@]}"; do
            echo "- $(wslpath -w "$dir" 2>/dev/null || printf '%s' "$dir")"
        done
    fi
    echo ""
    echo "## Safety"
    echo "This command is read-only. It does not create, delete, prune, or move worktrees."
} > "$REPORT"

echo "Worktree Status Summary"
echo "-----------------------"
echo "Active worktrees: $ACTIVE_COUNT"
if [ $ACTIVE_COUNT -gt 0 ]; then
    echo "Active worktree paths:"
    printf '%s\n' "${ACTIVE_WORKTREES[@]}" | sed 's/^/  - /'
fi
echo "Future worktree root: $WORKTREE_ROOT_WINDOWS ($ROOT_EXISTS)"
echo "Recent plans: ${#PLAN_REPORTS[@]}"
echo "Planned worktrees: $READY_PLAN_COUNT"
echo "Blocked plans: $BLOCKED_PLAN_COUNT"
echo "Stale-looking directories: $STALE_COUNT"
echo "Report: $(wslpath -w "$REPORT" 2>/dev/null || printf '%s' "$REPORT")"

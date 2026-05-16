#!/bin/bash

set -u

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
AUTO_RUNS_DIR="$WS_HOME/auto_runs"
REPORTS_DIR="$WS_HOME/reports"
STAMP=$(date +%Y%m%d_%H%M%S)
REPORT="$REPORTS_DIR/AGENT_HYGIENE_$STAMP.md"

mkdir -p "$REPORTS_DIR"

CURRENT_BRANCH=$(git -C "$WS_HOME" branch --show-current 2>/dev/null || true)
MAIN_HASH=$(git -C "$WS_HOME" rev-parse main 2>/dev/null || true)

BRANCH_ROWS=()
AGENT_BRANCH_COUNT=0
SAME_AS_MAIN_COUNT=0
UNIQUE_BRANCH_COUNT=0

while IFS='|' read -r name hash; do
    [ -z "$name" ] && continue
    category='other'
    if [ "$name" = "$CURRENT_BRANCH" ]; then
        category='current'
    elif [ "$name" = "main" ]; then
        category='main'
    elif [[ "$name" == agent/* ]]; then
        category='agent'
        AGENT_BRANCH_COUNT=$((AGENT_BRANCH_COUNT + 1))
    fi

    relation='unique_commit'
    if [ -n "$MAIN_HASH" ] && [ "$hash" = "$MAIN_HASH" ]; then
        relation='same_as_main'
        SAME_AS_MAIN_COUNT=$((SAME_AS_MAIN_COUNT + 1))
    else
        UNIQUE_BRANCH_COUNT=$((UNIQUE_BRANCH_COUNT + 1))
    fi
    BRANCH_ROWS+=("| \`$name\` | \`${hash:0:7}\` | $category | $relation |")
done < <(git -C "$WS_HOME" for-each-ref refs/heads --format='%(refname:short)|%(objectname)' | sort)

WORKTREE_LINES=()
while IFS= read -r line; do
    [ -z "$line" ] && continue
    WORKTREE_LINES+=("- \`$line\`")
done < <(git -C "$WS_HOME" worktree list 2>/dev/null || true)

declare -A STATUS_COUNTS
RUN_ROWS=()
STALE_ROWS=()
REVIEWED_STALE_ROWS=()
TOTAL_RUNS=0
STALE_RUNNING_COUNT=0
REVIEWED_STALE_COUNT=0

if [ -d "$AUTO_RUNS_DIR" ]; then
    while IFS= read -r run_dir; do
        [ -z "$run_dir" ] && continue
        TOTAL_RUNS=$((TOTAL_RUNS + 1))
        run_name=$(basename "$run_dir")
        status='MISSING_STATUS'
        if [ -f "$run_dir/status.txt" ]; then
            status=$(tr -d '\r\n\357\273\277' < "$run_dir/status.txt")
            [ -z "$status" ] && status='EMPTY_STATUS'
        fi
        STATUS_COUNTS["$status"]=$(( ${STATUS_COUNTS["$status"]:-0} + 1 ))
        timestamp=$(stat -c '%y' "$run_dir" 2>/dev/null | cut -d'.' -f1)
        final_report='no'
        stdout='no'
        stderr='no'
        exit_code='no'
        [ -f "$run_dir/final_report.md" ] && final_report='yes'
        [ -f "$run_dir/codex_stdout.md" ] && stdout='yes'
        [ -f "$run_dir/codex_stderr.md" ] && stderr='yes'
        [ -f "$run_dir/codex_exit_code.txt" ] && exit_code='yes'
        RUN_ROWS+=("| \`$run_name\` | $status | $timestamp | $final_report |")
        if [ "$status" = "CODEX_RUNNING" ]; then
            if [ -f "$run_dir/stale_reviewed.md" ]; then
                REVIEWED_STALE_COUNT=$((REVIEWED_STALE_COUNT + 1))
                REVIEWED_STALE_ROWS+=("| \`$run_name\` | $status | $timestamp | $final_report | $stdout | $stderr | $exit_code |")
            else
                STALE_RUNNING_COUNT=$((STALE_RUNNING_COUNT + 1))
                STALE_ROWS+=("| \`$run_name\` | $status | $timestamp | $final_report | $stdout | $stderr | $exit_code |")
            fi
        fi
    done < <(find "$AUTO_RUNS_DIR" -mindepth 1 -maxdepth 1 -type d | sort)
fi

AUTO_RUNS_IGNORED='no'
if git -C "$WS_HOME" check-ignore -q auto_runs/; then
    AUTO_RUNS_IGNORED='yes'
fi

VALIDATION_REPORT_COUNT=$(find "$REPORTS_DIR" -maxdepth 1 -type f -name 'AGENT_CONTRACT_VALIDATION_*.md' 2>/dev/null | wc -l | tr -d ' ')
VALIDATION_REPORT_IGNORED='no'
if find "$REPORTS_DIR" -maxdepth 1 -type f -name 'AGENT_CONTRACT_VALIDATION_*.md' -print -quit 2>/dev/null | grep -q .; then
    sample_validation_report=$(find "$REPORTS_DIR" -maxdepth 1 -type f -name 'AGENT_CONTRACT_VALIDATION_*.md' | head -n 1)
    if git -C "$WS_HOME" check-ignore --no-index -q "$sample_validation_report"; then
        VALIDATION_REPORT_IGNORED='yes'
    fi
fi

HYGIENE_REPORT_COUNT=$(find "$REPORTS_DIR" -maxdepth 1 -type f -name 'AGENT_HYGIENE_*.md' 2>/dev/null | wc -l | tr -d ' ')
HYGIENE_REPORT_IGNORED='no'
if find "$REPORTS_DIR" -maxdepth 1 -type f -name 'AGENT_HYGIENE_*.md' -print -quit 2>/dev/null | grep -q .; then
    sample_hygiene_report=$(find "$REPORTS_DIR" -maxdepth 1 -type f -name 'AGENT_HYGIENE_*.md' | head -n 1)
    if git -C "$WS_HOME" check-ignore --no-index -q "$sample_hygiene_report"; then
        HYGIENE_REPORT_IGNORED='yes'
    fi
fi

{
    echo "# Agent Hygiene Report"
    echo
    echo "## Summary"
    echo "- Current branch: \`$CURRENT_BRANCH\`"
    echo "- Main commit: \`${MAIN_HASH:-missing}\`"
    echo "- Agent branches: $AGENT_BRANCH_COUNT"
    echo "- Branches pointing to same commit as main: $SAME_AS_MAIN_COUNT"
    echo "- Branches with unique commits: $UNIQUE_BRANCH_COUNT"
    echo "- auto_runs folders scanned: $TOTAL_RUNS"
    echo "- Unresolved stale CODEX_RUNNING folders: $STALE_RUNNING_COUNT"
    echo "- Reviewed stale CODEX_RUNNING folders: $REVIEWED_STALE_COUNT"
    echo "- auto_runs ignored by Git: $AUTO_RUNS_IGNORED"
    echo "- validation reports found: $VALIDATION_REPORT_COUNT"
    echo "- validation reports ignored by Git: $VALIDATION_REPORT_IGNORED"
    echo "- hygiene reports found: $HYGIENE_REPORT_COUNT"
    echo "- hygiene reports ignored by Git: $HYGIENE_REPORT_IGNORED"
    echo
    echo "## Branches"
    echo "| branch | commit | category | relation to main |"
    echo "| --- | --- | --- | --- |"
    printf '%s\n' "${BRANCH_ROWS[@]}"
    echo
    echo "## Worktrees"
    if [ "${#WORKTREE_LINES[@]}" -gt 0 ]; then
        printf '%s\n' "${WORKTREE_LINES[@]}"
    else
        echo "- none reported"
    fi
    echo
    echo "## Run Status Counts"
    echo "| status | count |"
    echo "| --- | ---: |"
    for status in "${!STATUS_COUNTS[@]}"; do
        echo "| $status | ${STATUS_COUNTS[$status]} |"
    done | sort
    echo
    echo "## Run Folders"
    echo "| run folder | status | timestamp | final report |"
    echo "| --- | --- | --- | --- |"
    printf '%s\n' "${RUN_ROWS[@]}"
    echo
    echo "## Unresolved Stale CODEX_RUNNING Folders"
    if [ "$STALE_RUNNING_COUNT" -gt 0 ]; then
        echo "| run folder | status | timestamp | final report | stdout | stderr | exit code |"
        echo "| --- | --- | --- | --- | --- | --- | --- |"
        printf '%s\n' "${STALE_ROWS[@]}"
    else
        echo "- none"
    fi
    echo
    echo "## Reviewed Stale CODEX_RUNNING Folders"
    if [ "$REVIEWED_STALE_COUNT" -gt 0 ]; then
        echo "| run folder | status | timestamp | final report | stdout | stderr | exit code |"
        echo "| --- | --- | --- | --- | --- | --- | --- |"
        printf '%s\n' "${REVIEWED_STALE_ROWS[@]}"
    else
        echo "- none"
    fi
    echo
    echo "## Recommendations"
    echo "- Keep current and main branches until their purpose is clear."
    echo "- Keep runs with terminal reports when they are still needed for diagnosis or audit trail."
    echo "- Later review branches that point to the same commit as main before deleting them manually."
    echo "- Later review stale CODEX_RUNNING folders manually using 'ws agent-mark-stale-reviewed <run>'; do not delete them until the failure history is no longer needed."
    echo "- Retain curated summary reports such as R3/R4/R4.5; recurring AGENT_CONTRACT_VALIDATION and AGENT_HYGIENE reports follow the generated-report policy."
    echo "- No cleanup was performed by this command."
} > "$REPORT"

echo "Agent hygiene report: $REPORT"
echo "Current branch: $CURRENT_BRANCH"
echo "Agent branches: $AGENT_BRANCH_COUNT"
echo "Unresolved CODEX_RUNNING folders: $STALE_RUNNING_COUNT"
echo "Reviewed CODEX_RUNNING folders: $REVIEWED_STALE_COUNT"
echo "auto_runs ignored by Git: $AUTO_RUNS_IGNORED"
echo "Validation reports ignored by Git: $VALIDATION_REPORT_IGNORED"
echo "Hygiene reports ignored by Git: $HYGIENE_REPORT_IGNORED"

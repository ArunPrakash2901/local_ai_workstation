#!/bin/bash

set -u

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
REPORTS_DIR="$WS_HOME/reports"

STAMP=$(date +%Y%m%d_%H%M%S)
REPORT="$REPORTS_DIR/LOOP_STATUS_$STAMP.md"

cat <<EOF > "$REPORT"
# Independent Loop Status
Generated: $STAMP

## Recent Loop Plans

EOF

echo "Loop Status Summary"
echo "-------------------"

# Find latest 5 loop plans
PLANS=$(find "$REPORTS_DIR" -maxdepth 1 -name "LOOP_PLAN_*.md" -type f -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n 5 | cut -d' ' -f2-)

if [ -z "$PLANS" ]; then
    echo "No recent loop plans found."
    echo "No recent loop plans found." >> "$REPORT"
else
    printf "%-20s | %-20s | %-30s\n" "Timestamp" "Project" "Classification"
    printf "%-20s | %-20s | %-30s\n" "--------------------" "--------------------" "------------------------------"
    
    while IFS= read -r plan_file; do
        timestamp=$(grep -oP -- '^- \*\*Timestamp\*\*: \K.*' "$plan_file" || echo "unknown")
        project=$(grep -oP -- '^- \*\*Project\*\*: \K.*' "$plan_file" || echo "unknown")
        task=$(grep -oP -- '^- \*\*Task\*\*: \K.*' "$plan_file" || echo "unknown")
        classification=$(grep -oP -- '^- \*\*Classification\*\*: \K.*' "$plan_file" || echo "unknown")
        
        reason=$(grep -A 1 "^## Analysis" "$plan_file" | tail -n 1 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

        if [ "$classification" = "CLOUD_APPLY_ELIGIBLE" ] || [ "$classification" = "BLOCKED_CLOUD_QUOTA" ]; then
            next_cmd="ws agent-run $project \"$task\" --mode detect --branch"
        elif [ "$classification" = "LOCAL_PLAN_ONLY" ]; then
            next_cmd="ws loop-plan $project \"$task\""
        else
            next_cmd="resolve blockers before proceeding"
        fi

        # Truncate strings for terminal summary to avoid wrapping
        term_ts=$(echo "$timestamp" | cut -c1-20)
        term_proj=$(echo "$project" | cut -c1-20)
        term_class=$(echo "$classification" | cut -c1-30)

        printf "%-20s | %-20s | %-30s\n" "$term_ts" "$term_proj" "$term_class"
        
        cat <<EOF >> "$REPORT"
### Plan: $timestamp
- **Project**: $project
- **Task**: $task
- **Classification**: $classification
- **Reason**: $reason
- **Next Safe Command**: \`$next_cmd\`
- **File**: $(basename "$plan_file")

EOF
    done <<< "$PLANS"
fi

echo ""
echo "Full report: $(wslpath -w "$REPORT" 2>/dev/null || echo "$REPORT")"
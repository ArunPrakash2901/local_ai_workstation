#!/bin/bash
set -euo pipefail

WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
if [ -f "$WS_HOME/scripts/ws_env.sh" ]; then
    source "$WS_HOME/scripts/ws_env.sh"
fi

ROOT="$WS_HOME/tasks"
mkdir -p "$ROOT/inbox" "$ROOT/active" "$ROOT/completed" "$ROOT/blocked" "$ROOT/generated" "$ROOT/reviewed"

echo "Task Lifecycle Status"
echo "---------------------"
for d in inbox active completed blocked generated reviewed; do
    count=$(find "$ROOT/$d" -type f -name "*.md" 2>/dev/null | wc -l)
    printf "%-10s %s\n" "$d:" "$count"
done
echo ""
echo "Recent tasks:"
find "$ROOT"/inbox "$ROOT"/active "$ROOT"/generated "$ROOT"/reviewed "$ROOT"/blocked "$ROOT"/completed -type f -name "*.md" -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n 12 | cut -d' ' -f2-

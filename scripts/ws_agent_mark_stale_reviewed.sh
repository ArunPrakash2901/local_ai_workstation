#!/bin/bash

set -u

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
AUTO_RUNS_DIR="$WS_HOME/auto_runs"

RUN_FOLDER=${1:-}

if [ -z "$RUN_FOLDER" ]; then
    echo "Usage: ws agent-mark-stale-reviewed <run_folder_name_or_path>"
    exit 1
fi

# Resolve actual folder path
if [ -d "$RUN_FOLDER" ]; then
    TARGET_DIR="$RUN_FOLDER"
elif [ -d "$AUTO_RUNS_DIR/$RUN_FOLDER" ]; then
    TARGET_DIR="$AUTO_RUNS_DIR/$RUN_FOLDER"
else
    echo "Error: Run folder '$RUN_FOLDER' not found."
    exit 1
fi

# Ensure it's under auto_runs
if [[ "$TARGET_DIR" != "$AUTO_RUNS_DIR/"* ]]; then
    echo "Error: Directory is not under $AUTO_RUNS_DIR."
    exit 1
fi

if [ ! -f "$TARGET_DIR/status.txt" ]; then
    echo "Error: status.txt not found in '$TARGET_DIR'."
    exit 1
fi

STATUS=$(tr -d '\r\n\357\273\277' < "$TARGET_DIR/status.txt")

if [ "$STATUS" != "CODEX_RUNNING" ]; then
    echo "Error: Status is '$STATUS', not 'CODEX_RUNNING'. Only CODEX_RUNNING runs can be marked as stale reviewed."
    exit 1
fi

MARKER_FILE="$TARGET_DIR/stale_reviewed.md"

if [ -f "$MARKER_FILE" ]; then
    echo "Run folder is already marked as reviewed."
    exit 0
fi

STAMP=$(date +%Y%m%d_%H%M%S)
cat <<EOF > "$MARKER_FILE"
# Stale Run Reviewed

This run was stuck in CODEX_RUNNING and has been manually acknowledged by the operator as historical/stale.
It is no longer considered an active blocker for new runs.

Reviewed on: $STAMP
EOF

echo "Successfully marked $(basename "$TARGET_DIR") as a reviewed stale run."

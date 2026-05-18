#!/bin/bash

set -euo pipefail

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
APP="$WS_HOME/tui/app.py"

if [ ! -f "$APP" ]; then
    echo "TUI app not found: $APP"
    exit 1
fi

exec python3 "$APP" "$@"

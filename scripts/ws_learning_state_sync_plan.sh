#!/bin/bash

set -euo pipefail

# Robustly determine WS_HOME
if [ -z "${WS_HOME:-}" ]; then
    SOURCE="${BASH_SOURCE[0]}"
    while [ -h "$SOURCE" ]; do
        DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
        SOURCE="$(readlink "$SOURCE")"
        [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
    done
    _SCRIPTS_DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
    export WS_HOME="$(cd "$_SCRIPTS_DIR/.." >/dev/null 2>&1 && pwd)"
fi

if [ -f "$WS_HOME/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "$WS_HOME/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"
PLANNER_PY="$WS_HOME/scripts/learning_state_sync_planner.py"

"$PYTHON" "$PLANNER_PY" "$@"

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
ACTION_PACK_PY="$WS_HOME/scripts/learning_action_pack.py"

STRONGHOLD_INPUT=""
DRY_RUN=0

# Check for mandatory --dry-run and extract stronghold input
for arg in "$@"; do
    if [[ "$arg" == "--dry-run" ]]; then
        DRY_RUN=1
    elif [[ "$arg" != --* ]]; then
        STRONGHOLD_INPUT="$arg"
    fi
done

if [ -z "$STRONGHOLD_INPUT" ]; then
    echo "Usage: ws learning-action-pack <stronghold_id_or_path> --dry-run"
    exit 1
fi

if [ "$DRY_RUN" -eq 0 ]; then
    echo "Error: --dry-run is currently mandatory for the learning action pack."
    exit 1
fi

"$PYTHON" "$ACTION_PACK_PY" "$@"

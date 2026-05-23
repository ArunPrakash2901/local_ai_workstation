#!/bin/bash
# Learning Review Packet Checklist State Layer v1 wrapper

set -e

# Determine WS_HOME
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

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
PYTHON_EXEC="python3"

# Check if we are on Windows/WSL
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    PYTHON_EXEC="python"
fi

# Run the python script
"$PYTHON_EXEC" "$WS_HOME/scripts/learning_review_checklist_state.py" "$@"

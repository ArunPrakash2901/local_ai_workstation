#!/bin/bash
set -euo pipefail

PROJECT_DIR=${1:-}
RUN_DIR=${2:-}
TEST_COMMAND=${3:-}
MAX_MINUTES=${4:-60}

if [ -z "$PROJECT_DIR" ] || [ -z "$RUN_DIR" ]; then
    echo "Usage: ws_test_runner.sh <project_dir> <run_dir> [test_command] [max_minutes]"
    exit 1
fi

OUT="$RUN_DIR/test_output.md"
mkdir -p "$RUN_DIR"

if [ -z "$TEST_COMMAND" ] || [ "$TEST_COMMAND" = "not specified" ]; then
    if [ -f "$PROJECT_DIR/package.json" ] && grep -q '"test"' "$PROJECT_DIR/package.json"; then
        TEST_COMMAND="npm test"
    elif find "$PROJECT_DIR" -maxdepth 2 \( -name "pytest.ini" -o -name "pyproject.toml" -o -name "setup.cfg" -o -path "*/tests" \) | grep -q .; then
        TEST_COMMAND="pytest"
    else
        {
            echo "# Test Output"
            echo ""
            echo "No test command found."
        } > "$OUT"
        echo "NO_TESTS"
        exit 0
    fi
fi

if printf "%s" "$TEST_COMMAND" | grep -Eiq '(^|[;&|])\s*(npm|pnpm|yarn|pip|uv|conda)\s+(install|add|sync)|migrate|deploy|rm\s+-|git\s+reset|git\s+clean'; then
    {
        echo "# Test Output"
        echo ""
        echo "Refused unsafe test command: $TEST_COMMAND"
    } > "$OUT"
    echo "BLOCKED"
    exit 2
fi

timeout_seconds=$((MAX_MINUTES * 60))
{
    echo "# Test Output"
    echo ""
    echo "Command: \`$TEST_COMMAND\`"
    echo ""
    echo '```'
    cd "$PROJECT_DIR"
    set +e
    timeout "$timeout_seconds" bash -lc "$TEST_COMMAND"
    code=$?
    set -e
    echo '```'
    echo ""
    echo "Exit Code: $code"
    exit "$code"
} > "$OUT" 2>&1

#!/bin/bash
# Run Graphify on a single project
set -e

GRAPHIFY_VENV="/mnt/d/_ai_brain/runtimes/graphify_venv"
PROJECT_PATH="${1:?Usage: graphify_project.sh <project_path>}"
GLOBAL_GRAPH_DIR="/mnt/d/_ai_brain/global"

source "$GRAPHIFY_VENV/bin/activate"

echo "=== Graphify: $PROJECT_PATH ==="
echo "Time: $(date)"

# Check if project exists
if [ ! -d "$PROJECT_PATH" ]; then
    echo "ERROR: Project path does not exist: $PROJECT_PATH"
    exit 1
fi

# Check size (rough file count)
FILE_COUNT=$(find "$PROJECT_PATH" -maxdepth 5 -type f \
    -not -path "*/node_modules/*" \
    -not -path "*/.git/*" \
    -not -path "*/venv/*" \
    -not -path "*/.next/*" \
    -not -path "*/dist/*" \
    -not -path "*/build/*" \
    -not -path "*/__pycache__/*" \
    2>/dev/null | wc -l)

echo "Estimated source files: $FILE_COUNT"

if [ "$FILE_COUNT" -gt 10000 ]; then
    echo "WARNING: Very large project ($FILE_COUNT files). Skipping."
    exit 1
fi

# Run graphify
echo ""
echo "Running graphify..."
cd "$PROJECT_PATH"
graphify . 2>&1

echo ""
echo "=== Graphify complete for $PROJECT_PATH ==="

# Check output
if [ -f "$PROJECT_PATH/graphify-out/graph.json" ]; then
    echo "Graph generated: $PROJECT_PATH/graphify-out/graph.json"
    local_size=$(wc -c < "$PROJECT_PATH/graphify-out/graph.json")
    echo "Graph size: $local_size bytes"
    
    # Run explain on entry point if it exists
    echo ""
    echo "--- Quick graph queries ---"
    graphify explain "page.tsx" --graph "$PROJECT_PATH/graphify-out/graph.json" 2>/dev/null || true
else
    echo "WARNING: No graph.json generated"
fi

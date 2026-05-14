#!/bin/bash

TARGET=$1
QUERY=$2

if [ -z "$TARGET" ] || [ -z "$QUERY" ]; then
    echo "Usage: $0 <project_key|global> \"<query>\""
    exit 1
fi

REGISTRY_DIR="/mnt/d/_ai_brain/registry"
PROJECTS_YAML="$REGISTRY_DIR/projects.yaml"
RUNS_DIR="/mnt/d/_ai_brain/runs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RUN_DIR="$RUNS_DIR/${TIMESTAMP}_graph_${TARGET}"

mkdir -p "$RUN_DIR"

if [ "$TARGET" == "global" ]; then
    GRAPH_PATH="$HOME/.graphify/global-graph.json"
else
    # Look up project graph path
    GRAPH_PATH=$(/mnt/d/_ai_brain/runtimes/workstation_venv/bin/python3 -c "
import yaml
with open('$PROJECTS_YAML', 'r') as f:
    data = yaml.safe_load(f)
    project = data['projects'].get('$TARGET')
    if project:
        print(project.get('wsl_path', '') + '/graphify-out/graph.json')
")
fi

if [ ! -f "$GRAPH_PATH" ]; then
    echo "Error: Graph file not found at $GRAPH_PATH"
    exit 1
fi

echo "Querying Graph: $GRAPH_PATH"
echo "Query: $QUERY"

# Mocking graphify query for now if not in path, 
# but instructions say Graphify is in a venv.
VENV_PATH="/mnt/d/_ai_brain/runtimes/graphify_venv/bin/activate"
source "$VENV_PATH"

graphify query "$QUERY" --graph "$GRAPH_PATH" > "$RUN_DIR/graph_output.txt"

echo "Result saved to $RUN_DIR/graph_output.txt"
cat "$RUN_DIR/graph_output.txt"

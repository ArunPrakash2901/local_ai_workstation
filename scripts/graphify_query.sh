#!/bin/bash
# Query the global Graphify knowledge graph
set -e

GRAPHIFY_VENV="/mnt/d/_ai_brain/runtimes/graphify_venv"
GLOBAL_GRAPH="/home/$(whoami)/.graphify/global-graph.json"

if [ -z "$1" ]; then
    echo "Usage: graphify_query.sh \"Your question here\""
    exit 1
fi

source "$GRAPHIFY_VENV/bin/activate"

echo "Querying global graph for: $1"
echo "-----------------------------------"
graphify query "$1" --graph "$GLOBAL_GRAPH"

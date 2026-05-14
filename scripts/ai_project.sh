#!/bin/bash

WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
if [ -f "$WS_HOME/scripts/ws_env.sh" ]; then
    source "$WS_HOME/scripts/ws_env.sh"
fi

PROJECT_KEY=$1
if [ -z "$PROJECT_KEY" ]; then
    echo "Usage: $0 <project_key>"
    exit 1
fi

REGISTRY_DIR="$WS_HOME/registry"
PROJECTS_YAML="$REGISTRY_DIR/projects.yaml"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

$PYTHON -c "
import yaml
import sys
import os

with open('$PROJECTS_YAML', 'r') as f:
    data = yaml.safe_load(f)
    project = data['projects'].get('$PROJECT_KEY')
    if not project:
        print(f'Error: Project \"$PROJECT_KEY\" not found in registry.')
        sys.exit(1)
    
    print(f'Project: {project.get(\"display_name\", \"$PROJECT_KEY\")}')
    print(f'Type:    {project.get(\"project_type\", \"unknown\")}')
    print(f'Status:  {project.get(\"status\", \"unknown\")}')
    print(f'Path:    {project.get(\"windows_path\", \"unknown\")}')
    print(f'Graph:   {project.get(\"graph_path\", \"unknown\")}')
    print(f'Notes:   {project.get(\"notes\", \"\")}')
    
    # Check if graph exists
    graph_path = project.get(\"graph_path\")
    if graph_path and graph_path != \"unknown\":
        # Convert windows path to wsl path for checking if we are in wsl
        # But here we can just use the graph_path if it was windows style, or expect wsl style
        # Let's try to find it
        wsl_graph_path = project.get(\"wsl_path\") + \"/graphify-out/graph.json\"
        if os.path.exists(wsl_graph_path):
            print(f'Graph Check: FOUND at {wsl_graph_path}')
        else:
            print(f'Graph Check: NOT FOUND at {wsl_graph_path}')
    
    print('\nSuggested Commands:')
    print(f'  ai_ask $PROJECT_KEY \"your question\"')
    print(f'  ai_audit $PROJECT_KEY')
"

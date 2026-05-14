#!/bin/bash
set -euo pipefail

WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
MODEL_HOME="${MODEL_HOME:-/mnt/d/ollama/models}"
if [ -f "$WS_HOME/scripts/ws_env.sh" ]; then
    source "$WS_HOME/scripts/ws_env.sh"
fi
WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
MODEL_HOME="${MODEL_HOME:-/mnt/d/ollama/models}"

PROJECT_KEY=${1:-}
TASK_JSON=${2:-}
TASK_INDEX=${3:-0}
RUN_DIR=${4:-}

if [ -z "$PROJECT_KEY" ] || [ -z "$TASK_JSON" ] || [ -z "$RUN_DIR" ]; then
    echo "Usage: ws_context_pack.sh <project_key> <tasks_json> <task_index> <run_dir>"
    exit 1
fi

BASE="$WS_HOME"
PYTHON="$BASE/runtimes/workstation_venv/bin/python3"
GRAPHIFY="$BASE/runtimes/graphify_venv/bin/graphify"
PROJECTS_YAML="$BASE/registry/projects.yaml"

mkdir -p "$RUN_DIR"

"$PYTHON" - "$PROJECT_KEY" "$TASK_JSON" "$TASK_INDEX" "$RUN_DIR" "$PROJECTS_YAML" "$GRAPHIFY" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

import yaml

project_key, task_json, task_index, run_dir, projects_yaml, graphify = sys.argv[1:]
task_index = int(task_index)
run_dir = Path(run_dir)
tasks = json.loads(Path(task_json).read_text(encoding="utf-8"))["tasks"]
task = tasks[task_index]
projects = yaml.safe_load(Path(projects_yaml).read_text(encoding="utf-8"))["projects"]
project = projects.get(project_key)
if not project:
    print(f"Project not found: {project_key}", file=sys.stderr)
    sys.exit(1)

project_path = Path(project.get("wsl_path", ""))
graph_path = project_path / "graphify-out" / "graph.json"

metadata = [
    f"# Project Metadata",
    "",
    f"- Key: {project_key}",
    f"- Name: {project.get('display_name', project_key)}",
    f"- Type: {project.get('project_type', 'unknown')}",
    f"- WSL Path: {project_path}",
    f"- Graph Path: {graph_path}",
    f"- Safe To Modify: {project.get('safe_to_modify', False)}",
    f"- Notes: {project.get('notes', '')}",
]
run_dir.joinpath("project_metadata.md").write_text("\n".join(metadata) + "\n", encoding="utf-8")
run_dir.joinpath("task.md").write_text(task["raw"], encoding="utf-8")

query = f"{task['title']}\n{task['goal']}\n" + "\n".join(task["acceptance_criteria"])
if graph_path.is_file() and Path(graphify).is_file():
    try:
        result = subprocess.run(
            [graphify, "query", query, "--graph", str(graph_path)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=45,
            check=False,
        )
        graph_context = result.stdout.strip() if result.returncode == 0 else f"Graphify query failed: {result.stderr[:1200]}"
    except subprocess.TimeoutExpired:
        graph_context = "Graphify query timed out after 45 seconds."
else:
    graph_context = f"No project graph available at {graph_path}."

if len(graph_context) > 10000:
    graph_context = graph_context[:10000] + "\n...[truncated for 8192 context safety]"
run_dir.joinpath("graph_context.md").write_text(graph_context + "\n", encoding="utf-8")

allowed = "\n".join(f"- {x}" for x in task["allowed_files"]) or "- not specified"
criteria = "\n".join(f"- {x}" for x in task["acceptance_criteria"])
context = f"""# Build Context Pack

## Task
- ID: {task['id']}
- Title: {task['title']}
- Risk: {task['risk']}

## Goal
{task['goal']}

## Acceptance Criteria
{criteria}

## Allowed Files
{allowed}

## Test Command
{task['test_command'] or 'not specified'}

## Project Metadata
{run_dir.joinpath('project_metadata.md').read_text(encoding='utf-8')}

## Compact Graphify Context
{graph_context}

## Safety Boundary
Do not read or modify secrets, credentials, raw datasets, model files, archives, build outputs, dependency folders, `.git`, or `graphify-out`. Use local Hermes first. Escalate only if explicitly enabled.
"""
run_dir.joinpath("context_pack.md").write_text(context, encoding="utf-8", newline="\n")
print(run_dir / "context_pack.md")
PY

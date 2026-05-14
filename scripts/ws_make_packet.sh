#!/bin/bash
set -euo pipefail

TARGET=${1:-}
QUESTION=${2:-}

if [ -z "$TARGET" ] || [ -z "$QUESTION" ]; then
    echo "Usage: ws packet <project_key|global> \"<question>\""
    exit 1
fi

BASE="/mnt/d/_ai_brain"
PROJECTS_YAML="$BASE/registry/projects.yaml"
ACTIVE_MODEL_YAML="$BASE/registry/active_model.yaml"
ACTIVE_KV_YAML="$BASE/registry/active_kv_profile.yaml"
PACKETS_DIR="$BASE/frontier/packets"
RESPONSES_DIR="$BASE/frontier/responses"
LOGS_DIR="$BASE/frontier/logs"
PYTHON="$BASE/runtimes/workstation_venv/bin/python3"
GRAPHIFY="$BASE/runtimes/graphify_venv/bin/graphify"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SAFE_TARGET=$(printf "%s" "$TARGET" | tr -c 'A-Za-z0-9_.-' '_')
PACKET_FILE="$PACKETS_DIR/${TIMESTAMP}_packet_${SAFE_TARGET}.md"

mkdir -p "$PACKETS_DIR" "$RESPONSES_DIR" "$LOGS_DIR"

"$PYTHON" - "$TARGET" "$QUESTION" "$PACKET_FILE" "$PROJECTS_YAML" "$ACTIVE_MODEL_YAML" "$ACTIVE_KV_YAML" "$GRAPHIFY" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

import yaml

target, question, packet_file, projects_yaml, active_model_yaml, active_kv_yaml, graphify = sys.argv[1:]

projects = yaml.safe_load(Path(projects_yaml).read_text(encoding="utf-8")) or {}
active_model = yaml.safe_load(Path(active_model_yaml).read_text(encoding="utf-8")) or {}
active_kv = yaml.safe_load(Path(active_kv_yaml).read_text(encoding="utf-8")) or {}

project_key = target
project_name = "Global Workstation"
project_type = "global"
graph_path = str(Path.home() / ".graphify" / "global-graph.json")
project_metadata = {
    "project_key": "global",
    "name": project_name,
    "type": project_type,
    "graph_path": graph_path,
}

if target != "global":
    project = (projects.get("projects") or {}).get(target)
    if not project:
        print(f"Error: project key not found: {target}", file=sys.stderr)
        sys.exit(1)
    project_name = project.get("display_name", target)
    project_type = project.get("project_type", "unknown")
    wsl_path = project.get("wsl_path", "")
    graph_path = str(Path(wsl_path) / "graphify-out" / "graph.json") if wsl_path else ""
    project_metadata = {
        "project_key": target,
        "name": project_name,
        "type": project_type,
        "graph_path": graph_path,
        "status": project.get("status", "unknown"),
        "priority": project.get("priority", "unknown"),
        "notes": project.get("notes", ""),
    }

def compact_global_registry():
    rows = []
    for key, project in (projects.get("projects") or {}).items():
        rows.append(
            f"- {key}: {project.get('display_name', key)}; "
            f"type={project.get('project_type', 'unknown')}; "
            f"status={project.get('status', 'unknown')}; "
            f"priority={project.get('priority', 'unknown')}; "
            f"notes={project.get('notes', '')}"
        )
    return "\n".join(rows) if rows else "No registered projects found."

def query_graph():
    gp = Path(graph_path)
    if not graph_path or not gp.is_file():
        if target == "global":
            return (
                "Global Graphify graph was not found at "
                f"`{graph_path}`. Compact registry context used instead:\n\n"
                + compact_global_registry()
            )
        return f"Project Graphify graph was not found at `{graph_path}`."

    if not Path(graphify).is_file():
        return f"Graphify executable was not found at `{graphify}`."

    try:
        result = subprocess.run(
            [graphify, "query", question, "--graph", graph_path],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=45,
        )
    except subprocess.TimeoutExpired:
        return "Graphify query timed out after 45 seconds. No graph context included."

    output = result.stdout.strip()
    if result.returncode != 0:
        err = result.stderr.strip()
        return f"Graphify query failed locally with exit code {result.returncode}.\n\n{err[:1200]}"
    if not output:
        return "Graphify returned no matching context."

    lines = output.splitlines()
    compact = "\n".join(lines[:80])
    if len(compact) > 10_000:
        compact = compact[:10_000] + "\n...[truncated for packet safety]"
    return compact

graph_context = query_graph()

metadata_lines = [
    f"- Project Key: {project_metadata.get('project_key')}",
    f"- Name: {project_metadata.get('name')}",
    f"- Type: {project_metadata.get('type')}",
    f"- Graph Path: {project_metadata.get('graph_path')}",
]
for key in ("status", "priority", "notes"):
    if project_metadata.get(key):
        metadata_lines.append(f"- {key.title()}: {project_metadata[key]}")

local_notes = [
    f"- Active profile: {active_model.get('active_profile', 'unknown')}",
    f"- Active model: {active_model.get('active_model', 'unknown')}",
    f"- Active mode: {active_model.get('mode', 'unknown')}",
    f"- Active KV profile: {active_kv.get('active_profile', 'unknown')}",
    f"- KV type: {active_kv.get('kv_cache_type', 'unknown')}",
    f"- Context: {active_model.get('context_length', 'unknown')} model / {active_kv.get('context', 'unknown')} KV",
    "- No frontier CLI was called while creating this packet.",
]

packet = f"""# Escalation Packet

## Target
{target}

## Intended Provider
unset

## Reason for Escalation
user requested frontier-ready packet

## User Question
{question}

## Project Metadata
{chr(10).join(metadata_lines)}

## Local Context
{graph_context}

## Local Model Notes
{chr(10).join(local_notes)}

## Relevant Error or Test Output
blank unless provided

## Specific Question for Frontier Model
Please answer this narrow workstation escalation question: {question}

## Safety Notice
Secrets, raw datasets, credentials, .env files, private keys, and broker keys were excluded.
"""

Path(packet_file).write_text(packet, encoding="utf-8", newline="\n")
print(packet_file)
PY

echo "Packet created: $PACKET_FILE"

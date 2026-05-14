#!/bin/bash
set -euo pipefail

WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
MODEL_HOME="${MODEL_HOME:-/mnt/d/ollama/models}"
if [ -f "$WS_HOME/scripts/ws_env.sh" ]; then
    source "$WS_HOME/scripts/ws_env.sh"
fi
WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
MODEL_HOME="${MODEL_HOME:-/mnt/d/ollama/models}"

BASE="$WS_HOME"
TASK_ROOT="$BASE/tasks"
PYTHON="$BASE/runtimes/workstation_venv/bin/python3"

mkdir -p "$TASK_ROOT/inbox" "$TASK_ROOT/active" "$TASK_ROOT/completed" "$TASK_ROOT/blocked" "$TASK_ROOT/generated" "$TASK_ROOT/reviewed"

"$PYTHON" - "$TASK_ROOT" "$@" <<'PY'
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

task_root = Path(sys.argv[1])
argv = sys.argv[2:]

p = argparse.ArgumentParser()
p.add_argument("--project", default="workstation_control_plane")
p.add_argument("--title", default="")
p.add_argument("--goal", default="")
p.add_argument("--source", default="manual")
p.add_argument("--risk", default="low", choices=["low", "medium", "high"])
p.add_argument("--allowed", action="append", default=[])
p.add_argument("--test", default="")
p.add_argument("--notes", default="")
args = p.parse_args(argv)

if not args.title:
    args.title = input("Title: ").strip()
if not args.goal:
    args.goal = input("Goal: ").strip()
if not args.title or not args.goal:
    print("Title and goal are required.", file=sys.stderr)
    sys.exit(1)

ts = datetime.now().strftime("%Y%m%d_%H%M%S")
slug = re.sub(r"[^a-zA-Z0-9]+", "_", args.title).strip("_").lower()[:50] or "task"
task_id = f"{ts}_{slug}"
path = task_root / "inbox" / f"{task_id}.md"

allowed = args.allowed or ["not specified"]
criteria = ["Task goal is addressed.", "Changes stay within safety boundaries."]

text = f"""# Task {task_id}: {args.title}

Source:
{args.source}

Project:
{args.project}

Status:
inbox

Goal:
{args.goal}

Acceptance Criteria:
{chr(10).join(f"- {x}" for x in criteria)}

Allowed Files:
{chr(10).join(f"- {x}" for x in allowed)}

Denied Files:
- .env
- credentials
- raw datasets
- data/*
- models/*
- node_modules/*
- .git/*

Test Command:
{args.test}

Risk:
{args.risk}

Escalation:
none

Notes:
{args.notes}
"""
path.write_text(text, encoding="utf-8", newline="\n")
print(path)
PY

#!/bin/bash
set -euo pipefail

WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
if [ -f "$WS_HOME/scripts/ws_env.sh" ]; then
    source "$WS_HOME/scripts/ws_env.sh"
fi

FRONTIER_YAML="$WS_HOME/registry/frontier.yaml"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

mkdir -p "$WS_HOME/frontier/packets"
mkdir -p "$WS_HOME/frontier/responses"
mkdir -p "$WS_HOME/frontier/logs"

"$PYTHON" - "$FRONTIER_YAML" <<'PY'
import shutil
import sys
from pathlib import Path

frontier_yaml = Path(sys.argv[1])

providers = {
    "gemini": {
        "command": "gemini",
        "mode": "terminal_cli",
        "non_interactive": "gemini -p <packet>",
        "best_for": ["deep reasoning", "strategy", "large synthesis", "research"],
    },
    "codex": {
        "command": "codex",
        "mode": "terminal_cli",
        "non_interactive": "codex exec --skip-git-repo-check --sandbox read-only -",
        "best_for": ["coding review", "refactor planning", "implementation strategy", "debugging"],
    },
    "claude": {
        "command": "claude",
        "mode": "terminal_cli",
        "non_interactive": "unavailable",
        "best_for": ["debugging", "architecture review", "explanation", "code reasoning"],
    },
}

for info in providers.values():
    info["enabled"] = bool(shutil.which(info["command"]))

out = []
for name, info in providers.items():
    out.append(f"{name}:")
    out.append(f"  command: {info['command']}")
    out.append(f"  mode: {info['mode']}")
    out.append(f"  enabled: {str(info['enabled']).lower()}")
    out.append(f"  non_interactive: {info['non_interactive']}")
    out.append("  best_for:")
    for item in info["best_for"]:
        out.append(f"    - {item}")
    out.append("")

frontier_yaml.write_text("\n".join(out), encoding="utf-8")

print("Frontier Provider Status:")
print("------------------------")
for name, info in providers.items():
    path = shutil.which(info["command"])
    status = f"DETECTED ({path})" if path else "NOT FOUND"
    print(f"{name:10} | {status}")
    print(f"{'':10} | command: {info['command']}")
    print(f"{'':10} | non-interactive: {info['non_interactive']}")
    print(f"{'':10} | best for: {', '.join(info['best_for'])}")
PY

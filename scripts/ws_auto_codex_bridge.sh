#!/bin/bash
set -euo pipefail

WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
if [ -f "$WS_HOME/scripts/ws_env.sh" ]; then
    source "$WS_HOME/scripts/ws_env.sh"
fi
WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"

RUN_DIR=${1:-}
PACKET_FILE=${2:-}

if [ -z "$RUN_DIR" ]; then
    echo "Usage: ws_auto_codex_bridge.sh <run_dir> [packet_path]"
    exit 1
fi

RUN_DIR=${RUN_DIR//\\//}
if [[ "$RUN_DIR" =~ ^([A-Za-z]):/(.*)$ ]]; then
    drive=$(echo "${BASH_REMATCH[1]}" | tr 'A-Z' 'a-z')
    RUN_DIR="/mnt/$drive/${BASH_REMATCH[2]}"
fi

if [ -z "$PACKET_FILE" ]; then
    PACKET_FILE="$RUN_DIR/codex_packet.md"
fi
PACKET_FILE=${PACKET_FILE//\\//}
if [[ "$PACKET_FILE" =~ ^([A-Za-z]):/(.*)$ ]]; then
    drive=$(echo "${BASH_REMATCH[1]}" | tr 'A-Z' 'a-z')
    PACKET_FILE="/mnt/$drive/${BASH_REMATCH[2]}"
fi

if [ ! -d "$RUN_DIR" ]; then
    echo "Run directory not found: $RUN_DIR"
    exit 1
fi

if [ ! -f "$PACKET_FILE" ]; then
    echo "Packet file not found: $PACKET_FILE"
    exit 1
fi

PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

"$PYTHON" - "$WS_HOME" "$RUN_DIR" "$PACKET_FILE" <<'PY'
import json
import re
import subprocess
import sys
from pathlib import Path

ws_home = Path(sys.argv[1])
run_dir = Path(sys.argv[2])
packet = Path(sys.argv[3])
redactor = ws_home / "scripts" / "ws_redact_packet.sh"
escalator = ws_home / "scripts" / "ws_escalate.sh"

usage_path = run_dir / "codex_usage.md"
response_copy = run_dir / "codex_response.md"

redact = subprocess.run(
    ["bash", str(redactor), str(packet)],
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    timeout=120,
    check=False,
)
redaction_output = redact.stdout.strip()
redaction_status = "SAFE" if redact.returncode == 0 and redaction_output.endswith("SAFE") else "UNSAFE"

result = {
    "redaction_status": redaction_status,
    "redaction_exit_code": redact.returncode,
    "redaction_output": redaction_output,
    "status": "SAFETY_BLOCKED" if redaction_status != "SAFE" else "BLOCKED_CODEX",
    "used": False,
    "response_path": "",
    "log_path": "",
    "escalation_output": "",
}

if redaction_status == "SAFE":
    send = subprocess.run(
        ["bash", str(escalator), "codex", str(packet)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=300,
        check=False,
    )
    escalation_output = send.stdout.strip()
    result["escalation_output"] = escalation_output
    response_match = re.search(r"^Response path:\s*(.+)$", escalation_output, re.M)
    log_match = re.search(r"^Log path:\s*(.+)$", escalation_output, re.M)
    response_path = Path(response_match.group(1).strip()) if response_match else None
    log_path = Path(log_match.group(1).strip()) if log_match else None
    result["response_path"] = str(response_path) if response_path else ""
    result["log_path"] = str(log_path) if log_path else ""
    if send.returncode == 0 and response_path and response_path.exists():
        result["status"] = "SENT"
        result["used"] = True
        response_copy.write_text(response_path.read_text(encoding="utf-8", errors="replace"), encoding="utf-8", newline="\n")
    else:
        result["status"] = "BLOCKED_CODEX"
        if response_path and response_path.exists():
            response_copy.write_text(response_path.read_text(encoding="utf-8", errors="replace"), encoding="utf-8", newline="\n")

usage_path.write_text(
    "\n".join(
        [
            "# Codex Usage",
            "",
            f"- Redaction Status: {result['redaction_status']}",
            f"- Redaction Exit Code: {result['redaction_exit_code']}",
            f"- Sent: {str(result['used']).lower()}",
            f"- Status: {result['status']}",
            f"- Response Path: {result['response_path'] or 'none'}",
            f"- Log Path: {result['log_path'] or 'none'}",
            "",
            "## Redaction Output",
            "",
            result["redaction_output"] or "blank",
            "",
            "## Escalation Output",
            "",
            result["escalation_output"] or "blank",
            "",
        ]
    ),
    encoding="utf-8",
    newline="\n",
)

print(json.dumps(result, indent=2, sort_keys=True))
PY

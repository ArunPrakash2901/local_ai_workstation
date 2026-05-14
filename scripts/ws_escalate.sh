#!/bin/bash
set -euo pipefail

PROVIDER=${1:-}
PACKET_ARG=${2:-}

BASE="/mnt/d/_ai_brain"
PACKETS_DIR="$BASE/frontier/packets"
RESPONSES_DIR="$BASE/frontier/responses"
LOGS_DIR="$BASE/frontier/logs"
REDACTOR="$BASE/scripts/ws_redact_packet.sh"
PYTHON="$BASE/runtimes/workstation_venv/bin/python3"

usage() {
    echo "Usage: ws escalate <gemini|codex|claude> <packet_path|latest>"
}

if [ -z "$PROVIDER" ] || [ -z "$PACKET_ARG" ]; then
    usage
    exit 1
fi

mkdir -p "$RESPONSES_DIR" "$LOGS_DIR"

case "$PROVIDER" in
    gemini|codex|claude) ;;
    *)
        echo "Unsupported provider: $PROVIDER"
        usage
        exit 1
        ;;
esac

if [ "$PACKET_ARG" = "latest" ]; then
    PACKET=$(ls -t "$PACKETS_DIR"/*.md 2>/dev/null | head -n 1 || true)
else
    PACKET="$PACKET_ARG"
fi

if [ -z "${PACKET:-}" ] || [ ! -f "$PACKET" ]; then
    echo "Packet not found: $PACKET_ARG"
    exit 1
fi

PACKET=$(readlink -f "$PACKET")
TS=$(date +%Y%m%d_%H%M%S)
BASENAME=$(basename "$PACKET" .md)
RESPONSE="$RESPONSES_DIR/${TS}_${PROVIDER}_${BASENAME}_response.md"
LOG="$LOGS_DIR/${TS}_${PROVIDER}_${BASENAME}.log"

{
    echo "Frontier escalation log"
    echo "timestamp: $TS"
    echo "provider: $PROVIDER"
    echo "packet: $PACKET"
    echo "response: $RESPONSE"
    echo ""
} > "$LOG"

echo "Running redaction before escalation..."
set +e
REDACTION_OUTPUT=$(bash "$REDACTOR" "$PACKET" 2>&1)
REDACTION_CODE=$?
set -e
printf "%s\n" "$REDACTION_OUTPUT"
{
    echo "Redaction output:"
    printf "%s\n" "$REDACTION_OUTPUT"
    echo "redaction_exit_code: $REDACTION_CODE"
    echo ""
} >> "$LOG"

if [ "$REDACTION_CODE" -ne 0 ] || ! printf "%s\n" "$REDACTION_OUTPUT" | grep -qx "SAFE"; then
    echo "Escalation refused: packet redaction did not return SAFE."
    echo "Log path: $LOG"
    exit 2
fi

PACKET_WIN=$("$PYTHON" - "$PACKET" <<'PY'
import sys
from pathlib import Path
p = Path(sys.argv[1])
text = str(p)
if text.startswith("/mnt/") and len(text) > 6:
    drive = text[5].upper()
    rest = text[7:].replace("/", "\\")
    print(f"{drive}:\\{rest}")
else:
    print(text)
PY
)
BASE_WIN="D:\\_ai_brain"

write_manual() {
    local reason=$1
    local manual=$2
    {
        echo "# Frontier Escalation Not Sent"
        echo ""
        echo "Provider: \`$PROVIDER\`"
        echo "Packet: \`$PACKET\`"
        echo ""
        echo "Reason: $reason"
        echo ""
        echo "Manual command:"
        echo ""
        echo '```powershell'
        echo "$manual"
        echo '```'
    } > "$RESPONSE"
    {
        echo "not_sent_reason: $reason"
        echo "manual_command: $manual"
    } >> "$LOG"
    echo "Escalation not sent: $reason"
    echo "Response path: $RESPONSE"
    echo "Log path: $LOG"
}

if [ "$PROVIDER" = "claude" ]; then
    write_manual "Claude CLI is not installed or not on PATH." "claude < \"$PACKET_WIN\""
    exit 3
fi

if [ "$PROVIDER" = "gemini" ]; then
    if ! command -v gemini >/dev/null 2>&1; then
        write_manual "Gemini CLI command was not found in WSL." "gemini -p \"\$(Get-Content -Raw -LiteralPath '$PACKET_WIN')\""
        exit 3
    fi
    set +e
    GEMINI_HELP=$(timeout 10 gemini --help 2>&1)
    GEMINI_HELP_CODE=$?
    set -e
    {
        echo "Gemini help probe exit: $GEMINI_HELP_CODE"
        printf "%s\n" "$GEMINI_HELP" | sed -n '1,40p'
    } >> "$LOG"
    if [ "$GEMINI_HELP_CODE" -ne 0 ] || printf "%s\n" "$GEMINI_HELP" | grep -qi "node: not found\|Failed to relaunch\|EPERM"; then
        write_manual "Gemini CLI is detected, but this environment cannot run it safely non-interactively." "gemini -p \"\$(Get-Content -Raw -LiteralPath '$PACKET_WIN')\""
        exit 3
    fi
    if ! printf "%s\n" "$GEMINI_HELP" | grep -Eq '(^|[[:space:]])-p([,[:space:]]|$)|--prompt'; then
        write_manual "Gemini CLI help did not confirm a non-interactive prompt flag." "gemini -p \"\$(Get-Content -Raw -LiteralPath '$PACKET_WIN')\""
        exit 3
    fi
    echo "Sending SAFE packet to Gemini CLI..."
    set +e
    timeout 180 bash -lc 'gemini -p "$(cat "$1")"' _ "$PACKET" > "$RESPONSE" 2>> "$LOG"
    SEND_CODE=$?
    set -e
elif [ "$PROVIDER" = "codex" ]; then
    set +e
    CODEX_HELP=$(powershell.exe -NoProfile -Command "codex exec --help | Select-Object -First 80" 2>&1)
    CODEX_HELP_CODE=$?
    set -e
    {
        echo "Codex exec help probe exit: $CODEX_HELP_CODE"
        printf "%s\n" "$CODEX_HELP" | sed -n '1,80p'
    } >> "$LOG"
    if [ "$CODEX_HELP_CODE" -ne 0 ] || ! printf "%s\n" "$CODEX_HELP" | grep -qi "Run Codex non-interactively"; then
        write_manual "Codex CLI did not confirm non-interactive exec support." "Get-Content -Raw -LiteralPath \"$PACKET_WIN\" | codex exec --skip-git-repo-check --sandbox read-only -C \"$BASE_WIN\" -"
        exit 3
    fi
    echo "Sending SAFE packet to Codex CLI..."
    set +e
    timeout 240 powershell.exe -NoProfile -Command "\$p = Get-Content -Raw -LiteralPath '$PACKET_WIN'; \$p | codex exec --skip-git-repo-check --sandbox read-only -C '$BASE_WIN' -" > "$RESPONSE" 2>> "$LOG"
    SEND_CODE=$?
    set -e
fi

echo "send_exit_code: $SEND_CODE" >> "$LOG"

if [ "$SEND_CODE" -ne 0 ]; then
    {
        echo ""
        echo "Provider command exited with code $SEND_CODE."
        echo "Review log: $LOG"
    } >> "$RESPONSE"
    echo "Escalation attempted but provider command failed or timed out."
    echo "Response path: $RESPONSE"
    echo "Log path: $LOG"
    exit "$SEND_CODE"
fi

echo "Response path: $RESPONSE"
echo "Log path: $LOG"

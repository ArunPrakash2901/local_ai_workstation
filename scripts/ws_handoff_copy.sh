#!/bin/bash

set -euo pipefail

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
HANDOFFS_DIR="$WS_HOME/handoffs"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"
SELECTOR=${1:-}

if [ -z "$SELECTOR" ]; then
    echo "Usage: ws handoff-copy <latest|handoff_id_or_path>"
    exit 1
fi

to_wsl_path() {
    case "$1" in
        /*) printf '%s' "$1" ;;
        *) wslpath -u "$1" 2>/dev/null || printf '%s' "$1" ;;
    esac
}

to_windows_path() {
    wslpath -w "$1" 2>/dev/null || printf '%s' "$1"
}

resolve_handoff() {
    local selector=$1
    local candidate=""
    if [ "$selector" = "latest" ]; then
        find "$HANDOFFS_DIR" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' 2>/dev/null \
            | sort -nr \
            | head -n 1 \
            | cut -d' ' -f2-
        return
    fi

    candidate=$(to_wsl_path "$selector")
    if [ -d "$candidate" ]; then
        printf '%s\n' "$candidate"
        return
    fi

    if [ -d "$HANDOFFS_DIR/$selector" ]; then
        printf '%s\n' "$HANDOFFS_DIR/$selector"
        return
    fi

    find "$HANDOFFS_DIR" -mindepth 1 -maxdepth 1 -type d -name "*$selector*" -printf '%T@ %p\n' 2>/dev/null \
        | sort -nr \
        | head -n 1 \
        | cut -d' ' -f2-
}

if [ ! -d "$HANDOFFS_DIR" ]; then
    echo "No handoff folders found."
    exit 1
fi

HANDOFF_DIR=$(resolve_handoff "$SELECTOR")
if [ -z "$HANDOFF_DIR" ] || [ ! -d "$HANDOFF_DIR" ]; then
    echo "Handoff folder not found: $SELECTOR"
    exit 1
fi

PROMPT_PATH="$HANDOFF_DIR/prompt.md"
METADATA_PATH="$HANDOFF_DIR/metadata.json"
TRANSCRIPT_PATH="$HANDOFF_DIR/transcript.md"
REPORT_PATH="$HANDOFF_DIR/handoff_report.md"

if [ ! -s "$PROMPT_PATH" ]; then
    echo "Prompt is missing or empty: $PROMPT_PATH"
    exit 1
fi

if [ ! -f "$METADATA_PATH" ]; then
    echo "Metadata file not found: $METADATA_PATH"
    exit 1
fi

if ! METADATA_SUMMARY=$(
    "$PYTHON" - "$METADATA_PATH" <<'PY'
import json
import sys
from pathlib import Path

metadata = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if metadata.get("provider_invocation") is True:
    print("REFUSE_PROVIDER_INVOCATION")
    raise SystemExit(1)
if metadata.get("browser_automation") is True:
    print("REFUSE_BROWSER_AUTOMATION")
    raise SystemExit(1)

state = metadata.get("current_state", "unknown")
if state not in {"PROMPT_READY", "BROWSER_MANUAL_REQUIRED", "COPIED_TO_CLIPBOARD"}:
    print(f"REFUSE_STATE:{state}")
    raise SystemExit(1)

print(metadata.get("target", "unknown"))
print(metadata.get("purpose", "unknown"))
print(state)
PY
); then
    case "$METADATA_SUMMARY" in
        REFUSE_PROVIDER_INVOCATION)
            echo "Refusing copy: metadata indicates provider_invocation=true."
            ;;
        REFUSE_BROWSER_AUTOMATION)
            echo "Refusing copy: metadata indicates browser_automation=true."
            ;;
        REFUSE_STATE:*)
            echo "Refusing copy: unsupported handoff state ${METADATA_SUMMARY#REFUSE_STATE:}."
            ;;
        *)
            echo "Unable to validate metadata for copy."
            ;;
    esac
    exit 1
fi

mapfile -t METADATA_FIELDS <<< "$METADATA_SUMMARY"
TARGET=${METADATA_FIELDS[0]:-unknown}
PURPOSE=${METADATA_FIELDS[1]:-unknown}
PREVIOUS_STATE=${METADATA_FIELDS[2]:-unknown}

PROMPT_WINDOWS=$(to_windows_path "$PROMPT_PATH")
powershell.exe -NoProfile -Command "Set-Clipboard -Value (Get-Content -Raw -LiteralPath '$PROMPT_WINDOWS')"

COPY_STAMP=$(date +%Y%m%d_%H%M%S)
"$PYTHON" - "$METADATA_PATH" "$TRANSCRIPT_PATH" "$REPORT_PATH" "$COPY_STAMP" "$PREVIOUS_STATE" <<'PY'
import json
import sys
from pathlib import Path

metadata_path, transcript_path, report_path, copy_stamp, previous_state = sys.argv[1:]
metadata_file = Path(metadata_path)
metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
metadata["current_state"] = "COPIED_TO_CLIPBOARD"
metadata["last_copied_timestamp"] = copy_stamp
metadata_file.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8", newline="\n")

transcript = Path(transcript_path)
with transcript.open("a", encoding="utf-8", newline="\n") as handle:
    handle.write(
        f"\n## {copy_stamp} - Prompt Copied\n"
        f"- Previous state: {previous_state}\n"
        "- State: COPIED_TO_CLIPBOARD\n"
        "- Provider invocation: false\n"
        "- Browser automation: false\n"
    )

report = Path(report_path)
if report.is_file():
    text = report.read_text(encoding="utf-8")
    text = text.replace(f"- State: {previous_state}", "- State: COPIED_TO_CLIPBOARD", 1)
else:
    text = "# Handoff Report\n"
text = text.rstrip() + (
    f"\n\n## Copy Event\n"
    f"- Timestamp: {copy_stamp}\n"
    f"- Previous State: {previous_state}\n"
    "- State: COPIED_TO_CLIPBOARD\n"
    "- Prompt copied to Windows clipboard only.\n"
    "- Provider invocation: false\n"
    "- Browser automation: false\n"
)
report.write_text(text + "\n", encoding="utf-8", newline="\n")
PY

echo "State: COPIED_TO_CLIPBOARD"
echo "Target: $TARGET"
echo "Purpose: $PURPOSE"
echo "Prompt: $(to_windows_path "$PROMPT_PATH")"
if [ "$TARGET" = "chatgpt" ] || [ "$TARGET" = "gemini-browser" ]; then
    echo "Next safe action: paste manually into the ChatGPT/Gemini browser lane."
else
    echo "Next safe action: review the copied prompt manually; no provider was invoked."
fi

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
SOURCE=${2:-}

if [ -z "$SELECTOR" ] || [ "$SOURCE" != "--from-clipboard" ] || [ $# -ne 2 ]; then
    echo "Usage: ws handoff-import <latest|handoff_id_or_path> --from-clipboard"
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

METADATA_PATH="$HANDOFF_DIR/metadata.json"
RESPONSE_PATH="$HANDOFF_DIR/response.md"
TRANSCRIPT_PATH="$HANDOFF_DIR/transcript.md"
REPORT_PATH="$HANDOFF_DIR/handoff_report.md"

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
if state not in {
    "PROMPT_READY",
    "BROWSER_MANUAL_REQUIRED",
    "COPIED_TO_CLIPBOARD",
    "RESPONSE_IMPORTED",
}:
    print(f"REFUSE_STATE:{state}")
    raise SystemExit(1)

print(metadata.get("target", "unknown"))
print(metadata.get("purpose", "unknown"))
print(state)
print(metadata.get("feature_path", ""))
print(metadata.get("feature_id", ""))
PY
); then
    case "$METADATA_SUMMARY" in
        REFUSE_PROVIDER_INVOCATION)
            echo "Refusing import: metadata indicates provider_invocation=true."
            ;;
        REFUSE_BROWSER_AUTOMATION)
            echo "Refusing import: metadata indicates browser_automation=true."
            ;;
        REFUSE_STATE:*)
            echo "Refusing import: unsupported handoff state ${METADATA_SUMMARY#REFUSE_STATE:}."
            ;;
        *)
            echo "Unable to validate metadata for import."
            ;;
    esac
    exit 1
fi

mapfile -t METADATA_FIELDS <<< "$METADATA_SUMMARY"
TARGET=${METADATA_FIELDS[0]:-unknown}
PURPOSE=${METADATA_FIELDS[1]:-unknown}
PREVIOUS_STATE=${METADATA_FIELDS[2]:-unknown}
FEATURE_PATH=${METADATA_FIELDS[3]:-}
FEATURE_ID=${METADATA_FIELDS[4]:-}

CLIPBOARD_TEXT=$(powershell.exe -NoProfile -Command "Get-Clipboard -Raw" | sed 's/\r$//')
if [ -z "$(printf '%s' "$CLIPBOARD_TEXT" | tr -d '[:space:]')" ]; then
    echo "Refusing import: Windows clipboard is empty."
    exit 1
fi

IMPORT_STAMP=$(date +%Y%m%d_%H%M%S)
printf '%s' "$CLIPBOARD_TEXT" > "$RESPONSE_PATH"
printf '\n' >> "$RESPONSE_PATH"

"$PYTHON" - \
    "$METADATA_PATH" \
    "$TRANSCRIPT_PATH" \
    "$REPORT_PATH" \
    "$FEATURE_PATH" \
    "$FEATURE_ID" \
    "$HANDOFF_DIR" \
    "$IMPORT_STAMP" \
    "$PREVIOUS_STATE" <<'PY'
import json
import sys
from pathlib import Path

(
    metadata_path,
    transcript_path,
    report_path,
    feature_path,
    feature_id,
    handoff_dir,
    import_stamp,
    previous_state,
) = sys.argv[1:]

metadata_file = Path(metadata_path)
metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
metadata["current_state"] = "RESPONSE_IMPORTED"
metadata["last_imported_timestamp"] = import_stamp
metadata["response_source"] = "clipboard"
metadata["provider_invocation"] = False
metadata["browser_automation"] = False
metadata_file.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8", newline="\n")

transcript = Path(transcript_path)
with transcript.open("a", encoding="utf-8", newline="\n") as handle:
    handle.write(
        f"\n## {import_stamp} - Response Imported\n"
        f"- Previous state: {previous_state}\n"
        "- State: RESPONSE_IMPORTED\n"
        "- Response source: clipboard\n"
        "- Provider invocation: false\n"
        "- Browser automation: false\n"
    )

report = Path(report_path)
if report.is_file():
    text = report.read_text(encoding="utf-8")
    text = text.replace(f"- State: {previous_state}", "- State: RESPONSE_IMPORTED", 1)
else:
    text = "# Handoff Report\n"
text = text.rstrip() + (
    f"\n\n## Import Event\n"
    f"- Timestamp: {import_stamp}\n"
    f"- Previous State: {previous_state}\n"
    "- State: RESPONSE_IMPORTED\n"
    "- Response source: clipboard\n"
    "- Provider invocation: false\n"
    "- Browser automation: false\n"
    "- Next safe action: inspect `response.md`; semantic review comes later.\n"
)
report.write_text(text + "\n", encoding="utf-8", newline="\n")

if feature_path:
    loop_log = Path(feature_path) / "loop_log.md"
    if loop_log.is_file():
        with loop_log.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(
                f"\n## {import_stamp} - Browser/Clipboard Response Imported\n"
                f"- Feature ID: {feature_id or 'unknown'}\n"
                f"- Handoff: {handoff_dir}\n"
                "- Provider invocation: false\n"
                "- Browser automation: false\n"
                "- Next safe action: inspect the imported response; no semantic classification has run.\n"
            )
PY

echo "State: RESPONSE_IMPORTED"
echo "Target: $TARGET"
echo "Purpose: $PURPOSE"
echo "Response: $(to_windows_path "$RESPONSE_PATH")"
echo "Next safe action: inspect response.md; semantic review comes later."

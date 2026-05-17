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

if [ -z "$SELECTOR" ] || [ $# -ne 1 ]; then
    echo "Usage: ws handoff-review <latest|handoff_id_or_path>"
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
REVIEW_PATH="$HANDOFF_DIR/review.md"
TRANSCRIPT_PATH="$HANDOFF_DIR/transcript.md"
REPORT_PATH="$HANDOFF_DIR/handoff_report.md"

if [ ! -f "$METADATA_PATH" ]; then
    echo "Metadata file not found: $METADATA_PATH"
    exit 1
fi

if [ ! -s "$RESPONSE_PATH" ]; then
    echo "Response is missing or empty: $RESPONSE_PATH"
    exit 1
fi

if ! REVIEW_INFO=$(
    "$PYTHON" - \
        "$METADATA_PATH" \
        "$RESPONSE_PATH" \
        "$REVIEW_PATH" \
        "$TRANSCRIPT_PATH" \
        "$REPORT_PATH" \
        "$HANDOFF_DIR" <<'PY'
import json
import re
import sys
from pathlib import Path

(
    metadata_path,
    response_path,
    review_path,
    transcript_path,
    report_path,
    handoff_dir,
) = sys.argv[1:]

metadata_file = Path(metadata_path)
metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
if metadata.get("current_state") != "RESPONSE_IMPORTED":
    print(f"REFUSE_STATE:{metadata.get('current_state', 'unknown')}")
    raise SystemExit(1)

response_text = Path(response_path).read_text(encoding="utf-8", errors="replace")
normalized = response_text.casefold()

accepted_patterns = [
    r"\bno blocking issue\b",
    r"\bno blocking issues\b",
    r"\bno blocker\b",
    r"\bno blockers\b",
    r"\bready for the next implementation phase\b",
]
attention_patterns = [
    r"\bblocker\b",
    r"\bblocked\b",
    r"\brisk\b",
    r"\bfailure\b",
]

accepted_matches = [pattern for pattern in accepted_patterns if re.search(pattern, normalized)]
attention_matches = [pattern for pattern in attention_patterns if re.search(pattern, normalized)]

if attention_matches:
    review_result = "REVIEW_NEEDS_ATTENTION"
    reason = "Response contains blocker/risk/failure language."
    next_action = "inspect the imported response manually before taking another step."
elif accepted_matches:
    review_result = "REVIEW_ACCEPTED"
    reason = "Response contains explicit no-blocker/ready language."
    next_action = "preserve this review as evidence; any execution decision remains separate."
else:
    review_result = "REVIEW_IMPORTED_UNCLASSIFIED"
    reason = "Response imported, but no deterministic review rule matched."
    next_action = "inspect the imported response manually before taking another step."

review_stamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
matched_acceptance = ", ".join(accepted_matches) if accepted_matches else "none"
matched_attention = ", ".join(attention_matches) if attention_matches else "none"

review = f"""# Handoff Review

- Timestamp: {review_stamp}
- Result: {review_result}
- Method: deterministic_local
- Prior State: RESPONSE_IMPORTED
- Provider Invocation: false
- Browser Automation: false

## Classification Basis

- Accepted-pattern matches: {matched_acceptance}
- Attention-pattern matches: {matched_attention}
- Reason: {reason}

## Response Excerpt

```text
{response_text.strip()}
```

## Next Safe Action

{next_action}
"""

metadata["current_state"] = review_result
metadata["last_reviewed_timestamp"] = review_stamp
metadata["review_method"] = "deterministic_local"
metadata["provider_invocation"] = False
metadata["browser_automation"] = False
metadata_file.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8", newline="\n")

Path(review_path).write_text(review, encoding="utf-8", newline="\n")

with Path(transcript_path).open("a", encoding="utf-8", newline="\n") as handle:
    handle.write(
        f"\n## {review_stamp} - Handoff Reviewed\n"
        "- Previous state: RESPONSE_IMPORTED\n"
        f"- State: {review_result}\n"
        "- Review method: deterministic_local\n"
        "- Provider invocation: false\n"
        "- Browser automation: false\n"
    )

report = Path(report_path)
if report.is_file():
    text = report.read_text(encoding="utf-8")
    text = text.replace("- State: RESPONSE_IMPORTED", f"- State: {review_result}", 1)
else:
    text = "# Handoff Report\n"
text = text.rstrip() + (
    f"\n\n## Review Event\n"
    f"- Timestamp: {review_stamp}\n"
    "- Previous State: RESPONSE_IMPORTED\n"
    f"- State: {review_result}\n"
    "- Review method: deterministic_local\n"
    f"- Reason: {reason}\n"
    "- Provider invocation: false\n"
    "- Browser automation: false\n"
    f"- Next safe action: {next_action}\n"
)
report.write_text(text + "\n", encoding="utf-8", newline="\n")

feature_path = metadata.get("feature_path", "")
feature_id = metadata.get("feature_id", "")
if feature_path:
    loop_log = Path(feature_path) / "loop_log.md"
    if loop_log.is_file():
        with loop_log.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(
                f"\n## {review_stamp} - Handoff Reviewed\n"
                f"- Feature ID: {feature_id or 'unknown'}\n"
                f"- Review result: {review_result}\n"
                f"- Handoff: {handoff_dir}\n"
                "- Provider invocation: false\n"
                "- Browser automation: false\n"
            )

print(review_result)
print(review_stamp)
print(reason)
print(next_action)
PY
); then
    case "$REVIEW_INFO" in
        REFUSE_STATE:*)
            echo "Refusing review: handoff state must be RESPONSE_IMPORTED, found ${REVIEW_INFO#REFUSE_STATE:}."
            ;;
        *)
            echo "Unable to review handoff."
            ;;
    esac
    exit 1
fi

mapfile -t REVIEW_FIELDS <<< "$REVIEW_INFO"
REVIEW_RESULT=${REVIEW_FIELDS[0]:-UNKNOWN}
REVIEW_STAMP=${REVIEW_FIELDS[1]:-}
REVIEW_REASON=${REVIEW_FIELDS[2]:-}
NEXT_ACTION=${REVIEW_FIELDS[3]:-}

echo "State: $REVIEW_RESULT"
echo "Reviewed at: $REVIEW_STAMP"
echo "Review: $(to_windows_path "$REVIEW_PATH")"
echo "Reason: $REVIEW_REASON"
echo "Next safe action: $NEXT_ACTION"

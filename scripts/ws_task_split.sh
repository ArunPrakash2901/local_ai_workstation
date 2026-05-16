#!/bin/bash
set -euo pipefail

WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
MODEL_HOME="${MODEL_HOME:-/mnt/d/ollama/models}"
if [ -f "$WS_HOME/scripts/ws_env.sh" ]; then
    source "$WS_HOME/scripts/ws_env.sh"
fi
WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
MODEL_HOME="${MODEL_HOME:-/mnt/d/ollama/models}"

PRD_FILE=${1:-}
if [ -z "$PRD_FILE" ]; then
    echo "Usage: ws task-split <prd_file> [--project <project_key>] [--to-inbox] [--dry-run] [--force] [--llm]"
    exit 1
fi
shift || true

PRD_FILE=${PRD_FILE//\\//}
if [[ "$PRD_FILE" =~ ^([A-Za-z]):/(.*)$ ]]; then
    drive=$(echo "${BASH_REMATCH[1]}" | tr 'A-Z' 'a-z')
    PRD_FILE="/mnt/$drive/${BASH_REMATCH[2]}"
fi

BASE="$WS_HOME"
TASK_ROOT="$BASE/tasks"
PYTHON="$BASE/runtimes/workstation_venv/bin/python3"
ACTIVE_MODEL_YAML="$BASE/registry/active_model.yaml"
SCRIPTS="$BASE/scripts"

mkdir -p "$TASK_ROOT/generated" "$TASK_ROOT/inbox"

if [ ! -f "$PRD_FILE" ]; then
    echo "PRD file not found: $PRD_FILE"
    exit 1
fi

LLM_MODE=false
for arg in "$@"; do
    if [ "$arg" == "--llm" ]; then
        LLM_MODE=true
        break
    fi
done

if [ "$LLM_MODE" = true ]; then
    echo "Using local LLM to split PRD into structured tasks..."
    USER_PROMPT=$(mktemp)
    echo "PRD Content:" > "$USER_PROMPT"
    cat "$PRD_FILE" >> "$USER_PROMPT"

    SYSTEM_PROMPT="$BASE/prompts/task_splitter.md"
    MODEL=$("$PYTHON" - "$ACTIVE_MODEL_YAML" <<'PY'
import sys, yaml
active = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
print(active.get("active_model", "hermes3:8b"))
PY
)
    OLLAMA_HOST=${OLLAMA_HOST:-"http://localhost:11434"}

    LLM_PRD=$(mktemp)
    if ! "$PYTHON" "$SCRIPTS/ollama_call.py" "$OLLAMA_HOST" "$MODEL" "$SYSTEM_PROMPT" "$USER_PROMPT" > "$LLM_PRD"; then
        echo "Error: LLM task splitting failed. Check if Ollama is running."
        rm -f "$USER_PROMPT" "$LLM_PRD"
        exit 1
    fi
    PRD_FILE="$LLM_PRD"
    rm -f "$USER_PROMPT"
    # Ensure temporary file is cleaned up on exit
    trap 'rm -f "$LLM_PRD"' EXIT
fi

"$PYTHON" - "$PRD_FILE" "$TASK_ROOT" "$@" <<'PY'
import argparse
import re
import shutil
import sys
from pathlib import Path

prd_file = Path(sys.argv[1])
task_root = Path(sys.argv[2])
argv = sys.argv[3:]

parser = argparse.ArgumentParser(prog="ws task-split", add_help=False)
parser.add_argument("--project", default="")
parser.add_argument("--to-inbox", action="store_true")
parser.add_argument("--dry-run", action="store_true")
parser.add_argument("--force", action="store_true")
parser.add_argument("--llm", action="store_true")
opts, extras = parser.parse_known_args(argv)
if extras:
    print(f"Unrecognized arguments: {' '.join(extras)}", file=sys.stderr)
    sys.exit(2)

text = prd_file.read_text(encoding="utf-8", errors="replace")
heading_re = re.compile(r"(?m)^##\s+Task\s+(\d+)(?:\s*[:\-]\s*|\s+)?(.*\S)?\s*$")
matches = list(heading_re.finditer(text))
if not matches:
    print("No structured task headings found. Use a structured PRD/task queue or add --llm later.", file=sys.stderr)
    sys.exit(2)

def section(body: str, name: str) -> str:
    pattern = re.compile(
        rf"(?ms)^\s*{re.escape(name)}:\s*\n(.*?)(?=^\s*[A-Za-z][A-Za-z ]*:\s*$|^##\s+Task\s+\d+|\Z)"
    )
    match = pattern.search(body)
    return match.group(1).strip() if match else ""

def normalize_text(value: str) -> str:
    lines = [line.rstrip() for line in value.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines).strip()

def bulletify(value: str, default: str = "") -> str:
    normalized = normalize_text(value)
    if not normalized:
        return default
    lines = []
    for line in normalized.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lines.append(stripped if stripped.startswith("- ") else f"- {stripped}")
    return "\n".join(lines) if lines else default

def slugify(value: str, fallback: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return slug[:60] if slug else fallback

project_key = opts.project.strip()
project_prefix = re.sub(r"[^A-Za-z0-9_.-]+", "_", project_key).strip("_").lower() if project_key else "unassigned"
created_count = 0
copied_count = 0
skipped_count = 0
planned_create_count = 0
planned_copy_count = 0

for index, match in enumerate(matches, 1):
    task_num = int(match.group(1))
    raw_title = (match.group(2) or "").strip(" :-.\t")
    title = raw_title or f"Task {task_num:03d}"
    start = match.start()
    end = matches[index].start() if index < len(matches) else len(text)
    body = text[start:end].strip() + "\n"

    goal = normalize_text(section(body, "Goal"))
    acceptance = normalize_text(section(body, "Acceptance Criteria"))
    allowed = normalize_text(section(body, "Allowed Files"))
    denied = normalize_text(section(body, "Denied Files"))
    test_command = normalize_text(section(body, "Test Command"))
    risk_raw = normalize_text(section(body, "Risk")).splitlines()[0].strip().lower() if section(body, "Risk") else ""
    escalation = normalize_text(section(body, "Escalation")).splitlines()[0].strip().lower() if section(body, "Escalation") else "none"
    notes = normalize_text(section(body, "Notes"))

    parser_notes = []
    if not goal:
        parser_notes.append("Missing Goal")
    if not acceptance:
        parser_notes.append("Missing Acceptance Criteria")
    if not risk_raw:
        parser_notes.append("Missing Risk")
        risk = "needs_review"
    elif risk_raw in {"low", "medium", "high", "needs_review"}:
        risk = risk_raw
    else:
        parser_notes.append(f"Unrecognized Risk value: {risk_raw}")
        risk = "needs_review"

    filename = f"{project_prefix}_task_{task_num:03d}_{slugify(title, f'task_{task_num:03d}')}.md"
    generated_path = task_root / "generated" / filename
    inbox_path = task_root / "inbox" / filename

    canonical = [
        f"# Task {task_num:03d}: {title}",
        "",
        "Source:",
        "prd",
        "",
        "Project:",
        project_key or "unknown",
        "",
        "Status:",
        "generated",
        "",
        "Goal:",
        goal,
        "",
        "Acceptance Criteria:",
        bulletify(acceptance),
        "",
        "Allowed Files:",
        bulletify(allowed, "- not specified"),
        "",
        "Denied Files:",
        bulletify(denied, "- .env\n- credentials\n- raw datasets\n- data/*\n- models/*\n- node_modules/*\n- .git/*"),
        "",
        "Test Command:",
        test_command,
        "",
        "Risk:",
        risk,
        "",
        "Escalation:",
        escalation or "none",
    ]

    if notes:
        canonical.extend(["", "Notes:", notes])
    if parser_notes:
        canonical.extend(["", "Parser Notes:", *[f"- {note}" for note in parser_notes]])
    canonical.extend(["", "Original Task Content:", "```markdown", body.rstrip("\n"), "```", ""])

    payload = "\n".join(canonical)
    generate_exists = generated_path.exists()
    inbox_exists = inbox_path.exists()

    if opts.dry_run:
        if generate_exists and not opts.force:
            print(f"Would skip existing: {generated_path}")
            skipped_count += 1
        else:
            print(f"Would create: {generated_path}")
            planned_create_count += 1
        if opts.to_inbox:
            if inbox_exists and not opts.force:
                print(f"Would skip existing inbox copy: {inbox_path}")
                skipped_count += 1
            else:
                print(f"Would copy to inbox: {inbox_path}")
                planned_copy_count += 1
        continue

    if generate_exists and not opts.force:
        skipped_count += 1
        continue

    generated_path.parent.mkdir(parents=True, exist_ok=True)
    generated_path.write_text(payload, encoding="utf-8", newline="\n")
    created_count += 1
    if opts.to_inbox:
        inbox_path.parent.mkdir(parents=True, exist_ok=True)
        if inbox_exists and not opts.force:
            skipped_count += 1
        else:
            shutil.copy2(generated_path, inbox_path)
            copied_count += 1

if opts.dry_run:
    print(f"Detected {len(matches)} structured task(s).")
    print(f"Would generate {planned_create_count} task file(s) under {task_root / 'generated'}.")
    if opts.to_inbox:
        print(f"Would copy {planned_copy_count} task file(s) into {task_root / 'inbox'}.")
    print(f"Project key: {project_key or 'unknown'}")
    print("No files written.")
    sys.exit(0)

print(f"Detected {len(matches)} structured task(s).")
print(f"Generated {created_count} task file(s) under {task_root / 'generated'}.")
if opts.to_inbox:
    print(f"Copied {copied_count} task file(s) into {task_root / 'inbox'}.")
if skipped_count:
    print(f"Skipped {skipped_count} existing file(s) without --force.")
for index, match in enumerate(matches, 1):
    task_num = int(match.group(1))
    raw_title = (match.group(2) or "").strip(" :-.\t")
    title = raw_title or f"Task {task_num:03d}"
    filename = f"{project_prefix}_task_{task_num:03d}_{slugify(title, f'task_{task_num:03d}')}.md"
    generated_path = task_root / "generated" / filename
    if generated_path.exists():
        print(generated_path)
PY

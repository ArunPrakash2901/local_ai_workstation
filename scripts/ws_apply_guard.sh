#!/bin/bash
set -euo pipefail

PROJECT_DIR=${1:-}
PATCH_FILE=${2:-}
ALLOWED_FILE=${3:-}
MAX_FILES=${4:-5}

if [ -z "$PROJECT_DIR" ] || [ -z "$PATCH_FILE" ]; then
    echo "Usage: ws_apply_guard.sh <project_dir> <patch_file> [allowed_file] [max_files]"
    exit 1
fi

PYTHON="/mnt/d/_ai_brain/runtimes/workstation_venv/bin/python3"

"$PYTHON" - "$PROJECT_DIR" "$PATCH_FILE" "$ALLOWED_FILE" "$MAX_FILES" <<'PY'
import fnmatch
import re
import sys
from pathlib import Path

project = Path(sys.argv[1]).resolve()
patch = Path(sys.argv[2])
allowed_file = Path(sys.argv[3]) if sys.argv[3] else None
max_files = int(sys.argv[4])

denied_parts = {".git", "node_modules", "venv", ".venv", "env", "data", "datasets", "raw_data", "processed_data", "models", "checkpoints", "build", "dist", "cache", "graphify-out"}
denied_suffixes = {".env", ".pem", ".key", ".p12", ".pfx", ".csv", ".parquet", ".xlsx", ".xls", ".sqlite", ".db", ".duckdb", ".gguf", ".safetensors", ".pt", ".pth", ".onnx", ".zip", ".7z", ".tar", ".gz", ".png", ".jpg", ".jpeg", ".gif", ".mp4", ".mov"}
denied_name = re.compile(r"(?i)(secret|credential|token|api[_-]?key|broker|private[_-]?key|password)")

text = patch.read_text(encoding="utf-8", errors="replace")
paths = []
for line in text.splitlines():
    if line.startswith(("+++ b/", "--- a/")):
        p = line[6:].strip()
        if p != "/dev/null":
            paths.append(p)
paths = sorted(set(paths))

if not paths:
    print("BLOCKED: patch contains no changed file paths")
    sys.exit(2)
if len(paths) > max_files:
    print(f"BLOCKED: patch changes {len(paths)} files, max is {max_files}")
    sys.exit(2)

allowed = []
if allowed_file and allowed_file.is_file():
    allowed = [x.strip() for x in allowed_file.read_text(encoding="utf-8").splitlines() if x.strip()]

for rel in paths:
    if rel.startswith("/") or ".." in Path(rel).parts:
        print(f"BLOCKED: unsafe path {rel}")
        sys.exit(2)
    candidate = (project / rel).resolve()
    try:
        candidate.relative_to(project)
    except ValueError:
        print(f"BLOCKED: path escapes project {rel}")
        sys.exit(2)
    parts = set(Path(rel).parts)
    if parts & denied_parts:
        print(f"BLOCKED: denied folder in path {rel}")
        sys.exit(2)
    if Path(rel).suffix.lower() in denied_suffixes or denied_name.search(Path(rel).name):
        print(f"BLOCKED: denied file type/name {rel}")
        sys.exit(2)
    if allowed and not any(fnmatch.fnmatch(rel, pat) for pat in allowed):
        print(f"BLOCKED: {rel} is outside Allowed Files")
        sys.exit(2)

if re.search(r"(?im)^\s*(rm\s+-|git\s+reset|git\s+clean|npm\s+install|pnpm\s+install|yarn\s+add|pip\s+install|alembic|migrate)", text):
    print("BLOCKED: destructive/install/migration command text found in patch")
    sys.exit(2)

print("SAFE")
for rel in paths:
    print(rel)
PY

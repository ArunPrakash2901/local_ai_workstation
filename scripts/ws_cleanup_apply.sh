#!/bin/bash
set -euo pipefail

BASE="/mnt/d/_ai_brain"
PLAN_DIR="$BASE/cleanup/plans"
ARCHIVE_BASE="$BASE/archive"
PYTHON="$BASE/runtimes/workstation_venv/bin/python3"

if [ "${1:-}" != "--apply" ]; then
    echo "Refusing to move files."
    echo "cleanup-apply is archive-only and requires explicit confirmation:"
    echo "  ws cleanup-apply --apply"
    echo "No files were moved."
    exit 1
fi

LATEST_PLAN_JSON=$(ls -t "$PLAN_DIR"/CLEANUP_PLAN_*.json 2>/dev/null | head -n 1 || true)
LATEST_PLAN_MD=$(ls -t "$PLAN_DIR"/CLEANUP_PLAN_*.md 2>/dev/null | head -n 1 || true)
if [ -z "$LATEST_PLAN_JSON" ] || [ -z "$LATEST_PLAN_MD" ]; then
    echo "Error: no cleanup plan found. Run ws cleanup-plan first."
    exit 1
fi

TS=$(date +%Y%m%d_%H%M%S)
ARCHIVE_DIR="$ARCHIVE_BASE/cleanup_${TS}"
mkdir -p "$ARCHIVE_DIR"

"$PYTHON" - "$BASE" "$LATEST_PLAN_JSON" "$LATEST_PLAN_MD" "$ARCHIVE_DIR" <<'PY'
import json
import shutil
import sys
from pathlib import Path

base = Path(sys.argv[1]).resolve()
plan_json = Path(sys.argv[2])
plan_md = Path(sys.argv[3])
archive_dir = Path(sys.argv[4]).resolve()
plan = json.loads(plan_json.read_text(encoding="utf-8"))

protected_prefixes = ("registry/", "scripts/", "global/", "runtimes/", "models/")
protected_exact = {
    "START_HERE.md",
    "WORKSTATION_MANUAL.md",
    "LOCAL_AI_STACK_STATUS.md",
    "FINAL_RECOMMENDED_PROFILE.md",
    "global/GLOBAL_GRAPH_STATUS.md",
}

def is_safe_rel(rel):
    rel = rel.replace("\\", "/").lstrip("/")
    if rel in protected_exact or rel.startswith(protected_prefixes):
        return False
    if ".." in Path(rel).parts:
        return False
    return True

moved = []
skipped = []

for item in plan.get("archive_candidates", []):
    rel = item.get("path", "").replace("\\", "/").lstrip("/")
    if item.get("confidence") != "high":
        skipped.append((rel, "not high confidence"))
        continue
    if not is_safe_rel(rel):
        skipped.append((rel, "protected path"))
        continue
    src = (base / rel).resolve()
    try:
        src.relative_to(base)
    except ValueError:
        skipped.append((rel, "outside control plane"))
        continue
    if not src.exists():
        skipped.append((rel, "missing"))
        continue
    dest = archive_dir / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))
    moved.append((rel, str(dest), item.get("reason", "")))

manifest = ["# Cleanup Archive Manifest\n", f"Plan: `{plan_md}`\n", "## Moved\n"]
if moved:
    for rel, dest, reason in moved:
        manifest.append(f"- `{rel}` -> `{dest}` ({reason})")
else:
    manifest.append("- None")
manifest.append("\n## Skipped\n")
if skipped:
    for rel, reason in skipped:
        manifest.append(f"- `{rel}` ({reason})")
else:
    manifest.append("- None")

(archive_dir / "MANIFEST.md").write_text("\n".join(manifest) + "\n", encoding="utf-8", newline="\n")
print(f"Archive folder: {archive_dir}")
print(f"Moved files/folders: {len(moved)}")
print(f"Skipped candidates: {len(skipped)}")
PY

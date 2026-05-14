#!/bin/bash
set -euo pipefail

WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
if [ -f "$WS_HOME/scripts/ws_env.sh" ]; then
    source "$WS_HOME/scripts/ws_env.sh"
fi

BASE="$WS_HOME"
REPORT_DIR="$BASE/cleanup/reports"
PLAN_DIR="$BASE/cleanup/plans"
ARCHIVE_DIR="$BASE/archive"
PYTHON="$BASE/runtimes/workstation_venv/bin/python3"

mkdir -p "$REPORT_DIR" "$PLAN_DIR" "$ARCHIVE_DIR"

LATEST_REPORT=$(ls -t "$REPORT_DIR"/WORKSTATION_AUDIT_*.md 2>/dev/null | head -n 1 || true)
LATEST_PLAN=$(ls -t "$PLAN_DIR"/CLEANUP_PLAN_*.md 2>/dev/null | head -n 1 || true)
LATEST_PLAN_JSON=$(ls -t "$PLAN_DIR"/CLEANUP_PLAN_*.json 2>/dev/null | head -n 1 || true)

echo "Workstation Cleanup Status"
echo "--------------------------"
echo "Latest audit report: ${LATEST_REPORT:-none}"
echo "Latest cleanup plan: ${LATEST_PLAN:-none}"
echo ""
echo "Archive folders:"
if compgen -G "$ARCHIVE_DIR/cleanup_*" > /dev/null; then
    ls -dt "$ARCHIVE_DIR"/cleanup_* | head -n 10
else
    echo "none"
fi

if [ -n "$LATEST_PLAN_JSON" ]; then
    "$PYTHON" - "$LATEST_PLAN_JSON" <<'PY'
import json
import sys
from pathlib import Path

plan = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print("")
print("Unresolved Issues:")
print(f"- Archive candidates: {len(plan.get('archive_candidates', []))}")
print(f"- Duplicate candidates: {len(plan.get('duplicate_candidates', []))}")
print(f"- Broken references: {len(plan.get('broken_references', []))}")
print(f"- Unsafe to touch: {len(plan.get('unsafe_to_touch', []))}")
print(f"- Needs user review: {len(plan.get('needs_user_review', []))}")
print(f"- Duplicate aliases: {len(plan.get('duplicate_aliases', []))}")
if plan.get("unsafe_to_touch"):
    print("")
    print("Unsafe-to-touch paths:")
    for item in plan["unsafe_to_touch"][:20]:
        print(f"- {item.get('path')}: {item.get('reason')}")
PY
fi

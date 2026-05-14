#!/bin/bash
set -euo pipefail

BASE="/mnt/d/_ai_brain"
REPORT_DIR="$BASE/cleanup/reports"
PLAN_DIR="$BASE/cleanup/plans"
PYTHON="$BASE/runtimes/workstation_venv/bin/python3"
TS=$(date +%Y%m%d_%H%M%S)
PLAN="$PLAN_DIR/CLEANUP_PLAN_${TS}.md"
JSON="$PLAN_DIR/CLEANUP_PLAN_${TS}.json"

mkdir -p "$REPORT_DIR" "$PLAN_DIR" "$BASE/archive"

LATEST_AUDIT_JSON=$(ls -t "$REPORT_DIR"/WORKSTATION_AUDIT_*.json 2>/dev/null | head -n 1 || true)
if [ -z "$LATEST_AUDIT_JSON" ]; then
    bash "$BASE/scripts/ws_audit_workstation.sh" >/dev/null
    LATEST_AUDIT_JSON=$(ls -t "$REPORT_DIR"/WORKSTATION_AUDIT_*.json 2>/dev/null | head -n 1 || true)
fi

if [ -z "$LATEST_AUDIT_JSON" ]; then
    echo "Error: could not create or find workstation audit JSON."
    exit 1
fi

"$PYTHON" - "$BASE" "$LATEST_AUDIT_JSON" "$PLAN" "$JSON" <<'PY'
import json
import sys
from pathlib import Path

base = Path(sys.argv[1])
audit_path = Path(sys.argv[2])
plan_path = Path(sys.argv[3])
json_path = Path(sys.argv[4])
audit = json.loads(audit_path.read_text(encoding="utf-8"))

protected_prefixes = [
    "registry/",
    "scripts/",
    "global/",
    "runtimes/",
    "models/",
]
protected_exact = {
    "START_HERE.md",
    "WORKSTATION_MANUAL.md",
    "LOCAL_AI_STACK_STATUS.md",
    "FINAL_RECOMMENDED_PROFILE.md",
    "global/GLOBAL_GRAPH_STATUS.md",
}

def exists(rel):
    return (base / rel).exists()

def size_of(rel):
    try:
        return (base / rel).stat().st_size
    except OSError:
        return 0

def size_fmt(n):
    units = ["B", "KB", "MB", "GB"]
    v = float(n)
    for unit in units:
        if v < 1024 or unit == units[-1]:
            return f"{v:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        v /= 1024

def protected(rel):
    rel = rel.replace("\\", "/")
    return rel in protected_exact or any(rel.startswith(prefix) for prefix in protected_prefixes)

archive = []
duplicates = []
stale = []
broken = []
unsafe = []
review = []
keep = []

def add_archive(rel, reason, category, confidence="medium"):
    if not rel or protected(rel) or not exists(rel):
        review.append({"path": rel, "reason": reason, "risk": "protected or missing path"})
        return
    archive.append({
        "path": rel,
        "reason": reason,
        "size": size_fmt(size_of(rel)),
        "category": category,
        "confidence": confidence,
    })

for rel in audit.get("empty_runs", []):
    add_archive(rel, "empty run folder", "archive_candidate", "high")

for rel in audit.get("partial_runs", []):
    if "bench_" in rel:
        add_archive(rel, "partial benchmark/run artifact; no answer/results marker found", "archive_candidate", "high")
    else:
        review.append({"path": rel, "reason": "partial run folder", "risk": "may contain useful debugging context"})

for row in audit.get("packet_rows", []):
    rel, size, status = row
    if status == "SAFE" and ("Which_registered_projects" in rel or "packet_global" in rel or "packet_portfolio_website" in rel):
        add_archive(rel, "safe smoke-test frontier packet", "archive_candidate", "high")
    elif status == "SAFE":
        review.append({"path": rel, "reason": "safe frontier packet", "risk": "may be intentionally retained"})
    else:
        review.append({"path": rel, "reason": f"packet redaction status: {status}", "risk": "inspect before archiving"})

seen_report_names = {}
for row in audit.get("report_rows", []):
    rel, size, status = row
    name = Path(rel).name.lower()
    if "old recovery" in status.lower() or "recovery" in name:
        add_archive(rel, "old recovery/status report", "stale_candidate", "medium")
    if name in seen_report_names:
        duplicates.append({"path": rel, "reason": f"same filename as {seen_report_names[name]}", "size": size, "category": "duplicate_candidate", "confidence": "medium"})
    else:
        seen_report_names[name] = rel
    if status == "empty":
        add_archive(rel, "empty report file", "archive_candidate", "high")

for row in audit.get("scratch_rows", []):
    rel, size, status = row
    if "empty" in status or "temporary/log" in status:
        add_archive(rel, f"scratch artifact: {status}", "archive_candidate", "high")
    else:
        review.append({"path": rel, "reason": "scratch file", "risk": "confirm no useful notes before archiving"})

for item in audit.get("missing_refs", []):
    script, missing, fix = item
    broken.append({"script": script, "missing_target": missing, "recommended_fix": fix})

for rel in audit.get("secret_looking", []):
    unsafe.append({"path": rel, "reason": "secret-looking filename; contents not opened"})

for rel in audit.get("legacy_scripts", []):
    review.append({"path": rel, "reason": "legacy/unrouted WSL script", "risk": "may be manually useful"})

for rel in protected_exact:
    if exists(rel):
        keep.append({"path": rel, "reason": "protected workstation document/config"})

plan = {
    "audit_json": str(audit_path),
    "plan_md": str(plan_path),
    "archive_candidates": archive,
    "duplicate_candidates": duplicates,
    "stale_candidates": stale,
    "broken_references": broken,
    "unsafe_to_touch": unsafe,
    "needs_user_review": review,
    "keep": keep,
    "duplicate_aliases": audit.get("duplicate_aliases", []),
}
json_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")

def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(x).replace("\n", " ") for x in row) + " |")
    return "\n".join(out)

summary = [
    ("Total files scanned", audit.get("total_files_scanned", 0)),
    ("Archive candidates", len(archive)),
    ("Duplicate candidates", len(duplicates)),
    ("Broken references", len(broken)),
    ("Unsafe to touch", len(unsafe)),
    ("Needs review", len(review)),
]

md = ["# Cleanup Plan\n"]
md.append("## Summary\n")
for key, value in summary:
    md.append(f"- {key}: {value}")

md.append("\n## Safe Archive Candidates\n")
md.append(table(["path", "reason", "size", "category", "confidence"], [[x["path"], x["reason"], x["size"], x["category"], x["confidence"]] for x in archive]) if archive else "None.")

md.append("\n## Needs User Review\n")
md.append(table(["path", "reason", "risk"], [[x["path"], x["reason"], x["risk"]] for x in review]) if review else "None.")

md.append("\n## Do Not Touch\n")
md.append(table(["path", "reason"], [[x["path"], x["reason"]] for x in unsafe] + [[x["path"], x["reason"]] for x in keep]) if (unsafe or keep) else "None.")

md.append("\n## Broken References\n")
md.append(table(["script/config", "missing target", "recommended fix"], [[x["script"], x["missing_target"], x["recommended_fix"]] for x in broken]) if broken else "None.")

md.append("\n## Duplicate Alias Entries\n")
md.append(table(["alias", "count", "recommendation"], [[a, c, "manually remove duplicate if intentional cleanup is desired"] for a, c in audit.get("duplicate_aliases", [])]) if audit.get("duplicate_aliases") else "None.")

md.append("\n## Duplicate Candidates\n")
md.append(table(["path", "reason", "size", "category", "confidence"], [[x["path"], x["reason"], x["size"], x["category"], x["confidence"]] for x in duplicates]) if duplicates else "None.")

md.append("\n## Recommended Manual Actions\n")
md.append("- Review this plan before archiving anything.")
md.append("- Run `ws cleanup-status` to see the latest audit and plan.")
md.append("- To archive only high-confidence archive candidates, run `ws cleanup-apply --apply`.")
md.append("- Do not manually delete registry files, active configs, scripts routed by `ws`, model files, project graphs, or secret-looking files.")

plan_path.write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
print(plan_path)
PY

echo "Cleanup plan: $PLAN"

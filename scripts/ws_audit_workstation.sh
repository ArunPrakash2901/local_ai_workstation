#!/bin/bash
set -euo pipefail

BASE="/mnt/d/_ai_brain"
REPORT_DIR="$BASE/cleanup/reports"
PLAN_DIR="$BASE/cleanup/plans"
ARCHIVE_DIR="$BASE/archive"
PYTHON="$BASE/runtimes/workstation_venv/bin/python3"
TS=$(date +%Y%m%d_%H%M%S)
REPORT="$REPORT_DIR/WORKSTATION_AUDIT_${TS}.md"
JSON="$REPORT_DIR/WORKSTATION_AUDIT_${TS}.json"

mkdir -p "$REPORT_DIR" "$PLAN_DIR" "$ARCHIVE_DIR"

"$PYTHON" - "$BASE" "$REPORT" "$JSON" <<'PY'
import json
import os
import re
import stat
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

base = Path(sys.argv[1])
report_path = Path(sys.argv[2])
json_path = Path(sys.argv[3])
now = datetime.now()

skip_dirs = {
    ".git", "node_modules", "venv", ".venv", "__pycache__", "cache", ".cache",
    "data", "datasets", "raw_data", "processed_data", "models", "checkpoints",
    "build", "dist",
}
secret_name_re = re.compile(r"(?i)(^|[._-])(\.env|env|secret|secrets|credential|credentials|token|tokens|api[_-]?key|broker|private[_-]?key|id_rsa|id_ed25519|\.pem|\.key|\.p12|\.pfx)([._-]|$)")
ws_routed = {
    "ai_list_projects.sh", "ai_project.sh", "ai_ask.sh", "ai_global_ask.sh", "ai_graph.sh",
    "ai_audit.sh", "ai_debug.sh", "ai_run_task.sh", "ai_model_current.sh", "ai_models.sh",
    "ai_model_use.sh", "ai_model_warm.sh", "ai_model_unload.sh", "ai_kv_profiles.sh",
    "ai_kv_use.sh", "ai_daily_restore.sh", "ws_frontier_status.sh", "ws_make_packet.sh",
    "ws_redact_packet.sh", "ws_audit_workstation.sh", "ws_cleanup_plan.sh",
    "ws_cleanup_apply.sh", "ws_cleanup_status.sh", "ws_build.sh", "ws_build_report.sh",
    "ws_apply_ready.sh", "ws_agent_hygiene.sh", "ws_agent_mark_stale_reviewed.sh",
    "ws_agent_validate.sh", "ws_task_new.sh", "ws_task_split.sh", "ws_task_status.sh",
    "ws_task_next.sh", "ws_task_review_packet.sh", "ws_task_complete.sh", "ws_task_block.sh",
    "ws_loop_plan.sh", "ws_loop_status.sh", "ws_loop_start.sh", "ws_path_status.sh",
    "ws_readiness.sh", "ws_env.sh", "ws_apply_guard.sh", "ws_test_runner.sh",
    "ws_context_pack.sh", "ws_task_parser.sh"
}

def rel(p):
    try:
        return str(Path(p).resolve().relative_to(base.resolve()))
    except Exception:
        return str(p)

def size_fmt(n):
    n = int(n or 0)
    units = ["B", "KB", "MB", "GB", "TB"]
    v = float(n)
    for unit in units:
        if v < 1024 or unit == units[-1]:
            return f"{v:.1f} {unit}" if unit != "B" else f"{n} B"
        v /= 1024

def read_text(path, limit=300_000):
    data = path.read_bytes()[:limit]
    return data.decode("utf-8", errors="replace")

def walk_files(root=base):
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        dirnames[:] = [
            d for d in dirnames
            if d not in skip_dirs and not d.endswith("_venv") and not secret_name_re.search(d)
        ]
        for name in filenames:
            yield current / name

all_files = list(walk_files())
secret_looking = [p for p in all_files if secret_name_re.search(p.name)]

scripts_dir = base / "scripts"
scripts = sorted([p for p in scripts_dir.glob("*") if p.is_file()])
script_rows = []
missing_refs = []
curl_without_timeout = []
ollama_call_risks = []
qwen_risks = []
frontier_direct_calls = []
legacy_scripts = []
crlf_scripts = []
missing_shebang = []
for script in scripts:
    ext = script.suffix.lower()
    is_wsl = ext == ".sh" or script.name == "ws"
    text = ""
    if is_wsl or ext in {".py", ".ps1"}:
        try:
            text = read_text(script)
        except Exception as exc:
            missing_refs.append((rel(script), f"unreadable: {exc}", "inspect permissions"))
    if is_wsl:
        mode = script.stat().st_mode
        executable = bool(mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
        if "\r\n" in text:
            crlf_scripts.append(rel(script))
        if not text.startswith("#!"):
            missing_shebang.append(rel(script))
        script_rows.append((script.name, "yes" if executable else "no", "yes" if "\r\n" in text else "no", "yes" if text.startswith("#!") else "no"))
        if script.name not in ws_routed and script.name != "ws":
            legacy_scripts.append(rel(script))

    for m in re.finditer(r"(/mnt/d/_ai_brain/[^\s'\"),;]+|D:/_ai_brain/[^\s'\"),;]+|D:\\_ai_brain\\[^\s'\"),;]+)", text):
        raw = m.group(1).strip().strip("'\"),;")
        check = raw.replace("D:/", "/mnt/d/").replace("D:\\", "/mnt/d/").replace("\\", "/")
        check_path = Path(check)
        if any(ch in check for ch in "$*{}[]"):
            continue
        if check.startswith("/mnt/d/_ai_brain") and not check_path.exists():
            missing_refs.append((rel(script), raw, "verify path or create missing script/config"))

    for line_no, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if "curl " in stripped and "--max-time" not in stripped and "--connect-timeout" not in stripped:
            curl_without_timeout.append((rel(script), line_no, stripped[:160]))
        if "/api/generate" in stripped or "ollama" in stripped:
            nearby = "\n".join(text.splitlines()[max(0, line_no - 8): line_no + 8])
            if "keep_alive" in nearby or "warm" in script.name:
                if '"stream": false' not in nearby and "'stream': False" not in nearby:
                    ollama_call_risks.append((rel(script), line_no, "warm/generate call without explicit stream=false nearby"))
                if "num_predict" not in nearby:
                    ollama_call_risks.append((rel(script), line_no, "warm/generate call without explicit num_predict nearby"))
        if "qwen2.5:32b" in stripped:
            qwen_risks.append((rel(script), line_no, stripped[:160]))
        if re.search(r"(^|[^A-Za-z0-9_-])(gemini|codex|claude)(\s|$)", stripped) and "command:" not in stripped and "which" not in stripped:
            frontier_direct_calls.append((rel(script), line_no, stripped[:160]))

registry_dir = base / "registry"
required_registries = ["projects.yaml", "models.yaml", "active_model.yaml", "kv_profiles.yaml", "active_kv_profile.yaml", "frontier.yaml"]
registry_status = []
registry_data = {}
for name in required_registries:
    path = registry_dir / name
    status_text = "exists" if path.exists() else "missing"
    if path.exists():
        try:
            registry_data[name] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            status_text = f"invalid yaml: {exc}"
    registry_status.append((name, status_text))

project_path_rows = []
projects = (registry_data.get("projects.yaml") or {}).get("projects") or {}
for key, info in projects.items():
    wsl_path = Path(info.get("wsl_path") or "")
    graph_path = wsl_path / "graphify-out" / "graph.json" if str(wsl_path) else Path()
    project_path_rows.append((key, str(wsl_path), "yes" if wsl_path.exists() else "no", str(graph_path), "yes" if graph_path.exists() else "no"))

model_profiles = registry_data.get("models.yaml") or {}
active_model = registry_data.get("active_model.yaml") or {}
active_kv = registry_data.get("active_kv_profile.yaml") or {}
ollama_models = []
try:
    with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5) as resp:
        tags = json.loads(resp.read().decode("utf-8", errors="replace"))
    ollama_models = sorted({m.get("name") for m in tags.get("models", []) if m.get("name")})
except Exception as exc:
    ollama_models = [f"unavailable: {exc}"]

model_rows = []
for key, info in model_profiles.items():
    if not isinstance(info, dict):
        continue
    model = info.get("model_name", "")
    installed = "unknown" if ollama_models and ollama_models[0].startswith("unavailable:") else ("yes" if model in ollama_models else "no")
    model_rows.append((key, model, installed))

active_safe = (
    active_model.get("active_profile") == "hermes_default"
    and active_model.get("active_model") == "hermes3:8b"
    and active_model.get("context_length") == 8192
    and active_kv.get("active_profile") == "stable_default"
)

bashrc = Path.home() / ".bashrc"
alias_counts = Counter()
alias_rows = []
if bashrc.exists():
    for line in bashrc.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"\s*alias\s+([A-Za-z0-9_-]+)=", line)
        if m:
            alias_counts[m.group(1)] += 1
    for name in ["ws", "ailist", "aiproj", "aiask", "aiglobal", "aimodels", "aimodel", "aiuse", "aikv", "aidaily"]:
        alias_rows.append((name, alias_counts.get(name, 0)))
duplicate_aliases = [(a, c) for a, c in alias_counts.items() if c > 1]

runs_dir = base / "runs"
run_rows = []
empty_runs = []
partial_runs = []
old_runs = []
if runs_dir.exists():
    for run in sorted([p for p in runs_dir.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True):
        files = [p for p in run.iterdir() if p.is_file()]
        names = {p.name for p in files}
        size = sum(p.stat().st_size for p in files)
        age_days = int((now.timestamp() - run.stat().st_mtime) // 86400)
        status = []
        if not files:
            status.append("empty")
            empty_runs.append(rel(run))
        if not ({"answer.md", "results.md", "graph_output.txt"} & names):
            status.append("partial")
            partial_runs.append(rel(run))
        if age_days >= 30:
            status.append("old")
            old_runs.append(rel(run))
        run_rows.append((rel(run), len(files), size_fmt(size), ", ".join(status) or "ok"))

packet_rows = []
frontier_packets = base / "frontier" / "packets"
if frontier_packets.exists():
    for pkt in sorted(frontier_packets.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        text = read_text(pkt, 120_000)
        status = "needs review"
        if "## Safety Notice" in text and not re.search(r"(?i)(BEGIN .*PRIVATE KEY|api[_-]?key\s*=|token\s*=|password\s*=)", text.split("## Safety Notice", 1)[0]):
            status = "SAFE"
        packet_rows.append((rel(pkt), size_fmt(pkt.stat().st_size), status))

report_rows = []
for folder in [base / "reports", base / "benchmarks"]:
    if folder.exists():
        for item in sorted(folder.glob("*")):
            if item.is_file():
                status = []
                if item.stat().st_size == 0:
                    status.append("empty")
                if item.stat().st_size > 1_000_000:
                    status.append("large")
                if "RECOVERY" in item.name.upper() or "STATUS" in item.name.upper():
                    status.append("status/recovery")
                report_rows.append((rel(item), size_fmt(item.stat().st_size), ", ".join(status) or "ok"))

scratch_rows = []
scratch = base / "scratch"
if scratch.exists():
    for item in scratch.rglob("*"):
        if item.is_file() and not secret_name_re.search(item.name):
            status = []
            if item.stat().st_size == 0:
                status.append("empty")
            if re.search(r"(?i)(tmp|temp|scratch|latest_error|error\.log)", item.name):
                status.append("temporary/log")
            scratch_rows.append((rel(item), size_fmt(item.stat().st_size), ", ".join(status) or "review"))

top_large = sorted([(p.stat().st_size, rel(p)) for p in all_files if p.exists()], reverse=True)[:15]
brain_size = sum(p.stat().st_size for p in all_files if p.exists())
ollama_model_dir = Path("/mnt/d/ollama/models")
ollama_size = None
if ollama_model_dir.exists():
    total = 0
    for dirpath, dirnames, filenames in os.walk(ollama_model_dir):
        for name in filenames:
            try:
                total += (Path(dirpath) / name).stat().st_size
            except OSError:
                pass
    ollama_size = total

audit = {
    "timestamp": now.isoformat(timespec="seconds"),
    "total_files_scanned": len(all_files),
    "script_rows": script_rows,
    "crlf_scripts": crlf_scripts,
    "missing_shebang": missing_shebang,
    "missing_refs": missing_refs,
    "curl_without_timeout": curl_without_timeout,
    "ollama_call_risks": ollama_call_risks,
    "qwen_risks": qwen_risks,
    "frontier_direct_calls": frontier_direct_calls,
    "legacy_scripts": legacy_scripts,
    "registry_status": registry_status,
    "project_path_rows": project_path_rows,
    "model_rows": model_rows,
    "ollama_models": ollama_models,
    "active_safe": active_safe,
    "alias_rows": alias_rows,
    "duplicate_aliases": duplicate_aliases,
    "run_rows": run_rows,
    "empty_runs": empty_runs,
    "partial_runs": partial_runs,
    "old_runs": old_runs,
    "packet_rows": packet_rows,
    "report_rows": report_rows,
    "scratch_rows": scratch_rows,
    "secret_looking": [rel(p) for p in secret_looking],
    "top_large": [(size_fmt(s), p) for s, p in top_large],
    "brain_size": size_fmt(brain_size),
    "ollama_models_size": size_fmt(ollama_size) if ollama_size is not None else "not found",
}
json_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")

def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(x).replace("\n", " ") for x in row) + " |")
    return "\n".join(out)

# Group findings by severity
high = []
medium = []
low = []

for name, status in registry_status:
    if status != "exists":
        high.append(f"Registry {name} is {status}")
for script, ref, fix in missing_refs:
    high.append(f"Broken reference in {script}: {ref} ({fix})")
for script in crlf_scripts:
    high.append(f"CRLF line endings in bash script {script}")
for script, line, risk in ollama_call_risks:
    high.append(f"Ollama call risk in {script}:{line} - {risk}")

if not active_safe:
    medium.append("Active daily profile is NOT the safe default (hermes_default/stable_default)")
for script in missing_shebang:
    medium.append(f"Missing shebang in {script}")
for alias, count in duplicate_aliases:
    medium.append(f"Duplicate alias '{alias}' found {count} times")
if qwen_risks:
    medium.append(f"Found {len(qwen_risks)} references to qwen2.5:32b (hardware bottleneck)")
for script in legacy_scripts:
    medium.append(f"Legacy script (not routed via ws): {script}")

if empty_runs:
    low.append(f"Found {len(empty_runs)} empty run folders")
if old_runs:
    low.append(f"Found {len(old_runs)} run folders older than 30 days")
if curl_without_timeout:
    low.append(f"Found {len(curl_without_timeout)} curl calls without timeout")

# Cleanup Candidates
cleanup_candidates = []
for run in empty_runs: cleanup_candidates.append((run, "Empty run folder"))
for run in old_runs: cleanup_candidates.append((run, "Old run folder (>30d)"))
for script in legacy_scripts: cleanup_candidates.append((script, "Legacy script"))
for path, size, status in scratch_rows:
    if "temporary/log" in status or "empty" in status:
        cleanup_candidates.append((path, f"Temporary file ({status})"))

md = []
md.append("# Workstation Audit Report\n")
md.append(f"Generated: {audit['timestamp']}\n")
md.append("Scope: `D:\\_ai_brain` infrastructure only. Project repos, raw datasets, secrets, project Graphify outputs, and model files were not modified.\n")

md.append("## Issues by Severity\n")
if high:
    md.append("### 🔴 HIGH\n")
    for item in high: md.append(f"- {item}")
if medium:
    md.append("\n### 🟡 MEDIUM\n")
    for item in medium: md.append(f"- {item}")
if low:
    md.append("\n### 🟢 LOW\n")
    for item in low: md.append(f"- {item}")
if not high and not medium and not low:
    md.append("No issues detected.")

md.append("\n## Cleanup Candidates\n")
md.append("The following items are recommended for archival via `ws cleanup-plan`. They are NOT deleted automatically.\n")
if cleanup_candidates:
    md.append(table(["Path", "Reason"], cleanup_candidates[:50]))
else:
    md.append("No cleanup candidates found.")

md.append("\n## Protected Files (DO NOT TOUCH)\n")
md.append("The following files are classified as sensitive or critical and are ignored by cleanup tools.\n")
protected = [(p, "Secret-looking filename") for p in audit["secret_looking"]]
for name, status in registry_status: protected.append((f"registry/{name}", "Critical Registry"))
protected.append(("scripts/ws", "Primary Orchestrator"))
md.append(table(["Path", "Classification"], protected))

md.append("\n## Script Health\n")
md.append(table(["script", "executable", "CRLF", "shebang"], script_rows))

md.append("\n## Registry Health\n")
md.append(table(["registry", "status"], registry_status))
md.append("\n### Registered Project Paths\n")
md.append(table(["key", "project path", "exists", "graph path", "graph exists"], project_path_rows))

md.append("\n## Notes\n")
md.append("- This audit is read-only.")
md.append("- Use `ws cleanup-plan` to generate a structured archive plan for candidates.")
md.append("- No cloud/frontier CLI was called.")

report_path.write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
print(report_path)
PY

echo "Audit report: $REPORT"

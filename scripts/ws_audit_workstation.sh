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
    "ws_cleanup_apply.sh", "ws_cleanup_status.sh",
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

md = []
md.append("# Workstation Audit Report\n")
md.append(f"Generated: {audit['timestamp']}\n")
md.append("Scope: `D:\\_ai_brain` infrastructure only. Project repos, raw datasets, secrets, project Graphify outputs, and model files were not modified.\n")
md.append("## Summary\n")
md.append(f"- Total files scanned: {len(all_files)}")
md.append(f"- D:\\_ai_brain size: {audit['brain_size']}")
md.append(f"- D:\\ollama\\models size: {audit['ollama_models_size']}")
md.append(f"- Secret-looking filenames detected: {len(secret_looking)}")
md.append(f"- Broken/missing references found: {len(missing_refs)}")
md.append(f"- Duplicate aliases found: {len(duplicate_aliases)}")
md.append(f"- Active daily profile safe: {'yes' if active_safe else 'no'}\n")
md.append("## Script Health\n")
md.append(table(["script", "executable", "CRLF", "shebang"], script_rows))
md.append("\n### Script Issues\n")
md.append(f"- CRLF scripts: {', '.join(crlf_scripts) if crlf_scripts else 'none'}")
md.append(f"- Missing shebangs: {', '.join(missing_shebang) if missing_shebang else 'none'}")
md.append(f"- Legacy/unrouted WSL scripts: {', '.join(legacy_scripts) if legacy_scripts else 'none'}")
md.append(f"- Curl calls without timeout: {len(curl_without_timeout)}")
md.append(f"- Ollama warm/generate risk findings: {len(ollama_call_risks)}")
md.append(f"- qwen2.5:32b references: {len(qwen_risks)}")
md.append(f"- Direct frontier CLI call findings: {len(frontier_direct_calls)}\n")
md.append("## Registry Health\n")
md.append(table(["registry", "status"], registry_status))
md.append("\n### Registered Project Paths\n")
md.append(table(["key", "project path", "exists", "graph path", "graph exists"], project_path_rows))
md.append("\n### Model Profiles vs Ollama Tags\n")
md.append(table(["profile", "model", "installed"], model_rows))
md.append("\n## Alias Health\n")
md.append(table(["alias", "count"], alias_rows))
if duplicate_aliases:
    md.append("\nDuplicate aliases:\n" + table(["alias", "count"], duplicate_aliases))
md.append("\n## Runs And Logs\n")
md.append(table(["run", "files", "size", "status"], run_rows[:30]))
md.append("\n## Frontier Packets\n")
md.append(table(["packet", "size", "redaction status"], packet_rows))
md.append("\n## Reports And Benchmarks\n")
md.append(table(["file", "size", "status"], report_rows))
md.append("\n## Scratch/Temp\n")
md.append(table(["file", "size", "status"], scratch_rows) if scratch_rows else "No scratch files found.")
md.append("\n## Safety Scan By Filename\n")
md.append(table(["path", "classification"], [(p, "unsafe_to_touch") for p in audit["secret_looking"]]) if secret_looking else "No secret-looking filenames found under scanned workstation paths.")
md.append("\n## Top Large Files In D:\\_ai_brain\n")
md.append(table(["size", "path"], audit["top_large"]))
md.append("\n## Broken References\n")
md.append(table(["script/config", "missing target", "recommended fix"], missing_refs) if missing_refs else "No broken references found by static scan.")
md.append("\n## Notes\n")
md.append("- This audit is read-only.")
md.append("- Cleanup candidates are generated separately by `ws cleanup-plan`.")
md.append("- No cloud/frontier CLI was called.")

report_path.write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
print(report_path)
PY

echo "Audit report: $REPORT"

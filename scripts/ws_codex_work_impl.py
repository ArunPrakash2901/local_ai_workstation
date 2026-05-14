#!/usr/bin/env python3
import argparse
import fnmatch
import difflib
import json
import os
import re
import shlex
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import yaml


WS_HOME = Path(os.environ.get("WS_HOME", "/mnt/d/_ai_brain"))
PROJECT_KEY = os.environ.get("CODEX_WORK_PROJECT_KEY", "")
TASK_FILE_ARG = os.environ.get("CODEX_WORK_TASK_FILE", "")
SCRIPTS_DIR = WS_HOME / "scripts"
AUTO_ROOT = WS_HOME / "auto_runs"
AUTO_ROOT.mkdir(parents=True, exist_ok=True)

KNOWN_DOCS = {
    "START_HERE.md",
    "WORKSTATION_MANUAL.md",
    "LOCAL_AI_STACK_STATUS.md",
    "FINAL_RECOMMENDED_PROFILE.md",
    "README.md",
}

parser = argparse.ArgumentParser(prog="ws codex-work")
parser.add_argument("project_key")
parser.add_argument("task_file")
parser.add_argument("--branch", action="store_true")
parser.add_argument("--max-files", type=int, default=5)
parser.add_argument("--max-minutes", type=int, default=20)
parser.add_argument("--tests", default="")
parser.add_argument("--dry-run", action="store_true")
parser.add_argument("--stop-on-fail", action="store_true")
parser.add_argument("--context", type=int, default=8192)
args, _extras = parser.parse_known_args(sys.argv[1:])

projects_yaml = WS_HOME / "registry" / "projects.yaml"
active_model_yaml = WS_HOME / "registry" / "active_model.yaml"
active_kv_yaml = WS_HOME / "registry" / "active_kv_profile.yaml"
current_run_dir = None


def fatal_exception_handler(exc_type, exc, tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc, tb)
        return
    if current_run_dir is not None:
        try:
            heartbeat(current_run_dir, f"internal exception: {exc_type.__name__}: {exc}")
            write_run_file(current_run_dir, "status.txt", "FAILED_INTERNAL\n")
            write_run_file(current_run_dir, "exception.log", "".join(traceback.format_exception(exc_type, exc, tb)))
            project_ctx = globals().get("project_dir")
            if project_ctx is not None:
                write_run_file(current_run_dir, "git_status_after.md", git_status(project_ctx, run_dir=current_run_dir) + "\n")
            write_final_report(
                current_run_dir,
                status="FAILED_INTERNAL",
                changed_files=[],
                bridge_status="FAILED_INTERNAL",
                codex_used=False,
                tests_passed=False,
                notes=f"internal exception: {exc_type.__name__}: {exc}",
                codex_mode="codex-work",
            )
        except Exception:
            pass
    sys.__excepthook__(exc_type, exc, tb)
    sys.exit(1)


sys.excepthook = fatal_exception_handler


def run_cmd(cmd, *, cwd=None, timeout=60, run_dir=None, label="command", env=None):
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    start = time.time()
    heartbeat_every = min(15, max(timeout // 4, 5))
    stdout = ""
    stderr = ""
    timed_out = False
    while True:
        try:
            out, err = proc.communicate(timeout=heartbeat_every)
            stdout += out or ""
            stderr += err or ""
            break
        except subprocess.TimeoutExpired:
            if run_dir is not None:
                heartbeat(run_dir, f"{label} still running")
            if time.time() - start >= timeout:
                timed_out = True
                proc.kill()
                out, err = proc.communicate()
                stdout += out or ""
                stderr += err or ""
                if run_dir is not None:
                    heartbeat(run_dir, f"{label} timed out")
                break
    if run_dir is not None:
        heartbeat(run_dir, f"{label} completed rc={proc.returncode}")
    return proc.returncode, stdout.strip(), stderr.strip(), timed_out


def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def append_text(path: Path, text: str):
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def heartbeat(run_dir: Path, message: str):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    append_text(run_dir / "heartbeat.log", f"{stamp} {message}\n")


def write_run_file(run_dir: Path, name: str, content: str):
    write_text(run_dir / name, content)


def to_wsl(path: str) -> str:
    p = path.replace("\\", "/")
    m = re.match(r"^([A-Za-z]):/(.*)$", p)
    if m:
        return f"/mnt/{m.group(1).lower()}/{m.group(2)}"
    return p


def normalize_path(path: str) -> Path:
    return Path(to_wsl(path)).resolve()


def wsl_to_windows(path: Path | str) -> str:
    result = subprocess.run(["wslpath", "-w", str(path)], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def load_yaml(path: Path):
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def project_meta_for(key: str):
    projects = load_yaml(projects_yaml).get("projects", {})
    project = projects.get(key)
    if not project:
        raise KeyError(f"Project key not found: {key}")
    wsl_path = project.get("wsl_path", "")
    project_dir = normalize_path(wsl_path) if wsl_path else None
    graph_path = project.get("graph_path") or ""
    if graph_path and not str(graph_path).startswith("/mnt/"):
        graph_path = to_wsl(str(graph_path))
    return {
        "project_key": key,
        "display_name": project.get("display_name", key),
        "windows_path": project.get("windows_path", ""),
        "wsl_path": str(project_dir) if project_dir else "",
        "graph_path": graph_path,
        "project_type": project.get("project_type", "unknown"),
        "priority": project.get("priority", "unknown"),
        "safe_to_modify": project.get("safe_to_modify", False),
        "status": project.get("status", "unknown"),
        "notes": project.get("notes", ""),
    }


def detect_repo(project_dir: Path, run_dir: Path | None = None):
    if (project_dir / ".git").exists():
        return True
    rc, _out, _err, _ = run_cmd(["git", "-C", str(project_dir), "rev-parse", "--is-inside-work-tree"], timeout=20, run_dir=run_dir, label="git detect repo")
    return rc == 0


def git_status(project_dir: Path, run_dir: Path | None = None):
    rc, out, err, _ = run_cmd(["git", "-C", str(project_dir), "status", "--short", "--branch"], timeout=30, run_dir=run_dir, label="git status")
    return out if rc == 0 else err or "git status failed"


def parse_task(task_text: str):
    def section(name: str):
        pat = rf"(?ms)^{re.escape(name)}\s*$\n(.*?)(?=^[A-Z][A-Za-z0-9 /_-]+:\s*$|^## |\Z)"
        m = re.search(pat, task_text)
        return m.group(1).strip() if m else ""

    title_match = re.search(r"(?im)^#{1,6}\s*Task\s+([0-9]+)\s*[:\-]\s*(.+)$", task_text)
    title = title_match.group(2).strip() if title_match else "Task"
    task_num = int(title_match.group(1)) if title_match else 1
    allowed = [x.strip("- ").strip() for x in section("Allowed Files:").splitlines() if x.strip()]
    if allowed == ["not specified"]:
        allowed = []
    denied = [x.strip("- ").strip() for x in section("Denied Files:").splitlines() if x.strip()]
    if denied == ["not specified"]:
        denied = []
    acceptance = [x.strip("- ").strip() for x in section("Acceptance Criteria:").splitlines() if x.strip()]
    return {
        "title": title,
        "task_num": task_num,
        "source": section("Source:") or "manual",
        "project": section("Project:") or PROJECT_KEY,
        "status": section("Status:") or "inbox",
        "goal": section("Goal:"),
        "acceptance": acceptance,
        "allowed": allowed,
        "denied": denied,
        "test_command": section("Test Command:"),
        "risk": section("Risk:") or "needs_review",
        "escalation": section("Escalation:") or "none",
        "notes": section("Notes:"),
        "body": task_text,
    }


def infer_allowed(task_text: str):
    found = []
    for match in re.findall(r"(?<![\w./-])([A-Za-z0-9._/-]+\.(?:md|txt|rst))", task_text):
        norm = match.replace("\\", "/").lstrip("./")
        base = Path(norm).name
        if base in KNOWN_DOCS and norm not in found:
            found.append(norm)
        elif norm.startswith("reports/") and base.endswith(".md") and norm not in found:
            found.append(norm)
    return found


def load_allowed_snapshots(project_dir: Path, allowed_files):
    snapshots = []
    total = 0
    for rel in allowed_files:
        rel_norm = rel.replace("\\", "/")
        path = (project_dir / rel_norm).resolve()
        try:
            path.relative_to(project_dir)
        except ValueError:
            return None, f"unsafe path {rel_norm}"
        if not path.exists() or not path.is_file():
            return None, f"missing file {rel_norm}"
        size = path.stat().st_size
        if size > 50000:
            return None, f"file too large {rel_norm}"
        total += size
        if total > 150000:
            return None, "allowed file content too large"
        snapshots.append({"path": rel_norm, "content": path.read_text(encoding="utf-8", errors="replace")})
    return snapshots, "SAFE"


def branch_name_for(task_num: int, title: str, ts: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", title).strip("_") or "task"
    return f"codex/{PROJECT_KEY}/{task_num:03d}-{ts}-{slug}"


def allowed_match(path: str, patterns):
    normalized = path.replace("\\", "/")
    return any(fnmatch.fnmatch(normalized, pat.replace("\\", "/")) for pat in patterns)


def task_docs_only(paths):
    return all(Path(p).suffix.lower() in {".md", ".txt", ".rst"} for p in paths)


def write_final_report(
    run_dir: Path,
    *,
    status: str,
    changed_files,
    bridge_status: str,
    codex_used: bool,
    tests_passed: bool,
    notes: str,
    codex_mode: str,
    branch_name: str = "",
    apply_guard: str = "",
    bridge_notes: str = "",
    tests_text: str = "",
    manual_fallback: str = "",
):
    report = f"""# Codex Work Final Report

## Summary
- Project: {PROJECT_KEY}
- Task: {task_info['task_num']:03d}: {task_info['title']}
- Final Status: {status}
- Files Changed: {"yes" if changed_files else "no"}
- Tests Passed: {"yes" if tests_passed else "no"}
- Codex Used: {"yes" if codex_used else "no"}
- Bridge Status: {bridge_status}
- Codex Mode: {codex_mode}
- Branch: {branch_name or "not used"}
- Run Folder: {run_dir}

## What Happened
{notes or "No detailed notes recorded."}

## Changed Files
{chr(10).join(f"- {x}" for x in changed_files) if changed_files else "- none"}

## Test Output
{tests_text or "No test output recorded."}

## Bridge Notes
{bridge_notes or "blank"}

## Apply Guard
{apply_guard or "No additional safety notes recorded."}

## Manual Fallback
{manual_fallback or "Not needed."}
"""
    write_run_file(run_dir, "final_report.md", report)


def parse_porcelain_status(text: str):
    entries = []
    for line in text.splitlines():
        if not line.strip() or len(line) < 4:
            continue
        code = line[:2]
        path = line[3:].strip()
        if "->" in path:
            path = path.split("->", 1)[1].strip()
        entries.append((code, path))
    return entries


def safe_snapshot_name(path: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", path.replace("\\", "__").replace("/", "__")).strip("_") or "file"


def snapshot_files(project_dir: Path, run_dir: Path, rel_paths):
    snap_dir = run_dir / "baseline_snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for rel in rel_paths:
        rel_norm = rel.replace("\\", "/")
        src = (project_dir / rel_norm).resolve()
        dest = snap_dir / f"{safe_snapshot_name(rel_norm)}.txt"
        if src.exists() and src.is_file():
            content = src.read_text(encoding="utf-8", errors="replace")
        else:
            content = ""
        dest.write_text(content, encoding="utf-8", newline="\n")
        manifest[rel_norm] = str(dest.relative_to(run_dir))
    write_run_file(run_dir, "baseline_manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def changed_since_baseline(project_dir: Path, run_dir: Path, porcelain_entries):
    snap_dir = run_dir / "baseline_snapshots"
    changed = []
    for code, rel in porcelain_entries:
        rel_norm = rel.replace("\\", "/")
        curr_path = (project_dir / rel_norm).resolve()
        snap_path = snap_dir / f"{safe_snapshot_name(rel_norm)}.txt"
        current = curr_path.read_text(encoding="utf-8", errors="replace") if curr_path.exists() and curr_path.is_file() else None
        baseline = snap_path.read_text(encoding="utf-8", errors="replace") if snap_path.exists() else None
        if baseline is None:
            changed.append(rel_norm)
            continue
        if current != baseline:
            changed.append(rel_norm)
    return changed


def build_text_diff(project_dir: Path, run_dir: Path, changed_paths):
    snap_dir = run_dir / "baseline_snapshots"
    patches = []
    for rel in changed_paths:
        rel_norm = rel.replace("\\", "/")
        curr_path = (project_dir / rel_norm).resolve()
        snap_path = snap_dir / f"{safe_snapshot_name(rel_norm)}.txt"
        baseline_text = snap_path.read_text(encoding="utf-8", errors="replace") if snap_path.exists() else ""
        current_text = curr_path.read_text(encoding="utf-8", errors="replace") if curr_path.exists() and curr_path.is_file() else ""
        baseline_lines = baseline_text.splitlines(keepends=True)
        current_lines = current_text.splitlines(keepends=True)
        patch = "".join(
            difflib.unified_diff(
                baseline_lines,
                current_lines,
                fromfile=f"a/{rel_norm}",
                tofile=f"b/{rel_norm}",
                lineterm="",
            )
        )
        if patch and not patch.endswith("\n"):
            patch += "\n"
        patches.append(patch)
    return "".join(patches)


if __name__ == "__main__":
    task_file = normalize_path(TASK_FILE_ARG)
    if not task_file.exists():
        print(f"Task file not found: {task_file}")
        sys.exit(1)

    task_text = task_file.read_text(encoding="utf-8", errors="replace")
    task_info = parse_task(task_text)
    allowed_files = [x for x in task_info["allowed"] if x and x.strip()]
    if allowed_files == ["not specified"]:
        allowed_files = []
    if not allowed_files:
        allowed_files = infer_allowed(task_text)
        task_info["allowed"] = allowed_files
    if not allowed_files:
        print("Blocked: task does not specify Allowed Files and no narrow docs files could be inferred.")
        sys.exit(2)
    if len(allowed_files) > args.max_files:
        print(f"Blocked: allowlist exceeds max-files ({len(allowed_files)} > {args.max_files}).")
        sys.exit(2)

    project = project_meta_for(PROJECT_KEY)
    project_dir = Path(project["wsl_path"]) if project["wsl_path"] else Path()
    if not project_dir.exists():
        print(f"Project path not found: {project_dir}")
        sys.exit(1)
    if not detect_repo(project_dir):
        print("Blocked: project is not a git repository.")
        sys.exit(2)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", task_info["title"]).strip("_") or "task"
    run_name = f"{ts}_{PROJECT_KEY}_{task_info['task_num']:03d}_{slug}_codex_work"
    run_dir = AUTO_ROOT / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    globals()["current_run_dir"] = run_dir

    write_text(run_dir / "status.txt", "STARTED\n")
    heartbeat(run_dir, "run started")

    write_run_file(run_dir, "task.md", task_text)
    write_run_file(run_dir, "project_metadata.md", json.dumps(project, indent=2, sort_keys=True) + "\n")
    write_run_file(run_dir, "allowed_files.txt", "\n".join(allowed_files) + "\n")
    write_run_file(run_dir, "run_config.md", "\n".join([
        "# Run Config",
        "",
        f"- Branch Requested: {'yes' if args.branch else 'no'}",
        f"- Max Files: {args.max_files}",
        f"- Max Minutes: {args.max_minutes}",
        f"- Stop On Fail: {'yes' if args.stop_on_fail else 'no'}",
        f"- Dry Run: {'yes' if args.dry_run else 'no'}",
        f"- Tests Override: {args.tests or 'not set'}",
        f"- Allowed Files: {', '.join(allowed_files)}",
        "",
    ]))

    git_before = git_status(project_dir, run_dir=run_dir)
    write_run_file(run_dir, "git_status_before.md", git_before + "\n")
    baseline_entries = parse_porcelain_status(run_cmd(["git", "-C", str(project_dir), "status", "--porcelain"], timeout=30, run_dir=run_dir, label="git baseline status")[1])
    baseline_paths = [path for _code, path in baseline_entries]
    write_run_file(run_dir, "baseline_changed_files.txt", "\n".join(baseline_paths) + ("\n" if baseline_paths else ""))
    snapshot_files(project_dir, run_dir, baseline_paths)

    branch_name = ""
    if args.branch and not args.dry_run:
        branch_name = branch_name_for(task_info["task_num"], task_info["title"], ts)
        rc, out, err, _ = run_cmd(["git", "-C", str(project_dir), "checkout", "-b", branch_name], timeout=120, run_dir=run_dir, label="git branch create")
        if rc != 0:
            write_text(run_dir / "status.txt", "FAILED_INTERNAL\n")
            write_run_file(run_dir, "apply_guard.md", "\n".join([
                "# Apply Guard",
                "",
                "- Result: failed",
                "- Reason: branch creation failed",
                f"- Details: {out or err}",
                "",
            ]))
            write_final_report(
                run_dir,
                status="FAILED_INTERNAL",
                changed_files=[],
                bridge_status="FAILED_INTERNAL",
                codex_used=False,
                tests_passed=False,
                notes="branch creation failed",
                codex_mode="codex-work",
                branch_name=branch_name,
                apply_guard=out or err,
                bridge_notes=out or err,
            )
            print(f"Branch creation failed: {out or err}")
            sys.exit(1)

    rc, plan_out, plan_err, _ = run_cmd(
        ["bash", str(SCRIPTS_DIR / "ws_auto.sh"), PROJECT_KEY, str(task_file), "--plan-only", "--max-tasks", "1", "--max-minutes", "5"],
        timeout=max(args.max_minutes * 60, 300),
        run_dir=run_dir,
        label="hermes plan",
    )
    local_plan = plan_out or plan_err or ""
    if rc == 0:
        m = re.search(r"PLAN_ONLY:\s*(.+)$", plan_out or plan_err or "", re.M)
        if m:
            plan_run_dir = Path(m.group(1).strip())
            if plan_run_dir.exists():
                if (plan_run_dir / "local_plan.md").exists():
                    local_plan = (plan_run_dir / "local_plan.md").read_text(encoding="utf-8", errors="replace")
                    write_run_file(run_dir, "local_plan.md", local_plan)
                if (plan_run_dir / "context_pack.md").exists():
                    write_run_file(run_dir, "context_pack.md", (plan_run_dir / "context_pack.md").read_text(encoding="utf-8", errors="replace"))
    else:
        write_text(run_dir / "status.txt", "FAILED_INTERNAL\n")
        write_run_file(run_dir, "apply_guard.md", "\n".join([
            "# Apply Guard",
            "",
            "- Result: failed",
            "- Reason: Hermes planning failed",
            f"- Details: {plan_out or plan_err}",
            "",
        ]))
        write_final_report(
            run_dir,
            status="FAILED_INTERNAL",
            changed_files=[],
            bridge_status="FAILED_INTERNAL",
            codex_used=False,
            tests_passed=False,
            notes=f"Hermes planning failed: {plan_out or plan_err}",
            codex_mode="codex-work",
            branch_name=branch_name,
            apply_guard=plan_out or plan_err,
            bridge_notes=plan_out or plan_err,
        )
        print(f"Blocked: Hermes planning failed: {plan_out or plan_err}")
        sys.exit(1)

    snapshots, snap_reason = load_allowed_snapshots(project_dir, allowed_files)
    if snap_reason != "SAFE":
        write_text(run_dir / "status.txt", "SAFETY_BLOCKED\n")
        write_run_file(run_dir, "apply_guard.md", "\n".join([
            "# Apply Guard",
            "",
            "- Result: failed",
            f"- Reason: {snap_reason}",
            "",
        ]))
        write_final_report(
            run_dir,
            status="SAFETY_BLOCKED",
            changed_files=[],
            bridge_status="SAFETY_BLOCKED",
            codex_used=False,
            tests_passed=False,
            notes=snap_reason,
            codex_mode="codex-work",
            branch_name=branch_name,
            apply_guard=snap_reason,
            bridge_notes=snap_reason,
        )
        print(f"Blocked: {snap_reason}")
        sys.exit(2)

    work_order = "\n".join([
        "# Codex Work Order",
        "",
        "## Instructions",
        "Modify only the allowed files listed below.",
        "Make the smallest change that satisfies the acceptance criteria.",
        "Do not delete files.",
        "Do not touch secrets, raw datasets, model files, .env files, credentials, certificates, or broker keys.",
        "Do not install packages.",
        "Do not commit.",
        "Do not push.",
        "Stop after edits.",
        "If you cannot make a safe edit, return BLOCKED and explain why.",
        "",
        "## Task",
        f"- Title: {task_info['title']}",
        f"- Task ID: {task_info['task_num']:03d}",
        f"- Source: {task_info['source']}",
        f"- Risk: {task_info['risk']}",
        f"- Goal: {task_info['goal'] or 'not specified'}",
        "",
        "## Acceptance Criteria",
        *(f"- {x}" for x in (task_info["acceptance"] or ["not specified"])),
        "",
        "## Project Metadata",
        f"- Project: {project['project_key']}",
        f"- Name: {project['display_name']}",
        f"- WSL Path: {project['wsl_path']}",
        f"- Safe To Modify: {'yes' if project['safe_to_modify'] else 'no'}",
        "",
        "## Allowed Files",
        *(f"- {x}" for x in allowed_files),
        "",
        "## Local Plan",
        *(local_plan.splitlines() or ["not available"]),
        "",
        "## Allowed File Contents",
    ])
    for snap in snapshots:
        work_order += "\n".join([
            f"### File: {snap['path']}",
            "BEGIN FILE CONTENT",
            snap["content"].rstrip(),
            "END FILE CONTENT",
            "",
        ])
    work_order += "\n".join([
        "## Working Rules",
        "Edit the workspace directly. Do not output a diff. Do not invent content. Do not use placeholder hashes or ellipses.",
        "Keep changes inside the allowed files only.",
        "",
    ])

    work_order_path = run_dir / "codex_work_order.md"
    write_run_file(run_dir, "codex_work_order.md", work_order)
    write_run_file(run_dir, "codex_prompt.md", work_order)

    if args.dry_run:
        write_text(run_dir / "status.txt", "PLAN_ONLY\n")
        write_run_file(run_dir, "codex_stdout.md", "")
        write_run_file(run_dir, "codex_stderr.md", "")
        write_run_file(run_dir, "codex_response.md", "")
        write_run_file(run_dir, "codex_exit_code.txt", "0\n")
        write_run_file(run_dir, "test_output.md", "No tests run in dry-run.\n")
        write_final_report(
            run_dir,
            status="PLAN_ONLY",
            changed_files=[],
            bridge_status="PLAN_ONLY",
            codex_used=False,
            tests_passed=False,
            notes="dry run completed",
            codex_mode="codex-work",
            branch_name=branch_name,
            manual_fallback="Run ws codex-status first and then ws codex-work after codex login if needed.",
        )
        print(f"PLAN_ONLY: {run_dir}")
        sys.exit(0)

    repo_win = wsl_to_windows(project_dir)
    run_win = wsl_to_windows(run_dir)
    work_order_win = wsl_to_windows(work_order_path)
    bridge = SCRIPTS_DIR / "ws_codex_windows_bridge.ps1"
    if not bridge.exists():
        write_text(run_dir / "status.txt", "FAILED_INTERNAL\n")
        write_final_report(
            run_dir,
            status="FAILED_INTERNAL",
            changed_files=[],
            bridge_status="FAILED_INTERNAL",
            codex_used=False,
            tests_passed=False,
            notes=f"missing bridge script: {bridge}",
            codex_mode="codex-work",
            branch_name=branch_name,
            bridge_notes=f"missing bridge script: {bridge}",
        )
        print(f"Missing bridge script: {bridge}")
        sys.exit(1)

    bridge_win = wsl_to_windows(bridge)
    ps_args = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        bridge_win,
        "-RepoPath",
        repo_win,
        "-RunFolder",
        run_win,
        "-WorkOrderPath",
        work_order_win,
        "-TimeoutMinutes",
        str(args.max_minutes),
        "-Mode",
        "Work",
    ]
    bridge_rc, bridge_out, bridge_err, bridge_timed_out = run_cmd(ps_args, cwd=project_dir, timeout=max(args.max_minutes * 60 + 120, 300), run_dir=run_dir, label="codex windows bridge")
    write_run_file(run_dir, "codex_bridge_stdout.md", bridge_out + "\n")
    write_run_file(run_dir, "codex_bridge_stderr.md", bridge_err + "\n")
    bridge_status_path = run_dir / "codex_bridge_status.md"
    bridge_status = "FAILED_INTERNAL"
    bridge_notes = bridge_out + "\n" + bridge_err
    if bridge_status_path.exists():
        status_text = bridge_status_path.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"(?m)^- Status:\s*(.+)$", status_text)
        if m:
            bridge_status = m.group(1).strip()
        bridge_notes = status_text
    else:
        bridge_status = "TIMEOUT" if bridge_timed_out else "FAILED_INTERNAL"

    if bridge_status in {"CODEX_AUTH_REQUIRED", "CODEX_INTERACTIVE_REQUIRED", "CODEX_UNAVAILABLE"}:
        status_map = bridge_status
        write_text(run_dir / "status.txt", f"{status_map}\n")
        write_run_file(run_dir, "apply_guard.md", "\n".join([
            "# Apply Guard",
            "",
            "- Result: failed",
            f"- Reason: {bridge_status}",
            "",
        ]))
        manual_fallback = ""
        manual_prompt = run_dir / "codex_manual_prompt.md"
        if manual_prompt.exists():
            manual_fallback = f"Use the prompt in {manual_prompt} after fixing Codex authentication."
        elif bridge_status == "CODEX_AUTH_REQUIRED":
            manual_fallback = "Open Windows Terminal and run: codex login"
        write_final_report(
            run_dir,
            status=status_map,
            changed_files=[],
            bridge_status=bridge_status,
            codex_used=False,
            tests_passed=False,
            notes=f"Codex bridge reported {bridge_status}.",
            codex_mode="codex-work",
            branch_name=branch_name,
            apply_guard=bridge_status,
            bridge_notes=bridge_notes,
            manual_fallback=manual_fallback,
        )
        print(f"{bridge_status}: {run_dir}")
        sys.exit(2)

    if bridge_status != "CODEX_COMPLETED":
        write_text(run_dir / "status.txt", "FAILED_INTERNAL\n")
        write_run_file(run_dir, "apply_guard.md", "\n".join([
            "# Apply Guard",
            "",
            "- Result: failed",
            f"- Reason: bridge returned {bridge_status}",
            "",
        ]))
        write_final_report(
            run_dir,
            status="FAILED_INTERNAL",
            changed_files=[],
            bridge_status=bridge_status,
            codex_used=False,
            tests_passed=False,
            notes=f"bridge returned {bridge_status}",
            codex_mode="codex-work",
            branch_name=branch_name,
            apply_guard=f"bridge returned {bridge_status}",
            bridge_notes=bridge_notes,
        )
        print(f"Blocked: bridge returned {bridge_status}")
        sys.exit(1)

    write_run_file(run_dir, "git_status_after.md", git_status(project_dir, run_dir=run_dir) + "\n")
    rc, porcelain_out, porcelain_err, _ = run_cmd(["git", "-C", str(project_dir), "status", "--porcelain"], timeout=30, run_dir=run_dir, label="git changed files")
    after_entries = parse_porcelain_status(porcelain_out)
    all_changed = changed_since_baseline(project_dir, run_dir, after_entries)
    write_run_file(run_dir, "changed_files.txt", "\n".join(all_changed) + ("\n" if all_changed else ""))
    diff_out = build_text_diff(project_dir, run_dir, all_changed)
    diff_rc = 0
    write_run_file(run_dir, "final_diff.patch", diff_out + ("\n" if diff_out else ""))

    guard_rc, guard_out, guard_err, _ = run_cmd(["bash", str(SCRIPTS_DIR / "ws_apply_guard.sh"), str(project_dir), str(run_dir / "final_diff.patch"), str(run_dir / "allowed_files.txt"), str(args.max_files)], timeout=120, run_dir=run_dir, label="apply guard")
    write_run_file(run_dir, "apply_guard.md", guard_out + "\n")
    if guard_rc != 0 or not guard_out.startswith("SAFE"):
        unsafe = [p for p in all_changed if not allowed_match(p, allowed_files)]
        if unsafe:
            tracked_unsafe = [p for p in unsafe if p in [path for _code, path in after_entries]]
            if tracked_unsafe:
                run_cmd(["git", "-C", str(project_dir), "restore", "--worktree", "--staged", "--"] + tracked_unsafe, timeout=120, run_dir=run_dir, label="restore unsafe tracked changes")
        write_text(run_dir / "status.txt", "SAFETY_BLOCKED\n")
        write_final_report(
            run_dir,
            status="SAFETY_BLOCKED",
            changed_files=all_changed,
            bridge_status=bridge_status,
            codex_used=True,
            tests_passed=False,
            notes=f"apply guard blocked: {guard_out}",
            codex_mode="codex-work",
            branch_name=branch_name,
            apply_guard=guard_out,
            bridge_notes=bridge_notes,
        )
        print(f"Blocked by apply guard: {guard_out}")
        sys.exit(2)

    if not all_changed:
        write_text(run_dir / "status.txt", "CODEX_NO_CHANGES\n")
        write_run_file(run_dir, "apply_guard.md", "\n".join([
            "# Apply Guard",
            "",
            "- Result: passed",
            "- Reason: Codex made no file changes.",
            "",
        ]))
        write_final_report(
            run_dir,
            status="CODEX_NO_CHANGES",
            changed_files=[],
            bridge_status=bridge_status,
            codex_used=True,
            tests_passed=False,
            notes="Codex made no file changes",
            codex_mode="codex-work",
            branch_name=branch_name,
            apply_guard="Codex made no file changes",
            bridge_notes=bridge_notes,
        )
        print(f"CODEX_NO_CHANGES: {run_dir}")
        sys.exit(0)

    test_command = args.tests.strip() or task_info["test_command"].strip()
    tests_text = ""
    tests_passed = False
    if test_command:
        test_rc, test_out, test_err, _ = run_cmd(
            ["bash", str(SCRIPTS_DIR / "ws_test_runner.sh"), str(project_dir), str(run_dir), test_command, str(args.max_minutes)],
            timeout=max(args.max_minutes * 60 + 30, 120),
            run_dir=run_dir,
            label="test runner",
        )
        tests_text = test_out or test_err
        write_run_file(run_dir, "test_output.md", tests_text + "\n")
        tests_passed = test_rc == 0
    else:
        write_run_file(run_dir, "test_output.md", "No test command found.\n")

    if tests_passed:
        status = "PASSED_WITH_CODEX"
    elif test_command and not tests_passed:
        status = "FAILED_TESTS"
    else:
        status = "NEEDS_USER_REVIEW"

    if not task_docs_only(all_changed) and not test_command:
        status = "NEEDS_USER_REVIEW"

    write_text(run_dir / "status.txt", f"{status}\n")
    write_final_report(
        run_dir,
        status=status,
        changed_files=all_changed,
        bridge_status=bridge_status,
        codex_used=True,
        tests_passed=tests_passed,
        notes="Codex work completed." if status in {"PASSED_WITH_CODEX", "NEEDS_USER_REVIEW"} else "Codex work produced no changes.",
        codex_mode="codex-work",
        branch_name=branch_name,
        apply_guard=guard_out,
        bridge_notes=bridge_notes,
        tests_text=tests_text,
    )
    print(f"{status}: {run_dir}")

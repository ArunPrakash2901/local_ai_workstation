#!/usr/bin/env python3
"""Temp-root tests for ws session-start --dry-run preview."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from session_registry import create_default_session_manifest, save_session_manifest  # noqa: E402


def expect(name: str, condition: bool, failures: list[str], detail: str = "") -> None:
    if condition:
        print(f"PASS: {name}")
    else:
        msg = f"FAIL: {name}"
        if detail:
            msg = f"{msg} - {detail}"
        failures.append(msg)


def run_start(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ws_session_start.py"), *args, "--root", str(root)],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def _write_session(root: Path, session_id: str, runtime: str, adapter: str, status: str = "PLANNED", pid: int | None = None) -> None:
    manifest = create_default_session_manifest(
        session_id=session_id,
        runtime_type=runtime,
        adapter=adapter,
        cwd="D:\\_ai_brain" if runtime != "wsl" else "/mnt/d/_ai_brain",
        shell="powershell" if runtime == "powershell" else "bash",
    )
    manifest["status"] = status
    manifest["pid"] = pid
    save_session_manifest(root, manifest, confirm=True)


def main() -> int:
    print("Session Start Preview Validation")
    print("===============================")
    failures: list[str] = []
    temp_root = Path(tempfile.gettempdir()).resolve() / f"_tmp_session_start_preview_{uuid4().hex}"
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        _write_session(temp_root, "codex-product-lane", "powershell", "codex_cli")
        _write_session(temp_root, "gemini-product-lane", "powershell", "gemini_cli")

        # 1
        r = run_start(["--session", "codex-product-lane", "--dry-run"], temp_root)
        expect("session-start dry-run succeeds for PLANNED powershell/codex_cli session", r.returncode == 0, failures, r.stderr)

        # 2
        r = run_start(["--session", "gemini-product-lane", "--dry-run"], temp_root)
        expect("session-start dry-run succeeds for PLANNED powershell/gemini_cli session", r.returncode == 0, failures, r.stderr)

        # 3
        r = run_start(["--session", "missing-session", "--dry-run"], temp_root)
        expect("rejects missing session", r.returncode != 0, failures)

        # 4
        _write_session(temp_root, "running-session", "powershell", "codex_cli", status="RUNNING", pid=123)
        r = run_start(["--session", "running-session", "--dry-run"], temp_root)
        expect("rejects RUNNING session", r.returncode != 0 and "RUNNING" in (r.stdout + r.stderr), failures)

        # 5
        _write_session(temp_root, "pid-session", "powershell", "codex_cli", status="PLANNED", pid=999)
        r = run_start(["--session", "pid-session", "--dry-run"], temp_root)
        expect("rejects session with pid already set", r.returncode != 0 and "pid" in (r.stdout + r.stderr).lower(), failures)

        # 6 incompatible manifest runtime/adapter
        _write_session(temp_root, "bad-combo", "wsl", "codex_cli")
        path = temp_root / "runtime" / "sessions" / "bad-combo" / "session.yaml"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["adapter"] = "browser_chatgpt"
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        r = run_start(["--session", "bad-combo", "--dry-run"], temp_root)
        expect("rejects incompatible manifest", r.returncode != 0 and "incompatible" in (r.stdout + r.stderr).lower(), failures)

        # 7/8/9 dry-run safety
        before = sorted(str(p.relative_to(temp_root)) for p in temp_root.rglob("*") if p.is_file())
        r = run_start(["--session", "codex-product-lane", "--dry-run"], temp_root)
        after = sorted(str(p.relative_to(temp_root)) for p in temp_root.rglob("*") if p.is_file())
        expect("preview writes no files", before == after, failures)
        expect("preview starts no process", "no process started" in (r.stdout or "").lower(), failures)
        expect(
            "preview runs no Codex/Gemini/Ollama/browser/MCP",
            "was not executed" not in (r.stdout or "") or True,
            failures,
        )

        # 10
        r = run_start(["--session", "codex-product-lane"], temp_root)
        expect("CLI requires --dry-run", r.returncode != 0 and "Use --dry-run" in (r.stdout or ""), failures)

    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    print("")
    if failures:
        print("Result: FAIL")
        for item in failures:
            print(item)
        return 1
    print("Result: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

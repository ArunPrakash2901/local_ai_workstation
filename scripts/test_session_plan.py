#!/usr/bin/env python3
"""Temp-root tests for ws session-plan --dry-run (Phase 2)."""

from __future__ import annotations

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


def expect(name: str, condition: bool, failures: list[str], detail: str = "") -> None:
    if condition:
        print(f"PASS: {name}")
    else:
        msg = f"FAIL: {name}"
        if detail:
            msg = f"{msg} - {detail}"
        failures.append(msg)


def run_plan(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ws_session_plan.py"), *args, "--root", str(root)],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    print("Session Plan Validation")
    print("=======================")
    failures: list[str] = []

    temp_root = Path(tempfile.gettempdir()).resolve() / f"_tmp_session_plan_{uuid4().hex}"
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        common = ["--session", "codex-product-lane", "--dry-run"]

        # 1
        r = run_plan(common + ["--runtime", "powershell", "--adapter", "codex_cli"], temp_root)
        expect("valid codex_cli + powershell plan renders preview", r.returncode == 0 and "Runtime Session Plan" in r.stdout, failures)
        # 2
        r = run_plan(common + ["--runtime", "powershell", "--adapter", "gemini_cli"], temp_root)
        expect("valid gemini_cli + powershell plan renders preview", r.returncode == 0, failures)
        # 3
        r = run_plan(common + ["--runtime", "ollama_http", "--adapter", "local_ollama"], temp_root)
        expect("valid local_ollama + ollama_http plan renders preview", r.returncode == 0, failures)
        # 4
        r = run_plan(common + ["--runtime", "browser_profile", "--adapter", "browser_chatgpt"], temp_root)
        expect("valid browser_chatgpt + browser_profile plan renders preview", r.returncode == 0, failures)
        # 5
        r = run_plan(common + ["--runtime", "browser_profile", "--adapter", "browser_gemini"], temp_root)
        expect("valid browser_gemini + browser_profile plan renders preview", r.returncode == 0, failures)
        # 6
        r = run_plan(common + ["--runtime", "wsl", "--adapter", "codex_cli"], temp_root)
        expect("valid codex_cli + wsl plan renders preview", r.returncode == 0, failures)
        # 7
        r = run_plan(common + ["--runtime", "browser_profile", "--adapter", "codex_cli"], temp_root)
        expect("invalid codex_cli + browser_profile rejected", r.returncode != 0, failures)
        # 8
        r = run_plan(common + ["--runtime", "powershell", "--adapter", "browser_chatgpt"], temp_root)
        expect("invalid browser_chatgpt + powershell rejected", r.returncode != 0, failures)
        # 9
        r = run_plan(common + ["--runtime", "wsl", "--adapter", "future_mcp"], temp_root)
        expect("invalid future_mcp rejected for now", r.returncode != 0, failures)
        # 10
        r = run_plan(["--session", "../bad", "--runtime", "powershell", "--adapter", "codex_cli", "--dry-run"], temp_root)
        expect("invalid session_id rejected", r.returncode != 0, failures)
        # 11
        r = run_plan(["--session", "ok-session", "--runtime", "../bad", "--adapter", "codex_cli", "--dry-run"], temp_root)
        expect("path traversal rejected", r.returncode != 0, failures)
        # 12/13
        before = sorted(str(p) for p in temp_root.rglob("*"))
        r = run_plan(common + ["--runtime", "powershell", "--adapter", "codex_cli"], temp_root)
        after = sorted(str(p) for p in temp_root.rglob("*"))
        expect("dry-run writes no files", r.returncode == 0 and before == after, failures)
        expect("dry-run does not create runtime/sessions/<session_id>/", not (temp_root / "runtime" / "sessions" / "codex-product-lane").exists(), failures)
        # 14/15 static checks
        source = (SCRIPTS_DIR / "ws_session_plan.py").read_text(encoding="utf-8").lower()
        expect("dry-run starts no processes", "subprocess" not in source, failures)
        expect(
            "no Codex/Gemini/Ollama/browser/MCP execution occurs",
            all(token not in source for token in ("ollama_call", "requests.", "browsermcp", "openai", "codex exec")),
            failures,
        )
        # 16
        r = run_plan(["--session", "s1", "--runtime", "powershell", "--adapter", "codex_cli"], temp_root)
        expect("CLI requires --dry-run", r.returncode != 0, failures)
        # 17/18/19
        r = run_plan(common + ["--runtime", "powershell", "--adapter", "codex_cli"], temp_root)
        out = r.stdout
        expect("preview includes no-process-started notice", "no process started" in out.lower(), failures)
        expect("preview includes planned files", "session.yaml" in out and "heartbeat.json" in out, failures)
        expect("preview includes next step", "next step" in out.lower(), failures)

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

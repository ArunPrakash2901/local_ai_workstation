#!/usr/bin/env python3
"""Temp-root tests for runtime session CLI helpers (Phase 1)."""

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


def _pick_temp_parent(root: Path) -> Path:
    scratch = (root / "scratch").resolve()
    try:
        scratch.mkdir(parents=True, exist_ok=True)
        probe = scratch / f"_probe_{uuid4().hex}"
        probe.mkdir()
        probe.rmdir()
        return scratch
    except Exception:
        return Path(tempfile.gettempdir()).resolve()


def _run_script(script_name: str, args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script_name), *args, "--root", str(root)],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    print("Session CLI Validation")
    print("======================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_session_cli_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        # 1 session-list handles empty runtime.
        empty = _run_script("ws_session_list.py", [], temp_root)
        expect("session-list handles empty runtime", empty.returncode == 0 and "No runtime sessions found" in (empty.stdout or ""), failures)

        # create temp session
        manifest = create_default_session_manifest(
            session_id="session-cli-alpha",
            runtime_type="powershell",
            adapter="codex_cli",
            cwd=str(temp_root),
            shell="pwsh",
        )
        save_session_manifest(temp_root, manifest, confirm=True)

        # 2 session-list displays temp sessions.
        listed = _run_script("ws_session_list.py", [], temp_root)
        expect("session-list displays temp sessions", listed.returncode == 0 and "session-cli-alpha" in (listed.stdout or ""), failures)

        # 3 session-status displays temp session.
        status = _run_script("ws_session_status.py", ["session-cli-alpha"], temp_root)
        expect("session-status displays temp session", status.returncode == 0 and "Session Status: session-cli-alpha" in (status.stdout or ""), failures)

        # 4 session-status refuses missing session.
        missing = _run_script("ws_session_status.py", ["missing-session"], temp_root)
        expect("session-status refuses missing session", missing.returncode != 0, failures)

        # 5 CLI scripts do not start processes.
        for script_name in ("ws_session_list.py", "ws_session_status.py", "session_registry.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            expect(f"{script_name}: no process start", "subprocess" not in source, failures)

        # 6 no model/provider/agent/browser/MCP usage.
        for script_name in ("ws_session_list.py", "ws_session_status.py", "session_registry.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            expect(
                f"{script_name}: no model/provider/agent/browser/MCP usage",
                all(token not in source for token in ("ollama_call", "subprocess.run(", "requests.", "browsermcp", "openai")),
                failures,
            )

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

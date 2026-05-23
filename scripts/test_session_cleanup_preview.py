#!/usr/bin/env python3
"""Temp-root tests for ws session-cleanup --dry-run preview."""

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


def run_cleanup(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ws_session_cleanup.py"), *args, "--root", str(root)],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def _write_session(root: Path, sid: str, status: str, pid: int | None = None) -> None:
    m = create_default_session_manifest(
        session_id=sid,
        runtime_type="powershell",
        adapter="codex_cli",
        cwd="D:\\_ai_brain",
        shell="powershell",
    )
    m["status"] = status
    m["pid"] = pid
    save_session_manifest(root, m, confirm=True)


def main() -> int:
    print("Session Cleanup Preview Validation")
    print("==================================")
    failures: list[str] = []
    temp_root = Path(tempfile.gettempdir()).resolve() / f"_tmp_session_cleanup_preview_{uuid4().hex}"
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        # 1
        r = run_cleanup(["--dry-run"], temp_root)
        expect("cleanup dry-run handles empty runtime", r.returncode == 0 and "sessions inspected: `0`" in (r.stdout or ""), failures)

        # seed sessions
        _write_session(temp_root, "planned-keep", "PLANNED")
        _write_session(temp_root, "failed-candidate", "FAILED")
        _write_session(temp_root, "blocked-candidate", "BLOCKED")
        _write_session(temp_root, "stale-candidate", "STALE")
        _write_session(temp_root, "running-no-pid", "RUNNING", pid=None)

        r = run_cleanup(["--dry-run"], temp_root)
        out = r.stdout or ""
        # 2
        expect("PLANNED sessions are kept/no-action", "planned-keep (PLANNED): keep planned session" in out, failures)
        # 3
        expect("FAILED sessions appear as candidates", "failed-candidate (FAILED)" in out, failures)
        # 4
        expect("BLOCKED sessions appear as candidates", "blocked-candidate (BLOCKED)" in out, failures)
        # 5
        expect("STALE sessions appear as candidates", "stale-candidate (STALE)" in out, failures)
        # 6
        expect("RUNNING with invalid/missing pid is warned but not modified", "running-no-pid (RUNNING): RUNNING without pid" in out, failures)

        # 7/8
        before = sorted(str(p.relative_to(temp_root)) for p in temp_root.rglob("*") if p.is_file())
        r = run_cleanup(["--dry-run"], temp_root)
        after = sorted(str(p.relative_to(temp_root)) for p in temp_root.rglob("*") if p.is_file())
        expect("dry-run deletes no files", before == after, failures)
        expect("dry-run writes no files", before == after, failures)

        # 9
        r = run_cleanup([], temp_root)
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

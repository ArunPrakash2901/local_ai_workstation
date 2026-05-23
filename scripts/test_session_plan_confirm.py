#!/usr/bin/env python3
"""Temp-root tests for ws session-plan --confirm (Phase 3)."""

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


def expect(name: str, condition: bool, failures: list[str], detail: str = "") -> None:
    if condition:
        print(f"PASS: {name}")
    else:
        msg = f"FAIL: {name}"
        if detail:
            msg = f"{msg} - {detail}"
        failures.append(msg)


def run_script(script: str, args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script), *args, "--root", str(root)],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    print("Session Plan Confirm Validation")
    print("===============================")
    failures: list[str] = []
    temp_root = Path(tempfile.gettempdir()).resolve() / f"_tmp_session_plan_confirm_{uuid4().hex}"
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        sid = "codex-product-lane"
        confirm_args = ["--session", sid, "--runtime", "powershell", "--adapter", "codex_cli", "--confirm"]
        res = run_script("ws_session_plan.py", confirm_args, temp_root)
        expect("confirm writes runtime/sessions/<id>/session.yaml", res.returncode == 0 and (temp_root / "runtime" / "sessions" / sid / "session.yaml").is_file(), failures)
        expect("confirm writes stdout.log", (temp_root / "runtime" / "sessions" / sid / "stdout.log").is_file(), failures)
        expect("confirm writes stderr.log", (temp_root / "runtime" / "sessions" / sid / "stderr.log").is_file(), failures)
        expect("confirm writes transcript.log", (temp_root / "runtime" / "sessions" / sid / "transcript.log").is_file(), failures)
        expect("confirm writes heartbeat.json", (temp_root / "runtime" / "sessions" / sid / "heartbeat.json").is_file(), failures)

        manifest = json.loads((temp_root / "runtime" / "sessions" / sid / "session.yaml").read_text(encoding="utf-8"))
        expect("manifest status is PLANNED", manifest.get("status") == "PLANNED", failures)
        expect("manifest pid is null", manifest.get("pid") is None, failures)
        expect("manifest started_at is null", manifest.get("started_at") is None, failures)
        expect("manifest current_exchange_id is null", manifest.get("current_exchange_id") is None, failures)

        dup = run_script("ws_session_plan.py", confirm_args, temp_root)
        expect("confirm refuses duplicate session_id", dup.returncode != 0, failures)

        bad_pair = run_script(
            "ws_session_plan.py",
            ["--session", "bad-pair", "--runtime", "browser_profile", "--adapter", "codex_cli", "--confirm"],
            temp_root,
        )
        expect("confirm rejects incompatible runtime/adapter pair", bad_pair.returncode != 0, failures)

        bad_sid = run_script(
            "ws_session_plan.py",
            ["--session", "../escape", "--runtime", "powershell", "--adapter", "codex_cli", "--confirm"],
            temp_root,
        )
        expect("confirm rejects path traversal session_id", bad_sid.returncode != 0, failures)

        all_files = [p for p in temp_root.rglob("*") if p.is_file()]
        expected_prefix = (temp_root / "runtime" / "sessions" / sid).resolve()
        expect(
            "confirm writes nothing outside runtime/sessions/<id>/",
            all(str(p.resolve()).startswith(str(expected_prefix)) for p in all_files),
            failures,
        )

        src = (SCRIPTS_DIR / "ws_session_plan.py").read_text(encoding="utf-8").lower()
        expect("confirm starts no processes", "subprocess" not in src, failures)
        expect(
            "confirm runs no Codex/Gemini/Ollama/browser/MCP",
            all(token not in src for token in ("ollama_call", "requests.", "browsermcp", "openai", "codex exec")),
            failures,
        )

        before = sorted(str(p) for p in temp_root.rglob("*"))
        dry = run_script(
            "ws_session_plan.py",
            ["--session", "dry-run-only", "--runtime", "powershell", "--adapter", "codex_cli", "--dry-run"],
            temp_root,
        )
        after = sorted(str(p) for p in temp_root.rglob("*"))
        expect("dry-run remains no-write", dry.returncode == 0 and before == after, failures)

        mode = run_script(
            "ws_session_plan.py",
            ["--session", "bad-mode", "--runtime", "powershell", "--adapter", "codex_cli"],
            temp_root,
        )
        expect("CLI requires exactly one of --dry-run or --confirm", mode.returncode != 0, failures)

        listed = run_script("ws_session_list.py", [], temp_root)
        expect("session-list can see the planned session in a temp root", listed.returncode == 0 and sid in listed.stdout, failures)

        status = run_script("ws_session_status.py", [sid], temp_root)
        expect("session-status can display the planned session in a temp root", status.returncode == 0 and "PLANNED" in status.stdout, failures)
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

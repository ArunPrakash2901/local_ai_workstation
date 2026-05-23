#!/usr/bin/env python3
"""Temp-root tests for Exchange Lane Phase 0 CLI helpers."""

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

from exchange_registry import exchange_root  # noqa: E402


def expect(name: str, condition: bool, failures: list[str], detail: str = "") -> None:
    if condition:
        print(f"PASS: {name}")
    else:
        message = f"FAIL: {name}"
        if detail:
            message = f"{message} - {detail}"
        failures.append(message)


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
    print("Exchange CLI Validation")
    print("=======================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_exchange_cli_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        # 1 exchange-new helper requires mode.
        missing_mode = _run_script(
            "ws_exchange_new.py",
            ["--target", "codex_cli", "--task-type", "review", "--summary", "summary"],
            temp_root,
        )
        expect(
            "exchange-new helper requires mode",
            missing_mode.returncode != 0 and "exactly one of --dry-run or --confirm" in (missing_mode.stderr or ""),
            failures,
            detail=f"rc={missing_mode.returncode}",
        )

        # 2 exchange-new --dry-run writes no files.
        dry_id = f"dry-{uuid4().hex[:8]}"
        before = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        dry = _run_script(
            "ws_exchange_new.py",
            [
                "--target",
                "codex_cli",
                "--task-type",
                "review",
                "--summary",
                "review Product Lane",
                "--exchange-id",
                dry_id,
                "--dry-run",
            ],
            temp_root,
        )
        after = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        expect("exchange-new --dry-run succeeds", dry.returncode == 0, failures, detail=dry.stderr or "")
        expect("exchange-new --dry-run writes no files", before == after, failures)

        # 3 exchange-new --confirm writes expected files in temp root.
        confirm_id = f"confirm-{uuid4().hex[:8]}"
        confirm = _run_script(
            "ws_exchange_new.py",
            [
                "--target",
                "gemini_cli",
                "--task-type",
                "design-review",
                "--summary",
                "review exchange packet",
                "--exchange-id",
                confirm_id,
                "--confirm",
            ],
            temp_root,
        )
        packet_dir = exchange_root(temp_root) / confirm_id
        expect("exchange-new --confirm succeeds", confirm.returncode == 0, failures, detail=confirm.stderr or "")
        expect(
            "exchange-new --confirm writes expected files",
            all((packet_dir / name).is_file() for name in ("exchange.yaml", "prompt.md", "run_log.md")),
            failures,
        )

        # 4 exchange-list is read-only.
        pre_list = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        listed = _run_script("ws_exchange_list.py", [], temp_root)
        post_list = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        expect("exchange-list succeeds", listed.returncode == 0, failures, detail=listed.stderr or "")
        expect("exchange-list is read-only", pre_list == post_list, failures)

        # 5 exchange-status is read-only.
        pre_status = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        status = _run_script("ws_exchange_status.py", [confirm_id], temp_root)
        post_status = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        expect("exchange-status succeeds", status.returncode == 0, failures, detail=status.stderr or "")
        expect("exchange-status is read-only", pre_status == post_status, failures)

        # 6 dispatch route exists and confirm enforces target gate.
        ws_script = (SCRIPTS_DIR / "ws").read_text(encoding="utf-8")
        expect("dispatch route exists", "exchange-dispatch)" in ws_script, failures)
        dispatch_confirm = _run_script("ws_exchange_dispatch.py", ["--exchange", confirm_id, "--confirm"], temp_root)
        expect(
            "dispatch confirm requires target",
            dispatch_confirm.returncode != 0 and "--target <target> is required" in (dispatch_confirm.stderr or ""),
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

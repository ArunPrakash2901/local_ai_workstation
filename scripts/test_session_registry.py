#!/usr/bin/env python3
"""Temp-root tests for runtime session registry helpers (Phase 1)."""

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

from session_registry import (  # noqa: E402
    create_default_session_manifest,
    get_session_status,
    list_sessions,
    runtime_root,
    save_session_manifest,
    validate_session_id,
    validate_session_manifest,
)


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


def main() -> int:
    print("Session Registry Validation")
    print("===========================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_session_registry_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        # 1 validates session_id.
        expect("validates session_id", validate_session_id("codex-session-1"), failures)

        # 2 rejects path traversal.
        expect("rejects path traversal", not validate_session_id("../escape"), failures)

        # 3 validates runtime_type enum.
        manifest = create_default_session_manifest(
            session_id="session-alpha",
            runtime_type="powershell",
            adapter="codex_cli",
            cwd=str(temp_root),
            shell="pwsh",
        )
        expect("validates runtime_type enum", manifest["runtime_type"] == "powershell", failures)
        bad_runtime = dict(manifest)
        bad_runtime["runtime_type"] = "unknown_runtime"
        try:
            validate_session_manifest(bad_runtime)
            failures.append("FAIL: rejects unsupported runtime_type")
        except ValueError:
            print("PASS: rejects unsupported runtime_type")

        # 4 validates adapter enum.
        bad_adapter = dict(manifest)
        bad_adapter["adapter"] = "unknown_adapter"
        try:
            validate_session_manifest(bad_adapter)
            failures.append("FAIL: rejects unsupported adapter")
        except ValueError:
            print("PASS: rejects unsupported adapter")

        # 5 validates status enum.
        bad_status = dict(manifest)
        bad_status["status"] = "STARTED"
        try:
            validate_session_manifest(bad_status)
            failures.append("FAIL: rejects unsupported status")
        except ValueError:
            print("PASS: rejects unsupported status")

        # 6 validates allowed safety modes.
        bad_modes = dict(manifest)
        bad_modes["allowed_safety_modes"] = ["REVIEW_ONLY", "UNKNOWN_MODE"]
        try:
            validate_session_manifest(bad_modes)
            failures.append("FAIL: rejects unsupported allowed safety mode")
        except ValueError:
            print("PASS: rejects unsupported allowed safety mode")

        # 7 creates default manifest.
        expect("creates default manifest", manifest["status"] == "PLANNED", failures)

        # 8 save/load manifest under temp runtime/sessions/<id>/.
        save_result = save_session_manifest(temp_root, manifest, confirm=True)
        expect("save writes manifest", len(save_result["files_written"]) == 1, failures)
        loaded = get_session_status(temp_root, "session-alpha")
        expect("load reads saved manifest", loaded["session_id"] == "session-alpha", failures)

        # 9 list_sessions reads temp manifests.
        rows = list_sessions(temp_root)
        expect("list_sessions reads temp manifests", len(rows) == 1 and rows[0]["session_id"] == "session-alpha", failures)

        # 10 get_session_status handles missing session.
        try:
            get_session_status(temp_root, "missing-session")
            failures.append("FAIL: get_session_status should reject missing session")
        except FileNotFoundError:
            print("PASS: get_session_status handles missing session")

        # 11 no writes outside runtime/.
        files = [path for path in temp_root.rglob("*") if path.is_file()]
        outside = [path for path in files if runtime_root(temp_root) not in path.resolve().parents]
        expect("no writes outside runtime/", not outside, failures, detail=", ".join(str(p) for p in outside))

        # 12 no process execution.
        source = (SCRIPTS_DIR / "session_registry.py").read_text(encoding="utf-8").lower()
        expect("no process execution", "subprocess" not in source, failures)

        # 13 no model/provider/agent/browser/MCP usage.
        expect(
            "no model/provider/agent/browser/MCP usage",
            all(token not in source for token in ("ollama_call", "subprocess.run(", "requests.", "browsermcp", "openai")),
            failures,
        )

        # dry-run save remains no-write.
        before = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        _ = save_session_manifest(
            temp_root,
            create_default_session_manifest(
                session_id="session-dry",
                runtime_type="wsl",
                adapter="gemini_cli",
                cwd=str(temp_root),
                shell="bash",
            ),
            confirm=False,
        )
        after = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        expect("dry-run save writes no files", before == after, failures)

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

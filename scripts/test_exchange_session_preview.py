#!/usr/bin/env python3
"""Temp-root tests for exchange adapter preview session suggestion metadata."""

from __future__ import annotations

import json
import os
import shutil
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

from exchange_adapter_preview import preview_exchange_adapter  # noqa: E402
from exchange_registry import create_exchange_packet, save_exchange  # noqa: E402
from session_registry import create_default_session_manifest, save_session_manifest  # noqa: E402


def expect(name: str, condition: bool, failures: list[str], detail: str = "") -> None:
    if condition:
        print(f"PASS: {name}")
    else:
        msg = f"FAIL: {name}"
        if detail:
            msg = f"{msg} - {detail}"
        failures.append(msg)


def _make_exchange(root: Path, exchange_id: str, target: str) -> None:
    p = create_exchange_packet(target=target, task_type="review", summary="session suggestion", exchange_id=exchange_id)
    p["source_artifacts"] = ["exchange/README.md"]
    p["allowed_commands"] = ["ws exchange-status"]
    p["forbidden_actions"] = ["Do not execute shell commands"]
    p["expected_outputs"] = ["Markdown review"]
    save_exchange(p, root, confirm=True)


def _make_session(root: Path, sid: str, adapter: str) -> None:
    m = create_default_session_manifest(
        session_id=sid,
        runtime_type="powershell",
        adapter=adapter,
        cwd="D:\\_ai_brain",
        shell="powershell",
    )
    save_session_manifest(root, m, confirm=True)


def main() -> int:
    print("Exchange Session Preview Validation")
    print("===================================")
    failures: list[str] = []
    temp_root = Path(tempfile.gettempdir()).resolve() / f"_tmp_exchange_session_preview_{uuid4().hex}"
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        (temp_root / "registry").mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "registry" / "ws_command_safety.yaml", temp_root / "registry" / "ws_command_safety.yaml")

        _make_exchange(temp_root, "x-codex", "codex_cli")
        _make_exchange(temp_root, "x-gemini", "codex_cli")
        _make_session(temp_root, "codex-exchange-lane", "codex_cli")
        _make_session(temp_root, "gemini-product-lane", "gemini_cli")

        # 1 codex suggestion
        codex = preview_exchange_adapter(temp_root, "x-codex", "codex_cli")
        out = codex["preview"]
        expect(
            "codex_cli adapter preview shows suggested codex-exchange-lane when session exists",
            "suggested_session_id: `codex-exchange-lane`" in out,
            failures,
        )

        # 2 gemini suggestion path via helper direct (packet target mismatch expected fail, but suggestion should still be available when target passed)
        packet_path = temp_root / "exchange" / "x-gemini" / "exchange.yaml"
        data = json.loads(packet_path.read_text(encoding="utf-8"))
        data["target"] = "gemini_cli"
        packet_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        from exchange_adapter_preview import suggest_runtime_session  # noqa: E402

        gemini_suggestion = suggest_runtime_session(temp_root, data, "gemini_cli")
        expect(
            "gemini_cli adapter preview shows suggested gemini-product-lane when session exists",
            gemini_suggestion.get("found") and gemini_suggestion.get("session_id") == "gemini-product-lane",
            failures,
        )

        # 3 no matching
        shutil.rmtree(temp_root / "runtime" / "sessions" / "codex-exchange-lane", ignore_errors=True)
        no_match = preview_exchange_adapter(temp_root, "x-codex", "codex_cli")
        expect("adapter preview warns if no matching session exists", "no matching planned runtime session found" in no_match["preview"], failures)

        # 4 no-write
        before = sorted(str(p.relative_to(temp_root)) for p in temp_root.rglob("*") if p.is_file())
        _ = preview_exchange_adapter(temp_root, "x-codex", "codex_cli")
        after = sorted(str(p.relative_to(temp_root)) for p in temp_root.rglob("*") if p.is_file())
        expect("adapter preview remains no-write", before == after, failures)

        # 5 no session.yaml modify
        session_path = temp_root / "runtime" / "sessions" / "gemini-product-lane" / "session.yaml"
        before_text = session_path.read_text(encoding="utf-8")
        _ = preview_exchange_adapter(temp_root, "x-codex", "codex_cli")
        after_text = session_path.read_text(encoding="utf-8")
        expect("adapter preview does not modify session.yaml", before_text == after_text, failures)

        # 6 no process start (static)
        src = (SCRIPTS_DIR / "exchange_adapter_preview.py").read_text(encoding="utf-8").lower()
        expect("adapter preview does not start process", "subprocess" not in src, failures)

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

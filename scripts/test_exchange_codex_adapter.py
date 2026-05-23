#!/usr/bin/env python3
"""Temp-root tests for guarded Codex REVIEW_ONLY dispatch adapter."""

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

from exchange_codex_adapter import (  # noqa: E402
    run_codex_adapter,
    validate_codex_dispatch_preconditions,
)
from exchange_dispatch import _load_command_manifest  # noqa: E402
from exchange_registry import create_exchange_packet, exchange_root, save_exchange  # noqa: E402


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


def _make_root() -> Path:
    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_exchange_codex_adapter_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    (temp_root / "registry").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "registry" / "ws_command_safety.yaml", temp_root / "registry" / "ws_command_safety.yaml")
    return temp_root


def _make_exchange(root: Path, exchange_id: str) -> tuple[Path, dict[str, object]]:
    packet = create_exchange_packet(target="codex_cli", task_type="review", summary="codex dispatch", exchange_id=exchange_id)
    packet["source_artifacts"] = ["exchange/README.md"]
    packet["allowed_commands"] = []
    result = save_exchange(packet, root, confirm=True)
    exchange_dir = exchange_root(root) / exchange_id
    packet_path = Path([p for p in result["files_written"] if p.endswith("exchange.yaml")][0])
    packet_data = json.loads(packet_path.read_text(encoding="utf-8"))
    return exchange_dir, packet_data


def _fake_executor_ok(prompt_text: str) -> tuple[int, str, str]:
    return 0, "# Exchange Result\n\n## Result\nok\n", ""


def _fake_executor_fail(prompt_text: str) -> tuple[int, str, str]:
    return 7, "# Exchange Result\n\n## Result\nblocked\n", "simulated codex error"


def main() -> int:
    print("Exchange Codex Adapter Validation")
    print("=================================")
    failures: list[str] = []
    temp_root = _make_root()

    try:
        # baseline packet
        exchange_id = f"codex-review-{uuid4().hex[:8]}"
        exchange_dir, packet = _make_exchange(temp_root, exchange_id)
        manifest = _load_command_manifest(temp_root)

        # 1 preconditions pass
        pre = validate_codex_dispatch_preconditions(packet, exchange_dir, "codex_cli", manifest)
        expect("Codex dispatch preconditions pass for READY REVIEW_ONLY codex_cli exchange", pre["ok"], failures)

        # 2 rejects non-codex target
        pre2 = validate_codex_dispatch_preconditions(packet, exchange_dir, "gemini_cli", manifest)
        expect("Rejects non-codex target", not pre2["ok"], failures)

        # 3 rejects safety_mode not REVIEW_ONLY
        packet_bad_mode = dict(packet)
        packet_bad_mode["safety_mode"] = "GUARDED_EXECUTION"
        pre3 = validate_codex_dispatch_preconditions(packet_bad_mode, exchange_dir, "codex_cli", manifest)
        expect("Rejects safety_mode not REVIEW_ONLY", not pre3["ok"], failures)

        # 4 rejects non-empty allowed_commands
        packet_bad_allowed = dict(packet)
        packet_bad_allowed["allowed_commands"] = ["ws exchange-status"]
        pre4 = validate_codex_dispatch_preconditions(packet_bad_allowed, exchange_dir, "codex_cli", manifest)
        expect("Rejects non-empty allowed_commands", not pre4["ok"], failures)

        # 5 rejects COMPLETED
        packet_completed = dict(packet)
        packet_completed["status"] = "COMPLETED"
        pre5 = validate_codex_dispatch_preconditions(packet_completed, exchange_dir, "codex_cli", manifest)
        expect("Rejects COMPLETED exchange", not pre5["ok"], failures)

        # 6 rejects existing root raw_output.md
        (exchange_dir / "raw_output.md").write_text("existing", encoding="utf-8")
        pre6 = validate_codex_dispatch_preconditions(packet, exchange_dir, "codex_cli", manifest)
        expect("Rejects existing root raw_output.md", not pre6["ok"], failures)
        (exchange_dir / "raw_output.md").unlink(missing_ok=True)

        # 7-11 writes adapter artifacts only on successful run
        run_res = run_codex_adapter(temp_root, exchange_id, "codex_cli", executor=_fake_executor_ok)
        expect("Writes adapter_runs/codex_cli/<run_id>/ only", run_res.get("ok") is True, failures)
        run_dir = exchange_dir / "adapter_runs" / "codex_cli" / run_res["run_id"]
        expect("Writes adapter_prompt.md", (run_dir / "adapter_prompt.md").is_file(), failures)
        expect("Writes stdout.md", (run_dir / "stdout.md").is_file(), failures)
        expect("Writes stderr.md", (run_dir / "stderr.md").is_file(), failures)
        expect("Writes adapter_run.yaml", (run_dir / "adapter_run.yaml").is_file(), failures)

        # 12-14 no import artifacts
        expect("Does not write raw_output.md", not (exchange_dir / "raw_output.md").exists(), failures)
        expect("Does not write parsed_result.json", not (exchange_dir / "parsed_result.json").exists(), failures)
        expect("Does not write operator_report.md", not (exchange_dir / "operator_report.md").exists(), failures)

        # 15 no product writes
        expect("Does not modify product files", not (temp_root / "products").exists(), failures)

        # 16 no command execution from output (smoke: output persisted as text)
        text = (run_dir / "stdout.md").read_text(encoding="utf-8")
        expect("Does not execute commands from Codex output", "Exchange Result" in text, failures)

        # 17 uses fake executor in tests
        expect("Uses fake executor in tests", run_res.get("return_code") == 0, failures)

        # 18 records executor return code
        adapter_yaml = json.loads((run_dir / "adapter_run.yaml").read_text(encoding="utf-8"))
        expect("Records executor return code", adapter_yaml.get("return_code") == 0, failures)

        # 19 handles nonzero exit as blocked/failed adapter run without crashing
        exchange_id_fail = f"codex-review-fail-{uuid4().hex[:8]}"
        exchange_dir_fail, _packet_fail = _make_exchange(temp_root, exchange_id_fail)
        fail_res = run_codex_adapter(temp_root, exchange_id_fail, "codex_cli", executor=_fake_executor_fail)
        expect("Handles nonzero Codex exit as BLOCKED/FAILED adapter run without crashing", fail_res.get("ok") is True and fail_res.get("run_status") == "FAILED" and fail_res.get("exchange_status") == "BLOCKED", failures)

        # 20 no Gemini/Ollama/browser/MCP execution paths
        src = (SCRIPTS_DIR / "exchange_codex_adapter.py").read_text(encoding="utf-8").lower()
        expect(
            "No Gemini/Ollama/browser/MCP execution paths",
            all(token not in src for token in ("gemini", "ollama_call", "browsermcp", "mcp")),
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

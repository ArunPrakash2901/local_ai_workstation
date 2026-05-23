#!/usr/bin/env python3
"""Temp-root tests for Exchange adapter preview dry-run gate."""

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

from exchange_adapter_preview import preview_exchange_adapter  # noqa: E402
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


def _run_cli(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ws_exchange_adapter_preview.py"), *args, "--root", str(root)],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def _write_packet(root: Path, packet: dict[str, object]) -> Path:
    result = save_exchange(packet, root, confirm=True)
    files = result["files_written"]
    exchange_yaml = [Path(p) for p in files if p.endswith("exchange.yaml")][0]
    return exchange_yaml


def main() -> int:
    print("Exchange Adapter Preview Validation")
    print("===================================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_exchange_adapter_preview_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    (temp_root / "registry").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "registry" / "ws_command_safety.yaml", temp_root / "registry" / "ws_command_safety.yaml")

    try:
        # Valid exchange for codex preview.
        packet = create_exchange_packet(target="codex_cli", task_type="review", summary="adapter preview")
        packet["source_artifacts"] = ["exchange/README.md"]
        packet["allowed_commands"] = ["ws exchange-status"]
        yaml_path = _write_packet(temp_root, packet)
        exchange_id = packet["exchange_id"]
        exchange_dir = exchange_root(temp_root) / exchange_id

        # 1 preview succeeds for codex_cli exchange.
        ok = _run_cli(["--exchange", exchange_id, "--target", "codex_cli", "--dry-run"], temp_root)
        expect("preview succeeds for codex_cli exchange", ok.returncode == 0, failures, detail=ok.stderr or "")

        # 2 preview rejects missing exchange.
        missing = _run_cli(["--exchange", "missing-id", "--target", "codex_cli", "--dry-run"], temp_root)
        expect("preview rejects missing exchange", missing.returncode != 0, failures)

        # 3 preview rejects unsupported target.
        bad_target = _run_cli(["--exchange", exchange_id, "--target", "gemini_cli", "--dry-run"], temp_root)
        expect("preview rejects unsupported target", bad_target.returncode != 0, failures)

        # 4 preview requires --dry-run.
        no_mode = _run_cli(["--exchange", exchange_id, "--target", "codex_cli"], temp_root)
        expect(
            "preview requires --dry-run",
            no_mode.returncode != 0 and "Use --dry-run" in (no_mode.stdout or ""),
            failures,
        )

        # 5 preview warns if exchange already COMPLETED.
        data = json.loads(yaml_path.read_text(encoding="utf-8"))
        data["status"] = "COMPLETED"
        yaml_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        completed = preview_exchange_adapter(temp_root, exchange_id, "codex_cli")
        warnings = completed["validation_result"]["warnings"]
        expect(
            "preview warns if exchange already COMPLETED",
            any("COMPLETED" in item for item in warnings),
            failures,
        )

        # restore ready for subsequent checks
        data["status"] = "READY"
        yaml_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        # 6 preview validates allowed_commands are manifest-known.
        data = json.loads(yaml_path.read_text(encoding="utf-8"))
        data["allowed_commands"] = ["ws definitely-not-real"]
        yaml_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        unknown = preview_exchange_adapter(temp_root, exchange_id, "codex_cli")
        expect(
            "preview validates allowed_commands are manifest-known",
            unknown["validation_result"]["preview_status"] == "FAIL",
            failures,
        )

        # restore known command for remaining checks
        data["allowed_commands"] = ["ws exchange-status"]
        yaml_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        # snapshot for write checks
        before = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        out = _run_cli(["--exchange", exchange_id, "--target", "codex_cli", "--dry-run"], temp_root)
        after = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())

        # 7 preview writes no files.
        expect("preview writes no files", before == after, failures)

        # 8 preview does not create raw_output.md.
        expect("preview does not create raw_output.md", not (exchange_dir / "raw_output.md").exists(), failures)

        # 9 preview does not modify exchange.yaml.
        final_data = json.loads(yaml_path.read_text(encoding="utf-8"))
        expect("preview does not modify exchange.yaml", final_data.get("status") == "READY", failures)

        # 10 preview does not run Codex/Gemini/Ollama/browser/MCP.
        src = (SCRIPTS_DIR / "exchange_adapter_preview.py").read_text(encoding="utf-8").lower()
        expect(
            "preview does not run Codex/Gemini/Ollama/browser/MCP",
            all(token not in src for token in ("subprocess", "requests.", "ollama_call", "browsermcp", "openai")),
            failures,
        )

        # 11 preview includes prompt path.
        expect("preview includes prompt path", "prompt_path:" in (out.stdout or ""), failures)

        # 12 preview includes future output capture path.
        expect("preview includes future output capture path", "planned_output_capture_path:" in (out.stdout or ""), failures)

        # 13 preview includes no-execution notice.
        expect("preview includes no-execution notice", "Codex CLI was not executed." in (out.stdout or ""), failures)

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

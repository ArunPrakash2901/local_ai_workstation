#!/usr/bin/env python3
"""Temp-root tests for Exchange Lane Phase 0 registry helpers."""

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

from exchange_registry import (  # noqa: E402
    create_exchange_packet,
    exchange_root,
    get_exchange_status,
    list_exchanges,
    render_exchange_preview,
    save_exchange,
    validate_exchange_id,
    validate_exchange_packet,
)


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


def _run_new_cli(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ws_exchange_new.py"), *args, "--root", str(root)],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    print("Exchange Registry Validation")
    print("============================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_exchange_registry_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        # 1 validates exchange_id.
        expect("validates exchange_id", validate_exchange_id("exchange-alpha-1"), failures)

        # 2 rejects path traversal.
        expect("rejects path traversal", not validate_exchange_id("../escape"), failures)

        # 3 validates allowed targets.
        packet = create_exchange_packet(target="codex_cli", task_type="review", summary="review packet")
        expect("validates allowed targets", packet["target"] == "codex_cli", failures)
        try:
            validate_exchange_packet({**packet, "target": "unknown_target"})
            failures.append("FAIL: rejects unsupported targets")
        except ValueError:
            print("PASS: rejects unsupported targets")

        # 4 validates allowed safety modes.
        try:
            validate_exchange_packet({**packet, "safety_mode": "UNSAFE_MODE"})
            failures.append("FAIL: rejects unsupported safety modes")
        except ValueError:
            print("PASS: rejects unsupported safety modes")

        # 5 validates required packet fields.
        broken = dict(packet)
        broken.pop("task_summary", None)
        try:
            validate_exchange_packet(broken)
            failures.append("FAIL: missing required packet field rejected")
        except ValueError:
            print("PASS: missing required packet field rejected")

        # 6 create packet defaults status.
        expect("create packet defaults status to READY", packet["status"] == "READY", failures)

        # 7 dry-run preview writes no files.
        preview = render_exchange_preview(packet)
        expect("dry-run preview includes no files written", "DRY RUN - no files written." in preview, failures)
        expect("dry-run preview writes no files", not exchange_root(temp_root).exists(), failures)

        # 8/9 confirm writes required packet files.
        result = save_exchange(packet, temp_root, confirm=True)
        packet_dir = exchange_root(temp_root) / packet["exchange_id"]
        expect("confirm writes exchange.yaml", (packet_dir / "exchange.yaml").is_file(), failures)
        expect(
            "confirm writes required markdown files",
            all(
                (packet_dir / name).is_file()
                for name in (
                    "prompt.md",
                    "source_artifacts.md",
                    "allowed_commands.md",
                    "forbidden_actions.md",
                    "expected_outputs.md",
                    "run_log.md",
                )
            ),
            failures,
        )

        # 10 confirm refuses duplicate exchange_id.
        try:
            save_exchange(packet, temp_root, confirm=True)
            failures.append("FAIL: duplicate exchange_id should be rejected")
        except FileExistsError:
            print("PASS: duplicate exchange_id rejected")

        # 11 list_exchanges reads temp records.
        rows = list_exchanges(temp_root)
        expect("list_exchanges reads temp exchange records", len(rows) == 1 and rows[0]["exchange_id"] == packet["exchange_id"], failures)

        # 12 status reads temp record.
        status = get_exchange_status(temp_root, packet["exchange_id"])
        expect("status reads temp exchange record", status["exchange_id"] == packet["exchange_id"], failures)

        # 13 no writes outside exchange/<exchange_id>/.
        files = [path for path in temp_root.rglob("*") if path.is_file()]
        outside = [path for path in files if exchange_root(temp_root) not in path.resolve().parents]
        expect("no writes outside exchange/<exchange_id>/", not outside, failures, detail=", ".join(str(p) for p in outside))

        # 14 no model/provider/agent usage.
        for script_name in ("exchange_registry.py", "ws_exchange_new.py", "ws_exchange_list.py", "ws_exchange_status.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            expect(
                f"{script_name}: no model/provider/agent usage",
                all(
                    token not in source
                    for token in (
                        "subprocess",
                        "requests.",
                        "ollama_call",
                        "codex exec",
                        "gemini api",
                        "browsermcp",
                    )
                ),
                failures,
            )

        # Sanity: CLI dry-run no write.
        fresh_packet_id = f"packet-{uuid4().hex[:8]}"
        before = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        cli_dry = _run_new_cli(
            [
                "--target",
                "codex_cli",
                "--task-type",
                "review",
                "--summary",
                "cli dry run",
                "--exchange-id",
                fresh_packet_id,
                "--dry-run",
            ],
            temp_root,
        )
        after = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        expect("CLI dry-run exits 0", cli_dry.returncode == 0, failures, detail=cli_dry.stderr or "")
        expect("CLI dry-run writes no files", before == after, failures)
        expect("CLI dry-run preview contains title", "Exchange Packet Preview" in (cli_dry.stdout or ""), failures)

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

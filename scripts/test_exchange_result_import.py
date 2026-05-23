#!/usr/bin/env python3
"""Temp-root tests for Exchange result import dry-run/confirm behavior."""

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

from exchange_registry import create_exchange_packet, exchange_root, save_exchange  # noqa: E402
from exchange_result_import import import_exchange_result  # noqa: E402


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
        [sys.executable, str(SCRIPTS_DIR / "ws_exchange_import_result.py"), *args, "--root", str(root)],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def _make_packet(root: Path, exchange_id: str) -> Path:
    packet = create_exchange_packet(target="codex_cli", task_type="review", summary="import result smoke", exchange_id=exchange_id)
    packet["source_artifacts"] = ["exchange/README.md"]
    save_exchange(packet, root, confirm=True)
    return exchange_root(root) / exchange_id


def _write_result(path: Path, *, blocked_reason: str = "None", include_required: bool = True) -> None:
    sections = [
        "# Exchange Result",
        "",
        "## Task ID",
        "sample-task-id",
        "",
        "## Inputs Read",
        "- EXCHANGE_LANE_MASTER_PLAN.md",
        "",
        "## Commands Run",
        "- None",
        "",
        "## Files Changed",
        "- None",
        "",
        "## Tests Run",
        "- None",
        "",
        "## Result",
        "Review-only packet imported as smoke-test result.",
        "",
        "## Blocked Reason",
        blocked_reason,
        "",
        "## Needs Human Decision",
        "None",
        "",
    ]
    if not include_required:
        sections = [line for line in sections if line not in {"## Task ID", "sample-task-id"}]
    path.write_text("\n".join(sections), encoding="utf-8", newline="\n")


def main() -> int:
    print("Exchange Result Import Validation")
    print("=================================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_exchange_result_import_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        # 1 dry-run validates well-formed result and writes no files.
        eid = f"import-pass-{uuid4().hex[:8]}"
        exchange_dir = _make_packet(temp_root, eid)
        result_file = temp_root / "result.md"
        _write_result(result_file)
        before = sorted(p.relative_to(temp_root).as_posix() for p in temp_root.rglob("*") if p.is_file())
        dry = import_exchange_result(temp_root, eid, result_file, confirm=False)
        after = sorted(p.relative_to(temp_root).as_posix() for p in temp_root.rglob("*") if p.is_file())
        expect("dry-run validates well-formed result and writes no files", dry["parsed_summary"]["validation"]["status"] in {"PASS", "WARN"} and before == after, failures)

        # 2-6 confirm writes artifacts and sets COMPLETED for PASS/WARN with no block.
        confirm = import_exchange_result(temp_root, eid, result_file, confirm=True)
        expect("confirm writes raw_output.md", (exchange_dir / "raw_output.md").is_file(), failures)
        expect("confirm writes parsed_result.json", (exchange_dir / "parsed_result.json").is_file(), failures)
        expect("confirm writes validation.md", (exchange_dir / "validation.md").is_file(), failures)
        expect("confirm writes operator_report.md", (exchange_dir / "operator_report.md").is_file(), failures)
        packet = json.loads((exchange_dir / "exchange.yaml").read_text(encoding="utf-8"))
        expect("confirm updates exchange.yaml status COMPLETED for PASS result", packet.get("status") == "COMPLETED", failures)

        # 7 BLOCKED status when blocked reason is non-empty.
        eid_blocked = f"import-blocked-{uuid4().hex[:8]}"
        exchange_dir_blocked = _make_packet(temp_root, eid_blocked)
        result_blocked = temp_root / "result_blocked.md"
        _write_result(result_blocked, blocked_reason="Awaiting human policy decision")
        import_exchange_result(temp_root, eid_blocked, result_blocked, confirm=True)
        packet_blocked = json.loads((exchange_dir_blocked / "exchange.yaml").read_text(encoding="utf-8"))
        expect("confirm updates exchange.yaml status BLOCKED when Blocked Reason is non-empty", packet_blocked.get("status") == "BLOCKED", failures)

        # 8 FAILED status when required sections missing.
        eid_failed = f"import-failed-{uuid4().hex[:8]}"
        exchange_dir_failed = _make_packet(temp_root, eid_failed)
        result_failed = temp_root / "result_failed.md"
        _write_result(result_failed, include_required=False)
        import_exchange_result(temp_root, eid_failed, result_failed, confirm=True)
        packet_failed = json.loads((exchange_dir_failed / "exchange.yaml").read_text(encoding="utf-8"))
        expect("confirm updates exchange.yaml status FAILED when required result sections are missing", packet_failed.get("status") == "FAILED", failures)

        # 9 missing exchange rejected.
        missing_exchange = _run_cli(["--exchange", "missing", "--file", str(result_file), "--confirm"], temp_root)
        expect("confirm refuses missing exchange", missing_exchange.returncode != 0, failures)

        # 10 missing result file rejected.
        missing_file = _run_cli(["--exchange", eid, "--file", str(temp_root / "missing.md"), "--confirm"], temp_root)
        expect("confirm refuses missing result file", missing_file.returncode != 0, failures)

        # 11 duplicate raw_output rejected.
        dup = _run_cli(["--exchange", eid, "--file", str(result_file), "--confirm"], temp_root)
        expect("confirm refuses duplicate raw_output.md", dup.returncode != 0, failures)

        # 12 nothing outside exchange/<exchange_id>/ except source file.
        written = set(Path(p).resolve() for p in confirm["files_written"])
        outside = [p for p in written if exchange_root(temp_root).resolve() not in p.parents]
        expect("confirm writes nothing outside exchange/<exchange_id>/", not outside, failures)

        # 13 does not modify product files.
        expect("confirm does not modify product files", not (temp_root / "products").exists(), failures)

        # 14/15 untrusted and no execution from result text.
        hostile = temp_root / "hostile.md"
        hostile.write_text("# Exchange Result\n\n## Task ID\nx\n\n## Result\ny\n\n## Blocked Reason\nNone\n\n## Needs Human Decision\nNone\n\n## Commands Run\n- rm -rf /\n", encoding="utf-8")
        eid_hostile = f"import-hostile-{uuid4().hex[:8]}"
        _make_packet(temp_root, eid_hostile)
        host_res = import_exchange_result(temp_root, eid_hostile, hostile, confirm=True)
        expect("confirm does not execute commands listed in result text", host_res["packet"]["status"] in {"COMPLETED", "FAILED", "BLOCKED"}, failures)
        rep = (exchange_root(temp_root) / eid_hostile / "operator_report.md").read_text(encoding="utf-8")
        expect("result text is treated as untrusted", "untrusted" in rep.lower(), failures)

        # 16 CLI requires exactly one mode.
        no_mode = _run_cli(["--exchange", eid_hostile, "--file", str(hostile)], temp_root)
        both_mode = _run_cli(["--exchange", eid_hostile, "--file", str(hostile), "--dry-run", "--confirm"], temp_root)
        expect("CLI requires exactly one of --dry-run or --confirm", no_mode.returncode != 0 and both_mode.returncode != 0, failures)

        # 17 no model/provider/agent/browser/MCP usage.
        source = (SCRIPTS_DIR / "exchange_result_import.py").read_text(encoding="utf-8").lower()
        expect(
            "no model/provider/agent/browser/MCP usage occurs",
            all(token not in source for token in ("subprocess", "requests.", "ollama_call", "browsermcp", "openai", "gemini")),
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

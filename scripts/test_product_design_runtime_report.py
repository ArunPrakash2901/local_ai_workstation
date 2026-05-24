#!/usr/bin/env python3
"""Temp-root tests for Product Lane Open Design runtime report (dry-run only)."""

from __future__ import annotations

import contextlib
import io
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

from product_design_runtime_probe import probe_design_runtime, render_design_runtime_report  # noqa: E402
from ws_product_design_runtime_report import main as runtime_report_cli_main  # noqa: E402


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


def _files_snapshot(root: Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())


def main() -> int:
    print("Product Design Runtime Report Validation")
    print("=======================================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_design_runtime_report_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        called_names: list[str] = []

        def _which_partial(name: str, path: str | None = None) -> str | None:
            _ = path
            called_names.append(name)
            return {
                "npm": "C:/fake/npm.cmd",
                "node": "C:/fake/node.exe",
            }.get(name)

        probe = probe_design_runtime(
            temp_root,
            "open-design",
            env={"OPENAI_API_KEY": "VERY_SECRET_VALUE"},
            which_fn=_which_partial,
        )
        rendered = render_design_runtime_report(probe)

        expect("accepts open-design", probe["tool"] == "open-design", failures)
        expect("output includes /design runtime", "/design runtime" in rendered, failures)
        expect(
            "output includes readiness classification",
            probe["readiness_classification"] in rendered and "readiness classification" in rendered.lower(),
            failures,
        )
        expect(
            "output includes node/npm/pnpm/open-design visibility",
            all(token in rendered for token in ("open-design", "node", "npm", "pnpm")),
            failures,
        )
        expect(
            "env reporting prints names/presence only, not values",
            "OPENAI_API_KEY" in rendered and "VERY_SECRET_VALUE" not in rendered,
            failures,
        )
        expect("does not execute Open Design", probe["execution_attempted"] is False, failures)
        expect(
            "does not run package managers",
            sorted(set(called_names)) == ["node", "npm", "od", "open-design", "pnpm"],
            failures,
            detail=str(called_names),
        )

        try:
            _ = probe_design_runtime(temp_root, "unknown", which_fn=_which_partial)
            failures.append("FAIL: rejects unknown tool - expected exception")
        except ValueError:
            expect("rejects unknown tool", True, failures)

        try:
            _ = probe_design_runtime(temp_root, "../open-design", which_fn=_which_partial)
            failures.append("FAIL: rejects path traversal tool - expected exception")
        except ValueError:
            expect("rejects path traversal tool", True, failures)

        with contextlib.redirect_stdout(io.StringIO()) as stdout_capture, contextlib.redirect_stderr(io.StringIO()) as stderr_capture:
            rc = runtime_report_cli_main(
                [
                    "--root",
                    str(temp_root),
                    "--tool",
                    "open-design",
                ]
            )
        expect(
            "requires --dry-run",
            rc == 2 and "--dry-run is required" in (stderr_capture.getvalue() or stdout_capture.getvalue()),
            failures,
        )

        before_files = _files_snapshot(temp_root)
        with contextlib.redirect_stdout(io.StringIO()):
            rc = runtime_report_cli_main(
                [
                    "--root",
                    str(temp_root),
                    "--tool",
                    "open-design",
                    "--dry-run",
                ]
            )
        after_files = _files_snapshot(temp_root)
        expect("writes no files", rc == 0 and before_files == after_files, failures)

        source_report = (SCRIPTS_DIR / "ws_product_design_runtime_report.py").read_text(encoding="utf-8").lower()
        source_probe = (SCRIPTS_DIR / "product_design_runtime_probe.py").read_text(encoding="utf-8").lower()
        disallowed_exec_tokens = ("subprocess", "os.system(", "popen(", "pip install", "npm install", "pnpm install", "npx ")
        expect(
            "does not run package managers",
            all(token not in source_report for token in disallowed_exec_tokens)
            and all(token not in source_probe for token in ("subprocess", "os.system(", "popen(")),
            failures,
        )
        expect("does not print secret values", "VERY_SECRET_VALUE" not in rendered, failures)

        shortcuts = json.loads((ROOT / "slash_commands" / "operator_shortcuts.json").read_text(encoding="utf-8"))
        design_entry = next(
            (item for item in shortcuts.get("commands", []) if item.get("command") == "/design"),
            {},
        )
        subactions = design_entry.get("subactions", {}) if isinstance(design_entry, dict) else {}
        expect(
            "includes /design runtime mapping",
            isinstance(subactions, dict)
            and subactions.get("runtime")
            == "ws product-design-runtime-report --tool open-design --dry-run",
            failures,
            detail=str(subactions),
        )

    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    print("")
    if failures:
        print("Result: FAIL")
        for failure in failures:
            print(failure)
        return 1
    print("Result: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

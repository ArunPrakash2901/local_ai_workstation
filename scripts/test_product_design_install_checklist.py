#!/usr/bin/env python3
"""Temp-root tests for Product Lane Open Design install checklist preview."""

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

from product_design_install_checklist import (  # noqa: E402
    INSTALL_CHECKLIST_DOC,
    build_install_checklist_preview,
    render_install_checklist_preview,
)
from ws_product_design_install_checklist import main as checklist_cli_main  # noqa: E402


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
    print("Product Design Install Checklist Validation")
    print("==========================================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_design_install_checklist_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        checklist_path = temp_root / INSTALL_CHECKLIST_DOC
        checklist_path.write_text("# checklist\n", encoding="utf-8")

        called_names: list[str] = []

        def _which_none(name: str, path: str | None = None) -> None:
            _ = path
            called_names.append(name)
            return None

        preview = build_install_checklist_preview(
            temp_root,
            "open-design",
            env={"OPENAI_API_KEY": "VERY_SECRET_VALUE"},
            which_fn=_which_none,
        )
        rendered = render_install_checklist_preview(preview)

        expect("accepts open-design", preview["tool"] == "open-design", failures)
        expect("output includes /design install-check", "/design install-check" in rendered, failures)
        expect("output includes checklist path", INSTALL_CHECKLIST_DOC in rendered, failures)
        expect("output includes manual-only warning", "Manual-only installation warning".lower() in rendered.lower(), failures)
        expect("output includes stop conditions", "Stop Conditions" in rendered, failures)
        expect("does not print secret values", "VERY_SECRET_VALUE" not in rendered, failures)
        expect(
            "does not execute Open Design",
            preview["open_design_executed"] is False and preview["runtime_probe"]["execution_attempted"] is False,
            failures,
        )
        expect(
            "does not run package managers",
            preview["package_manager_executed"] is False and sorted(set(called_names)) == ["node", "npm", "od", "open-design", "pnpm"],
            failures,
            detail=str(called_names),
        )

        try:
            _ = build_install_checklist_preview(temp_root, "unknown", which_fn=_which_none)
            failures.append("FAIL: rejects unknown tool - expected exception")
        except ValueError:
            expect("rejects unknown tool", True, failures)

        try:
            _ = build_install_checklist_preview(temp_root, "../open-design", which_fn=_which_none)
            failures.append("FAIL: rejects path traversal tool - expected exception")
        except ValueError:
            expect("rejects path traversal tool", True, failures)

        with contextlib.redirect_stdout(io.StringIO()) as stdout_capture, contextlib.redirect_stderr(io.StringIO()) as stderr_capture:
            rc = checklist_cli_main(
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
            rc = checklist_cli_main(
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

        source_install = (SCRIPTS_DIR / "product_design_install_checklist.py").read_text(encoding="utf-8").lower()
        source_cli = (SCRIPTS_DIR / "ws_product_design_install_checklist.py").read_text(encoding="utf-8").lower()
        source_probe = (SCRIPTS_DIR / "product_design_runtime_probe.py").read_text(encoding="utf-8").lower()
        disallowed_exec_tokens = ("subprocess", "os.system(", "popen(", "pip install", "npm install", "pnpm install", "npx ")
        expect(
            "does not run package managers",
            all(token not in source_install for token in disallowed_exec_tokens)
            and all(token not in source_cli for token in disallowed_exec_tokens)
            and all(token not in source_probe for token in ("subprocess", "os.system(", "popen(")),
            failures,
        )

        shortcuts = json.loads((ROOT / "slash_commands" / "operator_shortcuts.json").read_text(encoding="utf-8"))
        design_entry = next(
            (item for item in shortcuts.get("commands", []) if item.get("command") == "/design"),
            {},
        )
        subactions = design_entry.get("subactions", {}) if isinstance(design_entry, dict) else {}
        expect(
            "includes /design install-check mapping",
            isinstance(subactions, dict)
            and subactions.get("install-check")
            == "ws product-design-install-checklist --tool open-design --dry-run",
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

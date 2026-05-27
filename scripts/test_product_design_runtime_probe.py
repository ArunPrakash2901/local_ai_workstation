#!/usr/bin/env python3
"""Temp-root tests for Product Lane Open Design runtime probe (dry-run only)."""

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

from product_design_runtime_probe import (  # noqa: E402
    PARTIAL_RUNTIME_FOUND,
    RUNTIME_CANDIDATE_FOUND,
    RUNTIME_NOT_FOUND,
    RENDER_CONTRACT_FOUND,
    RENDER_READY,
    PROBE_COMMAND_NAMES,
    classify_runtime_readiness,
    probe_design_runtime,
    render_design_runtime_probe,
)
from ws_product_design_runtime_probe import main as probe_cli_main  # noqa: E402


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


def _create_source_checkout(root: Path, *, include_daemon_cli: bool) -> Path:
    checkout = root / "open_design_source"
    checkout.mkdir(parents=True, exist_ok=True)
    (checkout / "package.json").write_text("{}\n", encoding="utf-8")
    (checkout / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
    (checkout / "node_modules").mkdir(parents=True, exist_ok=True)
    if include_daemon_cli:
        daemon_cli = checkout / "apps" / "daemon" / "dist" / "cli.js"
        daemon_cli.parent.mkdir(parents=True, exist_ok=True)
        daemon_cli.write_text("console.log('cli');\n", encoding="utf-8")
    return checkout


def main() -> int:
    print("Product Design Runtime Probe Validation")
    print("======================================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_design_runtime_probe_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        called_names: list[str] = []

        def _which_none(name: str, path: str | None = None) -> None:
            _ = path
            called_names.append(name)
            return None

        probe = probe_design_runtime(temp_root, "open-design", which_fn=_which_none)
        expect("accepts tool open-design", probe["tool"] == "open-design", failures)
        expect(
            "handles no commands found",
            probe["readiness_classification"] == RUNTIME_NOT_FOUND,
            failures,
            detail=str(probe["readiness_classification"]),
        )

        try:
            _ = probe_design_runtime(temp_root, "unknown", which_fn=_which_none)
            failures.append("FAIL: rejects unknown tool - expected exception")
        except ValueError:
            expect("rejects unknown tool", True, failures)

        try:
            _ = probe_design_runtime(temp_root, "../open-design", which_fn=_which_none)
            failures.append("FAIL: rejects path traversal tool - expected exception")
        except ValueError:
            expect("rejects path traversal tool", True, failures)

        with contextlib.redirect_stdout(io.StringIO()) as stdout_capture, contextlib.redirect_stderr(io.StringIO()) as stderr_capture:
            rc = probe_cli_main(
                [
                    "--root",
                    str(temp_root),
                    "--tool",
                    "open-design",
                ]
            )
        expect(
            "CLI requires --dry-run",
            rc == 2
            and "--dry-run is required" in (stderr_capture.getvalue() or stdout_capture.getvalue()),
            failures,
        )

        before_files = _files_snapshot(temp_root)
        with contextlib.redirect_stdout(io.StringIO()):
            rc = probe_cli_main(
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

        expect(
            "does not execute discovered command paths",
            sorted(set(called_names)) == sorted(PROBE_COMMAND_NAMES),
            failures,
            detail=str(called_names),
        )

        partial_probe = probe_design_runtime(
            temp_root,
            "open-design",
            which_fn=lambda name, path=None: "C:/fake/node.exe" if name == "node" else None,
        )
        expect(
            "handles partial commands found",
            partial_probe["readiness_classification"] == PARTIAL_RUNTIME_FOUND,
            failures,
            detail=str(partial_probe["readiness_classification"]),
        )

        source_candidate = _create_source_checkout(temp_root, include_daemon_cli=False)
        candidate_probe = probe_design_runtime(
            temp_root,
            "open-design",
            env={"OPEN_DESIGN_HOME": source_candidate.as_posix()},
            which_fn=lambda name, path=None: (
                {
                    "open-design": "C:/fake/open-design",
                    "node": "C:/fake/node.exe",
                    "pnpm": "C:/fake/pnpm.cmd",
                }.get(name)
            ),
        )
        expect(
            "renders readiness classification",
            candidate_probe["readiness_classification"] == RUNTIME_CANDIDATE_FOUND
            and RUNTIME_CANDIDATE_FOUND in render_design_runtime_probe(candidate_probe),
            failures,
        )

        source_contract = _create_source_checkout(temp_root, include_daemon_cli=True)
        contract_probe = probe_design_runtime(
            temp_root,
            "open-design",
            env={"OPEN_DESIGN_HOME": source_contract.as_posix()},
            which_fn=lambda name, path=None: (
                {
                    "node": "C:/fake/node.exe",
                    "pnpm": "C:/fake/pnpm.cmd",
                }.get(name)
            ),
        )
        expect(
            "detects render contract found when daemon CLI exists",
            contract_probe["readiness_classification"] == RENDER_CONTRACT_FOUND,
            failures,
            detail=str(contract_probe["readiness_classification"]),
        )
        expect(
            "does not classify render ready when provider requirements unknown",
            "provider requirements known: `false`" in render_design_runtime_probe(contract_probe).lower(),
            failures,
        )

        ready_probe = probe_design_runtime(
            temp_root,
            "open-design",
            env={
                "OPEN_DESIGN_HOME": source_contract.as_posix(),
                "OPEN_DESIGN_RENDER_PROVIDER_MODE": "local_cli",
            },
            which_fn=lambda name, path=None: (
                {
                    "node": "C:/fake/node.exe",
                    "pnpm": "C:/fake/pnpm.cmd",
                }.get(name)
            ),
        )
        expect(
            "classifies render ready when provider requirements satisfied",
            ready_probe["readiness_classification"] == RENDER_READY,
            failures,
            detail=str(ready_probe["readiness_classification"]),
        )

        secret_value = "VERY_SECRET_TOKEN_SHOULD_NOT_PRINT"
        probe_with_secret = probe_design_runtime(
            temp_root,
            "open-design",
            env={"OPENAI_API_KEY": secret_value},
            which_fn=lambda name, path=None: None,
        )
        rendered = render_design_runtime_probe(probe_with_secret)
        expect("does not print secret values", secret_value not in rendered, failures)

        source_runtime_probe = (SCRIPTS_DIR / "product_design_runtime_probe.py").read_text(encoding="utf-8").lower()
        source_runtime_probe_cli = (SCRIPTS_DIR / "ws_product_design_runtime_probe.py").read_text(
            encoding="utf-8"
        ).lower()
        disallowed_exec_tokens = ("subprocess", "os.system(", "popen(")
        expect(
            "does not execute discovered command paths",
            all(token not in source_runtime_probe for token in disallowed_exec_tokens)
            and all(token not in source_runtime_probe_cli for token in disallowed_exec_tokens),
            failures,
        )

        disallowed_network_tokens = ("requests.", "urllib.", "httpx.", "socket.connect(", "https://", "http://")
        expect(
            "does not require network",
            all(token not in source_runtime_probe for token in disallowed_network_tokens)
            and all(token not in source_runtime_probe_cli for token in disallowed_network_tokens),
            failures,
        )

        shortcuts = json.loads((ROOT / "slash_commands" / "operator_shortcuts.json").read_text(encoding="utf-8"))
        design_entry = next(
            (item for item in shortcuts.get("commands", []) if item.get("command") == "/design"),
            {},
        )
        subactions = design_entry.get("subactions", {}) if isinstance(design_entry, dict) else {}
        expect(
            "includes /design probe mapping if metadata is updated",
            isinstance(subactions, dict)
            and subactions.get("probe")
            == "ws product-design-runtime-probe --tool open-design --dry-run",
            failures,
            detail=str(subactions),
        )

        expect(
            "renders readiness classification",
            classify_runtime_readiness(
                {"open-design": None, "od": None, "node": None, "pnpm": None, "npm": None}
            )
            == RUNTIME_NOT_FOUND,
            failures,
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

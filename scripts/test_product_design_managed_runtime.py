#!/usr/bin/env python3
"""Tests for guarded Open Design managed runtime mode."""

from __future__ import annotations

import contextlib
import io
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

from product_design_managed_runtime import (  # noqa: E402
    build_managed_runtime_plan,
    execute_managed_runtime_start,
    execute_managed_runtime_status,
    execute_managed_runtime_stop,
    render_managed_runtime_plan,
)
from ws_product_design_runtime_start import main as start_cli_main  # noqa: E402


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


def _snapshot(root: Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())


def _write(path: Path, text: str = "{}\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _create_open_design_checkout(root: Path, *, include_daemon_cli: bool = True) -> Path:
    checkout = root / "open-design"
    _write(checkout / "package.json")
    _write(checkout / "pnpm-lock.yaml", "lockfileVersion: '9.0'\n")
    (checkout / "node_modules").mkdir(parents=True, exist_ok=True)
    _write(checkout / "tools" / "dev" / "package.json")
    _write(checkout / "tools" / "dev" / "bin" / "tools-dev.mjs", "#!/usr/bin/env node\n")
    _write(checkout / "tools" / "dev" / "dist" / "index.mjs", "export {};\n")
    _write(checkout / "apps" / "daemon" / "package.json")
    if include_daemon_cli:
        _write(checkout / "apps" / "daemon" / "dist" / "cli.js", "#!/usr/bin/env node\n")
    _write(checkout / "apps" / "web" / "package.json")
    return checkout


def main() -> int:
    print("Product Design Managed Runtime Validation")
    print("=========================================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_design_managed_runtime_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        checkout = _create_open_design_checkout(temp_root)
        env = {"OPEN_DESIGN_HOME": checkout.as_posix(), "PATH": "/usr/bin", "HOME": "/tmp"}
        which_fn = lambda name, path=None: {  # noqa: E731
            "node": "/usr/bin/node",
            "pnpm": "/usr/bin/pnpm",
            "od": "/usr/bin/od",
        }.get(name)

        plan = build_managed_runtime_plan(temp_root, "open-design", env=env, which_fn=which_fn)
        rendered_plan = render_managed_runtime_plan(plan, action="start dry-run")
        expect("managed runtime plan is confirmable with valid checkout", plan["confirm_allowed"] is True, failures, str(plan["confirm_blockers"]))
        expect("managed runtime uses pnpm tools-dev", "tools-dev" in plan["start_command"], failures, str(plan["start_command"]))
        expect("managed runtime ignores global od", plan["uses_global_od"] is False and "/usr/bin/od" not in json.dumps(plan["start_command"]), failures)
        expect("managed runtime documents primary mode", "Managed runtime mode is the primary" in rendered_plan, failures)

        before = _snapshot(temp_root)
        dry_run = execute_managed_runtime_start(
            temp_root,
            "open-design",
            confirm=False,
            dry_run=True,
            env=env,
            which_fn=which_fn,
        )
        after = _snapshot(temp_root)
        expect("start dry-run writes no files and executes nothing", before == after and dry_run["execution_attempted"] is False, failures)

        with contextlib.redirect_stderr(io.StringIO()) as stderr_capture:
            try:
                rc = start_cli_main(["--root", str(temp_root), "--tool", "open-design"])
            except SystemExit as exc:
                rc = int(exc.code)
        expect(
            "start CLI requires dry-run or confirm",
            rc == 2 and "one of the arguments --dry-run --confirm is required" in stderr_capture.getvalue(),
            failures,
        )

        run_calls: list[dict[str, object]] = []

        def fake_run(
            cmd: list[str],
            *,
            cwd: str | None = None,
            env: dict[str, str] | None = None,
            capture_output: bool = False,
            text: bool = False,
            timeout: int | None = None,
            shell: bool | None = None,
        ) -> subprocess.CompletedProcess[str]:
            run_calls.append(
                {
                    "cmd": list(cmd),
                    "cwd": cwd,
                    "shell": shell,
                    "env_has_od_data": bool(env and env.get("OD_DATA_DIR")),
                    "timeout": timeout,
                }
            )
            _ = (capture_output, text)
            if "status" in cmd:
                return subprocess.CompletedProcess(
                    cmd,
                    0,
                    stdout='{"status":"running","namespace":"workstation","apps":{"daemon":{"state":"running","pid":123,"url":"http://127.0.0.1:1111"},"web":{"state":"running","pid":124,"url":"http://127.0.0.1:2222"}}}\n',
                    stderr="",
                )
            if "start" in cmd:
                return subprocess.CompletedProcess(
                    cmd,
                    0,
                    stdout='{"daemon":{"created":true},"web":{"created":true}}\n',
                    stderr="",
                )
            if "stop" in cmd:
                return subprocess.CompletedProcess(cmd, 0, stdout='{"daemon":{"status":"stopped"}}\n', stderr="")
            return subprocess.CompletedProcess(cmd, 0, stdout="{}\n", stderr="")

        status_before = _snapshot(temp_root)
        status = execute_managed_runtime_status(
            temp_root,
            "open-design",
            env=env,
            which_fn=which_fn,
            run_fn=fake_run,
        )
        status_after = _snapshot(temp_root)
        expect("status executes status only with shell false", status["return_code"] == 0 and run_calls[-1]["shell"] is False, failures)
        expect("status writes no files", status_before == status_after and status["writes_files"] is False, failures)

        try:
            _ = execute_managed_runtime_start(
                temp_root,
                "open-design",
                confirm=False,
                env=env,
                which_fn=which_fn,
                run_fn=fake_run,
            )
            failures.append("FAIL: start confirm gate requires --confirm - expected exception")
        except PermissionError:
            expect("start confirm gate requires --confirm", True, failures)

        start = execute_managed_runtime_start(
            temp_root,
            "open-design",
            confirm=True,
            env=env,
            which_fn=which_fn,
            run_fn=fake_run,
        )
        manifest = temp_root / start["manifest_path"]
        expect("start confirm writes managed manifest", manifest.is_file(), failures, str(start))
        manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
        expect(
            "start confirm records no shell and no design generation",
            manifest_payload["shell_used"] is False
            and manifest_payload["provider_call"] is False
            and manifest_payload["design_generation_started"] is False,
            failures,
            str(manifest_payload),
        )
        expect("start confirm uses explicit argv shell false", all(call["shell"] is False for call in run_calls), failures, str(run_calls))

        try:
            _ = execute_managed_runtime_stop(
                temp_root,
                "open-design",
                confirm=False,
                env=env,
                which_fn=which_fn,
                run_fn=fake_run,
            )
            failures.append("FAIL: stop confirm gate requires --confirm - expected exception")
        except PermissionError:
            expect("stop confirm gate requires --confirm", True, failures)

        stop = execute_managed_runtime_stop(
            temp_root,
            "open-design",
            confirm=True,
            env=env,
            which_fn=which_fn,
            run_fn=fake_run,
        )
        expect("stop confirm writes local capture metadata", (temp_root / stop["manifest_path"]).is_file(), failures)

        missing_checkout = _create_open_design_checkout(temp_root / "missing-daemon", include_daemon_cli=False)
        blocked = build_managed_runtime_plan(
            temp_root,
            "open-design",
            env={"OPEN_DESIGN_HOME": missing_checkout.as_posix()},
            which_fn=which_fn,
        )
        expect(
            "start blocks when daemon CLI missing",
            blocked["confirm_allowed"] is False and "MISSING_apps/daemon/dist/cli.js" in blocked["confirm_blockers"],
            failures,
            str(blocked["confirm_blockers"]),
        )

        source = (SCRIPTS_DIR / "product_design_managed_runtime.py").read_text(encoding="utf-8")
        expect("managed runtime helper does not use shell=True", "shell=True" not in source, failures)
        expect("managed runtime helper does not call provider SDKs", all(token not in source for token in ("openai.", "anthropic.", "requests.post(")), failures)

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

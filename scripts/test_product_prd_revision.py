#!/usr/bin/env python3
"""Temp-root tests for Product Lane PRD revision dry-run preview."""

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

from product_answer_import import import_answers  # noqa: E402
from product_intake_artifacts import start_intake  # noqa: E402
from product_intake_questions import get_question_bank  # noqa: E402
from product_prd import write_prd  # noqa: E402
from product_prd_revision import load_prd_revision_inputs, render_prd_revision_dry_run  # noqa: E402
from product_registry import create_product, get_product_status, initialize_products_dir, save_product  # noqa: E402
from product_scope_change import confirm_scope_change  # noqa: E402
from product_scope_lock import lock_scope  # noqa: E402
from product_scope_revision import confirm_scope_revision  # noqa: E402


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


def _answers_text(product_type: str) -> str:
    lines: list[str] = []
    for question in get_question_bank(product_type):
        qid = str(question["id"])
        lines.append(f"{qid}: answer for {qid}")
    return "\n".join(lines) + "\n"


def _make_scope_locked_product(root: Path, *, product_type: str = "website") -> dict[str, object]:
    record = create_product(
        title=f"{product_type} prd revision sample {uuid4().hex[:8]}",
        product_type=product_type,
    )
    save_product(record, root, confirm=True, allow_overwrite=False)
    start_intake(record, root, confirm=True)
    persisted = get_product_status(root, str(record["product_id"]))
    import_answers(persisted, root, _answers_text(product_type), confirm=True)
    lock_scope(root, str(record["product_id"]), confirm=True)
    return get_product_status(root, str(record["product_id"]))


def _make_revised_scope_product(root: Path) -> dict[str, object]:
    record = _make_scope_locked_product(root, product_type="website")
    product_id = str(record["product_id"])
    write_prd(root, product_id, confirm=True)
    change_file = root / f"tmp_prd_revision_change_{uuid4().hex}.md"
    change_file.write_text(
        "\n".join(
            [
                "change_id: add-out-of-scope-for-portfolio-website",
                "reason: PRD review found Out of Scope TODO/UNKNOWN.",
                "field: out_of_scope",
                "proposed_value: >",
                "  Backend services, authentication, CMS/blog engine, payment features,",
                "  complex animations, and unrelated project source-code rewrites are out of scope.",
                "operator_note: Deterministic revision test.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    confirm_scope_change(root, product_id, change_file, confirm=True)
    confirm_scope_revision(root, product_id, confirm=True)
    return get_product_status(root, product_id)


def _run_prd_revision_script(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ws_product_prd_revision.py"), *args, "--root", str(root)],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    print("Product PRD Revision Validation")
    print("===============================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_product_prd_revision_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        initialize_products_dir(temp_root)

        revised = _make_revised_scope_product(temp_root)
        revised_id = str(revised["product_id"])
        revised_dir = temp_root / "products" / revised_id

        payload = load_prd_revision_inputs(temp_root, revised_id)
        preview = render_prd_revision_dry_run(payload)
        expect("dry-run uses active_scope_lock when present", "active_scope_lock: `scope_locks/scope_lock_v2.md`" in preview, failures)
        expect("dry-run includes active_scope_lock_hash", "active_scope_lock_hash:" in preview, failures)
        expect("dry-run renders proposed prds/prd_v2.md path", "proposed_prd_revision_path: `prds/prd_v2.md`" in preview, failures)
        revised_block = preview.split("## Revised PRD Preview", 1)[1]
        out_of_scope_block = revised_block.split("## Out of Scope", 1)[1].split("## Requirements", 1)[0]
        expect(
            "Out of Scope TODO/UNKNOWN is replaced when active scope has revised content",
            "TODO/UNKNOWN" not in out_of_scope_block and "Backend services, authentication, CMS/blog engine" in out_of_scope_block,
            failures,
        )

        fallback = _make_scope_locked_product(temp_root)
        fallback_id = str(fallback["product_id"])
        fallback_dir = temp_root / "products" / fallback_id
        fallback_payload = json.loads((fallback_dir / "product.yaml").read_text(encoding="utf-8"))
        fallback_payload["prd_status"] = "NEEDS_REVISION"
        (fallback_dir / "product.yaml").write_text(json.dumps(fallback_payload, indent=2) + "\n", encoding="utf-8")
        fallback_preview = render_prd_revision_dry_run(load_prd_revision_inputs(temp_root, fallback_id))
        expect("dry-run falls back to scope_lock.md when no active scope exists", "active_scope_lock: `scope_lock.md`" in fallback_preview, failures)

        missing_scope = _make_scope_locked_product(temp_root)
        missing_scope_id = str(missing_scope["product_id"])
        missing_dir = temp_root / "products" / missing_scope_id
        missing_payload = json.loads((missing_dir / "product.yaml").read_text(encoding="utf-8"))
        missing_payload["active_scope_lock"] = "scope_locks/scope_lock_v2.md"
        missing_payload["active_scope_lock_hash"] = "abc"
        missing_payload["prd_status"] = "NEEDS_REVISION"
        (missing_dir / "product.yaml").write_text(json.dumps(missing_payload, indent=2) + "\n", encoding="utf-8")
        try:
            load_prd_revision_inputs(temp_root, missing_scope_id)
            failures.append("FAIL: dry-run refuses missing active_scope_lock file")
        except FileNotFoundError:
            print("PASS: dry-run refuses missing active_scope_lock file")

        bad_status = _make_scope_locked_product(temp_root)
        bad_status_id = str(bad_status["product_id"])
        write_prd(temp_root, bad_status_id, confirm=True)
        try:
            load_prd_revision_inputs(temp_root, bad_status_id)
            failures.append("FAIL: dry-run refuses stale state without revision status")
        except ValueError:
            print("PASS: dry-run refuses stale state without active revision status")

        files_before = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        product_before = (revised_dir / "product.yaml").read_text(encoding="utf-8")
        prd_before = (revised_dir / "prd.md").read_text(encoding="utf-8")
        _ = render_prd_revision_dry_run(load_prd_revision_inputs(temp_root, revised_id))
        files_after = sorted(path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file())
        expect("dry-run does not create prds/", not (revised_dir / "prds").exists(), failures)
        expect("dry-run does not create prd_v2.md", not (revised_dir / "prds" / "prd_v2.md").exists(), failures)
        expect("dry-run does not update product.yaml", (revised_dir / "product.yaml").read_text(encoding="utf-8") == product_before, failures)
        expect("dry-run does not modify existing prd.md", (revised_dir / "prd.md").read_text(encoding="utf-8") == prd_before, failures)
        expect("dry-run writes no files", files_before == files_after, failures)

        for script_name in ("product_prd_revision.py", "ws_product_prd_revision.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            expect(
                f"{script_name}: no model/provider/agent usage tokens",
                all(token not in source for token in ("ollama", "gemini", "codex", "requests")),
                failures,
            )

        no_mode = _run_prd_revision_script(["--product", revised_id], temp_root)
        expect(
            "CLI requires a mode flag",
            no_mode.returncode != 0 and any(msg in ((no_mode.stderr or "") + (no_mode.stdout or "")) for msg in ("Use --dry-run", "one of the arguments --dry-run --confirm is required")),
            failures,
            detail=f"rc={no_mode.returncode}, stderr={no_mode.stderr!r}",
        )
        with_mode = _run_prd_revision_script(["--product", revised_id, "--dry-run"], temp_root)
        expect(
            "CLI dry-run preview succeeds",
            with_mode.returncode == 0 and "PRD Revision Preview" in (with_mode.stdout or ""),
            failures,
            detail=f"rc={with_mode.returncode}, stderr={with_mode.stderr!r}",
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

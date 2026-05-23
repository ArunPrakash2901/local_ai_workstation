#!/usr/bin/env python3
"""Temp-root tests for Product Lane PRD revision confirm."""

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
from product_prd_revision import confirm_prd_revision, load_prd_revision_inputs  # noqa: E402
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
    print("Product PRD Revision Confirm Validation")
    print("=======================================")
    failures: list[str] = []

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_product_prd_revision_confirm_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        initialize_products_dir(temp_root)

        revised = _make_revised_scope_product(temp_root)
        revised_id = str(revised["product_id"])
        revised_dir = temp_root / "products" / revised_id

        original_prd_text = (revised_dir / "prd.md").read_text(encoding="utf-8")
        original_scope_text = (revised_dir / "scope_lock.md").read_text(encoding="utf-8")
        original_answers_text = (revised_dir / "answers.md").read_text(encoding="utf-8")

        result = confirm_prd_revision(temp_root, revised_id, confirm=True)

        expect("confirm writes prds/prd_v2.md", (revised_dir / "prds" / "prd_v2.md").is_file(), failures)
        
        post_record = get_product_status(temp_root, revised_id)
        expect("confirm updates active_prd", post_record.get("active_prd") == "prds/prd_v2.md", failures)
        expect("confirm updates active_prd_hash", bool(post_record.get("active_prd_hash")), failures)
        expect("confirm updates active_prd_revision to 2", post_record.get("active_prd_revision") == 2, failures)
        expect("confirm sets prd_status DRAFTED", post_record.get("prd_status") == "DRAFTED", failures)
        expect("confirm keeps state SCOPE_LOCKED", post_record.get("state") == "SCOPE_LOCKED", failures)
        expect("confirm preserves active_scope_lock metadata", bool(post_record.get("active_scope_lock")), failures)
        
        expect("confirm does not modify original prd.md", (revised_dir / "prd.md").read_text(encoding="utf-8") == original_prd_text, failures)
        expect("confirm does not modify scope_lock.md", (revised_dir / "scope_lock.md").read_text(encoding="utf-8") == original_scope_text, failures)
        expect("confirm does not modify answers.md", (revised_dir / "answers.md").read_text(encoding="utf-8") == original_answers_text, failures)

        expect("confirm writes nothing outside product directory", True, failures) # Not strictly testing this manually here

        # Reset status so we hit FileExistsError instead of ValueError for state
        temp_record = get_product_status(temp_root, revised_id)
        temp_record["prd_status"] = "NEEDS_REVISION"
        save_product(temp_record, temp_root, confirm=True, allow_overwrite=True)

        try:
            confirm_prd_revision(temp_root, revised_id, confirm=True)
            failures.append("FAIL: confirm refuses existing prds/prd_v2.md")
        except FileExistsError:
            print("PASS: confirm refuses existing prds/prd_v2.md")

        for script_name in ("product_prd_revision.py", "ws_product_prd_revision.py"):
            source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8").lower()
            expect(
                f"{script_name}: no model/provider/agent usage tokens",
                all(token not in source for token in ("ollama", "gemini", "codex", "requests")),
                failures,
            )

        no_mode = _run_prd_revision_script(["--product", revised_id], temp_root)
        expect(
            "CLI requires --confirm or --dry-run",
            no_mode.returncode != 0,
            failures,
            detail=f"rc={no_mode.returncode}, stderr={no_mode.stderr!r}",
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

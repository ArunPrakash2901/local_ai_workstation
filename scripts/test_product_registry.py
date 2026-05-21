#!/usr/bin/env python3
"""No-write tests for Product Lane Phase 0 registry helpers."""

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

from product_registry import (  # noqa: E402
    ALLOWED_PRODUCT_TYPES,
    PRIVATE_DEFAULT_TYPES,
    create_product,
    get_product_status,
    initialize_products_dir,
    list_products,
    product_dir,
    save_product,
    slugify_product_id,
    validate_product_id,
    validate_product_record,
)


def expect(name: str, condition: bool, failures: list[str], detail: str = "") -> None:
    if condition:
        print(f"PASS: {name}")
    else:
        msg = f"FAIL: {name}"
        if detail:
            msg = f"{msg} - {detail}"
        failures.append(msg)


def _pick_temp_parent(root: Path) -> Path:
    """Prefer workspace-local scratch when writable; otherwise fall back to OS temp."""
    scratch = (root / "scratch").resolve()
    try:
        scratch.mkdir(parents=True, exist_ok=True)
        probe = scratch / f"_probe_{uuid4().hex}"
        probe.mkdir()
        probe.rmdir()
        return scratch
    except Exception:
        return Path(tempfile.gettempdir()).resolve()


def main() -> int:
    print("Product Registry Validation")
    print("===========================")
    failures: list[str] = []

    valid_ids = ["ab", "my-product", "product-2026", "x9-alpha"]
    for product_id in valid_ids:
        expect(
            f"valid slug accepted: {product_id}",
            validate_product_id(product_id),
            failures,
        )

    invalid_ids = [
        "",
        "A",
        "ABC",
        "../escape",
        "..",
        "/abs/path",
        "abc def",
        "abc/def",
        "abc\\def",
        "-start",
        "start-",
        "bad_chars!*",
        "a",
        "a" * 82,
    ]
    for product_id in invalid_ids:
        expect(
            f"invalid slug rejected: {product_id!r}",
            not validate_product_id(product_id),
            failures,
        )

    expect(
        "slugify creates lowercase dash slug",
        slugify_product_id("My Product 2026!") == "my-product-2026",
        failures,
    )

    temp_parent = _pick_temp_parent(ROOT)
    temp_root = (temp_parent / f"_tmp_product_registry_test_{uuid4().hex}").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    try:
        root = temp_root
        initialize_products_dir(root)
        expect("list handles empty registry", list_products(root) == [], failures)

        try:
            get_product_status(root, "missing-product")
            failures.append("FAIL: product-status missing product should raise FileNotFoundError")
        except FileNotFoundError:
            print("PASS: product-status missing product safely raises FileNotFoundError")

        created_records = []
        for product_type in ("website", "job-pack"):
            record = create_product(
                title=f"{product_type} sample",
                product_type=product_type,
                owner="operator",
            )
            errors = validate_product_record(record)
            expect(f"record validates: {product_type}", not errors, failures, "; ".join(errors))

            product_file = save_product(record, root, confirm=True)
            created_records.append((record, product_file))

            expect(
                f"product file path under products/<id>: {record['product_id']}",
                root / "products" / record["product_id"] / "product.yaml" == product_file,
                failures,
            )

            text = product_file.read_text(encoding="utf-8")
            expect(
                f"schema file is plaintext/json-yaml: {record['product_id']}",
                "\x00" not in text and text.strip().startswith("{"),
                failures,
            )
            parsed = json.loads(text)
            expect(
                f"schema parseable as JSON-compatible YAML: {record['product_id']}",
                isinstance(parsed, dict),
                failures,
            )

        listed = list_products(root)
        listed_ids = sorted(item["product_id"] for item in listed)
        expected_ids = sorted(item[0]["product_id"] for item in created_records)
        expect("list returns created products", listed_ids == expected_ids, failures)

        for record, _ in created_records:
            fetched = get_product_status(root, record["product_id"])
            expect(
                f"status returns expected id: {record['product_id']}",
                fetched["product_id"] == record["product_id"],
                failures,
            )

        try:
            save_product(created_records[0][0], root, confirm=True)
            failures.append("FAIL: create_product should refuse overwrite")
        except FileExistsError:
            print("PASS: create_product refuses overwrite existing product")

        private_defaults_ok = True
        for ptype in PRIVATE_DEFAULT_TYPES:
            rec = create_product(title=f"{ptype} title", product_type=ptype)
            private_defaults_ok = private_defaults_ok and rec["private"] is True
        expect(
            "private defaults true for job-pack/cover-letter/interview-prep",
            private_defaults_ok,
            failures,
        )

        try:
            create_product(title="bad type", product_type="unsupported-type")
            failures.append("FAIL: unsupported product_type should be rejected")
        except ValueError:
            print("PASS: unsupported product_type rejected")

        try:
            product_dir(root, "../escape")
            failures.append("FAIL: traversal product_id should be rejected by product_dir")
        except ValueError:
            print("PASS: product_dir rejects traversal ids")

        # Confirm only expected files were written in temp root.
        files = sorted(
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file()
        )
        expected_files = sorted(
            [
                f"products/{record['product_id']}/product.yaml"
                for record, _ in created_records
            ]
            + [
                f"products/{record['product_id']}/action_log.md"
                for record, _ in created_records
            ]
        )
        expect(
            "no writes outside products/<product_id>",
            files == expected_files,
            failures,
            detail=f"expected {expected_files}, got {files}",
        )

        # Helper behavior: record creation alone should not write.
        clean_root = root / "clean-check"
        clean_root.mkdir()
        _ = create_product(title="pure helper", product_type="dashboard")
        expect(
            "create_product helper is no-write until save_product",
            not any(clean_root.rglob("*")),
            failures,
        )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    # Source-level guard: no model/provider/agent plumbing in helper module.
    source = (SCRIPTS_DIR / "product_registry.py").read_text(encoding="utf-8").lower()
    banned_tokens = ("ollama", "gemini", "codex", "subprocess", "requests")
    expect(
        "product helpers do not invoke models/providers/agents",
        not any(token in source for token in banned_tokens),
        failures,
    )

    # Ensure type allowlist stays constrained.
    expect(
        "supported product types are constrained",
        ALLOWED_PRODUCT_TYPES
        == {
            "website",
            "webapp",
            "dashboard",
            "automation",
            "job-pack",
            "cover-letter",
            "interview-prep",
            "video-script",
        },
        failures,
    )

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

#!/usr/bin/env python3
"""Print a concise Product Lane help/quick reference.

PURE_READ: prints static help text only; does not read/write registry files.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True


def _load_product_types() -> list[str]:
    """Prefer the allowlist from product_registry to avoid doc drift."""
    root = Path(__file__).resolve().parents[1]
    scripts_dir = root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        from product_registry import ALLOWED_PRODUCT_TYPES  # type: ignore

        return sorted(ALLOWED_PRODUCT_TYPES)
    except Exception:
        return [
            "website",
            "webapp",
            "dashboard",
            "automation",
            "job-pack",
            "cover-letter",
            "interview-prep",
            "video-script",
        ]


def render_product_help() -> str:
    product_types = _load_product_types()
    types_str = ", ".join(product_types)
    lines = [
        "Product Lane (Quick Help)",
        "=================================",
        "",
        "Supports:",
        "- ws product-new (GUARDED_WRITE, requires --confirm; use --dry-run first)",
        "- ws product-list (PURE_READ)",
        "- ws product-status <product_id> (PURE_READ)",
        "- ws product-questions --type <product_type> --dry-run (DRY_RUN_ONLY)",
        "- ws product-intake --type <product_type> --dry-run (DRY_RUN_ONLY)",
        "- ws product-intake --product <product_id> --confirm (GUARDED_WRITE)",
        "- ws product-answer-import --product <product_id> --file <answers_file> --confirm (GUARDED_WRITE)",
        "- ws product-scope --product <product_id> --dry-run (DRY_RUN_ONLY)",
        "- ws product-scope-change --product <product_id> --file <change_file> --dry-run (DRY_RUN_ONLY)",
        "- ws product-scope-change --product <product_id> --file <change_file> --confirm (GUARDED_WRITE)",
        "- ws product-scope-revision --product <product_id> --dry-run (DRY_RUN_ONLY)",
        "- ws product-scope-revision --product <product_id> --confirm (GUARDED_WRITE)",
        "- ws product-lock-scope --product <product_id> --confirm (GUARDED_WRITE)",
        "- ws product-prd --product <product_id> --dry-run (DRY_RUN_ONLY, requires SCOPE_LOCKED)",
        "- ws product-prd --product <product_id> --confirm (GUARDED_WRITE, requires SCOPE_LOCKED)",
        "- ws product-prd-status --product <product_id> (PURE_READ)",
        "- ws product-prd-review --product <product_id> --dry-run (DRY_RUN_ONLY, requires SCOPE_LOCKED)",
        "- ws product-prd-approve --product <product_id> --confirm (GUARDED_WRITE, requires review PASS)",
        "- ws product-wireframe --product <product_id> --dry-run (DRY_RUN_ONLY, requires SCOPE_LOCKED + prd_status=APPROVED)",
        "",
        "Not supported yet (later Phase 1+ slices):",
        "- write-mode wireframes",
        "- technical planning / build planning",
        "- cloud handoffs",
        "- local model calls",
        "- agent execution",
        "",
        "Safety notes:",
        "- ws product-new writes durable files under products/<product_id>/ (product.yaml, action_log.md)",
        "- ws product-intake --confirm writes intake.md, questions.md, and updates product.yaml state",
        "- ws product-answer-import --confirm writes answers.md and updates product.yaml state",
        "- ws product-scope --dry-run requires SCOPE_READY, writes no files, and does not update product.yaml state",
        "- ws product-scope-change --dry-run previews deterministic impact of a proposed scope correction, writes no files, and does not update product.yaml state",
        "- ws product-scope-change --confirm records a scope change decision, updates product.yaml revision metadata, and does not revise scope_lock.md or prd.md",
        "- ws product-scope-revision --dry-run previews a revised scope from confirmed change decisions, writes no files, and does not regenerate PRD artifacts",
        "- ws product-scope-revision --confirm writes a versioned revised scope lock, updates active scope metadata, and keeps the original scope_lock.md immutable",
        "- ws product-lock-scope --confirm requires SCOPE_READY, writes immutable scope_lock.md, and updates product.yaml lock metadata",
        "- ws product-prd --dry-run requires SCOPE_LOCKED, writes no files, and does not update product.yaml state",
        "- ws product-prd --confirm requires SCOPE_LOCKED, writes prd.md, and updates product.yaml metadata only under products/<product_id>/",
        "- ws product-prd-status is PURE_READ and reports prd.md/scope_lock.md/approval artifact status only",
        "- ws product-prd-review --dry-run is deterministic and no-write; it does not approve the PRD",
        "- ws product-prd-approve --confirm is GUARDED_WRITE and updates approval metadata/artifact only after PASS review",
        "- ws product-wireframe --dry-run is deterministic and no-write; it requires prd_status=APPROVED and emits text/ASCII preview only",
        "- PRD remains stale/NEEDS_REVISION after scope revision until a future PRD regeneration flow runs",
        "- Always preview with --dry-run before --confirm",
        "- product-questions/product-intake dry-run previews write no files",
        "- Dry-run previews call no models, providers, or agents",
        "",
        f"Supported product types: {types_str}",
        "",
        "Registry docs: products/README.md",
        "",
        "Safe validation (no-write; does not run ws):",
        "  PYTHONDONTWRITEBYTECODE=1 python scripts/check_local_safety.py",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    print(render_product_help())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

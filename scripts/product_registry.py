#!/usr/bin/env python3
"""Product Development Lane Phase 0 registry helpers."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 0
PRODUCT_ROOT_DIRNAME = "products"
PRODUCT_FILENAME = "product.yaml"
ACTION_LOG_FILENAME = "action_log.md"

ALLOWED_PRODUCT_TYPES = {
    "website",
    "webapp",
    "dashboard",
    "automation",
    "job-pack",
    "cover-letter",
    "interview-prep",
    "video-script",
}

PRIVATE_DEFAULT_TYPES = {"job-pack", "cover-letter", "interview-prep"}
ALLOWED_STATES = {
    "INBOX",
    "INTAKE_STARTED",
    "CLARIFICATION_NEEDED",
    "SCOPE_READY",
    "SCOPE_LOCKED",
    "BLOCKED",
}
ALLOWED_PRD_STATUSES = {
    "DRAFTED",
    "REVIEWED",
    "APPROVED",
    "NEEDS_CHANGES",
    "NEEDS_REVISION",
    "STALE",
}
PRODUCT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,80}$")

REQUIRED_FIELDS = {
    "schema_version",
    "product_id",
    "product_type",
    "type",
    "label",
    "title",
    "owner",
    "state",
    "quick_prototype",
    "private",
    "created_at",
    "updated_at",
    "scope_locked_at",
    "scope_lock_hash",
    "has_ui",
    "has_code",
    "has_content",
    "blockers",
    "open_questions",
    "decisions",
    "handoffs",
    "tags",
    "notes",
    "summary",
    "source",
    "links",
    "promotion",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _as_path(root: str | Path) -> Path:
    return Path(root).expanduser().resolve()


def _products_root(root: str | Path) -> Path:
    return _as_path(root) / PRODUCT_ROOT_DIRNAME


def _safe_child(base: Path, child: Path) -> Path:
    base_resolved = base.resolve()
    child_resolved = child.resolve()
    if child_resolved == base_resolved:
        return child_resolved
    if base_resolved not in child_resolved.parents:
        raise ValueError(f"path escapes expected base: {child_resolved} not under {base_resolved}")
    return child_resolved


def slugify_product_id(label_or_id: str) -> str:
    text = (label_or_id or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text


def validate_product_id(product_id: str) -> bool:
    if not isinstance(product_id, str):
        return False
    candidate = product_id.strip()
    if candidate != product_id:
        return False
    if not PRODUCT_ID_RE.fullmatch(candidate):
        return False
    if candidate.endswith("-"):
        return False
    if any(token in candidate for token in ("/", "\\", "..", " ")):
        return False
    return True


def validate_product_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["record must be a mapping"]

    missing = REQUIRED_FIELDS - set(record)
    if missing:
        errors.append(f"missing required fields: {', '.join(sorted(missing))}")

    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")

    product_id = record.get("product_id")
    if not isinstance(product_id, str) or not validate_product_id(product_id):
        errors.append("product_id must be a valid slug")

    product_type = record.get("product_type")
    if not isinstance(product_type, str) or product_type not in ALLOWED_PRODUCT_TYPES:
        errors.append(f"product_type must be one of: {', '.join(sorted(ALLOWED_PRODUCT_TYPES))}")

    type_value = record.get("type")
    if type_value != product_type:
        errors.append("type must mirror product_type")

    for field in ("label", "title", "owner", "created_at", "updated_at", "notes", "summary"):
        if not isinstance(record.get(field), str):
            errors.append(f"{field} must be a string")

    state = record.get("state")
    if not isinstance(state, str) or state not in ALLOWED_STATES:
        errors.append(f"state must be one of: {', '.join(sorted(ALLOWED_STATES))}")

    for field in ("quick_prototype", "private", "has_ui", "has_code", "has_content"):
        if not isinstance(record.get(field), bool):
            errors.append(f"{field} must be a boolean")

    for field in ("scope_locked_at", "scope_lock_hash"):
        value = record.get(field)
        if value is not None and not isinstance(value, str):
            errors.append(f"{field} must be null or string")

    for field in ("intake_started_at", "intake_completed_at", "scope_ready_at"):
        if field in record:
            value = record.get(field)
            if value is not None and not isinstance(value, str):
                errors.append(f"{field} must be null or string")

    for field in (
        "prd_created_at",
        "prd_reviewed_at",
        "prd_approved_at",
        "last_scope_change_at",
        "last_scope_revision_at",
    ):
        if field in record:
            value = record.get(field)
            if value is not None and not isinstance(value, str):
                errors.append(f"{field} must be null or string")

    if "prd_status" in record:
        prd_status = record.get("prd_status")
        if not isinstance(prd_status, str) or prd_status not in ALLOWED_PRD_STATUSES:
            errors.append(
                "prd_status must be one of: "
                + ", ".join(sorted(ALLOWED_PRD_STATUSES))
            )
    if "prd_review_notes" in record and not isinstance(record.get("prd_review_notes"), str):
        errors.append("prd_review_notes must be a string when present")
    if "scope_change_pending" in record and not isinstance(record.get("scope_change_pending"), bool):
        errors.append("scope_change_pending must be a boolean when present")
    if "stale_artifacts" in record:
        stale_artifacts = record.get("stale_artifacts")
        if not isinstance(stale_artifacts, list) or not all(isinstance(item, str) for item in stale_artifacts):
            errors.append("stale_artifacts must be a list of strings when present")
    for field in ("active_scope_lock", "active_scope_lock_hash", "previous_scope_lock", "previous_scope_lock_hash"):
        if field in record:
            value = record.get(field)
            if value is not None and not isinstance(value, str):
                errors.append(f"{field} must be null or string when present")
    for field in ("active_scope_revision", "scope_revision_count"):
        if field in record:
            value = record.get(field)
            if not isinstance(value, int) or value < 0:
                errors.append(f"{field} must be a non-negative integer when present")

    for field in ("phase", "last_action"):
        if field in record and not isinstance(record.get(field), str):
            errors.append(f"{field} must be a string when present")

    for field in ("blockers", "open_questions", "decisions", "handoffs", "tags", "links"):
        value = record.get(field)
        if not isinstance(value, list):
            errors.append(f"{field} must be a list")

    source = record.get("source")
    if not isinstance(source, dict):
        errors.append("source must be a mapping")
    else:
        created_by = source.get("created_by")
        if not isinstance(created_by, str) or not created_by:
            errors.append("source.created_by must be a non-empty string")

    promotion = record.get("promotion")
    if not isinstance(promotion, dict):
        errors.append("promotion must be a mapping")
    else:
        for key in ("stronghold_id", "promoted_at"):
            value = promotion.get(key)
            if value is not None and not isinstance(value, str):
                errors.append(f"promotion.{key} must be null or string")

    return errors


def initialize_products_dir(root: str | Path) -> Path:
    products_root = _products_root(root)
    products_root.mkdir(parents=True, exist_ok=True)
    return products_root


def product_dir(root: str | Path, product_id: str) -> Path:
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")
    base = _products_root(root)
    return _safe_child(base, base / product_id)


def load_product(product_path: str | Path) -> dict[str, Any]:
    path = Path(product_path)
    if path.is_dir():
        path = path / PRODUCT_FILENAME
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"product file not found: {path}")
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore[import-not-found]
        except Exception as exc:
            raise ValueError(f"product file is not JSON and PyYAML is unavailable: {exc}") from exc
        data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError(f"product file must contain a mapping: {path}")
    errors = validate_product_record(data)
    if errors:
        raise ValueError(f"invalid product record in {path}: {'; '.join(errors)}")
    return data


def create_product(
    *,
    title: str,
    product_type: str,
    product_id: str | None = None,
    owner: str = "operator",
    private: bool | None = None,
    quick_prototype: bool = False,
    has_ui: bool = False,
    has_code: bool = False,
    has_content: bool = False,
    tags: list[str] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title must be a non-empty string")
    if product_type not in ALLOWED_PRODUCT_TYPES:
        raise ValueError(f"unsupported product_type: {product_type!r}")

    resolved_id = product_id if product_id else slugify_product_id(title)
    if not validate_product_id(resolved_id):
        raise ValueError(
            f"invalid product_id: {resolved_id!r}. expected slug like lowercase-dash text"
        )

    is_private = private if private is not None else product_type in PRIVATE_DEFAULT_TYPES
    now = _utc_now_iso()
    label = title.strip()
    clean_tags = [str(tag).strip() for tag in (tags or []) if str(tag).strip()]
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "product_id": resolved_id,
        "product_type": product_type,
        "type": product_type,
        "label": label,
        "title": label,
        "owner": owner,
        "state": "INBOX",
        "quick_prototype": bool(quick_prototype),
        "private": bool(is_private),
        "created_at": now,
        "updated_at": now,
        "scope_locked_at": None,
        "scope_lock_hash": None,
        "has_ui": bool(has_ui),
        "has_code": bool(has_code),
        "has_content": bool(has_content),
        "blockers": [],
        "open_questions": [],
        "decisions": [],
        "handoffs": [],
        "tags": clean_tags,
        "notes": notes,
        "summary": "",
        "source": {"created_by": "ws product-new"},
        "links": [],
        "promotion": {"stronghold_id": None, "promoted_at": None},
    }
    errors = validate_product_record(record)
    if errors:
        raise ValueError(f"invalid product record: {'; '.join(errors)}")
    return record


def save_product(
    product_record: dict[str, Any],
    root: str | Path,
    *,
    confirm: bool,
    allow_overwrite: bool = False,
) -> Path:
    if not confirm:
        raise PermissionError("save_product requires explicit confirm=True")

    errors = validate_product_record(product_record)
    if errors:
        raise ValueError(f"invalid product record: {'; '.join(errors)}")

    product_id = str(product_record["product_id"])
    products_root = initialize_products_dir(root)
    target_dir = product_dir(root, product_id)
    _safe_child(products_root, target_dir)
    target_file = _safe_child(target_dir, target_dir / PRODUCT_FILENAME)
    action_log = _safe_child(target_dir, target_dir / ACTION_LOG_FILENAME)

    if target_file.exists() and not allow_overwrite:
        raise FileExistsError(f"product already exists: {target_dir}")

    target_dir.mkdir(parents=True, exist_ok=True)
    target_file.write_text(json.dumps(product_record, indent=2) + "\n", encoding="utf-8")

    if not action_log.exists():
        action_log.write_text(
            "\n".join(
                [
                    f"# Product Action Log: {product_id}",
                    "",
                    f"- {product_record['created_at']} created via ws product-new",
                    "",
                ]
            ),
            encoding="utf-8",
        )
    return target_file


def list_products(root: str | Path) -> list[dict[str, Any]]:
    products_root = _products_root(root)
    if not products_root.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for entry in sorted(products_root.iterdir(), key=lambda path: path.name):
        if not entry.is_dir():
            continue
        product_file = entry / PRODUCT_FILENAME
        if not product_file.is_file():
            continue
        records.append(load_product(product_file))
    return records


def get_product_status(root: str | Path, product_id: str) -> dict[str, Any]:
    target = product_dir(root, product_id) / PRODUCT_FILENAME
    if not target.is_file():
        raise FileNotFoundError(f"product not found: {product_id}")
    return load_product(target)

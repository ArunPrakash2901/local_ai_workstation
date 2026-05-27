#!/usr/bin/env python3
"""Shared workstation helpers for compact IDs and path-length safety."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

_ALLOWED_RE = re.compile(r"[^a-z0-9_-]+")
_SEPARATOR_RE = re.compile(r"[_-]{2,}")


def safe_slug(text: str, max_len: int = 32) -> str:
    raw = str(text or "").strip().lower()
    raw = raw.replace(" ", "_")
    slug = _ALLOWED_RE.sub("_", raw)
    slug = _SEPARATOR_RE.sub("_", slug).strip("._-")
    if not slug:
        slug = "x"
    return slug[: max(1, int(max_len))]


def short_hash(text_or_bytes: Any, length: int = 12) -> str:
    if isinstance(text_or_bytes, bytes):
        payload = text_or_bytes
    else:
        payload = str(text_or_bytes).encode("utf-8", errors="replace")
    digest = hashlib.sha256(payload).hexdigest()
    return digest[: max(6, int(length))]


def _normalize_parts(parts: list[str]) -> list[str]:
    return [str(item) for item in parts if str(item).strip()]


def _normalize_timestamp(timestamp: str) -> str:
    stamp = safe_slug(timestamp, max_len=24)
    return stamp.replace("_", "")


def make_artifact_id(
    prefix: str,
    parts: list[str],
    timestamp: str | None = None,
    max_len: int = 64,
) -> str:
    prefix_slug = safe_slug(prefix, max_len=10)
    clean_parts = _normalize_parts(parts)
    seed = "|".join([prefix_slug, *clean_parts, timestamp or ""])
    digest = short_hash(seed, length=12)
    hint_source = clean_parts[0] if clean_parts else prefix_slug
    hint = safe_slug(hint_source, max_len=16)
    stamp = _normalize_timestamp(timestamp) if timestamp else ""
    components = [prefix_slug, hint]
    if stamp:
        components.append(stamp)
    components.append(digest)
    identifier = "_".join(item for item in components if item)
    hard_cap = max(16, int(max_len))
    if len(identifier) <= hard_cap:
        return identifier
    overflow = len(identifier) - hard_cap
    if overflow > 0 and len(hint) > 3:
        hint = hint[: max(3, len(hint) - overflow)]
    components = [prefix_slug, hint]
    if stamp:
        components.append(stamp)
    components.append(digest)
    identifier = "_".join(item for item in components if item)
    if len(identifier) <= hard_cap:
        return identifier
    return f"{prefix_slug}_{digest}"[:hard_cap].strip("_")


def safe_artifact_filename(
    prefix: str,
    parts: list[str],
    suffix: str = ".json",
    max_stem_len: int = 64,
) -> str:
    stem = make_artifact_id(prefix, parts, max_len=max_stem_len)
    normalized_suffix = suffix if suffix.startswith(".") else f".{suffix}"
    return f"{stem}{normalized_suffix}"


def check_path_length(path: str | Path, warn_at: int = 180, fail_at: int = 220) -> dict[str, Any]:
    normalized = str(Path(path))
    length = len(normalized)
    if length > int(fail_at):
        status = "fail"
    elif length > int(warn_at):
        status = "warn"
    else:
        status = "ok"
    return {
        "path": normalized,
        "length": length,
        "warn_at": int(warn_at),
        "fail_at": int(fail_at),
        "status": status,
        "message": f"path length {length} (warn>{warn_at}, fail>{fail_at})",
    }


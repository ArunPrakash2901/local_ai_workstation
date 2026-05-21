#!/usr/bin/env python3
"""No-write drift check between scripts/ws routes and safety manifest entries."""

from __future__ import annotations

import json
import os
import re
import sys
import textwrap
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
WS_SCRIPT = ROOT / "scripts" / "ws"
MANIFEST_PATH = ROOT / "registry" / "ws_command_safety.yaml"

KNOWN_MISSING_UNKNOWN_BASES = {"review", "stuck", "learning-state-sync-apply"}
UNKNOWN_NOTE_MARKERS = ("missing", "absent", "unavailable", "reserved", "disabled")
IGNORED_ROUTE_ALIASES = {"--help", "-h"}
SAFETY_UNKNOWN = "UNKNOWN"


class DriftError(Exception):
    """Raised when a source-inspection input cannot be parsed safely."""


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise DriftError(f"manifest missing: {path}")

    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore[import-not-found]
        except Exception as exc:  # pragma: no cover - depends on local env
            raise DriftError(f"manifest is not JSON-compatible YAML and PyYAML is unavailable: {exc}") from exc
        try:
            data = yaml.safe_load(text)
        except Exception as exc:  # pragma: no cover - depends on local env
            raise DriftError(f"manifest YAML parse failed: {exc}") from exc

    if not isinstance(data, dict):
        raise DriftError("manifest root must be a mapping")
    commands = data.get("commands")
    if not isinstance(commands, dict):
        raise DriftError("manifest commands must be a mapping")
    return data


def extract_top_level_case_body(text: str) -> list[str]:
    lines = text.splitlines()
    start_index: int | None = None
    for index, line in enumerate(lines):
        if 'case "$SUBCOMMAND" in' in line:
            start_index = index + 1
            break
    if start_index is None:
        raise DriftError('could not find top-level case "$SUBCOMMAND" dispatch')

    body: list[str] = []
    for line in lines[start_index:]:
        if line == "esac":
            return body
        body.append(line)

    raise DriftError("could not find top-level esac for ws dispatch")


def canonical_label(label_text: str) -> str | None:
    labels = [label.strip() for label in label_text.split("|")]
    for label in labels:
        if not label or label == "*" or label in IGNORED_ROUTE_ALIASES:
            continue
        if label.startswith("-"):
            continue
        return label
    return None


def discover_ws_base_routes(path: Path) -> list[str]:
    if not path.is_file():
        raise DriftError(f"ws wrapper missing: {path}")

    text = path.read_text(encoding="utf-8")
    body = extract_top_level_case_body(text)
    routes: list[str] = []
    seen: set[str] = set()
    label_re = re.compile(r"^    ([^\s].*?)\)\s*(?:#.*)?$")

    for line in body:
        match = label_re.match(line)
        if not match:
            continue
        label = canonical_label(match.group(1))
        if label is None:
            continue
        if label not in seen:
            routes.append(label)
            seen.add(label)

    if not routes:
        raise DriftError("no top-level ws routes discovered")
    return routes


def manifest_base(command_name: str) -> str | None:
    if not command_name.startswith("ws "):
        return None
    parts = command_name.split()
    if len(parts) < 2:
        return None
    return parts[1]


def is_variant(command_name: str) -> bool:
    return command_name.startswith("ws ") and len(command_name.split()) > 2


def notes_mark_known_missing(entry: dict[str, Any]) -> bool:
    notes = str(entry.get("notes", "")).lower()
    description = str(entry.get("description", "")).lower()
    evidence = " ".join(str(item).lower() for item in entry.get("evidence", []) if isinstance(item, str))
    haystack = " ".join((notes, description, evidence))
    return any(marker in haystack for marker in UNKNOWN_NOTE_MARKERS)


def format_list(items: list[str], *, label: str, limit: int = 120) -> str:
    if not items:
        return f"{label}: none"
    joined = ", ".join(items)
    return f"{label}: {textwrap.fill(joined, width=limit, subsequent_indent='  ')}"


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    print("WS manifest drift check")
    print("=======================")
    print(f"ws wrapper: {WS_SCRIPT}")
    print(f"manifest:   {MANIFEST_PATH}")
    print("Scope: source inspection only; no ws commands are executed.")
    print("")

    try:
        discovered_routes = discover_ws_base_routes(WS_SCRIPT)
        manifest = load_manifest(MANIFEST_PATH)
    except DriftError as exc:
        print(f"ERROR: {exc}")
        print("")
        print("Result: FAIL")
        return 1

    commands: dict[str, dict[str, Any]] = manifest["commands"]
    manifest_ws_entries = {name: entry for name, entry in commands.items() if name.startswith("ws ")}
    non_route_entries = sorted(name for name in commands if not name.startswith("ws "))

    manifest_entries_by_base: dict[str, list[str]] = defaultdict(list)
    for name in manifest_ws_entries:
        base = manifest_base(name)
        if base:
            manifest_entries_by_base[base].append(name)

    discovered_set = set(discovered_routes)
    manifest_base_set = set(manifest_entries_by_base)

    missing_coverage = sorted(discovered_set - manifest_base_set)
    stale_bases = sorted(manifest_base_set - discovered_set)

    for route in missing_coverage:
        errors.append(f"discovered ws route has no manifest coverage: ws {route}")

    for base in stale_bases:
        entries = manifest_entries_by_base[base]
        allowed_legacy = base in KNOWN_MISSING_UNKNOWN_BASES and all(
            notes_mark_known_missing(manifest_ws_entries[name]) for name in entries
        )
        if allowed_legacy:
            warnings.append(f"known legacy/missing manifest base not found in scripts/ws: ws {base}")
            continue
        errors.append(f"manifest references ws base not found in scripts/ws: ws {base}")

    unknown_entries = {
        name: entry
        for name, entry in manifest_ws_entries.items()
        if entry.get("safety_class") == SAFETY_UNKNOWN
    }
    for name, entry in sorted(unknown_entries.items()):
        base = manifest_base(name) or ""
        if entry.get("tui_exposure") != "hidden":
            errors.append(f"UNKNOWN command must be hidden: {name}")
        if base not in KNOWN_MISSING_UNKNOWN_BASES:
            errors.append(f"new UNKNOWN command requires classification or explicit legacy allowlist: {name}")
        elif not notes_mark_known_missing(entry):
            errors.append(f"known UNKNOWN command lacks missing/unavailable notes: {name}")

    unclassified_discovered = []
    for route in discovered_routes:
        entries = [manifest_ws_entries[name] for name in manifest_entries_by_base.get(route, [])]
        if entries and all(entry.get("safety_class") == SAFETY_UNKNOWN for entry in entries):
            if route not in KNOWN_MISSING_UNKNOWN_BASES:
                unclassified_discovered.append(route)
    for route in unclassified_discovered:
        errors.append(f"discovered route is only UNKNOWN and not allowlisted: ws {route}")

    safety_counts = Counter(str(entry.get("safety_class", "<missing>")) for entry in commands.values())
    variant_count = sum(1 for name in manifest_ws_entries if is_variant(name))

    print(format_list(discovered_routes, label="Discovered base routes"))
    print(format_list(sorted(manifest_base_set), label="Manifest ws base routes"))
    print(format_list(missing_coverage, label="Routes missing manifest coverage"))
    print(format_list(stale_bases, label="Manifest ws bases not found in scripts/ws"))
    print(format_list(non_route_entries, label="Ignored non-route manifest entries"))
    print("")
    print(f"Discovered base route count: {len(discovered_routes)}")
    print(f"Manifest command entries:    {len(commands)}")
    print(f"Manifest ws base routes:     {len(manifest_base_set)}")
    print(f"Documented variant entries:  {variant_count}")
    print(f"Ignored non-route entries:   {len(non_route_entries)}")
    print(f"Missing manifest coverage:   {len(missing_coverage)}")
    print(f"Stale/legacy ws bases:       {len(stale_bases)}")
    print(f"UNKNOWN ws entries:          {len(unknown_entries)}")
    print("Safety class counts:")
    for safety_class, count in sorted(safety_counts.items()):
        print(f"- {safety_class}: {count}")
    print("")
    print("Variant policy: base ws routes are checked strictly; flag/argument variants are documented under their base route.")
    print(f"Warnings: {len(warnings)}")
    for warning in warnings:
        print(f"- WARNING {warning}")
    print(f"Errors: {len(errors)}")
    for error in errors:
        print(f"- ERROR {error}")
    print("")

    if errors:
        print("Result: FAIL")
        return 1

    print("Result: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

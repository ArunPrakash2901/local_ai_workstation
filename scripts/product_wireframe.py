#!/usr/bin/env python3
"""Deterministic no-write Product Lane wireframe preview helpers."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from product_prd import PRD_FILENAME
from product_registry import ACTION_LOG_FILENAME, PRODUCT_FILENAME, get_product_status, product_dir, save_product, validate_product_id
from product_scope_lock import SCOPE_LOCK_FILENAME, compute_scope_lock_hash


SCOPE_LOCKED_STATE = "SCOPE_LOCKED"
APPROVED_STATUS = "APPROVED"
TODO_UNKNOWN = "TODO/UNKNOWN"
UI_PRODUCT_TYPES = {"website", "webapp", "dashboard"}
NON_UI_PRODUCT_MESSAGE = (
    "Wireframe preview is not applicable for this product type; use future "
    "product-tech-plan --dry-run."
)
WIREFRAME_ACTION_CONFIRM = "ws product-wireframe --confirm"
WIREFRAMES_DIR = "wireframes"
WIREFRAME_V1_FILENAME = "wireframe_v1.md"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


SECTION_HEADER_RE = re.compile(r"^##\s+(.*)$")


def _safe_child(base: Path, child: Path) -> Path:
    base_resolved = base.resolve()
    child_resolved = child.resolve()
    if child_resolved == base_resolved:
        return child_resolved
    if base_resolved not in child_resolved.parents:
        raise ValueError(f"path escapes expected base: {child_resolved} not under {base_resolved}")
    return child_resolved


def _clean_lines(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = value.strip()
        if not item:
            continue
        if item.startswith("- "):
            item = item[2:].strip()
        if not item:
            continue
        if item in seen:
            continue
        cleaned.append(item)
        seen.add(item)
    return cleaned


def _section_values(sections: dict[str, list[str]], section_name: str, *, fallback: str = TODO_UNKNOWN) -> list[str]:
    values = _clean_lines(list(sections.get(section_name, [])))
    return values if values else [fallback]


def _first_or_unknown(values: list[str]) -> str:
    for value in values:
        if value and value != TODO_UNKNOWN:
            return value
    return TODO_UNKNOWN


def classify_product_ui_type(product_record: dict[str, Any]) -> str | None:
    product_type = str(product_record.get("product_type", "")).strip().lower()
    if product_type in UI_PRODUCT_TYPES:
        return product_type
    return None


def extract_prd_sections(prd_text: str) -> dict[str, list[str]]:
    if not isinstance(prd_text, str) or not prd_text.strip():
        raise ValueError("prd text must contain non-empty text")

    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in prd_text.splitlines():
        stripped = raw_line.strip()
        header = SECTION_HEADER_RE.match(stripped)
        if header:
            current = header.group(1).strip()
            sections.setdefault(current, [])
            continue
        if current is None:
            continue
        if not stripped:
            continue
        sections[current].append(stripped)
    return sections


def _wireframe_template_for_type(product_type: str) -> list[tuple[str, str, list[str]]]:
    if product_type == "website":
        return [
            (
                "Home",
                "Primary entry page",
                [
                    "+------------------------------------------------------------+",
                    "| Header: [Logo] [Primary Nav] [CTA]                         |",
                    "|------------------------------------------------------------|",
                    "| Hero: Value proposition / key message                      |",
                    "|------------------------------------------------------------|",
                    "| Featured Projects Grid                                     |",
                    "|------------------------------------------------------------|",
                    "| About Snapshot | Contact CTA                               |",
                    "|------------------------------------------------------------|",
                    "| Footer: Links / social / resume                            |",
                    "+------------------------------------------------------------+",
                ],
            ),
            (
                "Projects",
                "Portfolio listing",
                [
                    "+------------------------------------------------------------+",
                    "| Header + Filters/Sort                                      |",
                    "|------------------------------------------------------------|",
                    "| Project Card Grid (title, short summary, tags)             |",
                    "|------------------------------------------------------------|",
                    "| Pagination / Load More                                     |",
                    "+------------------------------------------------------------+",
                ],
            ),
            (
                "Project Detail",
                "Case-study page",
                [
                    "+------------------------------------------------------------+",
                    "| Breadcrumbs | Project Title                                |",
                    "|------------------------------------------------------------|",
                    "| Problem | Approach | Outcome                               |",
                    "|------------------------------------------------------------|",
                    "| Media / screenshots / artifacts                             |",
                    "|------------------------------------------------------------|",
                    "| Related Projects | Next Project CTA                         |",
                    "+------------------------------------------------------------+",
                ],
            ),
            (
                "About",
                "Author narrative",
                [
                    "+------------------------------------------------------------+",
                    "| Header                                                     |",
                    "|------------------------------------------------------------|",
                    "| Bio / Experience summary                                   |",
                    "|------------------------------------------------------------|",
                    "| Skills / Timeline / Principles                             |",
                    "|------------------------------------------------------------|",
                    "| Contact CTA                                                |",
                    "+------------------------------------------------------------+",
                ],
            ),
            (
                "Contact / Resume",
                "Reach-out and resume access",
                [
                    "+------------------------------------------------------------+",
                    "| Header                                                     |",
                    "|------------------------------------------------------------|",
                    "| Contact methods / form (if applicable)                     |",
                    "|------------------------------------------------------------|",
                    "| Resume download / profile links                            |",
                    "+------------------------------------------------------------+",
                ],
            ),
        ]

    if product_type == "dashboard":
        return [
            (
                "Overview",
                "High-level metrics",
                [
                    "+------------------------------------------------------------+",
                    "| Header: product context + date range                        |",
                    "|------------------------------------------------------------|",
                    "| KPI cards row                                               |",
                    "|------------------------------------------------------------|",
                    "| Main visualization area                                     |",
                    "|------------------------------------------------------------|",
                    "| Notes / updates panel                                       |",
                    "+------------------------------------------------------------+",
                ],
            ),
            (
                "Filters / Controls",
                "Interactive controls",
                [
                    "+------------------------------------------------------------+",
                    "| Filter bar: segment, date, metric, reset                    |",
                    "|------------------------------------------------------------|",
                    "| Applied filter chips                                        |",
                    "|------------------------------------------------------------|",
                    "| Control presets / save view                                 |",
                    "+------------------------------------------------------------+",
                ],
            ),
            (
                "Main Visualization Area",
                "Primary analysis zone",
                [
                    "+------------------------------------------------------------+",
                    "| Chart/Table switch                                          |",
                    "|------------------------------------------------------------|",
                    "| Visualization canvas                                        |",
                    "|------------------------------------------------------------|",
                    "| Legend / annotations                                        |",
                    "+------------------------------------------------------------+",
                ],
            ),
            (
                "Detail / Drilldown",
                "Focused item detail",
                [
                    "+------------------------------------------------------------+",
                    "| Selected item context                                       |",
                    "|------------------------------------------------------------|",
                    "| Drilldown metrics + trend                                   |",
                    "|------------------------------------------------------------|",
                    "| Related entities/activity                                   |",
                    "+------------------------------------------------------------+",
                ],
            ),
            (
                "Export / Notes Area",
                "Share and annotation zone",
                [
                    "+------------------------------------------------------------+",
                    "| Export options (CSV/PDF/Image TODO/UNKNOWN)                |",
                    "|------------------------------------------------------------|",
                    "| Analyst notes / comments                                    |",
                    "|------------------------------------------------------------|",
                    "| Audit trail / last updated                                  |",
                    "+------------------------------------------------------------+",
                ],
            ),
        ]

    return [
        (
            "Landing / Entry",
            "Starting context",
            [
                "+------------------------------------------------------------+",
                "| Header + value statement                                    |",
                "|------------------------------------------------------------|",
                "| Entry CTA / sign-in / start workflow                        |",
                "|------------------------------------------------------------|",
                "| Supporting context                                           |",
                "+------------------------------------------------------------+",
            ],
        ),
        (
            "Main Workflow",
            "Core flow execution",
            [
                "+------------------------------------------------------------+",
                "| Step navigation / progress                                   |",
                "|------------------------------------------------------------|",
                "| Primary form/task area                                       |",
                "|------------------------------------------------------------|",
                "| Validation / action controls                                 |",
                "+------------------------------------------------------------+",
            ],
        ),
        (
            "Item Detail",
            "Focused record/item page",
            [
                "+------------------------------------------------------------+",
                "| Item header + status                                         |",
                "|------------------------------------------------------------|",
                "| Detail sections                                              |",
                "|------------------------------------------------------------|",
                "| Related actions/history                                      |",
                "+------------------------------------------------------------+",
            ],
        ),
        (
            "Settings / Account",
            "Configuration and preferences",
            [
                "+------------------------------------------------------------+",
                "| Account summary                                              |",
                "|------------------------------------------------------------|",
                "| Preferences / security / integrations                        |",
                "+------------------------------------------------------------+",
            ],
        ),
        (
            "Empty/Error States",
            "Fallback and failure handling",
            [
                "+------------------------------------------------------------+",
                "| Empty state illustration/message TODO/UNKNOWN               |",
                "|------------------------------------------------------------|",
                "| Error state guidance + retry                                 |",
                "+------------------------------------------------------------+",
            ],
        ),
    ]


def infer_wireframe_pages(product_record: dict[str, Any], prd_text: str) -> list[dict[str, Any]]:
    del prd_text  # Pages are deterministic by supported UI product type in this slice.
    ui_type = classify_product_ui_type(product_record)
    if ui_type is None:
        raise ValueError(NON_UI_PRODUCT_MESSAGE)

    pages: list[dict[str, Any]] = []
    for name, purpose, ascii_lines in _wireframe_template_for_type(ui_type):
        pages.append({"name": name, "purpose": purpose, "ascii": ascii_lines})
    return pages


def validate_wireframe_preconditions(root: str | Path, product_id: str) -> dict[str, Any]:
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")

    product_record = get_product_status(root, product_id)
    pdir = product_dir(root, product_id)

    state = str(product_record.get("state", "")).strip()
    if state != SCOPE_LOCKED_STATE:
        raise ValueError(
            f"product must be in {SCOPE_LOCKED_STATE} for wireframe preview (found {state or 'UNKNOWN'})"
        )

    prd_status = str(product_record.get("prd_status", "")).strip().upper()
    stale_artifacts = list(product_record.get("stale_artifacts", []) or [])
    active_prd = str(product_record.get("active_prd", "")).strip()
    
    current_prd_stale = (not active_prd and PRD_FILENAME in stale_artifacts) or (prd_status in {"NEEDS_REVISION", "STALE"})
    if current_prd_stale:
         raise ValueError("Current PRD is stale or needs revision. Approve a revised PRD first.")

    if prd_status != APPROVED_STATUS:
        raise ValueError(
            f"wireframe preview requires prd_status={APPROVED_STATUS} (found {prd_status or 'UNSET'})"
        )

    # 1. Determine Scope Source
    active_scope_lock = str(product_record.get("active_scope_lock", "")).strip()
    if active_scope_lock:
        scope_source = "active_scope_lock"
        scope_path = _safe_child(pdir, pdir / active_scope_lock)
        scope_display_path = active_scope_lock
        scope_hash_expected = product_record.get("active_scope_lock_hash")
    else:
        scope_source = "legacy_scope_lock"
        scope_path = _safe_child(pdir, pdir / SCOPE_LOCK_FILENAME)
        scope_display_path = SCOPE_LOCK_FILENAME
        scope_hash_expected = product_record.get("scope_lock_hash")

    if not scope_path.is_file():
        raise FileNotFoundError(f"Scope lock file not found: {scope_path}")
    
    if not scope_hash_expected:
        raise ValueError(f"Scope lock hash is missing in product.yaml for {scope_source}")

    scope_hash_expected = str(scope_hash_expected).strip()
    scope_text = scope_path.read_text(encoding="utf-8")
    actual_scope_hash = compute_scope_lock_hash(scope_text)
    if actual_scope_hash != scope_hash_expected:
        raise ValueError(f"Scope lock hash mismatch for {scope_source}")

    # 2. Determine PRD Source
    if active_prd:
        prd_source = "active_prd"
        prd_path = _safe_child(pdir, pdir / active_prd)
        prd_display_path = active_prd
        prd_hash_expected = product_record.get("active_prd_hash")
    else:
        prd_source = "legacy_prd"
        prd_path = _safe_child(pdir, pdir / PRD_FILENAME)
        prd_display_path = PRD_FILENAME
        prd_hash_expected = "" # Legacy PRD might not have a hash in some versions

    if not prd_path.is_file():
        raise FileNotFoundError(f"PRD file not found: {prd_path}")
    
    prd_text = prd_path.read_text(encoding="utf-8")
    prd_hash_status = "UNSET"
    if prd_hash_expected:
        prd_hash_expected = str(prd_hash_expected).strip()
        actual_prd_hash = hashlib.sha256(prd_text.encode("utf-8")).hexdigest()
        if actual_prd_hash != prd_hash_expected:
            raise ValueError(f"PRD hash mismatch for {prd_source}")
        prd_hash_status = "MATCH"

    ui_type = classify_product_ui_type(product_record)
    if ui_type is None:
        raise ValueError(NON_UI_PRODUCT_MESSAGE)

    return {
        "product_record": product_record,
        "product_dir": pdir,
        "ui_type": ui_type,
        "prd_source": prd_source,
        "prd_path": prd_path,
        "prd_display_path": prd_display_path,
        "prd_text": prd_text,
        "prd_hash_status": prd_hash_status,
        "scope_source": scope_source,
        "scope_path": scope_path,
        "scope_display_path": scope_display_path,
        "scope_text": scope_text,
        "scope_hash_status": "MATCH",
        "prd_status": prd_status,
        "current_prd_stale": current_prd_stale,
    }


def load_wireframe_inputs(root: str | Path, product_id: str) -> dict[str, Any]:
    return validate_wireframe_preconditions(root, product_id)


def render_wireframe_preview(
    product_record: dict[str, Any],
    scope_lock_text: str,
    prd_text: str,
    *,
    payload_extras: dict[str, Any] | None = None,
) -> str:
    del scope_lock_text  # Scope lock integrity preconditions are checked before rendering.

    product_id = str(product_record.get("product_id", "")).strip()
    product_type = str(product_record.get("product_type", "")).strip()
    label = str(product_record.get("label", "")).strip() or product_id or TODO_UNKNOWN
    state = str(product_record.get("state", "")).strip() or "UNKNOWN"
    
    payload_extras = payload_extras or {}
    prd_status = payload_extras.get("prd_status") or str(product_record.get("prd_status", "")).strip() or "UNSET"
    current_prd_stale = payload_extras.get("current_prd_stale", False)
    prd_source = payload_extras.get("prd_source", "legacy_prd")
    prd_display_path = payload_extras.get("prd_display_path", PRD_FILENAME)
    prd_hash_status = payload_extras.get("prd_hash_status", "UNSET")
    scope_source = payload_extras.get("scope_source", "legacy_scope_lock")
    scope_display_path = payload_extras.get("scope_display_path", SCOPE_LOCK_FILENAME)
    scope_hash_status = payload_extras.get("scope_hash_status", "UNSET")

    ui_type = classify_product_ui_type(product_record)
    if ui_type is None:
        raise ValueError(NON_UI_PRODUCT_MESSAGE)

    prd_sections = extract_prd_sections(prd_text)
    goals = _section_values(prd_sections, "Goals")
    audiences = _section_values(prd_sections, "Target Users / Audience")
    in_scope = _section_values(prd_sections, "In Scope")
    constraints = _section_values(prd_sections, "Constraints")
    success = _section_values(prd_sections, "Success Criteria")
    open_questions = _section_values(prd_sections, "Open Questions At Lock")

    assumptions = [
        f"Primary goal: {_first_or_unknown(goals)}",
        f"Primary audience: {_first_or_unknown(audiences)}",
        f"Scope focus: {_first_or_unknown(in_scope)}",
        f"Constraint: {_first_or_unknown(constraints)}",
        f"Success signal: {_first_or_unknown(success)}",
    ]

    pages = infer_wireframe_pages(product_record, prd_text)

    component_inventory = [
        "Global header/navigation",
        "Primary content area",
        "Section-level calls to action",
        "Supporting metadata/context blocks",
        "Footer or utility region",
        "Error/empty state treatment",
    ]

    navigation_model = [
        "Top-level navigation between primary screens/pages",
        "Contextual links from list/overview to detail",
        "Return paths (breadcrumbs/back action)",
        "Direct entry handling for deep links",
    ]

    content_hierarchy = [
        "Level 1: Core value/intent framing",
        "Level 2: Primary workflow or key content",
        "Level 3: Supporting evidence/details",
        "Level 4: Secondary utilities and metadata",
    ]

    responsive_notes = [
        "Desktop-first multi-column layouts collapse to single column on small screens.",
        "Navigation reduces to compact menu on narrow widths.",
        "Dense modules (grids/charts/tables) need stacked fallback.",
    ]

    accessibility_notes = [
        "Ensure semantic landmarks (header/main/nav/footer).",
        "Keyboard focus order must follow visual reading order.",
        "Color contrast and non-color state indicators required.",
        "Interactive controls require explicit labels and states.",
    ]

    lines: list[str] = [
        "Wireframe Preview",
        "=================",
        "",
        "DRY RUN - no files written.",
        "No product state changes.",
        "No model/provider/agent calls.",
        "",
        "Product Metadata:",
        f"- product_id: {product_id}",
        f"- product_type: {product_type}",
        f"- label/title: {label}",
        f"- product_state: {state}",
        f"- prd_status: {prd_status}",
        f"- current_prd_stale: {current_prd_stale}",
        "",
        "Artifact Sources:",
        f"- prd_source: {prd_source}",
        f"- prd_path: {prd_display_path}",
        f"- prd_hash_status: {prd_hash_status}",
        f"- scope_source: {scope_source}",
        f"- scope_path: {scope_display_path}",
        f"- scope_hash_status: {scope_hash_status}",
        "",
        "Design Assumptions (from PRD):",
    ]

    lines.extend(f"- {item}" for item in assumptions)

    lines.extend(["", "## Page/Screen Map", ""])
    for index, page in enumerate(pages, start=1):
        lines.append(f"- {index}. {page['name']}: {page['purpose']}")

    lines.extend(["", "## ASCII/Text Wireframes", ""])
    for page in pages:
        lines.append("")
        lines.append(f"### {page['name']}")
        lines.extend(page["ascii"])

    lines.extend(["", "## Component Inventory", ""])
    lines.extend(f"- {item}" for item in component_inventory)

    lines.extend(["", "## Navigation Model", ""])
    lines.extend(f"- {item}" for item in navigation_model)

    lines.extend(["", "## Content Hierarchy", ""])
    lines.extend(f"- {item}" for item in content_hierarchy)

    lines.extend(["", "## Responsive Notes", ""])
    lines.extend(f"- {item}" for item in responsive_notes)

    lines.extend(["", "## Accessibility Notes", ""])
    lines.extend(f"- {item}" for item in accessibility_notes)

    lines.extend(["", "## Unresolved Design Questions", ""])
    lines.extend(f"- {item}" for item in open_questions)

    lines.extend(
        [
            "",
            "## Generated From",
            "",
            "- product.yaml",
            f"- {prd_display_path}",
            f"- {scope_display_path}",
            "",
            "Next Step:",
            "- future ws product-wireframe --confirm (not implemented in Phase 2 Slice 4)",
        ]
    )

    if ui_type in UI_PRODUCT_TYPES:
        lines.append("- future ws product-ux-spec --dry-run")
    lines.append("- future ws product-tech-plan --dry-run")

    return "\n".join(lines)


def confirm_wireframe(root: str | Path, product_id: str, *, confirm: bool) -> dict[str, Any]:
    if not confirm:
        raise PermissionError("confirm_wireframe requires explicit confirm=True")

    payload = load_wireframe_inputs(root, product_id)
    product_record = payload["product_record"]
    pdir = payload["product_dir"]
    
    artifact_dir = pdir / WIREFRAMES_DIR
    artifact_path = artifact_dir / WIREFRAME_V1_FILENAME
    
    if artifact_path.exists():
        raise FileExistsError(f"Wireframe artifact already exists: {artifact_path}")
    
    artifact_dir.mkdir(parents=True, exist_ok=True)
    
    preview_text = render_wireframe_preview(
        product_record,
        payload["scope_text"],
        payload["prd_text"],
        payload_extras=payload,
    )
    lines: list[str] = []
    for raw_line in preview_text.splitlines():
        line = raw_line
        if line == "Wireframe Preview":
            line = f"# Wireframe v1: {product_record.get('label') or product_id}"
        elif line == "=================":
            continue
        elif line == "DRY RUN - no files written.":
            continue
        elif line == "No product state changes.":
            continue
        elif line.startswith("- future ws product-wireframe --confirm"):
            line = f"- Generated by `{WIREFRAME_ACTION_CONFIRM}`"
        lines.append(line)
    wireframe_text = "\n".join(lines).rstrip() + "\n"
    artifact_path.write_text(wireframe_text, encoding="utf-8", newline="\n")
    
    wireframe_hash = hashlib.sha256(wireframe_text.encode("utf-8")).hexdigest()
    timestamp = _utc_now_iso()
    
    updated_record = dict(product_record)
    updated_record["active_wireframe"] = f"{WIREFRAMES_DIR}/{WIREFRAME_V1_FILENAME}"
    updated_record["active_wireframe_hash"] = wireframe_hash
    updated_record["active_wireframe_revision"] = 1
    updated_record["wireframe_status"] = "DRAFTED"
    updated_record["wireframe_created_at"] = timestamp
    updated_record["wireframe_reviewed_at"] = None
    updated_record["wireframe_approved_at"] = None
    updated_record["last_action"] = WIREFRAME_ACTION_CONFIRM
    updated_record["updated_at"] = timestamp
    
    product_file = save_product(updated_record, root, confirm=True, allow_overwrite=True)
    
    action_log = _safe_child(pdir, pdir / ACTION_LOG_FILENAME)
    if action_log.is_file():
        with action_log.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(f"- {timestamp} Wireframe drafted via {WIREFRAME_ACTION_CONFIRM}\n")
            
    files_written = [str(artifact_path), str(product_file)]
    if action_log.is_file():
        files_written.append(str(action_log))
        
    return {
        "product_id": product_id,
        "wireframe_path": str(artifact_path),
        "product_file": str(product_file),
        "active_wireframe_hash": wireframe_hash,
        "wireframe_created_at": timestamp,
        "files_written": files_written,
        "used_model_provider_agent": False,
    }

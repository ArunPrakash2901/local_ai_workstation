#!/usr/bin/env python3
"""Deterministic no-write Product Lane design adapter helpers."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from product_registry import get_product_status, product_dir, validate_product_id
from product_scope_lock import compute_scope_lock_hash
from product_wireframe_review import review_wireframe_text, validate_wireframe_review_preconditions


SUPPORTED_DESIGN_TOOLS = ("open-design",)
UI_CAPABLE_PRODUCT_TYPES = {"website", "webapp", "dashboard"}
READY_STATUS = "READY_FOR_DESIGN_RENDER_PREVIEW"
RENDER_READY_STATUS = "READY_FOR_DESIGN_RENDER_DRY_RUN"
DESIGN_PREVIEW_ACTION = "ws product-design-adapter-preview --product <product_id> --tool open-design --dry-run"
DESIGN_RENDER_ACTION = "ws product-design-render --product <product_id> --tool open-design --dry-run"
DESIGN_SLASH_COMMAND = "/design"
DESIGN_RENDER_SLASH_COMMAND = "/design render"
PLANNED_ADAPTER_RUN_ID = "open-design-preview-v1"
PLANNED_RENDER_RUN_ID = "open-design-render-v1"
PLANNED_RUN_ID = PLANNED_ADAPTER_RUN_ID

PLANNED_FUTURE_FILES = (
    "design_input.yaml",
    "design_prompt.md",
    "design_run.yaml",
    "raw_output/",
    "prototype/",
    "screenshots/",
    "export/",
    "validation.md",
    "operator_report.md",
)

PLANNED_RENDER_FILES = (
    "design_input.yaml",
    "design_prompt.md",
    "design_run.yaml",
    "validation.md",
    "operator_report.md",
)

PLANNED_RENDER_OUTPUT_FOLDERS = (
    "raw_output/",
    "prototype/",
    "screenshots/",
    "export/",
)

FORBIDDEN_FUTURE_ACTIONS = (
    "no direct writes to src/",
    "no direct writes to app/",
    "no direct writes to components/",
    "no package.json changes",
    "no deployment/build commands",
)

FORBIDDEN_FUTURE_PATHS = (
    "src/",
    "app/",
    "components/",
    "package.json",
)

TOOL_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")


def _safe_child(base: Path, child: Path) -> Path:
    base_resolved = base.resolve()
    child_resolved = child.resolve()
    if child_resolved == base_resolved:
        return child_resolved
    if base_resolved not in child_resolved.parents:
        raise ValueError(f"path escapes expected base: {child_resolved} not under {base_resolved}")
    return child_resolved


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_text(path.read_text(encoding="utf-8"))


def _tool_dirname(tool: str) -> str:
    return tool.replace("-", "_")


def _hash_status(actual: str | None, expected: str | None) -> str:
    if not expected:
        return "UNSET"
    if not actual:
        return "MISSING"
    return "MATCH" if actual == expected else "MISMATCH"


def get_supported_design_tools() -> tuple[str, ...]:
    return SUPPORTED_DESIGN_TOOLS


def validate_design_tool(tool: str) -> str:
    if not isinstance(tool, str) or not tool.strip():
        raise ValueError("design tool must be a non-empty string")
    normalized = tool.strip().lower()
    if any(token in normalized for token in ("..", "/", "\\")):
        raise ValueError(f"invalid design tool path token: {tool!r}")
    if not TOOL_SLUG_RE.fullmatch(normalized):
        raise ValueError(f"invalid design tool name: {tool!r}")
    if normalized not in SUPPORTED_DESIGN_TOOLS:
        raise ValueError(
            f"unsupported design tool: {tool!r}. supported tools: {', '.join(SUPPORTED_DESIGN_TOOLS)}"
        )
    return normalized


def build_design_run_id(product_record: dict[str, Any], tool: str, *, mode: str = "preview") -> str:
    _ = product_record
    _ = tool
    if mode == "render":
        return PLANNED_RENDER_RUN_ID
    return PLANNED_ADAPTER_RUN_ID


def planned_design_run_dir(product_root: Path, tool: str, run_id: str) -> Path:
    return _safe_child(product_root, product_root / "design_runs" / _tool_dirname(tool) / run_id)


def load_design_adapter_inputs(root: str | Path, product_id: str, tool: str) -> dict[str, Any]:
    if not validate_product_id(str(product_id)):
        raise ValueError(f"invalid product_id: {product_id!r}")
    validated_tool = validate_design_tool(tool)
    root_path = Path(root).expanduser().resolve()
    product_record = get_product_status(root_path, str(product_id))
    product_root = product_dir(root_path, str(product_id))

    product_type = str(product_record.get("product_type", "")).strip()
    prd_status = str(product_record.get("prd_status", "")).strip().upper()
    label = str(product_record.get("label", "")).strip() or str(product_id)

    active_scope_lock = str(product_record.get("active_scope_lock", "")).strip()
    active_scope_lock_hash = str(product_record.get("active_scope_lock_hash", "")).strip()
    active_prd = str(product_record.get("active_prd", "")).strip()
    active_prd_hash = str(product_record.get("active_prd_hash", "")).strip()
    active_wireframe = str(product_record.get("active_wireframe", "")).strip()
    active_wireframe_hash = str(product_record.get("active_wireframe_hash", "")).strip()
    active_technical_plan = str(product_record.get("active_technical_plan", "")).strip()
    active_technical_plan_hash = str(product_record.get("active_technical_plan_hash", "")).strip()

    scope_path = _safe_child(product_root, product_root / active_scope_lock) if active_scope_lock else None
    prd_path = _safe_child(product_root, product_root / active_prd) if active_prd else None
    wireframe_path = _safe_child(product_root, product_root / active_wireframe) if active_wireframe else None
    tech_path = _safe_child(product_root, product_root / active_technical_plan) if active_technical_plan else None

    scope_actual_hash = compute_scope_lock_hash(scope_path.read_text(encoding="utf-8")) if scope_path and scope_path.is_file() else None
    prd_actual_hash = _sha256_file(prd_path) if prd_path and prd_path.is_file() else None
    wireframe_actual_hash = _sha256_file(wireframe_path) if wireframe_path and wireframe_path.is_file() else None
    tech_actual_hash = _sha256_file(tech_path) if tech_path and tech_path.is_file() else None

    return {
        "root": root_path,
        "product_id": str(product_id),
        "product_record": product_record,
        "product_root": product_root,
        "product_type": product_type,
        "label": label,
        "tool": validated_tool,
        "prd_status": prd_status,
        "active_scope_lock": active_scope_lock,
        "active_scope_lock_hash": active_scope_lock_hash,
        "active_prd": active_prd,
        "active_prd_hash": active_prd_hash,
        "active_wireframe": active_wireframe,
        "active_wireframe_hash": active_wireframe_hash,
        "active_technical_plan": active_technical_plan,
        "active_technical_plan_hash": active_technical_plan_hash,
        "scope_path": scope_path,
        "prd_path": prd_path,
        "wireframe_path": wireframe_path,
        "tech_path": tech_path,
        "scope_hash_status": _hash_status(scope_actual_hash, active_scope_lock_hash),
        "prd_hash_status": _hash_status(prd_actual_hash, active_prd_hash),
        "wireframe_hash_status": _hash_status(wireframe_actual_hash, active_wireframe_hash),
        "tech_hash_status": _hash_status(tech_actual_hash, active_technical_plan_hash),
    }


def validate_design_adapter_preconditions(
    root: str | Path,
    product_id: str,
    tool: str,
    *,
    context_label: str = "design adapter preview",
    run_mode: str = "preview",
) -> dict[str, Any]:
    payload = load_design_adapter_inputs(root, product_id, tool)

    if payload["product_type"] not in UI_CAPABLE_PRODUCT_TYPES:
        raise ValueError(
            f"product type is not UI-capable for {context_label}: "
            f"{payload['product_type']!r}. supported: {', '.join(sorted(UI_CAPABLE_PRODUCT_TYPES))}"
        )
    if payload["prd_status"] != "APPROVED":
        raise ValueError(f"prd_status must be APPROVED for {context_label} (found {payload['prd_status']!r})")

    if not payload["active_scope_lock"]:
        raise ValueError("missing active_scope_lock metadata")
    if payload["scope_path"] is None or not payload["scope_path"].is_file():
        raise FileNotFoundError(f"active_scope_lock file missing: {payload['active_scope_lock']}")
    if payload["scope_hash_status"] != "MATCH":
        raise ValueError(f"active_scope_lock hash mismatch ({payload['scope_hash_status']})")

    if not payload["active_prd"]:
        raise ValueError("missing active_prd metadata")
    if payload["prd_path"] is None or not payload["prd_path"].is_file():
        raise FileNotFoundError(f"active_prd file missing: {payload['active_prd']}")
    if payload["prd_hash_status"] != "MATCH":
        raise ValueError(f"active_prd hash mismatch ({payload['prd_hash_status']})")

    if not payload["active_wireframe"]:
        raise ValueError("missing active_wireframe metadata")
    if payload["wireframe_path"] is None or not payload["wireframe_path"].is_file():
        raise FileNotFoundError(f"active_wireframe file missing: {payload['active_wireframe']}")
    if payload["wireframe_hash_status"] != "MATCH":
        raise ValueError(f"active_wireframe hash mismatch ({payload['wireframe_hash_status']})")

    review_payload = validate_wireframe_review_preconditions(payload["root"], payload["product_id"])
    review_result = review_wireframe_text(
        payload["product_record"],
        review_payload["wireframe_text"],
        payload_extras=review_payload,
    )
    payload["wireframe_review_status"] = review_result.get("status", "FAIL")
    payload["wireframe_review"] = review_result
    if payload["wireframe_review_status"] != "PASS":
        raise ValueError(
            f"wireframe review status must be PASS for {context_label} "
            f"(found {payload['wireframe_review_status']})"
        )

    run_id = build_design_run_id(payload["product_record"], payload["tool"], mode=run_mode)
    payload["planned_run_id"] = run_id
    payload["planned_run_dir"] = planned_design_run_dir(payload["product_root"], payload["tool"], run_id)
    return payload


def build_design_adapter_preview(root: str | Path, product_id: str, tool: str) -> dict[str, Any]:
    payload = validate_design_adapter_preconditions(
        root,
        product_id,
        tool,
        context_label="design adapter preview",
        run_mode="preview",
    )
    planned_dir = payload["planned_run_dir"]
    root_path = payload["root"]
    planned_rel = planned_dir.relative_to(root_path).as_posix()
    tool_canonical = payload["tool"]
    tech_present = bool(payload["active_technical_plan"])
    tech_exists = bool(payload["tech_path"] and payload["tech_path"].is_file())

    return {
        "adapter_status": READY_STATUS,
        "product_id": payload["product_id"],
        "product_type": payload["product_type"],
        "label": payload["label"],
        "tool": tool_canonical,
        "slash_command_surface": DESIGN_SLASH_COMMAND,
        "canonical_ws_command": (
            f"ws product-design-adapter-preview --product {payload['product_id']} "
            f"--tool {tool_canonical} --dry-run"
        ),
        "active_scope": {
            "path": payload["active_scope_lock"],
            "hash_status": payload["scope_hash_status"],
        },
        "active_prd": {
            "path": payload["active_prd"],
            "hash_status": payload["prd_hash_status"],
            "approval_status": payload["prd_status"],
        },
        "active_wireframe": {
            "path": payload["active_wireframe"],
            "hash_status": payload["wireframe_hash_status"],
            "review_status": payload["wireframe_review_status"],
        },
        "optional_technical_plan": {
            "present": tech_present,
            "path": payload["active_technical_plan"] if tech_present else None,
            "exists": tech_exists if tech_present else None,
            "hash_status": payload["tech_hash_status"] if tech_present else "NOT_REQUIRED",
            "required": False,
        },
        "planned_design_run_directory": planned_rel,
        "planned_future_files": list(PLANNED_FUTURE_FILES),
        "allowed_future_write_boundary": f"{planned_rel}/",
        "forbidden_future_actions": list(FORBIDDEN_FUTURE_ACTIONS),
        "next_step": "future ws product-design-render --product <id> --tool open-design --confirm",
        "no_write": True,
        "tool_executed": False,
        "tool_installed": False,
    }


def build_design_render_preview(root: str | Path, product_id: str, tool: str) -> dict[str, Any]:
    payload = validate_design_adapter_preconditions(
        root,
        product_id,
        tool,
        context_label="design render preview",
        run_mode="render",
    )
    planned_dir = payload["planned_run_dir"]
    root_path = payload["root"]
    planned_rel = planned_dir.relative_to(root_path).as_posix()
    tool_canonical = payload["tool"]
    tech_present = bool(payload["active_technical_plan"])

    return {
        "readiness_status": RENDER_READY_STATUS,
        "product_id": payload["product_id"],
        "product_type": payload["product_type"],
        "label": payload["label"],
        "tool": tool_canonical,
        "slash_command_surface": DESIGN_RENDER_SLASH_COMMAND,
        "canonical_ws_command": (
            f"ws product-design-render --product {payload['product_id']} "
            f"--tool {tool_canonical} --dry-run"
        ),
        "active_scope": {
            "path": payload["active_scope_lock"],
            "hash_status": payload["scope_hash_status"],
        },
        "active_prd": {
            "path": payload["active_prd"],
            "hash_status": payload["prd_hash_status"],
            "approval_status": payload["prd_status"],
        },
        "active_wireframe": {
            "path": payload["active_wireframe"],
            "hash_status": payload["wireframe_hash_status"],
            "review_status": payload["wireframe_review_status"],
        },
        "optional_technical_plan": {
            "present": tech_present,
            "path": payload["active_technical_plan"] if tech_present else None,
            "hash_status": payload["tech_hash_status"] if tech_present else "NOT_REQUIRED",
            "required": False,
        },
        "planned_run_directory": planned_rel,
        "planned_files": list(PLANNED_RENDER_FILES),
        "planned_output_folders": list(PLANNED_RENDER_OUTPUT_FOLDERS),
        "allowed_future_write_boundary": f"{planned_rel}/",
        "forbidden_paths": list(FORBIDDEN_FUTURE_PATHS),
        "external_execution_status": {
            "open_design_executed": False,
            "install_attempted": False,
        },
        "next_step": "future ws product-design-render --product <id> --tool open-design --confirm",
        "no_write": True,
    }


def render_design_adapter_preview(preview: dict[str, Any]) -> str:
    lines = [
        "# Product Design Adapter Preview",
        "",
        "- DRY RUN / no files written",
        f"- product_id: `{preview['product_id']}`",
        f"- product_type: `{preview['product_type']}`",
        f"- label/title: `{preview['label']}`",
        f"- tool: `{preview['tool']}`",
        f"- adapter_status: `{preview['adapter_status']}`",
        f"- slash command surface: `{preview['slash_command_surface']}`",
        f"- canonical ws command: `{preview['canonical_ws_command']}`",
        "",
        "## Active Scope",
        f"- path: `{preview['active_scope']['path']}`",
        f"- hash status: `{preview['active_scope']['hash_status']}`",
        "",
        "## Active PRD",
        f"- path: `{preview['active_prd']['path']}`",
        f"- hash status: `{preview['active_prd']['hash_status']}`",
        f"- approval status: `{preview['active_prd']['approval_status']}`",
        "",
        "## Active Wireframe",
        f"- path: `{preview['active_wireframe']['path']}`",
        f"- hash status: `{preview['active_wireframe']['hash_status']}`",
        f"- review status: `{preview['active_wireframe']['review_status']}`",
        "",
        "## Optional Technical Plan",
        f"- present: `{preview['optional_technical_plan']['present']}`",
        f"- path: `{preview['optional_technical_plan']['path'] or 'UNSET'}`",
        f"- hash status: `{preview['optional_technical_plan']['hash_status']}`",
        "- required: `false`",
        "",
        f"## Planned Design Run Directory",
        f"- `{preview['planned_design_run_directory']}/`",
        "",
        "## Planned Future Files",
    ]
    for item in preview["planned_future_files"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "## Allowed Future Write Boundary",
            f"- `{preview['allowed_future_write_boundary']}`",
            "",
            "## Forbidden Future Actions",
        ]
    )
    for item in preview["forbidden_future_actions"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Next Step",
            f"- {preview['next_step']}",
            "",
        ]
    )
    return "\n".join(lines)


def render_design_render_preview(preview: dict[str, Any]) -> str:
    lines = [
        "# Product Design Render Preview",
        "",
        "- DRY RUN / no files written",
        f"- slash command surface: `{preview['slash_command_surface']}`",
        f"- canonical ws command: `{preview['canonical_ws_command']}`",
        f"- product_id: `{preview['product_id']}`",
        f"- tool: `{preview['tool']}`",
        f"- readiness status: `{preview['readiness_status']}`",
        "",
        "## Source Artifact Readiness",
        f"- active scope: `{preview['active_scope']['path']}` (`{preview['active_scope']['hash_status']}`)",
        f"- active PRD: `{preview['active_prd']['path']}` (`{preview['active_prd']['hash_status']}`), status `{preview['active_prd']['approval_status']}`",
        f"- active wireframe: `{preview['active_wireframe']['path']}` (`{preview['active_wireframe']['hash_status']}`), review `{preview['active_wireframe']['review_status']}`",
        f"- optional technical plan: `{preview['optional_technical_plan']['path'] or 'UNSET'}` (`{preview['optional_technical_plan']['hash_status']}`), required `false`",
        "",
        "## Planned Run Directory",
        f"- `{preview['planned_run_directory']}/`",
        "",
        "## Planned Files",
    ]
    for item in preview["planned_files"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Planned Output Folders"])
    for item in preview["planned_output_folders"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "## Future Write Boundary",
            f"- `{preview['allowed_future_write_boundary']}`",
            "",
            "## Forbidden Paths",
        ]
    )
    for item in preview["forbidden_paths"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "## External Execution Status",
            f"- Open Design not executed: `{not preview['external_execution_status']['open_design_executed']}`",
            f"- no install attempted: `{not preview['external_execution_status']['install_attempted']}`",
            "",
            "## Next Step",
            f"- {preview['next_step']}",
            "",
        ]
    )
    return "\n".join(lines)

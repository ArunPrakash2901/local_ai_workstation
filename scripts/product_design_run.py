#!/usr/bin/env python3
"""Product Lane design run sandbox prepare/status helpers (no execution)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from product_design_adapter import (
    FORBIDDEN_FUTURE_PATHS,
    PLANNED_RENDER_OUTPUT_FOLDERS,
    build_design_run_id,
    planned_design_run_dir,
    validate_design_adapter_preconditions,
    validate_design_tool,
)
from product_registry import get_product_status, product_dir, validate_product_id


DESIGN_RUN_PREPARE_ACTION = (
    "ws product-design-run-prepare --product <product_id> --tool open-design --confirm"
)
DESIGN_RUN_STATUS_ACTION = "ws product-design-run-status --product <product_id> --tool open-design"
DESIGN_RUN_RENDER_NEXT_ACTION = (
    "future ws product-design-render --product <id> --tool open-design --confirm"
)

DESIGN_PREPARE_SLASH_COMMAND = "/design prepare"
DESIGN_STATUS_SLASH_COMMAND = "/design status"

DESIGN_RUN_FILENAME = "design_run.yaml"
DESIGN_INPUT_FILENAME = "design_input.yaml"
DESIGN_PROMPT_FILENAME = "design_prompt.md"
DESIGN_OPERATOR_REPORT_FILENAME = "operator_report.md"

DESIGN_RUN_STATUS_PREPARED = "PREPARED_NOT_EXECUTED"
DESIGN_RUN_STATUS_NOT_PREPARED = "NOT_PREPARED"
DESIGN_EXECUTION_MODE_NOT_EXECUTED = "NOT_EXECUTED"

SECTION_HEADER_RE = re.compile(r"^##\s+(.*)$")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_child(base: Path, child: Path) -> Path:
    base_resolved = base.resolve()
    child_resolved = child.resolve()
    if child_resolved == base_resolved:
        return child_resolved
    if base_resolved not in child_resolved.parents:
        raise ValueError(f"path escapes expected base: {child_resolved} not under {base_resolved}")
    return child_resolved


def _tool_dirname(tool: str) -> str:
    return tool.replace("-", "_")


def _load_json_or_yaml_like(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore[import-not-found]
        except Exception:
            return {}
        try:
            loaded = yaml.safe_load(text)
        except Exception:
            return {}
        return loaded if isinstance(loaded, dict) else {}
    return data if isinstance(data, dict) else {}


def _extract_section_items(text: str, section_name: str) -> list[str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        header = SECTION_HEADER_RE.match(stripped)
        if header:
            current = header.group(1).strip()
            sections.setdefault(current, [])
            continue
        if current is None:
            continue
        sections[current].append(raw_line)

    items: list[str] = []
    for raw_line in sections.get(section_name, []):
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        items.append(stripped)
    return items


def _summary_or_default(values: list[str], *, default_value: str) -> list[str]:
    if not values:
        return [default_value]
    return values


def _build_design_input_payload(payload: dict[str, Any], *, allowed_write_root: str) -> dict[str, Any]:
    wireframe_text = payload["wireframe_path"].read_text(encoding="utf-8")
    page_map = _summary_or_default(
        _extract_section_items(wireframe_text, "Page/Screen Map"),
        default_value="NOT_SPECIFIED_IN_ACTIVE_WIREFRAME",
    )
    components = _summary_or_default(
        _extract_section_items(wireframe_text, "Component Inventory"),
        default_value="NOT_SPECIFIED_IN_ACTIVE_WIREFRAME",
    )
    accessibility = _summary_or_default(
        _extract_section_items(wireframe_text, "Accessibility Notes"),
        default_value="NOT_SPECIFIED_IN_ACTIVE_WIREFRAME",
    )
    responsive = _summary_or_default(
        _extract_section_items(wireframe_text, "Responsive Notes"),
        default_value="NOT_SPECIFIED_IN_ACTIVE_WIREFRAME",
    )

    product_record = payload["product_record"]
    product_id = payload["product_id"]
    label = str(product_record.get("label", "")).strip() or product_id

    source_artifacts: dict[str, Any] = {
        "active_scope_lock": payload["active_scope_lock"],
        "active_scope_lock_hash": payload["active_scope_lock_hash"],
        "active_prd": payload["active_prd"],
        "active_prd_hash": payload["active_prd_hash"],
        "active_wireframe": payload["active_wireframe"],
        "active_wireframe_hash": payload["active_wireframe_hash"],
    }
    if payload["active_technical_plan"]:
        source_artifacts["active_technical_plan"] = payload["active_technical_plan"]
        source_artifacts["active_technical_plan_hash"] = payload["active_technical_plan_hash"]

    return {
        "product": {
            "product_id": product_id,
            "product_type": payload["product_type"],
            "label": label,
            "title": str(product_record.get("title", "")).strip() or label,
        },
        "design_objective": (
            "Prepare deterministic Open Design inputs aligned to the approved PRD, "
            "active scope lock, and active wireframe without changing product scope."
        ),
        "source_artifacts": source_artifacts,
        "page_screen_map_summary": page_map,
        "component_inventory_summary": components,
        "accessibility_requirements": accessibility,
        "responsive_requirements": responsive,
        "explicit_non_goals": [
            "Do not execute Open Design in this prepare phase.",
            "Do not modify src/, app/, components/, or package.json.",
            "Do not expand scope beyond approved Product Lane artifacts.",
        ],
        "sandbox_write_boundary": allowed_write_root,
    }


def _build_design_prompt_text(payload: dict[str, Any], *, allowed_write_root: str) -> str:
    product_id = payload["product_id"]
    tool = payload["tool"]
    lines = [
        "# Open Design Render Prompt (Prepared, Not Executed)",
        "",
        f"- product_id: `{product_id}`",
        f"- tool: `{tool}`",
        f"- run_id: `{payload['planned_run_id']}`",
        "",
        "## Instructions For Future Render",
        "",
        "- Use only the supplied source artifacts and prepared design_input.yaml context.",
        f"- Keep all generated outputs inside `{allowed_write_root}`.",
        "- Do not write to application/source repositories.",
        "- Preserve approved scope, PRD, and wireframe constraints.",
        "",
        "## Forbidden Paths",
        "",
        "- `src/`",
        "- `app/`",
        "- `components/`",
        "- `package.json`",
        "",
        "## Expected Future Render Output Folders",
        "",
        "- `raw_output/`",
        "- `prototype/`",
        "- `screenshots/`",
        "- `export/`",
        "",
        "This prompt file is prepared by ws product-design-run-prepare and is not executed by this command.",
        "",
    ]
    return "\n".join(lines)


def prepare_design_run(
    root: str | Path,
    product_id: str,
    tool: str,
    *,
    confirm: bool,
    write_operator_report: bool = True,
) -> dict[str, Any]:
    if not confirm:
        raise PermissionError("design run prepare requires explicit --confirm")

    payload = validate_design_adapter_preconditions(
        root,
        product_id,
        tool,
        context_label="design run prepare",
        run_mode="render",
    )
    root_path: Path = payload["root"]
    run_dir: Path = payload["planned_run_dir"]
    run_id = payload["planned_run_id"]

    design_run_path = _safe_child(run_dir, run_dir / DESIGN_RUN_FILENAME)
    design_input_path = _safe_child(run_dir, run_dir / DESIGN_INPUT_FILENAME)
    design_prompt_path = _safe_child(run_dir, run_dir / DESIGN_PROMPT_FILENAME)
    operator_report_path = _safe_child(run_dir, run_dir / DESIGN_OPERATOR_REPORT_FILENAME)

    if design_run_path.exists():
        raise FileExistsError(f"design run already prepared: {design_run_path}")

    run_dir.mkdir(parents=True, exist_ok=True)

    allowed_write_root = f"{run_dir.relative_to(root_path).as_posix()}/"
    created_at = _utc_now_iso()

    source_artifacts: dict[str, Any] = {
        "active_scope_lock": payload["active_scope_lock"],
        "active_scope_lock_hash": payload["active_scope_lock_hash"],
        "active_prd": payload["active_prd"],
        "active_prd_hash": payload["active_prd_hash"],
        "active_wireframe": payload["active_wireframe"],
        "active_wireframe_hash": payload["active_wireframe_hash"],
    }
    if payload["active_technical_plan"]:
        source_artifacts["active_technical_plan"] = payload["active_technical_plan"]
        source_artifacts["active_technical_plan_hash"] = payload["active_technical_plan_hash"]

    design_run_payload: dict[str, Any] = {
        "run_id": run_id,
        "product_id": payload["product_id"],
        "tool": payload["tool"],
        "status": DESIGN_RUN_STATUS_PREPARED,
        "execution_mode": DESIGN_EXECUTION_MODE_NOT_EXECUTED,
        "created_at": created_at,
        "source_artifacts": source_artifacts,
        "allowed_write_root": allowed_write_root,
        "forbidden_paths": list(FORBIDDEN_FUTURE_PATHS),
        "external_calls_policy": "NOT_ALLOWED_IN_PREPARE_PHASE",
        "validation_status": "PREPARED",
        "operator_review_status": "NOT_REVIEWED",
    }
    design_input_payload = _build_design_input_payload(payload, allowed_write_root=allowed_write_root)
    design_prompt_text = _build_design_prompt_text(payload, allowed_write_root=allowed_write_root)

    design_input_path.write_text(
        json.dumps(design_input_payload, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    design_prompt_path.write_text(design_prompt_text, encoding="utf-8", newline="\n")
    design_run_path.write_text(
        json.dumps(design_run_payload, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    files_written: list[str] = [
        run_dir.relative_to(root_path).as_posix() + f"/{DESIGN_INPUT_FILENAME}",
        run_dir.relative_to(root_path).as_posix() + f"/{DESIGN_PROMPT_FILENAME}",
        run_dir.relative_to(root_path).as_posix() + f"/{DESIGN_RUN_FILENAME}",
    ]

    if write_operator_report:
        operator_report_text = "\n".join(
            [
                "# Product Design Run Operator Report",
                "",
                f"- product_id: `{payload['product_id']}`",
                f"- tool: `{payload['tool']}`",
                f"- run_id: `{run_id}`",
                f"- status: `{DESIGN_RUN_STATUS_PREPARED}`",
                f"- execution_mode: `{DESIGN_EXECUTION_MODE_NOT_EXECUTED}`",
                f"- allowed_write_root: `{allowed_write_root}`",
                "- Open Design execution: `not executed`",
                "- Install attempts: `none`",
                "",
            ]
        )
        operator_report_path.write_text(operator_report_text + "\n", encoding="utf-8", newline="\n")
        files_written.append(
            run_dir.relative_to(root_path).as_posix() + f"/{DESIGN_OPERATOR_REPORT_FILENAME}"
        )

    return {
        "product_id": payload["product_id"],
        "tool": payload["tool"],
        "run_id": run_id,
        "status": DESIGN_RUN_STATUS_PREPARED,
        "execution_mode": DESIGN_EXECUTION_MODE_NOT_EXECUTED,
        "allowed_write_root": allowed_write_root,
        "files_written": files_written,
        "open_design_executed": False,
        "open_design_installed": False,
    }


def get_design_run_status(root: str | Path, product_id: str, tool: str) -> dict[str, Any]:
    if not validate_product_id(str(product_id)):
        raise ValueError(f"invalid product_id: {product_id!r}")
    validated_tool = validate_design_tool(tool)
    root_path = Path(root).expanduser().resolve()
    product_record = get_product_status(root_path, str(product_id))
    pdir = product_dir(root_path, str(product_id))
    run_id = build_design_run_id(product_record, validated_tool, mode="render")
    run_dir = planned_design_run_dir(pdir, validated_tool, run_id)
    run_rel = run_dir.relative_to(root_path).as_posix()

    design_run_path = _safe_child(run_dir, run_dir / DESIGN_RUN_FILENAME)
    design_input_path = _safe_child(run_dir, run_dir / DESIGN_INPUT_FILENAME)
    design_prompt_path = _safe_child(run_dir, run_dir / DESIGN_PROMPT_FILENAME)
    operator_report_path = _safe_child(run_dir, run_dir / DESIGN_OPERATOR_REPORT_FILENAME)

    output_presence = {
        name.rstrip("/"): _safe_child(run_dir, run_dir / name.rstrip("/")).exists()
        for name in PLANNED_RENDER_OUTPUT_FOLDERS
    }

    if not design_run_path.is_file():
        return {
            "product_id": str(product_id),
            "tool": validated_tool,
            "run_id": run_id,
            "run_dir": run_rel,
            "design_run_yaml_present": False,
            "design_input_yaml_present": design_input_path.is_file(),
            "design_prompt_md_present": design_prompt_path.is_file(),
            "operator_report_md_present": operator_report_path.is_file(),
            "status": DESIGN_RUN_STATUS_NOT_PREPARED,
            "execution_mode": DESIGN_EXECUTION_MODE_NOT_EXECUTED,
            "allowed_write_root": f"{run_rel}/",
            "source_artifacts": {},
            "output_folder_presence": output_presence,
            "next_command": (
                f"ws product-design-run-prepare --product {product_id} --tool {validated_tool} --confirm"
            ),
            "slash_command_surface": DESIGN_STATUS_SLASH_COMMAND,
            "open_design_executed": False,
            "open_design_installed": False,
            "writes_files": False,
        }

    run_payload = _load_json_or_yaml_like(design_run_path)
    return {
        "product_id": str(product_id),
        "tool": validated_tool,
        "run_id": str(run_payload.get("run_id") or run_id),
        "run_dir": run_rel,
        "design_run_yaml_present": True,
        "design_input_yaml_present": design_input_path.is_file(),
        "design_prompt_md_present": design_prompt_path.is_file(),
        "operator_report_md_present": operator_report_path.is_file(),
        "status": str(run_payload.get("status", DESIGN_RUN_STATUS_PREPARED)),
        "execution_mode": str(run_payload.get("execution_mode", DESIGN_EXECUTION_MODE_NOT_EXECUTED)),
        "allowed_write_root": str(run_payload.get("allowed_write_root", f"{run_rel}/")),
        "source_artifacts": run_payload.get("source_artifacts", {}) if isinstance(run_payload, dict) else {},
        "output_folder_presence": output_presence,
        "next_command": DESIGN_RUN_RENDER_NEXT_ACTION,
        "slash_command_surface": DESIGN_STATUS_SLASH_COMMAND,
        "open_design_executed": bool(run_payload.get("open_design_executed", False)),
        "open_design_installed": False,
        "writes_files": False,
    }


def render_design_run_status(status: dict[str, Any]) -> str:
    lines = [
        "# Product Design Run Status",
        "",
        f"- slash command surface: `{status['slash_command_surface']}`",
        (
            f"- canonical ws command: `ws product-design-run-status --product {status['product_id']} "
            f"--tool {status['tool']}`"
        ),
        f"- product_id: `{status['product_id']}`",
        f"- tool: `{status['tool']}`",
        f"- run_id: `{status['run_id']}`",
        f"- status: `{status['status']}`",
        f"- execution_mode: `{status['execution_mode']}`",
        f"- run directory: `{status['run_dir']}/`",
        "",
        "## Prepared Files",
        f"- design_run.yaml: `{status['design_run_yaml_present']}`",
        f"- design_input.yaml: `{status['design_input_yaml_present']}`",
        f"- design_prompt.md: `{status['design_prompt_md_present']}`",
        f"- operator_report.md: `{status['operator_report_md_present']}`",
        "",
        "## Allowed Write Root",
        f"- `{status['allowed_write_root']}`",
        "",
        "## Source Artifact Hash References",
    ]

    source = status.get("source_artifacts") if isinstance(status.get("source_artifacts"), dict) else {}
    if source:
        for key in (
            "active_scope_lock",
            "active_scope_lock_hash",
            "active_prd",
            "active_prd_hash",
            "active_wireframe",
            "active_wireframe_hash",
            "active_technical_plan",
            "active_technical_plan_hash",
        ):
            if key in source:
                lines.append(f"- {key}: `{source[key]}`")
    else:
        lines.append("- none (run not prepared)")

    lines.extend(["", "## Output Folder Presence"])
    for folder, present in status["output_folder_presence"].items():
        lines.append(f"- {folder}/: `{present}`")

    lines.extend(
        [
            "",
            "## External Execution Status",
            f"- Open Design executed: `{status['open_design_executed']}`",
            f"- Open Design installed: `{status['open_design_installed']}`",
            "",
            "## Next Command",
            f"- {status['next_command']}",
            "",
        ]
    )
    return "\n".join(lines)

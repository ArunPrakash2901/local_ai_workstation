#!/usr/bin/env python3
"""Dry-run Open Design manual install/evaluation checklist preview helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from product_design_adapter import validate_design_tool
from product_design_runtime_probe import probe_design_runtime


INSTALL_CHECKLIST_DOC = "OPEN_DESIGN_MANUAL_INSTALL_EVALUATION_CHECKLIST.md"
INSTALL_CHECKLIST_COMMAND = "ws product-design-install-checklist --tool open-design --dry-run"
INSTALL_CHECKLIST_SLASH_COMMAND = "/design install-check"

STOP_CONDITIONS = (
    "unknown write behavior",
    "unknown external/provider calls",
    "cannot constrain output to allowed_write_root",
    "requires writing into app/source repository paths",
    "requires secrets in unmanaged files",
)


def build_install_checklist_preview(
    root: str | Path,
    tool: str,
    *,
    path_env: str | None = None,
    env: dict[str, str] | None = None,
    which_fn: Callable[..., str | None] | None = None,
) -> dict[str, Any]:
    validated_tool = validate_design_tool(tool)
    root_path = Path(root).expanduser().resolve()
    checklist_path = root_path / INSTALL_CHECKLIST_DOC
    probe = probe_design_runtime(
        root_path,
        validated_tool,
        path_env=path_env,
        env=env,
        which_fn=which_fn,
    )

    if checklist_path.is_absolute():
        checklist_display = checklist_path.as_posix()
    else:
        checklist_display = checklist_path.as_posix()

    return {
        "title": "Product Design Install Checklist Preview",
        "tool": validated_tool,
        "dry_run": True,
        "slash_command_surface": INSTALL_CHECKLIST_SLASH_COMMAND,
        "canonical_ws_command": INSTALL_CHECKLIST_COMMAND,
        "checklist_path": checklist_display,
        "checklist_exists": checklist_path.is_file(),
        "runtime_probe": probe,
        "manual_install_warning": (
            "Manual-only evaluation: this command does not install Open Design, "
            "does not execute Open Design, and does not execute package managers."
        ),
        "stop_conditions": list(STOP_CONDITIONS),
        "next_step": "manually review checklist, then rerun /design probe",
        "writes_files": False,
        "open_design_executed": False,
        "package_manager_executed": False,
    }


def render_install_checklist_preview(preview: dict[str, Any]) -> str:
    probe = preview["runtime_probe"]
    detected = probe["detected_command_paths"]
    lines = [
        "# Product Design Install Checklist Preview",
        "",
        "- DRY RUN / no files written",
        f"- tool: `{preview['tool']}`",
        f"- slash command surface: `{preview['slash_command_surface']}`",
        f"- canonical ws command: `{preview['canonical_ws_command']}`",
        f"- checklist path: `{preview['checklist_path']}`",
        f"- checklist exists: `{preview['checklist_exists']}`",
        "",
        "## Runtime Probe Summary",
        f"- readiness classification: `{probe['readiness_classification']}`",
        f"- open-design: `{detected.get('open-design') or 'NOT_FOUND'}`",
        f"- node: `{detected.get('node') or 'NOT_FOUND'}`",
        f"- pnpm: `{detected.get('pnpm') or 'NOT_FOUND'}`",
        f"- npm: `{detected.get('npm') or 'NOT_FOUND'}`",
        "",
        "## Manual-Only Installation Warning",
        f"- {preview['manual_install_warning']}",
        "",
        "## Stop Conditions",
    ]
    for item in preview["stop_conditions"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Safety Guarantees",
            f"- writes files: `{preview['writes_files']}`",
            f"- Open Design executed: `{preview['open_design_executed']}`",
            f"- package managers executed: `{preview['package_manager_executed']}`",
            "",
            "## Next Step",
            f"- {preview['next_step']}",
            "",
        ]
    )
    return "\n".join(lines)

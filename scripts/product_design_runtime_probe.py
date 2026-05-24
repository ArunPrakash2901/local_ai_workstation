#!/usr/bin/env python3
"""No-write local runtime probe for future Open Design execution readiness."""

from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path
from typing import Any, Callable

from product_design_adapter import validate_design_tool


RUNTIME_PROBE_COMMAND = "ws product-design-runtime-probe --tool open-design --dry-run"
RUNTIME_PROBE_SLASH_COMMAND = "/design probe"
RUNTIME_REPORT_COMMAND = "ws product-design-runtime-report --tool open-design --dry-run"
RUNTIME_REPORT_SLASH_COMMAND = "/design runtime"

RUNTIME_NOT_FOUND = "RUNTIME_NOT_FOUND"
PARTIAL_RUNTIME_FOUND = "PARTIAL_RUNTIME_FOUND"
RUNTIME_CANDIDATE_FOUND = "RUNTIME_CANDIDATE_FOUND"

PROBE_COMMAND_NAMES = ("open-design", "od", "node", "pnpm", "npm")
ENV_VAR_HINTS = (
    "OPEN_DESIGN_HOME",
    "OPEN_DESIGN_CONFIG",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "OPENROUTER_API_KEY",
)
DEFAULT_PACKET_PRODUCT_ID = "portfolio-website-redesign"
DEFAULT_PACKET_RUN_ID = "open-design-render-v1"


def classify_runtime_readiness(command_paths: dict[str, str | None]) -> str:
    open_design_found = bool(command_paths.get("open-design"))
    od_found = bool(command_paths.get("od"))
    node_found = bool(command_paths.get("node"))
    package_manager_found = bool(command_paths.get("pnpm") or command_paths.get("npm"))
    any_found = any(command_paths.get(name) for name in PROBE_COMMAND_NAMES)

    if not any_found:
        return RUNTIME_NOT_FOUND
    if open_design_found and node_found and package_manager_found:
        return RUNTIME_CANDIDATE_FOUND
    if od_found and not open_design_found:
        return PARTIAL_RUNTIME_FOUND
    return PARTIAL_RUNTIME_FOUND


def _prepared_packet_probe(root: Path) -> dict[str, Any]:
    run_dir = (
        root
        / "products"
        / DEFAULT_PACKET_PRODUCT_ID
        / "design_runs"
        / "open_design"
        / DEFAULT_PACKET_RUN_ID
    )
    required_files = ("design_run.yaml", "design_input.yaml", "design_prompt.md")
    optional_files = ("operator_report.md",)

    return {
        "product_id": DEFAULT_PACKET_PRODUCT_ID,
        "run_id": DEFAULT_PACKET_RUN_ID,
        "run_dir": run_dir.relative_to(root).as_posix() if run_dir.exists() else run_dir.as_posix(),
        "run_dir_present": run_dir.is_dir(),
        "required_file_presence": {
            name: (run_dir / name).is_file() for name in required_files
        },
        "optional_file_presence": {
            name: (run_dir / name).is_file() for name in optional_files
        },
    }


def probe_design_runtime(
    root: str | Path,
    tool: str,
    *,
    path_env: str | None = None,
    env: dict[str, str] | None = None,
    which_fn: Callable[..., str | None] | None = None,
) -> dict[str, Any]:
    validated_tool = validate_design_tool(tool)
    root_path = Path(root).expanduser().resolve()
    env_map = env if env is not None else dict(os.environ)

    if which_fn is None:
        which_impl = lambda name: shutil.which(name, path=path_env)  # noqa: E731
    else:
        which_impl = lambda name: which_fn(name, path=path_env)  # noqa: E731

    detected_paths: dict[str, str | None] = {}
    for name in PROBE_COMMAND_NAMES:
        resolved = which_impl(name)
        detected_paths[name] = str(Path(resolved).expanduser()) if resolved else None

    readiness = classify_runtime_readiness(detected_paths)
    env_presence = {name: bool(name in env_map) for name in ENV_VAR_HINTS}
    packet_probe = _prepared_packet_probe(root_path)
    warnings: list[str] = []
    if detected_paths.get("od") and not detected_paths.get("open-design"):
        warnings.append(
            "Found `od` without `open-design`; `od` can be a non-Open-Design system utility and is not treated as execution-ready."
        )

    return {
        "title": "Product Design Runtime Probe",
        "tool": validated_tool,
        "dry_run": True,
        "slash_command_surface": RUNTIME_PROBE_SLASH_COMMAND,
        "canonical_ws_command": RUNTIME_PROBE_COMMAND,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "python": platform.python_version(),
        },
        "detected_command_paths": detected_paths,
        "environment_variable_presence": env_presence,
        "prepared_packet_probe": packet_probe,
        "warnings": warnings,
        "execution_attempted": False,
        "install_attempted": False,
        "agent_cli_execution_attempted": False,
        "network_used": False,
        "writes_files": False,
        "readiness_classification": readiness,
        "next_step": (
            "manual local install/evaluation or future guarded "
            "ws product-design-render --product <id> --tool open-design --confirm"
        ),
    }


def render_design_runtime_probe(probe: dict[str, Any]) -> str:
    lines = [
        "# Product Design Runtime Probe",
        "",
        "- DRY RUN / no execution",
        f"- slash command surface: `{probe['slash_command_surface']}`",
        f"- canonical ws command: `{probe['canonical_ws_command']}`",
        f"- tool: `{probe['tool']}`",
        (
            "- platform: "
            f"`{probe['platform']['system']} {probe['platform']['release']}` "
            f"(python `{probe['platform']['python']}`)"
        ),
        "",
        "## PATH Visibility",
    ]
    for name in PROBE_COMMAND_NAMES:
        resolved = probe["detected_command_paths"].get(name)
        lines.append(f"- {name}: `{resolved or 'NOT_FOUND'}`")
    if probe.get("warnings"):
        lines.append("- warning: `od` path is advisory only unless `open-design` is also found")

    lines.extend(
        [
            "",
            "## Environment Variable Names (Presence Only)",
            "- values are redacted by policy",
        ]
    )
    for name in ENV_VAR_HINTS:
        lines.append(f"- {name}: `{probe['environment_variable_presence'][name]}`")

    if probe.get("warnings"):
        lines.extend(["", "## Warnings"])
        for warning in probe["warnings"]:
            lines.append(f"- {warning}")

    packet_probe = probe["prepared_packet_probe"]
    lines.extend(
        [
            "",
            "## Prepared Packet Observation (Optional)",
            f"- product_id: `{packet_probe['product_id']}`",
            f"- run_id: `{packet_probe['run_id']}`",
            f"- run directory present: `{packet_probe['run_dir_present']}`",
            f"- run directory: `{packet_probe['run_dir']}`",
            "- required file presence:",
        ]
    )
    for filename, present in packet_probe["required_file_presence"].items():
        lines.append(f"  - {filename}: `{present}`")
    lines.append("- optional file presence:")
    for filename, present in packet_probe["optional_file_presence"].items():
        lines.append(f"  - {filename}: `{present}`")

    lines.extend(
        [
            "",
            "## Execution Safeguards",
            f"- execution attempted: `{probe['execution_attempted']}`",
            f"- install attempted: `{probe['install_attempted']}`",
            f"- agent CLI execution attempted: `{probe['agent_cli_execution_attempted']}`",
            f"- network used: `{probe['network_used']}`",
            f"- files written: `{probe['writes_files']}`",
            "",
            "## Readiness Classification",
            f"- `{probe['readiness_classification']}`",
            "",
            "## Next Step",
            f"- {probe['next_step']}",
            "",
        ]
    )
    return "\n".join(lines)


def render_design_runtime_report(probe: dict[str, Any]) -> str:
    packet_probe = probe["prepared_packet_probe"]
    env_presence = probe["environment_variable_presence"]
    detected = probe["detected_command_paths"]

    present_env = [name for name, present in env_presence.items() if present]
    missing_env = [name for name, present in env_presence.items() if not present]

    lines = [
        "# Product Design Runtime Report",
        "",
        "- DRY RUN / read-only runtime visibility report",
        f"- slash command surface: `{RUNTIME_REPORT_SLASH_COMMAND}`",
        f"- canonical ws command: `{RUNTIME_REPORT_COMMAND}`",
        f"- tool: `{probe['tool']}`",
        f"- readiness classification: `{probe['readiness_classification']}`",
        "",
        "## Executable Visibility",
        f"- open-design: `{detected.get('open-design') or 'NOT_FOUND'}`",
        f"- od: `{detected.get('od') or 'NOT_FOUND'}`",
        f"- node: `{detected.get('node') or 'NOT_FOUND'}`",
        f"- pnpm: `{detected.get('pnpm') or 'NOT_FOUND'}`",
        f"- npm: `{detected.get('npm') or 'NOT_FOUND'}`",
        "",
        "## Environment Variable Names (Presence Only)",
        "- values are not printed by policy",
        f"- present: `{', '.join(present_env) if present_env else 'none'}`",
        f"- missing: `{', '.join(missing_env) if missing_env else 'none'}`",
        "",
        "## Prepared Packet Presence (Optional)",
        f"- product_id: `{packet_probe['product_id']}`",
        f"- run_id: `{packet_probe['run_id']}`",
        f"- run directory present: `{packet_probe['run_dir_present']}`",
        "",
        "## Safety Guarantees",
        f"- execution attempted: `{probe['execution_attempted']}`",
        f"- install attempted: `{probe['install_attempted']}`",
        f"- agent CLI execution attempted: `{probe['agent_cli_execution_attempted']}`",
        f"- network used: `{probe['network_used']}`",
        f"- files written: `{probe['writes_files']}`",
    ]
    if probe.get("warnings"):
        lines.extend(["", "## Warnings"])
        for warning in probe["warnings"]:
            lines.append(f"- {warning}")

    lines.extend(
        [
            "",
            "## Next Recommended Action",
            "- Review runtime gaps, then perform manual install/evaluation steps only.",
            "- Re-run `/design probe` and `/design runtime` before any future guarded render execution work.",
            "",
        ]
    )
    return "\n".join(lines)

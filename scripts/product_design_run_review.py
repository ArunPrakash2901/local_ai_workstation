#!/usr/bin/env python3
"""Product Lane design run review helpers (static HTML surface, no execution)."""

from __future__ import annotations

import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from product_design_adapter import build_design_run_id, planned_design_run_dir, validate_design_tool
from product_design_run import (
    DESIGN_EXECUTION_MODE_NOT_EXECUTED,
    DESIGN_INPUT_FILENAME,
    DESIGN_OPERATOR_REPORT_FILENAME,
    DESIGN_PROMPT_FILENAME,
    DESIGN_RUN_FILENAME,
    DESIGN_RUN_RENDER_NEXT_ACTION,
    DESIGN_RUN_STATUS_PREPARED,
)
from product_registry import get_product_status, product_dir, validate_product_id


DESIGN_RUN_REVIEW_ACTION_DRY = (
    "ws product-design-run-review --product <product_id> --tool open-design --dry-run"
)
DESIGN_RUN_REVIEW_ACTION_CONFIRM = (
    "ws product-design-run-review --product <product_id> --tool open-design --confirm"
)
DESIGN_RUN_REVIEW_SLASH_COMMAND = "/design review"
DESIGN_RUN_REVIEW_WRITE_SLASH_COMMAND = "/design review-write"

DESIGN_REVIEW_DIRNAME = "review"
DESIGN_REVIEW_HTML_FILENAME = "design_run_review.html"
DESIGN_REVIEW_MANIFEST_FILENAME = "design_run_review_manifest.json"
DESIGN_REVIEW_REPORT_FILENAME = "design_run_review_report.md"

REQUIRED_FORBIDDEN_PATHS = ("src/", "app/", "components/", "package.json")
REQUIRED_SOURCE_ARTIFACT_KEYS = (
    "active_scope_lock",
    "active_scope_lock_hash",
    "active_prd",
    "active_prd_hash",
    "active_wireframe",
    "active_wireframe_hash",
)

CANONICAL_SOURCE_WARNING = (
    "Markdown/YAML packet files are canonical source of truth. "
    "This HTML page is a human review surface only."
)
NO_EXECUTION_STATEMENT = (
    "Open Design was not executed by this command and no render output folders were created."
)


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


def _load_json_or_yaml_like(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore[import-not-found]
        except Exception:
            return {}
        try:
            parsed = yaml.safe_load(raw)
        except Exception:
            return {}
    return parsed if isinstance(parsed, dict) else {}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize_path_token(value: str) -> str:
    token = str(value).strip().replace("\\", "/")
    while token.startswith("./"):
        token = token[2:]
    return token


def _normalize_forbidden(value: str) -> str:
    token = _normalize_path_token(value)
    if token != "package.json":
        token = token.rstrip("/") + "/"
    return token


def resolve_design_run_dir(root: str | Path, product_id: str, tool: str) -> dict[str, Any]:
    if not validate_product_id(str(product_id)):
        raise ValueError(f"invalid product_id: {product_id!r}")
    validated_tool = validate_design_tool(tool)
    root_path = Path(root).expanduser().resolve()
    product_record = get_product_status(root_path, str(product_id))
    pdir = product_dir(root_path, str(product_id))
    run_id = build_design_run_id(product_record, validated_tool, mode="render")
    run_dir = planned_design_run_dir(pdir, validated_tool, run_id)
    run_rel = run_dir.relative_to(root_path).as_posix()

    return {
        "root": root_path,
        "product_id": str(product_id),
        "product_record": product_record,
        "product_root": pdir,
        "product_type": str(product_record.get("product_type", "")).strip(),
        "tool": validated_tool,
        "run_id": run_id,
        "run_dir": run_dir,
        "run_rel": run_rel,
        "expected_allowed_write_root": f"{run_rel}/",
    }


def load_design_run_packet(root: str | Path, product_id: str, tool: str) -> dict[str, Any]:
    context = resolve_design_run_dir(root, product_id, tool)
    run_dir: Path = context["run_dir"]

    if not run_dir.is_dir():
        raise FileNotFoundError(
            f"prepared design run directory missing: {context['run_rel']}/. "
            "Run ws product-design-run-prepare first."
        )

    required_paths = {
        DESIGN_RUN_FILENAME: _safe_child(run_dir, run_dir / DESIGN_RUN_FILENAME),
        DESIGN_INPUT_FILENAME: _safe_child(run_dir, run_dir / DESIGN_INPUT_FILENAME),
        DESIGN_PROMPT_FILENAME: _safe_child(run_dir, run_dir / DESIGN_PROMPT_FILENAME),
    }
    optional_paths = {
        DESIGN_OPERATOR_REPORT_FILENAME: _safe_child(run_dir, run_dir / DESIGN_OPERATOR_REPORT_FILENAME),
    }

    missing_required = [name for name, path in required_paths.items() if not path.is_file()]
    if missing_required:
        raise FileNotFoundError(
            "missing required design run packet files: " + ", ".join(sorted(missing_required))
        )

    run_payload = _load_json_or_yaml_like(required_paths[DESIGN_RUN_FILENAME])
    if not run_payload:
        raise ValueError("design_run.yaml is empty or invalid")

    packet_files: dict[str, Path] = {}
    packet_files.update(required_paths)
    for name, path in optional_paths.items():
        if path.is_file():
            packet_files[name] = path

    context["required_paths"] = required_paths
    context["optional_paths"] = optional_paths
    context["packet_files"] = packet_files
    context["design_run_payload"] = run_payload
    return context


def validate_review_preconditions(packet: dict[str, Any]) -> None:
    run_payload = packet["design_run_payload"]
    status = str(run_payload.get("status", "")).strip()
    if status != DESIGN_RUN_STATUS_PREPARED:
        raise ValueError(
            f"design run status must be {DESIGN_RUN_STATUS_PREPARED} for review "
            f"(found {status!r})"
        )

    execution_mode = str(run_payload.get("execution_mode", "")).strip()
    if execution_mode != DESIGN_EXECUTION_MODE_NOT_EXECUTED:
        raise ValueError(
            f"design execution_mode must be {DESIGN_EXECUTION_MODE_NOT_EXECUTED} for review "
            f"(found {execution_mode!r})"
        )

    allowed_write_root = _normalize_path_token(str(run_payload.get("allowed_write_root", "")))
    expected_write_root = packet["expected_allowed_write_root"]
    if not allowed_write_root:
        raise ValueError("design_run.yaml missing allowed_write_root")
    if not allowed_write_root.endswith("/"):
        allowed_write_root = allowed_write_root + "/"
    if allowed_write_root != expected_write_root:
        raise ValueError(
            "design_run.yaml allowed_write_root must stay inside the expected sandbox "
            f"(expected {expected_write_root!r}, found {allowed_write_root!r})"
        )

    forbidden_paths = run_payload.get("forbidden_paths")
    if not isinstance(forbidden_paths, list) or not forbidden_paths:
        raise ValueError("design_run.yaml missing forbidden_paths")
    normalized_forbidden = {_normalize_forbidden(str(item)) for item in forbidden_paths}
    missing_forbidden = [path for path in REQUIRED_FORBIDDEN_PATHS if path not in normalized_forbidden]
    if missing_forbidden:
        raise ValueError(
            "design_run.yaml forbidden_paths missing required boundary protections: "
            + ", ".join(missing_forbidden)
        )

    source_artifacts = run_payload.get("source_artifacts")
    if not isinstance(source_artifacts, dict) or not source_artifacts:
        raise ValueError("design_run.yaml missing source_artifacts")
    missing_sources = [key for key in REQUIRED_SOURCE_ARTIFACT_KEYS if not source_artifacts.get(key)]
    if missing_sources:
        raise ValueError(
            "design_run.yaml source_artifacts missing required entries: "
            + ", ".join(missing_sources)
        )


def compute_packet_file_hashes(packet_files: dict[str, Path]) -> dict[str, str]:
    return {name: _sha256_file(path) for name, path in sorted(packet_files.items())}


def _execution_boundary_warnings(
    run_dir: Path, run_payload: dict[str, Any], *, expected_write_root: str
) -> list[str]:
    warnings: list[str] = []

    if str(run_payload.get("allowed_write_root", "")).strip().replace("\\", "/") != expected_write_root:
        warnings.append("allowed_write_root differs from expected sandbox path")

    for folder_name in ("raw_output", "prototype", "screenshots", "export"):
        if _safe_child(run_dir, run_dir / folder_name).exists():
            warnings.append(f"{folder_name}/ exists before render execution")

    return warnings


def build_design_run_review_model(packet: dict[str, Any]) -> dict[str, Any]:
    validate_review_preconditions(packet)

    run_payload = packet["design_run_payload"]
    run_dir: Path = packet["run_dir"]
    root: Path = packet["root"]
    review_dir = _safe_child(run_dir, run_dir / DESIGN_REVIEW_DIRNAME)
    review_rel = review_dir.relative_to(root).as_posix()

    packet_files: dict[str, Path] = packet["packet_files"]
    packet_file_presence = {
        DESIGN_RUN_FILENAME: packet["required_paths"][DESIGN_RUN_FILENAME].is_file(),
        DESIGN_INPUT_FILENAME: packet["required_paths"][DESIGN_INPUT_FILENAME].is_file(),
        DESIGN_PROMPT_FILENAME: packet["required_paths"][DESIGN_PROMPT_FILENAME].is_file(),
        DESIGN_OPERATOR_REPORT_FILENAME: packet["optional_paths"][DESIGN_OPERATOR_REPORT_FILENAME].is_file(),
    }
    packet_hashes = compute_packet_file_hashes(packet_files)

    warnings: list[str] = []
    if not packet_file_presence[DESIGN_OPERATOR_REPORT_FILENAME]:
        warnings.append("optional operator_report.md is missing")
    if not run_payload.get("created_at"):
        warnings.append("design_run.yaml created_at is missing")

    warnings.extend(
        _execution_boundary_warnings(
            run_dir,
            run_payload,
            expected_write_root=packet["expected_allowed_write_root"],
        )
    )

    review_status = "WARN" if warnings else "PASS"
    source_artifacts = run_payload.get("source_artifacts", {})
    forbidden_paths = run_payload.get("forbidden_paths", [])
    allowed_write_root = str(run_payload.get("allowed_write_root", packet["expected_allowed_write_root"]))

    planned_output_files = [
        f"{review_rel}/{DESIGN_REVIEW_HTML_FILENAME}",
        f"{review_rel}/{DESIGN_REVIEW_MANIFEST_FILENAME}",
        f"{review_rel}/{DESIGN_REVIEW_REPORT_FILENAME}",
    ]

    return {
        "product_id": packet["product_id"],
        "product_type": packet["product_type"] or "UNKNOWN",
        "tool": packet["tool"],
        "run_id": packet["run_id"],
        "root_path": root,
        "run_dir": packet["run_rel"],
        "run_dir_path": run_dir,
        "review_dir": review_rel,
        "review_dir_path": review_dir,
        "review_status": review_status,
        "warnings": warnings,
        "blockers": [],
        "run_status": str(run_payload.get("status", "")),
        "execution_mode": str(run_payload.get("execution_mode", "")),
        "allowed_write_root": allowed_write_root,
        "forbidden_paths": [str(item) for item in forbidden_paths],
        "packet_file_presence": packet_file_presence,
        "packet_file_paths": {name: path.relative_to(root).as_posix() for name, path in packet_files.items()},
        "packet_file_hashes": packet_hashes,
        "source_artifacts": source_artifacts if isinstance(source_artifacts, dict) else {},
        "execution_boundary_warnings": _execution_boundary_warnings(
            run_dir,
            run_payload,
            expected_write_root=packet["expected_allowed_write_root"],
        ),
        "review_checklist": [
            "Does the design objective match the PRD?",
            "Does the prompt preserve wireframe constraints?",
            "Are forbidden paths clear?",
            "Is sandbox output boundary clear?",
            "Are non-goals preserved?",
            "Is the packet safe to render later?",
        ],
        "human_review_questions": [
            "Are source artifact hashes present and plausible for current approved product state?",
            "Does allowed_write_root stay strictly inside the design sandbox?",
            "Do prompt instructions prevent app/source repository writes?",
            "Do packet files contain enough context for a future render without scope expansion?",
        ],
        "next_recommended_command": DESIGN_RUN_RENDER_NEXT_ACTION,
        "canonical_source_warning": CANONICAL_SOURCE_WARNING,
        "no_execution_statement": NO_EXECUTION_STATEMENT,
        "planned_output_files": planned_output_files,
        "slash_command_surface": DESIGN_RUN_REVIEW_SLASH_COMMAND,
        "canonical_ws_command_dry_run": (
            f"ws product-design-run-review --product {packet['product_id']} --tool {packet['tool']} --dry-run"
        ),
        "canonical_ws_command_confirm": (
            f"ws product-design-run-review --product {packet['product_id']} --tool {packet['tool']} --confirm"
        ),
        "open_design_executed": False,
        "open_design_installed": False,
        "generated_at": _utc_now_iso(),
    }


def _html_list(items: list[str]) -> str:
    if not items:
        return "<ul><li>None</li></ul>"
    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"


def render_design_run_review_html(review_model: dict[str, Any]) -> str:
    source_artifacts = review_model["source_artifacts"]
    packet_rows = []
    for key in (
        DESIGN_INPUT_FILENAME,
        DESIGN_PROMPT_FILENAME,
        DESIGN_RUN_FILENAME,
        DESIGN_OPERATOR_REPORT_FILENAME,
    ):
        present = review_model["packet_file_presence"].get(key, False)
        rel_path = review_model["packet_file_paths"].get(key, "MISSING")
        digest = review_model["packet_file_hashes"].get(key, "UNAVAILABLE")
        packet_rows.append(
            "<tr>"
            f"<td><code>{html.escape(key)}</code></td>"
            f"<td>{'present' if present else 'missing'}</td>"
            f"<td><code>{html.escape(rel_path)}</code></td>"
            f"<td><code>{html.escape(digest)}</code></td>"
            "</tr>"
        )

    source_rows = []
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
        if key in source_artifacts and str(source_artifacts.get(key)).strip():
            source_rows.append(
                "<tr>"
                f"<td><code>{html.escape(key)}</code></td>"
                f"<td><code>{html.escape(str(source_artifacts[key]))}</code></td>"
                "</tr>"
            )

    warnings_html = _html_list([str(item) for item in review_model["warnings"]])
    checklist_html = _html_list([str(item) for item in review_model["review_checklist"]])
    questions_html = _html_list([str(item) for item in review_model["human_review_questions"]])
    forbidden_paths_html = _html_list([str(item) for item in review_model["forbidden_paths"]])

    return "\n".join(
        [
            "<!doctype html>",
            "<html lang=\"en\">",
            "<head>",
            "  <meta charset=\"utf-8\">",
            "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
            "  <title>Product Design Run Review</title>",
            "  <style>",
            "    body { font-family: Segoe UI, Arial, sans-serif; margin: 24px; line-height: 1.45; color: #111; }",
            "    h1, h2 { margin: 0 0 10px 0; }",
            "    section { margin: 20px 0; padding: 12px 14px; border: 1px solid #d0d0d0; border-radius: 8px; }",
            "    code { background: #f4f4f4; padding: 1px 4px; border-radius: 4px; }",
            "    table { border-collapse: collapse; width: 100%; }",
            "    th, td { border: 1px solid #d8d8d8; padding: 8px; text-align: left; vertical-align: top; }",
            "    .warning { color: #7a5a00; font-weight: 600; }",
            "    .pass { color: #0f5132; font-weight: 700; }",
            "    .warn { color: #7a5a00; font-weight: 700; }",
            "    .fail { color: #842029; font-weight: 700; }",
            "  </style>",
            "</head>",
            "<body>",
            "  <header>",
            "    <h1>Product Design Run Review</h1>",
            f"    <p><strong>product_id:</strong> <code>{html.escape(review_model['product_id'])}</code></p>",
            f"    <p><strong>tool:</strong> <code>{html.escape(review_model['tool'])}</code></p>",
            f"    <p><strong>run_id:</strong> <code>{html.escape(review_model['run_id'])}</code></p>",
            f"    <p><strong>review status:</strong> <span class=\"{review_model['review_status'].lower()}\">{html.escape(review_model['review_status'])}</span></p>",
            "  </header>",
            "  <section>",
            "    <h2>Canonical Source Warning</h2>",
            f"    <p>{html.escape(review_model['canonical_source_warning'])}</p>",
            "  </section>",
            "  <section>",
            "    <h2>Prepared Packet Summary</h2>",
            "    <table>",
            "      <thead><tr><th>File</th><th>Presence</th><th>Path</th><th>SHA-256</th></tr></thead>",
            "      <tbody>",
            *packet_rows,
            "      </tbody>",
            "    </table>",
            "  </section>",
            "  <section>",
            "    <h2>Execution Boundary</h2>",
            f"    <p><strong>Open Design not executed:</strong> <code>{str(not review_model['open_design_executed']).lower()}</code></p>",
            f"    <p><strong>execution_mode:</strong> <code>{html.escape(review_model['execution_mode'])}</code></p>",
            f"    <p><strong>allowed_write_root:</strong> <code>{html.escape(review_model['allowed_write_root'])}</code></p>",
            "    <h3>Forbidden Paths</h3>",
            f"    {forbidden_paths_html}",
            "  </section>",
            "  <section>",
            "    <h2>Source Artifacts</h2>",
            "    <table>",
            "      <thead><tr><th>Field</th><th>Value</th></tr></thead>",
            "      <tbody>",
            *(source_rows or ["<tr><td colspan=\"2\">No source artifact references found</td></tr>"]),
            "      </tbody>",
            "    </table>",
            "  </section>",
            "  <section>",
            "    <h2>Human Review Checklist</h2>",
            f"    {checklist_html}",
            "    <h3>Human Review Questions</h3>",
            f"    {questions_html}",
            "  </section>",
            "  <section>",
            "    <h2>Warnings</h2>",
            f"    {warnings_html}",
            "  </section>",
            "  <section>",
            "    <h2>Next Step</h2>",
            f"    <p>{html.escape(review_model['next_recommended_command'])}</p>",
            "  </section>",
            "</body>",
            "</html>",
            "",
        ]
    )


def render_design_run_review_report(review_model: dict[str, Any]) -> str:
    lines = [
        "# Product Design Run Review Report",
        "",
        "## Summary",
        f"- product_id: `{review_model['product_id']}`",
        f"- tool: `{review_model['tool']}`",
        f"- run_id: `{review_model['run_id']}`",
        f"- review_status: `{review_model['review_status']}`",
        f"- slash command surface: `{review_model['slash_command_surface']}`",
        f"- canonical ws command (dry-run): `{review_model['canonical_ws_command_dry_run']}`",
        f"- canonical ws command (confirm): `{review_model['canonical_ws_command_confirm']}`",
        "",
        "## Canonical Source Warning",
        f"- {review_model['canonical_source_warning']}",
        "",
        "## Files Written",
    ]
    for output_path in review_model["planned_output_files"]:
        lines.append(f"- `{output_path}`")
    lines.extend(["", "## Blockers"])
    blockers = review_model.get("blockers", [])
    if blockers:
        for blocker in blockers:
            lines.append(f"- {blocker}")
    else:
        lines.append("- none")
    lines.extend(["", "## Warnings"])
    warnings = review_model.get("warnings", [])
    if warnings:
        for warning in warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## No Execution Statement",
            f"- {review_model['no_execution_statement']}",
            "",
            "## Next Step",
            f"- {review_model['next_recommended_command']}",
            "",
        ]
    )
    return "\n".join(lines)


def render_design_run_review_manifest(review_model: dict[str, Any]) -> dict[str, Any]:
    return {
        "product_id": review_model["product_id"],
        "tool": review_model["tool"],
        "run_id": review_model["run_id"],
        "review_status": review_model["review_status"],
        "generated_at": review_model["generated_at"],
        "source_packet_files": review_model["packet_file_paths"],
        "source_packet_hashes": review_model["packet_file_hashes"],
        "output_files": review_model["planned_output_files"],
        "canonical_source_warning": review_model["canonical_source_warning"],
        "no_execution_statement": review_model["no_execution_statement"],
    }


def preview_design_run_review_writes(review_model: dict[str, Any]) -> list[str]:
    return list(review_model["planned_output_files"])


def render_design_run_review_preview(review_model: dict[str, Any]) -> str:
    lines = [
        "# Product Design Run Review Preview",
        "",
        "- DRY RUN / no files written",
        f"- slash command surface: `{review_model['slash_command_surface']}`",
        f"- canonical ws command: `{review_model['canonical_ws_command_dry_run']}`",
        f"- product_id: `{review_model['product_id']}`",
        f"- tool: `{review_model['tool']}`",
        f"- run_id: `{review_model['run_id']}`",
        f"- review_status: `{review_model['review_status']}`",
        "",
        "## Prepared Packet Presence",
        f"- design_run.yaml: `{review_model['packet_file_presence'].get(DESIGN_RUN_FILENAME, False)}`",
        f"- design_input.yaml: `{review_model['packet_file_presence'].get(DESIGN_INPUT_FILENAME, False)}`",
        f"- design_prompt.md: `{review_model['packet_file_presence'].get(DESIGN_PROMPT_FILENAME, False)}`",
        f"- operator_report.md: `{review_model['packet_file_presence'].get(DESIGN_OPERATOR_REPORT_FILENAME, False)}`",
        "",
        "## Planned Review Writes",
    ]
    for path in review_model["planned_output_files"]:
        lines.append(f"- `{path}`")
    lines.extend(
        [
            "",
            "## Canonical Source Warning",
            f"- {review_model['canonical_source_warning']}",
            "",
            "## No Execution Statement",
            f"- {review_model['no_execution_statement']}",
            "",
            "## Next Step",
            f"- {review_model['canonical_ws_command_confirm']}",
            "",
        ]
    )
    return "\n".join(lines)


def write_design_run_review_artifacts(review_model: dict[str, Any], *, confirm: bool) -> dict[str, Any]:
    if not confirm:
        raise PermissionError("design run review write requires explicit --confirm")

    review_dir: Path = review_model["review_dir_path"]
    root_path: Path = review_model["root_path"]
    review_dir.mkdir(parents=True, exist_ok=True)

    html_path = _safe_child(review_dir, review_dir / DESIGN_REVIEW_HTML_FILENAME)
    manifest_path = _safe_child(review_dir, review_dir / DESIGN_REVIEW_MANIFEST_FILENAME)
    report_path = _safe_child(review_dir, review_dir / DESIGN_REVIEW_REPORT_FILENAME)

    if html_path.exists():
        raise FileExistsError(f"review HTML already exists: {html_path}")

    html_text = render_design_run_review_html(review_model)
    manifest_payload = render_design_run_review_manifest(review_model)
    report_text = render_design_run_review_report(review_model)

    html_path.write_text(html_text, encoding="utf-8", newline="\n")
    manifest_path.write_text(json.dumps(manifest_payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    report_path.write_text(report_text, encoding="utf-8", newline="\n")

    files_written = [
        html_path.relative_to(root_path).as_posix(),
        manifest_path.relative_to(root_path).as_posix(),
        report_path.relative_to(root_path).as_posix(),
    ]

    return {
        "review_status": review_model["review_status"],
        "files_written": files_written,
        "open_design_executed": False,
        "open_design_installed": False,
        "canonical_source_warning": review_model["canonical_source_warning"],
        "no_execution_statement": review_model["no_execution_statement"],
    }


def build_design_run_review(root: str | Path, product_id: str, tool: str) -> dict[str, Any]:
    packet = load_design_run_packet(root, product_id, tool)
    return build_design_run_review_model(packet)

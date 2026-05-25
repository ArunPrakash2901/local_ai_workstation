import datetime
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


APPROVED_PLAN = "APPROVED_FOR_GRAPHIFY_EXECUTION"
APPROVED_PACKET = "APPROVED_FOR_CONTEXT_USE"
SUCCESS_RUN = "SUCCEEDED"


def _new_project(project_id: str) -> Dict[str, Any]:
    return {
        "project_id": project_id,
        "inventory": None,
        "plan": None,
        "plans": [],
        "run": None,
        "runs": [],
        "intake": None,
        "intakes": [],
        "summary": None,
        "summaries": [],
        "packets": [],
        "handoffs": [],
        "warnings": [],
    }


def _strip_known_suffixes(stem: str) -> str:
    for suffix in ("_inventory", "_plan", "_summary", "_intake", "_run", "_review"):
        if stem.endswith(suffix):
            return stem[: -len(suffix)] or "unknown"

    timestamp_match = re.match(r"^(?P<project>.+)_\d{8}_\d{6}(?:_intake)?$", stem)
    if timestamp_match:
        return timestamp_match.group("project") or "unknown"

    return stem or "unknown"


def _project_id_from_graph_path(value: Any) -> Optional[str]:
    if not value:
        return None
    parts = Path(str(value)).parts
    for index, part in enumerate(parts):
        if part == "graphify-results" and index + 1 < len(parts):
            return parts[index + 1]
    return None


def _project_id_from_data(data: Dict[str, Any], path: Path) -> str:
    direct = data.get("project_id")
    if direct:
        return str(direct)

    nested = data.get("project")
    if isinstance(nested, dict) and nested.get("id"):
        return str(nested["id"])
    if isinstance(nested, str) and nested:
        return nested

    for key in ("graph_path", "output_path", "source_output_path", "proposed_output_path"):
        candidate = _project_id_from_graph_path(data.get(key))
        if candidate:
            return candidate

    for key in ("plan_path", "run_manifest_path", "source_packet"):
        value = data.get(key)
        if value:
            inferred = _strip_known_suffixes(Path(str(value)).stem)
            if inferred:
                return inferred

    return _strip_known_suffixes(path.stem)


def _timestamp_value(artifact: Optional[Dict[str, Any]]) -> str:
    if not artifact:
        return ""
    for key in (
        "started_at",
        "finished_at",
        "created_at",
        "intake_timestamp",
        "timestamp",
        "approved_at",
        "_mtime",
    ):
        value = artifact.get(key)
        if value is not None:
            return str(value)
    return ""


def _latest(artifacts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not artifacts:
        return None
    return sorted(artifacts, key=_timestamp_value, reverse=True)[0]


def _preferred_plan(plans: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    approved = [p for p in plans if p.get("approval_status") == APPROVED_PLAN]
    return _latest(approved) or _latest(plans)


def _read_json(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        return None, str(exc)

    if not isinstance(data, dict):
        return None, "top-level JSON value is not an object"

    data = dict(data)
    data["_path"] = str(path)
    try:
        data["_mtime"] = path.stat().st_mtime
    except OSError:
        pass
    return data, None


def _ensure_project(
    projects: Dict[str, Dict[str, Any]],
    project_id: str,
    target_project_id: Optional[str],
) -> Optional[Dict[str, Any]]:
    if target_project_id and project_id != target_project_id:
        return None
    if project_id not in projects:
        projects[project_id] = _new_project(project_id)
    return projects[project_id]


def _add_json_artifact(
    projects: Dict[str, Dict[str, Any]],
    path: Path,
    artifact_kind: str,
    target_project_id: Optional[str],
) -> None:
    data, error = _read_json(path)
    if error:
        project_id = _strip_known_suffixes(path.stem)
        project = _ensure_project(projects, project_id, target_project_id)
        if project is not None:
            project["warnings"].append(f"Malformed artifact {path}: {error}")
        return

    assert data is not None
    project_id = _project_id_from_data(data, path)
    project = _ensure_project(projects, project_id, target_project_id)
    if project is None:
        return

    if artifact_kind == "inventory":
        project["inventory"] = data
    elif artifact_kind == "plan":
        project["plans"].append(data)
    elif artifact_kind == "run":
        project["runs"].append(data)
    elif artifact_kind == "intake":
        project["intakes"].append(data)
    elif artifact_kind == "summary":
        project["summaries"].append(data)
    elif artifact_kind == "packet":
        project["packets"].append(data)
    elif artifact_kind == "handoff":
        project["handoffs"].append(data)


def _add_summary_markdown(
    projects: Dict[str, Dict[str, Any]],
    path: Path,
    target_project_id: Optional[str],
) -> None:
    project_id = _strip_known_suffixes(path.stem)
    project = _ensure_project(projects, project_id, target_project_id)
    if project is None:
        return
    project["summaries"].append(
        {
            "project_id": project_id,
            "summary_status": "REPORT_EXISTS",
            "_path": str(path),
            "_mtime": path.stat().st_mtime,
        }
    )


def discover_projects(
    output_root: Path,
    target_project_id: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """Index Repo Context Lane artifacts without inspecting source repositories."""
    projects: Dict[str, Dict[str, Any]] = {}

    scans = [
        ("project_inventories", "*_inventory.json", "inventory"),
        ("graphify_plans", "*_plan.json", "plan"),
        ("graphify_runs", "*.json", "run"),
        ("graphify_intake_reports", "*.json", "intake"),
        ("graph_summaries", "*_summary.json", "summary"),
        ("context_packets", "*.json", "packet"),
        ("handoff_manifests", "*.json", "handoff"),
    ]

    for folder, pattern, artifact_kind in scans:
        artifact_dir = output_root / folder
        if not artifact_dir.exists():
            continue
        for path in sorted(artifact_dir.glob(pattern)):
            _add_json_artifact(projects, path, artifact_kind, target_project_id)

    summary_dir = output_root / "graph_summaries"
    if summary_dir.exists():
        for path in sorted(summary_dir.glob("*_summary.md")):
            _add_summary_markdown(projects, path, target_project_id)

    for project in projects.values():
        project["plan"] = _preferred_plan(project["plans"])
        project["run"] = _latest(project["runs"])
        project["intake"] = _latest(project["intakes"])
        project["summary"] = _latest(project["summaries"])
        project["packets"] = sorted(project["packets"], key=_timestamp_value, reverse=True)
        project["handoffs"] = sorted(project["handoffs"], key=_timestamp_value, reverse=True)

    return projects


def _artifact_path(artifact: Optional[Dict[str, Any]], fallback: str) -> str:
    if artifact and artifact.get("_path"):
        return str(artifact["_path"])
    return fallback


def _approved_packets(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [p for p in data["packets"] if p.get("human_approval_status") == APPROVED_PACKET]


def get_recommendation(project_id: str, data: Dict[str, Any]) -> str:
    if not data["inventory"]:
        return f"ws repo-context inventory --project <path_to_{project_id}>"

    if not data["plan"]:
        return f"ws repo-context graphify-plan --project <path_to_{project_id}>"

    plan_path = _artifact_path(
        data["plan"],
        f"repo_context_lane/graphify_plans/{project_id}_plan.json",
    )
    if data["plan"].get("approval_status") != APPROVED_PLAN:
        return (
            f"ws repo-context graphify-plan-review --plan {plan_path} "
            f"OR ws repo-context graphify-plan-approve --plan {plan_path} --confirm"
        )

    if not data["run"]:
        return f"ws repo-context graphify-run --plan {plan_path} --confirm"

    if data["run"].get("execution_status") != SUCCESS_RUN:
        return f"Review failed run, then rerun if safe: ws repo-context graphify-run --plan {plan_path} --confirm"

    run_path = _artifact_path(
        data["run"],
        f"repo_context_lane/graphify_runs/{project_id}_run.json",
    )
    if not data["intake"]:
        return f"ws repo-context graphify-intake --run {run_path}"

    if not data["summary"]:
        graph_path = data["run"].get("graph_path") or data["intake"].get("graph_path") or "<graph.json>"
        return f"ws repo-context summarize --graph {graph_path}"

    if not data["packets"]:
        return f"ws repo-context packet --project {project_id} --task <task_name>"

    approved_packets = _approved_packets(data)
    if not approved_packets:
        packet_path = _artifact_path(data["packets"][0], "<packet_path>")
        return (
            f"ws repo-context packet-review --packet {packet_path} "
            f"OR ws repo-context packet-approve --packet {packet_path} --confirm"
        )

    if not data["handoffs"]:
        packet_path = _artifact_path(approved_packets[0], "<path_to_approved_packet>")
        return f"ws repo-context handoff --packet {packet_path} --target gemini"

    return "READY_FOR_OPERATOR_USE (HANDOFF_READY)"


def _plan_status(data: Dict[str, Any]) -> Tuple[str, str]:
    if not data["plan"]:
        return "MISSING", "MISSING"
    return "EXISTS", str(data["plan"].get("approval_status") or "UNKNOWN")


def _run_status(data: Dict[str, Any]) -> str:
    run = data["run"]
    if not run:
        return "NOT_RUN"
    status = str(run.get("execution_status") or "UNKNOWN")
    if run.get("started_at"):
        status += f" (started {run['started_at']})"
    return status


def _packet_state_counts(packets: List[Dict[str, Any]]) -> Dict[str, int]:
    states: Dict[str, int] = {}
    for packet in packets:
        state = str(packet.get("human_approval_status") or "UNKNOWN")
        states[state] = states.get(state, 0) + 1
    return states


def _handoff_target_counts(handoffs: List[Dict[str, Any]]) -> Dict[str, int]:
    targets: Dict[str, int] = {}
    for handoff in handoffs:
        target = str(handoff.get("target_agent") or handoff.get("target") or "unknown")
        targets[target] = targets.get(target, 0) + 1
    return targets


def render_status(projects: Dict[str, Dict[str, Any]]) -> str:
    if not projects:
        return "No Repo Context Lane projects discovered."

    lines = ["# Repo Context Lane: Pipeline Status", ""]

    for project_id in sorted(projects.keys()):
        data = projects[project_id]
        plan_status, approval_status = _plan_status(data)
        packet_states = _packet_state_counts(data["packets"])
        target_counts = _handoff_target_counts(data["handoffs"])

        lines.append(f"## Project: {project_id}")
        lines.append(f"- Inventory: {'EXISTS' if data['inventory'] else 'MISSING'}")
        lines.append(f"- Graphify Plan: {plan_status}")
        lines.append(f"- Graphify Plan Approval: {approval_status}")
        lines.append(f"- Latest Graphify Run: {_run_status(data)}")
        lines.append(
            f"- Graphify Intake: {data['intake'].get('intake_status', 'EXISTS') if data['intake'] else 'MISSING'}"
        )
        lines.append(f"- Graph Summary: {'READY' if data['summary'] else 'MISSING'}")

        packet_detail = ", ".join(f"{state}: {count}" for state, count in sorted(packet_states.items()))
        if not packet_detail:
            packet_detail = "none"
        lines.append(f"- Context Packets: {len(data['packets'])} ({packet_detail})")

        handoff_detail = ", ".join(f"{target}: {count}" for target, count in sorted(target_counts.items()))
        if not handoff_detail:
            handoff_detail = "none"
        lines.append(f"- Handoffs: {len(data['handoffs'])} ({handoff_detail})")

        if data["warnings"]:
            lines.append("- Warnings:")
            for warning in data["warnings"]:
                lines.append(f"  - [!] {warning}")
        else:
            lines.append("- Warnings: none")

        lines.append(f"- Next Recommended Command: {get_recommendation(project_id, data)}")
        lines.append("")

    return "\n".join(lines).rstrip()


def _has_malformed_artifacts(projects: Dict[str, Dict[str, Any]]) -> bool:
    for project in projects.values():
        if any("Malformed artifact" in warning for warning in project["warnings"]):
            return True
    return False


def generate_freeze_report(output_root: Path, projects: Dict[str, Dict[str, Any]]) -> str:
    timestamp = datetime.datetime.now().isoformat()

    from . import audit_repo_context_lane

    audit, counts = audit_repo_context_lane.audit_lane(output_root)
    malformed_found = _has_malformed_artifacts(projects)
    freeze_candidate = not audit["errors"] and not malformed_found

    lines = ["# Repo Context Lane Freeze Report", ""]
    lines.append(f"- Generated At: {timestamp}")
    lines.append(f"- Readiness: {'FREEZE_CANDIDATE' if freeze_candidate else 'IN_PROGRESS'}")
    lines.append("")

    lines.append("## Lane Commands")
    commands = [
        ("inventory", "LOCAL_REPORT_WRITE", "Generate shallow project inventory"),
        ("graphify-plan", "LOCAL_REPORT_WRITE", "Generate Graphify execution plan"),
        ("graphify-plan-list", "PURE_READ", "List Graphify plans"),
        ("graphify-plan-review", "PURE_READ", "Review Graphify plan"),
        ("graphify-plan-approve", "GUARDED_WRITE", "Approve Graphify plan"),
        ("graphify-run", "GUARDED_EXECUTION", "Run approved Graphify plan"),
        ("graphify-run-status", "PURE_READ", "Show Graphify run status"),
        ("graphify-intake", "LOCAL_REPORT_WRITE", "Ingest successful Graphify run"),
        ("summarize", "LOCAL_REPORT_WRITE", "Summarize existing graph.json"),
        ("status", "PURE_READ", "Show operator pipeline status"),
        ("freeze-report", "LOCAL_REPORT_WRITE", "Write freeze readiness report"),
        ("packet", "LOCAL_REPORT_WRITE", "Generate context packet"),
        ("packet-list", "PURE_READ", "List context packets"),
        ("packet-review", "PURE_READ", "Review context packet"),
        ("packet-approve", "GUARDED_WRITE", "Approve context packet"),
        ("handoff", "LOCAL_REPORT_WRITE", "Generate non-executed handoff draft"),
        ("audit", "PURE_READ", "Audit lane artifacts"),
    ]
    lines.append("| Command | Safety Class | Purpose |")
    lines.append("| --- | --- | --- |")
    for command, safety_class, purpose in commands:
        lines.append(f"| `{command}` | {safety_class} | {purpose} |")
    lines.append("")

    lines.append("## Artifact Directories")
    artifact_dirs = [
        "project_inventories",
        "graphify_plans",
        "graphify_runs",
        "graphify_intake_reports",
        "graph_summaries",
        "context_packets",
        "review_reports",
        "handoffs",
        "handoff_manifests",
    ]
    for directory in artifact_dirs:
        status = "EXISTS" if (output_root / directory).exists() else "MISSING"
        lines.append(f"- `{directory}/`: {status}")
    lines.append("")

    lines.append("## Current Project States")
    if projects:
        for project_id in sorted(projects.keys()):
            data = projects[project_id]
            _, approval_status = _plan_status(data)
            lines.append(f"### Project: {project_id}")
            lines.append(f"- Inventory: {'EXISTS' if data['inventory'] else 'MISSING'}")
            lines.append(f"- Plan Approval: {approval_status}")
            lines.append(f"- Latest Run: {_run_status(data)}")
            lines.append(
                f"- Intake: {data['intake'].get('intake_status', 'EXISTS') if data['intake'] else 'MISSING'}"
            )
            lines.append(f"- Summary: {'READY' if data['summary'] else 'MISSING'}")
            lines.append(f"- Packets: {len(data['packets'])}")
            lines.append(f"- Approved Packets: {len(_approved_packets(data))}")
            lines.append(f"- Handoffs: {len(data['handoffs'])}")
            lines.append(f"- Next: {get_recommendation(project_id, data)}")
            if data["warnings"]:
                lines.append("- Warnings:")
                for warning in data["warnings"]:
                    lines.append(f"  - [!] {warning}")
            lines.append("")
    else:
        lines.append("- No projects discovered.")
        lines.append("")

    lines.append("## Audit")
    for key, value in counts.items():
        lines.append(f"- {key}: {value}")
    if audit["errors"]:
        lines.append("- Audit Status: FAIL")
        for error in audit["errors"]:
            lines.append(f"  - [!] {error}")
    else:
        lines.append(f"- Audit Status: PASS ({len(audit['warnings'])} warnings)")
    if audit["warnings"]:
        for warning in audit["warnings"]:
            lines.append(f"  - [?] {warning}")
    lines.append(f"- Malformed Artifact Warnings: {'YES' if malformed_found else 'NO'}")
    lines.append("")
    lines.append(f"**FINAL STATE**: {'FREEZE_CANDIDATE' if freeze_candidate else 'IN_PROGRESS'}")

    report_dir = output_root / "review_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"freeze_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return str(report_path)


if __name__ == "__main__":
    root = Path("repo_context_lane")
    print(render_status(discover_projects(root)))

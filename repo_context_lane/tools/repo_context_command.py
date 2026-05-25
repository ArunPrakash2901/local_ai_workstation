#!/usr/bin/env python3
"""Local ergonomic command surface for Repo Context Lane."""

import argparse
import sys
import json
from pathlib import Path
from typing import Optional, Iterable

from . import inventory
from . import graphify_plan
from . import summarize
from . import context_packet
from . import packet_review
from . import context_handoff
from . import graphify_plan_review
from . import graphify_run
from . import graphify_intake
from . import status
from . import audit_repo_context_lane

DEFAULT_ROOT = Path("repo_context_lane")

def command_inventory(args: argparse.Namespace) -> int:
    try:
        project_path = Path(args.project)
        output_root = Path(args.output or DEFAULT_ROOT)
        result = inventory.run_inventory(project_path, output_root, dry_run=args.dry_run)
        if args.dry_run:
            print(json.dumps(result, indent=2))
        else:
            project_id = result["project_id"]
            print(f"Inventory completed for {project_id}.")
            print(f"Report: {output_root}/project_inventories/{project_id}_inventory.md")
            print(f"Manifest: {output_root}/project_inventories/{project_id}_inventory.json")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def command_graphify_plan(args: argparse.Namespace) -> int:
    try:
        project_path = Path(args.project)
        output_root = Path(args.output or DEFAULT_ROOT)
        result = graphify_plan.generate_plan(project_path, output_root, dry_run=args.dry_run)
        if args.dry_run:
            print(json.dumps(result, indent=2))
        else:
            project_id = result["project_id"]
            print(f"Graphify plan generated for {project_id}.")
            print(f"Plan report: {output_root}/graphify_plans/{project_id}_plan.md")
            print(f"Plan manifest: {output_root}/graphify_plans/{project_id}_plan.json")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def command_summarize(args: argparse.Namespace) -> int:
    try:
        graph_path = Path(args.graph)
        output_root = Path(args.output or DEFAULT_ROOT)
        result = summarize.summarize_graph(graph_path, output_root, dry_run=args.dry_run)
        if args.dry_run:
            print(json.dumps(result, indent=2))
        else:
            project_id = result["project_id"]
            print(f"Summary generated for {project_id}.")
            print(f"Summary report: {output_root}/graph_summaries/{project_id}_summary.md")
            print(f"Summary manifest: {output_root}/graph_summaries/{project_id}_summary.json")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def command_audit(args: argparse.Namespace) -> int:
    root = Path(args.root or DEFAULT_ROOT)
    audit, counts = audit_repo_context_lane.audit_lane(root)
    print(audit_repo_context_lane.render_audit(root, audit, counts))
    return 1 if audit["errors"] else 0

def command_packet(args: argparse.Namespace) -> int:
    try:
        project_id = args.project
        task_name = args.task
        output_root = Path(args.output or DEFAULT_ROOT)
        result = context_packet.generate_packet(project_id, task_name, output_root, dry_run=args.dry_run)
        if args.dry_run:
            print(json.dumps(result, indent=2))
        else:
            print(f"Context packet generated for {project_id} / {task_name}.")
            print(f"Packet: {output_root}/context_packets/")
            print(f"Report: {output_root}/review_reports/")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def command_packet_list(args: argparse.Namespace) -> int:
    try:
        output_root = Path(args.output or DEFAULT_ROOT)
        packets = packet_review.list_packets(output_root)
        if not packets:
            print("No context packets found.")
            return 0
        
        print(f"{'PROJECT':<20} {'TASK':<25} {'STATUS':<25} {'CREATED'}")
        print("-" * 90)
        for p in packets:
            print(f"{p['project_id']:<20} {p['task_name']:<25} {p['human_approval_status']:<25} {p['created_at']}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def command_packet_review(args: argparse.Namespace) -> int:
    try:
        packet_path = Path(args.packet)
        output_root = Path(args.output or DEFAULT_ROOT)
        is_valid, issues, data = packet_review.review_packet(packet_path, output_root)
        
        if args.dry_run:
            result = {
                "packet": str(packet_path),
                "is_valid": is_valid,
                "issues": issues,
                "status": data.get("human_approval_status")
            }
            print(json.dumps(result, indent=2))
        else:
            if is_valid:
                print(f"Packet {packet_path.name} is VALID.")
            else:
                print(f"Packet {packet_path.name} has ISSUES:")
                for issue in issues:
                    print(f"- [!] {issue}")
        return 0 if is_valid else 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def command_packet_approve(args: argparse.Namespace) -> int:
    try:
        packet_path = Path(args.packet)
        output_root = Path(args.output or DEFAULT_ROOT)
        success, message, data = packet_review.approve_packet(packet_path, output_root, confirm=args.confirm)
        
        if success:
            print(f"SUCCESS: {message}")
            return 0
        else:
            print(f"FAILURE: {message}", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def command_handoff(args: argparse.Namespace) -> int:
    try:
        packet_path = Path(args.packet)
        target = args.target
        output_root = Path(args.output or DEFAULT_ROOT)
        success, message, manifest = context_handoff.generate_handoff(packet_path, target, output_root, dry_run=args.dry_run)
        
        if success:
            if args.dry_run:
                print(json.dumps(manifest, indent=2))
            else:
                print(f"SUCCESS: {message}")
                print(f"Handoff: {output_root}/handoffs/")
                print(f"Manifest: {output_root}/handoff_manifests/")
            return 0
        else:
            print(f"FAILURE: {message}", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def command_graphify_plan_list(args: argparse.Namespace) -> int:
    try:
        output_root = Path(args.output or DEFAULT_ROOT)
        plans = graphify_plan_review.list_plans(output_root)
        if not plans:
            print("No Graphify plans found.")
            return 0
        
        print(f"{'PROJECT':<20} {'STATUS':<35} {'PATH'}")
        print("-" * 100)
        for p in plans:
            print(f"{p['project_id']:<20} {p['approval_status']:<35} {p['path']}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def command_graphify_plan_review(args: argparse.Namespace) -> int:
    try:
        plan_path = Path(args.plan)
        output_root = Path(args.output or DEFAULT_ROOT)
        is_valid, issues, data = graphify_plan_review.review_plan(plan_path, output_root)
        
        if args.dry_run:
            result = {
                "plan": str(plan_path),
                "is_valid": is_valid,
                "issues": issues,
                "status": data.get("approval_status")
            }
            print(json.dumps(result, indent=2))
        else:
            if is_valid:
                print(f"Plan {plan_path.name} is VALID.")
            else:
                print(f"Plan {plan_path.name} has ISSUES:")
                for issue in issues:
                    print(f"- [!] {issue}")
        return 0 if is_valid else 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def command_graphify_plan_approve(args: argparse.Namespace) -> int:
    try:
        plan_path = Path(args.plan)
        output_root = Path(args.output or DEFAULT_ROOT)
        success, message, data = graphify_plan_review.approve_plan(plan_path, output_root, confirm=args.confirm)
        
        if success:
            print(f"SUCCESS: {message}")
            return 0
        else:
            print(f"FAILURE: {message}", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def command_graphify_run(args: argparse.Namespace) -> int:
    try:
        plan_path = Path(args.plan)
        output_root = Path(args.output or DEFAULT_ROOT)
        success, message, manifest = graphify_run.run_graphify(plan_path, output_root, confirm=args.confirm)
        
        if success:
            print(f"SUCCESS: {message}")
            print(f"Output: {manifest['output_path']}")
            return 0
        else:
            print(f"FAILURE: {message}", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def command_graphify_run_status(args: argparse.Namespace) -> int:
    try:
        plan_path = Path(args.plan)
        output_root = Path(args.output or DEFAULT_ROOT)
        status = graphify_run.get_run_status(plan_path, output_root)
        
        print(f"Project: {plan_path.stem.replace('_plan', '')}")
        print(f"Status: {status['status']}")
        if "last_run" in status:
            print(f"Last Run: {status['last_run']['id']}")
            print(f"Started: {status['last_run']['started_at']}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def command_graphify_intake(args: argparse.Namespace) -> int:
    try:
        run_path = Path(args.run)
        output_root = Path(args.output or DEFAULT_ROOT)
        success, message, report = graphify_intake.run_intake(run_path, output_root, dry_run=args.dry_run)
        
        if success:
            if args.dry_run:
                print(json.dumps(report, indent=2))
            else:
                print(f"SUCCESS: {message}")
                print(f"Report: {output_root}/graphify_intake_reports/")
                print(f"Summary: {report['summary_path']}")
            return 0
        else:
            print(f"FAILURE: {message}", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def command_status(args: argparse.Namespace) -> int:
    try:
        output_root = Path(args.output or DEFAULT_ROOT)
        projects = status.discover_projects(output_root)
        print(status.render_status(projects))
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def command_freeze_report(args: argparse.Namespace) -> int:
    try:
        output_root = Path(args.output or DEFAULT_ROOT)
        projects = status.discover_projects(output_root)
        report_path = status.generate_freeze_report(output_root, projects)
        print(f"Freeze report generated: {report_path}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Repo Context Lane command dispatcher.")
    sub = parser.add_subparsers(dest="command", required=True)

    inv = sub.add_parser("inventory", help="Generate project directory inventory.")
    inv.add_argument("--project", required=True, help="Path to project.")
    inv.add_argument("--output", help="Output root.")
    inv.add_argument("--dry-run", action="store_true", help="Print result without writing files.")
    inv.set_defaults(func=command_inventory)

    plan = sub.add_parser("graphify-plan", help="Generate Graphify run plan.")
    plan.add_argument("--project", required=True, help="Path to project.")
    plan.add_argument("--output", help="Output root.")
    plan.add_argument("--dry-run", action="store_true", help="Print result without writing files.")
    plan.set_defaults(func=command_graphify_plan)

    summ = sub.add_parser("summarize", help="Summarize an existing graph.json.")
    summ.add_argument("--graph", required=True, help="Path to graph.json.")
    summ.add_argument("--output", help="Output root.")
    summ.add_argument("--dry-run", action="store_true", help="Print result without writing files.")
    summ.set_defaults(func=command_summarize)

    packet = sub.add_parser("packet", help="Generate a task-specific context packet.")
    packet.add_argument("--project", required=True, help="Project ID.")
    packet.add_argument("--task", required=True, help="Task name.")
    packet.add_argument("--output", help="Output root.")
    packet.add_argument("--dry-run", action="store_true", help="Print result without writing files.")
    packet.set_defaults(func=command_packet)

    p_list = sub.add_parser("packet-list", help="List generated context packets.")
    p_list.add_argument("--output", help="Output root.")
    p_list.set_defaults(func=command_packet_list)

    p_rev = sub.add_parser("packet-review", help="Review a context packet for safety.")
    p_rev.add_argument("--packet", required=True, help="Path to packet JSON.")
    p_rev.add_argument("--output", help="Output root.")
    p_rev.add_argument("--dry-run", action="store_true", help="Print result as JSON.")
    p_rev.set_defaults(func=command_packet_review)

    p_app = sub.add_parser("packet-approve", help="Approve a context packet.")
    p_app.add_argument("--packet", required=True, help="Path to packet JSON.")
    p_app.add_argument("--output", help="Output root.")
    p_app.add_argument("--confirm", action="store_true", help="Required confirmation flag.")
    p_app.set_defaults(func=command_packet_approve)

    handoff = sub.add_parser("handoff", help="Generate a context handoff for a target agent.")
    handoff.add_argument("--packet", required=True, help="Path to approved packet JSON.")
    handoff.add_argument("--target", required=True, choices=["codex", "gemini", "local"], help="Target agent.")
    handoff.add_argument("--output", help="Output root.")
    handoff.add_argument("--dry-run", action="store_true", help="Print result without writing files.")
    handoff.set_defaults(func=command_handoff)

    gp_list = sub.add_parser("graphify-plan-list", help="List generated Graphify run plans.")
    gp_list.add_argument("--output", help="Output root.")
    gp_list.set_defaults(func=command_graphify_plan_list)

    gp_rev = sub.add_parser("graphify-plan-review", help="Review a Graphify plan for safety.")
    gp_rev.add_argument("--plan", required=True, help="Path to plan JSON.")
    gp_rev.add_argument("--output", help="Output root.")
    gp_rev.add_argument("--dry-run", action="store_true", help="Print result as JSON.")
    gp_rev.set_defaults(func=command_graphify_plan_review)

    gp_app = sub.add_parser("graphify-plan-approve", help="Approve a Graphify plan.")
    gp_app.add_argument("--plan", required=True, help="Path to plan JSON.")
    gp_app.add_argument("--output", help="Output root.")
    gp_app.add_argument("--confirm", action="store_true", help="Required confirmation flag.")
    gp_app.set_defaults(func=command_graphify_plan_approve)

    gr = sub.add_parser("graphify-run", help="Execute an approved Graphify run plan.")
    gr.add_argument("--plan", required=True, help="Path to approved plan JSON.")
    gr.add_argument("--output", help="Output root.")
    gr.add_argument("--confirm", action="store_true", help="Required confirmation flag.")
    gr.set_defaults(func=command_graphify_run)

    gr_status = sub.add_parser("graphify-run-status", help="Show status of Graphify runs for a plan.")
    gr_status.add_argument("--plan", required=True, help="Path to plan JSON.")
    gr_status.add_argument("--output", help="Output root.")
    gr_status.set_defaults(func=command_graphify_run_status)

    intake = sub.add_parser("graphify-intake", help="Process results of a Graphify run.")
    intake.add_argument("--run", required=True, help="Path to run manifest JSON.")
    intake.add_argument("--output", help="Output root.")
    intake.add_argument("--dry-run", action="store_true", help="Print result without writing files.")
    intake.set_defaults(func=command_graphify_intake)

    stat = sub.add_parser("status", help="Show Repo Context Lane pipeline status.")
    stat.add_argument("--output", help="Output root.")
    stat.set_defaults(func=command_status)

    freeze = sub.add_parser("freeze-report", help="Generate a lane freeze readiness report.")
    freeze.add_argument("--output", help="Output root.")
    freeze.set_defaults(func=command_freeze_report)

    aud = sub.add_parser("audit", help="Audit Repo Context Lane state.")
    aud.add_argument("--root", help="Lane root.")
    aud.set_defaults(func=command_audit)

    help_cmd = sub.add_parser("help", help="Show help.")
    help_cmd.set_defaults(func=lambda args: (parser.print_help() or 0))

    return parser

def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Read-only operator dashboard for the Local AI Workstation."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable


WS_HOME = Path(os.environ.get("WS_HOME", Path(__file__).resolve().parents[1]))
WS_SCRIPT = WS_HOME / "scripts" / "ws"
SAFETY_MODE = "READ_ONLY"
DISABLED_ACTIONS = (
    "Learning cockpit: not implemented",
    "Research cockpit: not implemented",
    "Provider execution: disabled",
    "Mutation/apply: disabled",
    "Trading execution: disabled",
)
UNSAFE_DEFAULT_READS = (
    ".env",
    "credentials",
    "raw datasets",
    "model files",
    "archives",
    ".git",
)
STATUS_COMMANDS = (
    ("readiness", ("ready",)),
    ("strongholds", ("stronghold-status",)),
    ("handoffs", ("handoff-status",)),
    ("features", ("feature-status",)),
    ("agent_hygiene", ("agent-hygiene",)),
)
PLAIN_CONTROLS = (
    "r refresh dashboard",
    "h show help",
    "q quit",
)


@dataclass
class CommandResult:
    label: str
    args: tuple[str, ...]
    stdout: str
    stderr: str
    returncode: int

    @property
    def command_text(self) -> str:
        return "ws " + " ".join(self.args)

    @property
    def display_text(self) -> str:
        if self.returncode == 0:
            return self.stdout.strip() or "(no output)"
        parts = [f"Command failed with exit code {self.returncode}."]
        if self.stdout.strip():
            parts.append(self.stdout.strip())
        if self.stderr.strip():
            parts.append(self.stderr.strip())
        return "\n".join(parts)


@dataclass
class DashboardData:
    results: dict[str, CommandResult] = field(default_factory=dict)
    command_log: list[str] = field(default_factory=list)


def run_status_command(label: str, args: tuple[str, ...], command_log: list[str]) -> CommandResult:
    if args not in tuple(command for _, command in STATUS_COMMANDS):
        raise ValueError(f"Command is not allowlisted for the read-only dashboard: {args}")

    command_text = "ws " + " ".join(args)
    timestamp = datetime.now().strftime("%H:%M:%S")
    command_log.append(f"[{timestamp}] {command_text}")
    completed = subprocess.run(
        ["bash", str(WS_SCRIPT), *args],
        cwd=WS_HOME,
        capture_output=True,
        text=True,
        check=False,
    )
    return CommandResult(
        label=label,
        args=args,
        stdout=completed.stdout,
        stderr=completed.stderr,
        returncode=completed.returncode,
    )


def collect_dashboard_data(command_log: list[str] | None = None) -> DashboardData:
    log = command_log if command_log is not None else []
    results = {
        label: run_status_command(label, args, log)
        for label, args in STATUS_COMMANDS
    }
    return DashboardData(results=results, command_log=log)


def section(title: str, body: str) -> str:
    line = "=" * len(title)
    return f"{title}\n{line}\n{body.strip() or '(no output)'}"


def render_snapshot(data: DashboardData) -> str:
    sections = [
        "Local AI Workstation Operator Dashboard",
        f"Current safety mode: {SAFETY_MODE}",
        "",
        section("Workstation Readiness", data.results["readiness"].display_text),
        "",
        section("Strongholds", data.results["strongholds"].display_text),
        "",
        section("Recent Handoffs", data.results["handoffs"].display_text),
        "",
        section("Recent Feature Strongholds", data.results["features"].display_text),
        "",
        section("Agent Hygiene", data.results["agent_hygiene"].display_text),
        "",
        section("Disabled Actions", "\n".join(f"- {item}" for item in DISABLED_ACTIONS)),
        "",
        section(
            "Unsafe Default Reads",
            "The dashboard does not read by default: "
            + ", ".join(UNSAFE_DEFAULT_READS),
        ),
        "",
        section("Command Log", "\n".join(data.command_log)),
    ]
    return "\n".join(sections).rstrip() + "\n"


def print_textual_missing_message() -> None:
    print("Textual is not installed. Install later with the approved dependency process.")


def render_plain_dashboard(data: DashboardData, notice: str | None = None) -> str:
    blocks: list[str] = []
    if notice:
        blocks.extend([notice, ""])
    blocks.extend(
        [
            render_snapshot(data).rstrip(),
            "",
            section("Plain Mode Controls", "\n".join(PLAIN_CONTROLS)),
        ]
    )
    return "\n".join(blocks).rstrip() + "\n"


def run_plain_mode(notice: str | None = None) -> int:
    dashboard = collect_dashboard_data([])
    current_notice = notice

    while True:
        print(render_plain_dashboard(dashboard, current_notice), end="")
        current_notice = None
        try:
            choice = input("plain mode [r refresh, h help, q quit]> ").strip().lower()
        except EOFError:
            print()
            return 0

        if choice == "q":
            return 0
        if choice == "r":
            dashboard = collect_dashboard_data(dashboard.command_log)
            continue
        if choice == "h":
            current_notice = "Help: " + " | ".join(PLAIN_CONTROLS)
            continue

        current_notice = "Unknown option. Use r to refresh, h for help, or q to quit."


def build_textual_app():
    try:
        from textual.app import App, ComposeResult
        from textual.binding import Binding
        from textual.containers import Horizontal, VerticalScroll
        from textual.widgets import Footer, Header, Static
    except ImportError:
        return None

    class OperatorDashboard(App):
        CSS = """
        Screen {
            layout: vertical;
        }

        #summary {
            height: auto;
            padding: 1 2;
        }

        #content {
            height: 1fr;
        }

        .column {
            width: 1fr;
            padding: 0 1 1 1;
        }

        .panel {
            border: solid $accent;
            margin: 0 0 1 0;
            padding: 1;
        }

        #help {
            display: none;
            border: solid $warning;
            padding: 1;
            margin: 0 1 1 1;
        }
        """

        BINDINGS = [
            Binding("r", "refresh_dashboard", "Refresh"),
            Binding("q", "quit", "Quit"),
            Binding("?", "toggle_help", "Help"),
        ]

        def __init__(self) -> None:
            super().__init__()
            self.dashboard = collect_dashboard_data([])

        def compose(self) -> ComposeResult:
            yield Header()
            yield Static(self.summary_text(), id="summary")
            with Horizontal(id="content"):
                with VerticalScroll(classes="column"):
                    yield Static(
                        self.dashboard.results["readiness"].display_text,
                        id="readiness",
                        classes="panel",
                    )
                    yield Static(
                        self.dashboard.results["strongholds"].display_text,
                        id="strongholds",
                        classes="panel",
                    )
                    yield Static(
                        self.dashboard.results["features"].display_text,
                        id="features",
                        classes="panel",
                    )
                with VerticalScroll(classes="column"):
                    yield Static(
                        self.dashboard.results["handoffs"].display_text,
                        id="handoffs",
                        classes="panel",
                    )
                    yield Static(
                        self.dashboard.results["agent_hygiene"].display_text,
                        id="agent-hygiene",
                        classes="panel",
                    )
                    yield Static(self.command_log_text(), id="command-log", classes="panel")
            yield Static(
                "\n".join(
                    [
                        "Help",
                        "r refresh dashboard",
                        "q quit",
                        "? toggle help",
                        "",
                        *DISABLED_ACTIONS,
                    ]
                ),
                id="help",
            )
            yield Footer()

        def summary_text(self) -> str:
            disabled = " | ".join(DISABLED_ACTIONS)
            return f"Safety mode: {SAFETY_MODE} | {disabled}"

        def command_log_text(self) -> str:
            return "Command Log\n" + "\n".join(self.dashboard.command_log)

        def action_refresh_dashboard(self) -> None:
            self.dashboard = collect_dashboard_data(self.dashboard.command_log)
            self.query_one("#summary", Static).update(self.summary_text())
            self.query_one("#readiness", Static).update(
                self.dashboard.results["readiness"].display_text
            )
            self.query_one("#strongholds", Static).update(
                self.dashboard.results["strongholds"].display_text
            )
            self.query_one("#features", Static).update(
                self.dashboard.results["features"].display_text
            )
            self.query_one("#handoffs", Static).update(
                self.dashboard.results["handoffs"].display_text
            )
            self.query_one("#agent-hygiene", Static).update(
                self.dashboard.results["agent_hygiene"].display_text
            )
            self.query_one("#command-log", Static).update(self.command_log_text())

        def action_toggle_help(self) -> None:
            help_widget = self.query_one("#help", Static)
            help_widget.styles.display = (
                "block" if help_widget.styles.display == "none" else "none"
            )

    return OperatorDashboard


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only workstation operator dashboard")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--snapshot",
        action="store_true",
        help="print the read-only dashboard as plain text and exit",
    )
    mode_group.add_argument(
        "--plain",
        action="store_true",
        help="launch the stdlib-only line-based dashboard",
    )
    mode_group.add_argument(
        "--textual",
        action="store_true",
        help="require the Textual dashboard; exit safely if Textual is unavailable",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    if args.snapshot:
        data = collect_dashboard_data([])
        print(render_snapshot(data), end="")
        return 0

    if args.plain:
        return run_plain_mode()

    textual_app = build_textual_app()
    if args.textual:
        if textual_app is None:
            print_textual_missing_message()
            return 1
        textual_app().run()
        return 0

    if textual_app is None:
        return run_plain_mode("Textual is not installed. Falling back to plain mode.")

    textual_app().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())

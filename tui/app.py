#!/usr/bin/env python3
"""Read-only operator dashboard for the Local AI Workstation."""

from __future__ import annotations
import argparse
import json
import os
import re
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
    "Learning Cockpit: safe dry-run execution enabled in plain mode",
    "Research cockpit: not implemented",
    "Learning dry-run execution: enabled in plain mode",
    "Learning model execution: disabled",
    "Learning assessment/import/advance execution: disabled",
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
    "l show learning cockpit",
    "x execute recommended safe learning dry-run",
    "h show help",
    "q quit",
)
LEARNING_DRY_RUN_ALLOWLIST = {
    ("learning-run", "--session", "--dry-run"),
    ("learning-review-session", "--dry-run"),
}
LEARNING_DRY_RUN_WRITES = {
    "learning-run": (
        "sessions/*_session_plan.md",
        "practice_log.md",
        "loop_log.md",
        "state.json",
    ),
    "learning-review-session": (
        "sessions/*_review_session_plan.md",
        "practice_log.md",
        "loop_log.md",
        "state.json",
    ),
}


@dataclass(frozen=True)
class LearningAction:
    label: str
    command_text: str
    args: tuple[str, ...]
    risk_class: str
    expected_writes: tuple[str, ...] = ()
    executable: bool = False


@dataclass
class LearningStronghold:
    id: str
    path: Path
    title: str = "unknown"
    current_state: str = "unknown"
    session_status: str = "unknown"
    next_task: str | None = None
    last_completed_task: str | None = None
    state: dict = field(default_factory=dict)
    
    # Artifact paths (Windows strings for display)
    latest_session_plan: str | None = None
    latest_tutor_session: str | None = None
    latest_answer_template: str | None = None
    latest_imported_answers: str | None = None
    latest_assessment: str | None = None
    latest_normal_decision: str | None = None
    latest_review_plan: str | None = None
    latest_review_tutor_session: str | None = None
    latest_review_answer_template: str | None = None
    latest_review_answers: str | None = None
    latest_review_assessment: str | None = None
    latest_review_decision: str | None = None
    
    # Provenance
    linked_tutor_session: str | None = None
    import_success: bool = False

    @property
    def next_action_label(self) -> str:
        return self.compute_next_action().label

    @property
    def next_action_command(self) -> str:
        return self.compute_next_action().command_text

    @property
    def decision_warning(self) -> str | None:
        review_decision = self.artifact_timestamp(
            "last_learning_review_decision_at",
            self.latest_review_decision,
        )
        review_plan = self.artifact_timestamp(
            "last_learning_review_plan_at",
            self.latest_review_plan,
        )
        review_tutor = self.artifact_timestamp(
            "last_review_tutor_session_at",
            self.latest_review_tutor_session,
        )
        if not review_decision:
            return None

        latest_normal_cycle = self.latest_timestamp(
            self.artifact_timestamp("last_tutor_session_at", self.latest_tutor_session),
            self.artifact_timestamp(
                "last_learning_answers_imported_at",
                self.latest_imported_answers,
            ),
            self.artifact_timestamp(
                "last_learning_assessment_at",
                self.latest_assessment,
            ),
            self.artifact_timestamp(
                "last_learning_decision_at",
                self.latest_normal_decision,
            ),
        )
        if latest_normal_cycle and review_decision <= latest_normal_cycle:
            return "Decision artifact may be stale; advancement preview suppressed."
        return None

    def to_win(self, p: str | Path | None) -> str | None:
        if not p:
            return None
        # Simple heuristic for TUI display; real commands use wslpath
        return str(p).replace("/mnt/d/", "D:\\").replace("/", "\\")

    def artifact_timestamp(self, state_key: str, artifact_path: str | None) -> datetime | None:
        explicit = self.parse_timestamp(self.state.get(state_key))
        if explicit:
            return explicit
        return self.timestamp_from_path(artifact_path)

    @staticmethod
    def parse_timestamp(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y%m%d_%H%M%S")
        except ValueError:
            return None

    @classmethod
    def timestamp_from_path(cls, artifact_path: str | None) -> datetime | None:
        if not artifact_path:
            return None
        match = re.search(r"(\d{8}_\d{6})", Path(artifact_path).name)
        return cls.parse_timestamp(match.group(1)) if match else None

    @staticmethod
    def latest_timestamp(*values: datetime | None) -> datetime | None:
        candidates = [value for value in values if value is not None]
        return max(candidates) if candidates else None

    @staticmethod
    def is_newer(candidate: datetime | None, baseline: datetime | None) -> bool:
        return candidate is not None and (baseline is None or candidate > baseline)

    def has_fresh_review_cycle(self) -> bool:
        normal_decision = self.artifact_timestamp(
            "last_learning_decision_at",
            self.latest_normal_decision,
        )
        review_plan = self.artifact_timestamp(
            "last_learning_review_plan_at",
            self.latest_review_plan,
        )
        return self.is_newer(review_plan, normal_decision)

    def review_advance_is_fresh(self) -> bool:
        if self.state.get("last_learning_review_decision") != "ADVANCE_TO_NEXT_TASK":
            return False

        review_assessment = self.artifact_timestamp(
            "last_learning_review_assessment_at",
            self.latest_review_assessment,
        )
        review_decision = self.artifact_timestamp(
            "last_learning_review_decision_at",
            self.latest_review_decision,
        )
        review_plan = self.artifact_timestamp(
            "last_learning_review_plan_at",
            self.latest_review_plan,
        )
        review_tutor = self.artifact_timestamp(
            "last_review_tutor_session_at",
            self.latest_review_tutor_session,
        )
        latest_normal_cycle = self.latest_timestamp(
            self.artifact_timestamp("last_tutor_session_at", self.latest_tutor_session),
            self.artifact_timestamp(
                "last_learning_answers_imported_at",
                self.latest_imported_answers,
            ),
            self.artifact_timestamp(
                "last_learning_assessment_at",
                self.latest_assessment,
            ),
            self.artifact_timestamp(
                "last_learning_decision_at",
                self.latest_normal_decision,
            ),
        )

        return (
            review_assessment is not None
            and self.is_newer(review_decision, review_assessment)
            and (latest_normal_cycle is None or review_decision > latest_normal_cycle)
        )

    def make_action(
        self,
        label: str,
        command_text: str,
        args: tuple[str, ...],
        risk_class: str,
    ) -> LearningAction:
        executable = is_allowlisted_learning_dry_run(args)
        expected_writes = LEARNING_DRY_RUN_WRITES.get(args[0], ()) if executable else ()
        return LearningAction(
            label=label,
            command_text=command_text,
            args=args,
            risk_class=risk_class,
            expected_writes=expected_writes,
            executable=executable,
        )

    def compute_next_action(self) -> LearningAction:
        sid = self.id
        normal_assessment = self.artifact_timestamp(
            "last_learning_assessment_at",
            self.latest_assessment,
        )
        normal_decision = self.artifact_timestamp(
            "last_learning_decision_at",
            self.latest_normal_decision,
        )
        review_assessment = self.artifact_timestamp(
            "last_learning_review_assessment_at",
            self.latest_review_assessment,
        )
        review_decision = self.artifact_timestamp(
            "last_learning_review_decision_at",
            self.latest_review_decision,
        )
        review_plan = self.artifact_timestamp(
            "last_learning_review_plan_at",
            self.latest_review_plan,
        )
        review_tutor = self.artifact_timestamp(
            "last_review_tutor_session_at",
            self.latest_review_tutor_session,
        )

        # A newer current-session assessment invalidates any older normal decision.
        if self.is_newer(normal_assessment, normal_decision):
            return self.make_action(
                "Run learning decision",
                f"ws learning-decision {sid}",
                ("learning-decision", sid),
                "BLUE",
            )

        # The current normal decision controls entry into a review/remediation lane.
        if self.state.get("last_learning_decision") == "REVIEW_CURRENT_TASK":
            if not self.has_fresh_review_cycle():
                return self.make_action(
                    "Generate targeted review session",
                    f"ws learning-review-session {sid} --dry-run",
                    ("learning-review-session", sid, "--dry-run"),
                    "BLUE",
                )

            review_plan_path = self.state.get("last_learning_review_plan_path")
            if self.is_newer(review_plan, review_tutor):
                return self.make_action(
                    "Start review tutor",
                    f"ws learning-run {sid} --review-session --model hermes3:8b --from-plan {self.to_win(review_plan_path)}",
                    (
                        "learning-run",
                        sid,
                        "--review-session",
                        "--model",
                        "hermes3:8b",
                        "--from-plan",
                        self.to_win(review_plan_path) or "",
                    ),
                    "PURPLE",
                )
            if self.session_status == "awaiting_review_answers":
                return self.make_action(
                    "Import review answers",
                    f"ws learning-import-answers {sid} --from-file <answers_file> --review",
                    ("learning-import-answers", sid, "--from-file", "<answers_file>", "--review"),
                    "BLUE",
                )
            if self.session_status == "awaiting_review_assessment":
                return self.make_action(
                    "Assess review answers",
                    f"ws learning-assess {sid} --model hermes3:8b --review",
                    ("learning-assess", sid, "--model", "hermes3:8b", "--review"),
                    "PURPLE",
                )
            if self.is_newer(review_assessment, review_decision) or self.session_status == "review_assessed":
                return self.make_action(
                    "Run review learning decision",
                    f"ws learning-decision {sid} --review",
                    ("learning-decision", sid, "--review"),
                    "BLUE",
                )
            if self.review_advance_is_fresh():
                return self.make_action(
                    "Advance to next task",
                    f"ws learning-advance {sid}",
                    ("learning-advance", sid),
                    "BLUE",
                )
            if review_plan_path and not self.latest_review_tutor_session:
                return self.make_action(
                    "Start review tutor",
                    f"ws learning-run {sid} --review-session --model hermes3:8b --from-plan {self.to_win(review_plan_path)}",
                    (
                        "learning-run",
                        sid,
                        "--review-session",
                        "--model",
                        "hermes3:8b",
                        "--from-plan",
                        self.to_win(review_plan_path) or "",
                    ),
                    "PURPLE",
                )
            return self.make_action(
                "Inspect learning state / run decision",
                f"ws learning-decision {sid}",
                ("learning-decision", sid),
                "BLUE",
            )

        if self.review_advance_is_fresh():
            return self.make_action(
                "Advance to next task",
                f"ws learning-advance {sid}",
                ("learning-advance", sid),
                "BLUE",
            )

        # Normal loop
        if self.next_task and self.session_status in ["ready_for_next_session", "unknown", "LOCAL_CHECKLIST_READY"]:
            # Check if current plan focus matches next_task
            plan_path = self.state.get("last_learning_session_plan_path")
            plan_ts = self.artifact_timestamp(
                "last_learning_session_plan_at",
                self.latest_session_plan,
            )
            tutor_ts = self.artifact_timestamp(
                "last_tutor_session_at",
                self.latest_tutor_session,
            )
            has_current_plan = False
            if plan_path and Path(plan_path).is_file():
                adv_at = self.state.get("last_learning_advanced_at")
                plan_at = self.state.get("last_learning_session_plan_at")
                if not adv_at or (plan_at and plan_at > adv_at):
                    has_current_plan = True

            if not has_current_plan:
                return self.make_action(
                    "Plan next session",
                    f"ws learning-run {sid} --session --dry-run",
                    ("learning-run", sid, "--session", "--dry-run"),
                    "BLUE",
                )
            
            if not self.state.get("last_tutor_session_path") or self.is_newer(plan_ts, tutor_ts):
                return self.make_action(
                    "Start tutor session",
                    f"ws learning-run {sid} --session --model hermes3:8b --from-plan {self.to_win(plan_path)}",
                    (
                        "learning-run",
                        sid,
                        "--session",
                        "--model",
                        "hermes3:8b",
                        "--from-plan",
                        self.to_win(plan_path) or "",
                    ),
                    "PURPLE",
                )
            
            if self.session_status == "awaiting_human_answers":
                return self.make_action(
                    "Import answers",
                    f"ws learning-import-answers {sid} --from-file <answers_file>",
                    ("learning-import-answers", sid, "--from-file", "<answers_file>"),
                    "BLUE",
                )
            
            if self.session_status == "awaiting_assessment":
                return self.make_action(
                    "Assess answers",
                    f"ws learning-assess {sid} --model hermes3:8b",
                    ("learning-assess", sid, "--model", "hermes3:8b"),
                    "PURPLE",
                )
            
            if self.session_status == "assessed":
                return self.make_action(
                    "Record decision",
                    f"ws learning-decision {sid}",
                    ("learning-decision", sid),
                    "BLUE",
                )

        return self.make_action(
            "Inspect learning state / run decision",
            f"ws learning-decision {sid}",
            ("learning-decision", sid),
            "BLUE",
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
    learning_strongholds: list[LearningStronghold] = field(default_factory=list)
    execution_log: list[str] = field(default_factory=list)


def discover_learning_strongholds() -> list[LearningStronghold]:
    base_dir = WS_HOME / "strongholds" / "learning"
    if not base_dir.is_dir():
        return []
    
    strongholds = []
    for d in base_dir.iterdir():
        state_file = d / "state.json"
        if not d.is_dir() or not state_file.is_file():
            continue
            
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            continue
            
        sh = LearningStronghold(
            id=state.get("stronghold_id", d.name),
            path=d,
            title=state.get("title", "unknown"),
            current_state=state.get("current_state", "unknown"),
            session_status=state.get("learning_session_status", "unknown"),
            next_task=state.get("next_learning_task"),
            last_completed_task=state.get("last_completed_learning_task"),
            state=state,
            latest_session_plan=state.get("last_learning_session_plan_path"),
            latest_tutor_session=state.get("last_tutor_session_path"),
            latest_answer_template=state.get("last_tutor_session_path"),
            latest_imported_answers=state.get("last_learning_answers_path"),
            latest_assessment=state.get("last_learning_assessment_path"),
            latest_review_plan=state.get("last_learning_review_plan_path"),
            latest_review_tutor_session=state.get("last_review_tutor_session_path"),
            latest_review_answers=state.get("last_learning_review_answers_path"),
            latest_review_assessment=state.get("last_learning_review_assessment_path"),
            linked_tutor_session=state.get("last_learning_answers_for_tutor_session_path"),
            import_success=state.get("last_learning_answers_import_success", False)
        )
        
        if sh.latest_tutor_session:
            tmpl = sh.latest_tutor_session.replace("_tutor_session.md", "_answer_template.md")
            if Path(tmpl).is_file():
                sh.latest_answer_template = tmpl

        if sh.latest_review_tutor_session:
            review_tmpl = sh.latest_review_tutor_session.replace(
                "_review_tutor_session.md",
                "_review_answer_template.md",
            )
            if Path(review_tmpl).is_file():
                sh.latest_review_answer_template = review_tmpl

        sh.latest_normal_decision = resolve_decision_report(
            sh.path,
            state.get("last_learning_decision_at"),
            "learning_decision",
        )
        sh.latest_review_decision = resolve_decision_report(
            sh.path,
            state.get("last_learning_review_decision_at"),
            "learning_review_decision",
        )

        strongholds.append(sh)
    
    return sorted(strongholds, key=lambda x: x.id)


def report_sort_key(path: Path) -> tuple[datetime, str]:
    timestamp = LearningStronghold.timestamp_from_path(str(path))
    return (timestamp or datetime.min, path.name)


def resolve_decision_report(
    stronghold_path: Path,
    state_timestamp: str | None,
    prefix: str,
) -> str | None:
    reports_dir = stronghold_path / "reports"
    if not reports_dir.is_dir():
        return None

    if state_timestamp:
        state_candidate = reports_dir / f"{prefix}_{state_timestamp}.md"
        if state_candidate.is_file():
            return str(state_candidate)

    matches = sorted(reports_dir.glob(f"{prefix}_*.md"), key=report_sort_key, reverse=True)
    return str(matches[0]) if matches else None


def run_status_command(label: str, args: tuple[str, ...], command_log: list[str]) -> CommandResult:
    command_text = "ws " + " ".join(args)
    timestamp = datetime.now().strftime("%H:%M:%S")
    command_log.append(f"[{timestamp}] {command_text}")
    completed = subprocess.run(
        ["bash", str(WS_SCRIPT), *args],
        cwd=WS_HOME,
        stdin=subprocess.DEVNULL,
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


def is_allowlisted_learning_dry_run(args: tuple[str, ...]) -> bool:
    if not args:
        return False
    if args[0] == "learning-run":
        return len(args) == 4 and (args[0], args[2], args[3]) in LEARNING_DRY_RUN_ALLOWLIST
    if args[0] == "learning-review-session":
        return len(args) == 3 and (args[0], args[2]) in LEARNING_DRY_RUN_ALLOWLIST
    return False


def run_learning_action(action: LearningAction) -> CommandResult:
    if not action.executable or not is_allowlisted_learning_dry_run(action.args):
        raise ValueError("Learning action is not allowlisted for execution.")

    completed = subprocess.run(
        ["bash", str(WS_SCRIPT), *action.args],
        cwd=WS_HOME,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    return CommandResult(
        label=action.label,
        args=action.args,
        stdout=completed.stdout,
        stderr=completed.stderr,
        returncode=completed.returncode,
    )


def first_learning_stronghold(data: DashboardData) -> LearningStronghold | None:
    return data.learning_strongholds[0] if data.learning_strongholds else None


def write_tui_execution_report(
    action: LearningAction,
    result: CommandResult,
    refreshed_action: LearningAction | None,
) -> Path:
    reports_dir = WS_HOME / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = reports_dir / f"TUI_EXECUTION_{timestamp}.md"
    report = "\n".join(
        [
            "# TUI Execution Report",
            "",
            f"- Timestamp: {timestamp}",
            f"- Action Label: {action.label}",
            f"- Risk Class: {action.risk_class}",
            f"- Command: `{action.command_text}`",
            f"- Exit Code: {result.returncode}",
            f"- Refreshed Recommendation: {refreshed_action.label if refreshed_action else 'none'}",
            f"- Refreshed Command: `{refreshed_action.command_text if refreshed_action else 'none'}`",
            "",
            "## Stdout",
            "```text",
            result.stdout.rstrip(),
            "```",
            "",
            "## Stderr",
            "```text",
            result.stderr.rstrip(),
            "```",
            "",
        ]
    )
    report_path.write_text(report, encoding="utf-8", newline="\n")
    return report_path


def collect_dashboard_data(command_log: list[str] | None = None) -> DashboardData:
    log = command_log if command_log is not None else []
    results = {
        label: run_status_command(label, args, log)
        for label, args in STATUS_COMMANDS
    }
    return DashboardData(
        results=results, 
        command_log=log,
        learning_strongholds=discover_learning_strongholds()
    )


def section(title: str, body: str) -> str:
    line = "=" * len(title)
    return f"{title}\n{line}\n{body.strip() or '(no output)'}"


def render_learning_cockpit(strongholds: list[LearningStronghold]) -> str:
    if not strongholds:
        return "No learning strongholds discovered."

    lines = []
    for sh in strongholds:
        lines.append(f"Stronghold: {sh.title} ({sh.id})")
        lines.append(f"  State:     {sh.current_state} | Session Status: {sh.session_status}")
        lines.append(f"  Next Task: {sh.next_task or 'none'}")
        lines.append(f"  Last Done: {sh.last_completed_task or 'none'}")

        lines.append("  Latest Artifacts:")
        if sh.latest_session_plan:
            lines.append(f"    Plan:      {sh.to_win(sh.latest_session_plan)}")
        if sh.latest_tutor_session:
            lines.append(f"    Tutor:     {sh.to_win(sh.latest_tutor_session)}")
        if sh.latest_answer_template:
            lines.append(f"    Template:  {sh.to_win(sh.latest_answer_template)}")
        if sh.latest_imported_answers:
            lines.append(f"    Answers:   {sh.to_win(sh.latest_imported_answers)}")
        if sh.latest_assessment:
            lines.append(f"    Assess:    {sh.to_win(sh.latest_assessment)}")
        if sh.latest_review_plan:
            lines.append(f"    Review Plan: {sh.to_win(sh.latest_review_plan)}")
        if sh.latest_normal_decision:
            lines.append(f"    Decision:  {sh.to_win(sh.latest_normal_decision)}")
        if sh.latest_review_tutor_session:
            lines.append(f"    Review Tutor: {sh.to_win(sh.latest_review_tutor_session)}")
        if sh.latest_review_answer_template:
            lines.append(f"    Review Template: {sh.to_win(sh.latest_review_answer_template)}")
        if sh.latest_review_answers:
            lines.append(f"    Review Answers: {sh.to_win(sh.latest_review_answers)}")
        if sh.latest_review_assessment:
            lines.append(f"    Review Assess: {sh.to_win(sh.latest_review_assessment)}")
        if sh.latest_review_decision:
            lines.append(f"    Review Decision: {sh.to_win(sh.latest_review_decision)}")

        if sh.latest_tutor_session and sh.latest_imported_answers:
            linked = sh.to_win(sh.linked_tutor_session)
            current = sh.to_win(sh.latest_tutor_session)
            status = "[OK] LINKED" if linked == current and sh.import_success else "[!!] STALE/UNLINKED"
            lines.append(f"  Provenance: {status}")
            if linked != current:
                lines.append(f"    Answers link to: {linked or 'None'}")

        if sh.decision_warning:
            lines.append(f"  Warning:    {sh.decision_warning}")

        lines.append(f"  Recommended Next: {sh.next_action_label}")
        lines.append(f"  Command Preview:  {sh.next_action_command}")
        lines.append("")

    return "\n".join(lines).rstrip()


def render_snapshot(data: DashboardData) -> str:
    sections = [
        "Local AI Workstation Operator Dashboard",
        f"Current safety mode: {SAFETY_MODE}",
        "",
        section("Workstation Readiness", data.results["readiness"].display_text),
        "",
        section("Learning Cockpit (Read-Only)", render_learning_cockpit(data.learning_strongholds)),
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
        "",
        section("Plain Execution Log", "\n".join(data.execution_log)),
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
            choice = input("plain mode [r refresh, l learning, x execute, h help, q quit]> ").strip().lower()
        except EOFError:
            print()
            return 0

        if choice == "q":
            return 0
        if choice == "r":
            dashboard = collect_dashboard_data(dashboard.command_log)
            continue
        if choice == "l":
            print("\n" + section("Learning Cockpit (Read-Only)", render_learning_cockpit(dashboard.learning_strongholds)))
            input("\nPress Enter to return to dashboard...")
            continue
        if choice == "x":
            dashboard, current_notice = execute_recommended_learning_action(dashboard)
            continue
        if choice == "h":
            current_notice = "Help: " + " | ".join(PLAIN_CONTROLS)
            continue

        current_notice = "Unknown option. Use r to refresh, l for learning, x to execute, h for help, or q to quit."


def execute_recommended_learning_action(dashboard: DashboardData) -> tuple[DashboardData, str]:
    displayed = first_learning_stronghold(dashboard)
    if displayed is None:
        return dashboard, "No learning stronghold is available for execution."

    approved_action = displayed.compute_next_action()
    if not approved_action.executable:
        return dashboard, "Recommended learning action is preview-only; execution is not enabled."

    refreshed = collect_dashboard_data(dashboard.command_log)
    refreshed.execution_log = dashboard.execution_log
    current = next((item for item in refreshed.learning_strongholds if item.id == displayed.id), None)
    if current is None:
        return refreshed, "Learning stronghold changed during refresh; execution cancelled."

    refreshed_action = current.compute_next_action()
    if (
        refreshed_action.command_text != approved_action.command_text
        or refreshed_action.label != approved_action.label
    ):
        return refreshed, "Recommended action changed during refresh. Execution cancelled; review the updated cockpit state."

    print("\n" + section("Confirm Learning Action", render_action_confirmation(approved_action)))
    confirmation = input("Execute? y/N> ").strip().lower()
    if confirmation != "y":
        return refreshed, "Execution cancelled."

    refreshed.execution_log.append(
        f"[{datetime.now().strftime('%H:%M:%S')}] START {approved_action.command_text}"
    )
    result = run_learning_action(approved_action)

    post_run = collect_dashboard_data(refreshed.command_log)
    post_run.execution_log = refreshed.execution_log
    post_stronghold = next((item for item in post_run.learning_strongholds if item.id == displayed.id), None)
    post_action = post_stronghold.compute_next_action() if post_stronghold else None
    report_path = write_tui_execution_report(approved_action, result, post_action)

    refreshed.execution_log.append(
        f"[{datetime.now().strftime('%H:%M:%S')}] END {approved_action.command_text} exit={result.returncode} report={report_path.name}"
    )
    post_run.execution_log = refreshed.execution_log

    print("\n" + section("Learning Action Result", result.display_text))
    print(f"Execution report: {report_path}")
    input("\nPress Enter to return to dashboard...")

    status = "completed" if result.returncode == 0 else f"failed with exit code {result.returncode}"
    return post_run, f"Learning action {status}; dashboard refreshed."


def render_action_confirmation(action: LearningAction) -> str:
    lines = [
        f"Action: {action.label}",
        "Risk Class: BLUE",
        f"Command: {action.command_text}",
        "Expected mutation: learning stronghold runtime files only",
        "Expected files changed:",
    ]
    lines.extend(f"- {item}" for item in action.expected_writes)
    return "\n".join(lines)


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

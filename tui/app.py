#!/usr/bin/env python3
"""Read-only operator dashboard for the Local AI Workstation."""

from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable


WS_HOME = Path(os.environ.get("WS_HOME", Path(__file__).resolve().parents[1]))
WS_SCRIPT = WS_HOME / "scripts" / "ws"
SAFETY_MODE = "READ_ONLY"
DISABLED_ACTIONS = (
    "Learning safe dry-run actions: enabled in plain mode",
    "Learning model-backed actions: disabled",
    "Learning assessment, import, and advancement: disabled",
    "Research cockpit: not implemented",
    "Provider and browser execution: disabled",
    "Mutation, apply, and trading: disabled",
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
    "1 open learning cockpit from home",
    "x execute the current safe learning dry-run when enabled",
    "h show help",
    "q quit",
)
APP_WIDTH = 108
SIDEBAR_WIDTH = 24
CONTENT_WIDTH = APP_WIDTH - SIDEBAR_WIDTH - 3
UNSAFE_ARTIFACT_PARTS = {
    ".env",
    "credentials",
    "raw datasets",
    "raw_datasets",
    "model files",
    "models",
    "archives",
    ".git",
}
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


def visible_lines(text: str, limit: int = 4) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[:limit] or ["(no output)"]


def fit_text(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    return text[: width - 3] + "..."


def wrap_lines(lines: Iterable[str], width: int) -> list[str]:
    wrapped: list[str] = []
    for line in lines:
        if not line:
            wrapped.append("")
            continue
        chunks = textwrap.wrap(
            line,
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        )
        wrapped.extend(chunks or [""])
    return wrapped


def panel(title: str, lines: Iterable[str], width: int) -> list[str]:
    inner = width - 4
    border = "+" + "-" * (width - 2) + "+"
    title_text = fit_text(title, inner)
    rendered = [border, f"| {title_text.ljust(inner)} |", border]
    for line in wrap_lines(lines, inner):
        rendered.append(f"| {fit_text(line, inner).ljust(inner)} |")
    rendered.append(border)
    return rendered


def merge_columns(left: list[str], right: list[str]) -> list[str]:
    height = max(len(left), len(right))
    output: list[str] = []
    for index in range(height):
        left_line = left[index] if index < len(left) else " " * SIDEBAR_WIDTH
        right_line = right[index] if index < len(right) else " " * CONTENT_WIDTH
        output.append(f"{left_line.ljust(SIDEBAR_WIDTH)}   {right_line}")
    return output


def badge(label: str) -> str:
    return f"[{label}]"


def latest_artifact(*paths: str | None) -> str | None:
    available = [path for path in paths if path]
    if not available:
        return None
    return max(
        available,
        key=lambda item: (
            LearningStronghold.timestamp_from_path(item) or datetime.min,
            item,
        ),
    )


def artifact_label(path: str | None) -> str:
    if not path:
        return "none"
    return Path(path).name


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


def render_header(title: str, dashboard: DashboardData) -> list[str]:
    readiness = dashboard.results["readiness"]
    readiness_badge = "READY" if readiness.returncode == 0 else "CHECK"
    refreshed = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    headline = f"{title}  {badge(SAFETY_MODE)} {badge('SAFE_DRY_RUN')} {badge(readiness_badge)}"
    return panel(
        "Local AI Workstation",
        [
            headline,
            f"Last refresh: {refreshed}",
        ],
        APP_WIDTH,
    )


def render_sidebar(active: str) -> list[str]:
    items = [
        ("home", "Home"),
        ("learning", "Learning"),
        ("research", "Research disabled"),
        ("handoffs", "Handoffs"),
        ("health", "System Health"),
        ("quit", "Quit"),
    ]
    lines = []
    for key, label in items:
        marker = ">" if key == active else " "
        lines.append(f"{marker} {label}")
    return panel("Navigation", lines, SIDEBAR_WIDTH)


def render_log_drawer(dashboard: DashboardData) -> list[str]:
    command_lines = dashboard.command_log[-4:] or ["No read-only commands recorded."]
    execution_lines = dashboard.execution_log[-3:] or ["No plain-mode executions recorded."]
    lines = [
        "Recent backend status reads:",
        *command_lines,
        "",
        "Recent learning execution log:",
        *execution_lines,
    ]
    return panel("Status / Log Drawer", lines, APP_WIDTH)


def render_shell(
    dashboard: DashboardData,
    *,
    active: str,
    breadcrumbs: str,
    main_lines: list[str],
    controls: str,
    notice: str | None = None,
) -> str:
    blocks: list[str] = []
    if notice:
        blocks.extend(panel("Notice", [notice], APP_WIDTH))
    blocks.extend(render_header("Operator Cockpit", dashboard))
    blocks.extend(panel("Breadcrumbs", [breadcrumbs], APP_WIDTH))
    blocks.extend(merge_columns(render_sidebar(active), main_lines))
    blocks.extend(render_log_drawer(dashboard))
    blocks.extend(panel("Controls", [controls], APP_WIDTH))
    return "\n".join(blocks).rstrip() + "\n"


def render_home_main(dashboard: DashboardData) -> list[str]:
    cards: list[str] = []
    card_lines: list[list[str]] = [
        panel(
            "Workstation Readiness",
            visible_lines(dashboard.results["readiness"].display_text),
            CONTENT_WIDTH,
        ),
        panel(
            "Strongholds",
            visible_lines(dashboard.results["strongholds"].display_text),
            CONTENT_WIDTH,
        ),
        panel(
            "Recent Handoffs",
            visible_lines(dashboard.results["handoffs"].display_text),
            CONTENT_WIDTH,
        ),
        panel(
            "Recent Feature Strongholds",
            visible_lines(dashboard.results["features"].display_text),
            CONTENT_WIDTH,
        ),
        panel(
            "Agent Hygiene",
            visible_lines(dashboard.results["agent_hygiene"].display_text),
            CONTENT_WIDTH,
        ),
        panel(
            "Actions",
            [
                "[1] Open Learning",
                "[2] Open Handoffs",
                "[3] Open System Health",
                "[0] Quit",
            ],
            CONTENT_WIDTH,
        ),
    ]
    for card in card_lines:
        cards.extend(card)
    return cards


def provenance_lines(sh: LearningStronghold) -> list[str]:
    if not sh.latest_tutor_session or not sh.latest_imported_answers:
        return [f"{badge('MANUAL_REQUIRED')} No linked answers imported for the current session."]
    linked = sh.to_win(sh.linked_tutor_session)
    current = sh.to_win(sh.latest_tutor_session)
    if linked == current and sh.import_success:
        return [f"{badge('LINKED')} Answers match the current tutor session."]
    lines = [f"{badge('STALE')} Answers are not linked to the current tutor session."]
    if linked != current:
        lines.append(f"Linked answers point to: {linked or 'none'}")
    return lines


def render_learning_main(
    sh: LearningStronghold | None,
    *,
    show_backend_command: bool,
) -> list[str]:
    if sh is None:
        return panel("Learning", ["No learning strongholds discovered."], CONTENT_WIDTH)

    action = sh.compute_next_action()
    latest_plan = latest_artifact(sh.latest_session_plan, sh.latest_review_plan)
    latest_assessment = latest_artifact(sh.latest_assessment, sh.latest_review_assessment)
    cards: list[str] = []
    cards.extend(
        panel(
            "Current Task",
            [
                sh.title,
                f"Current task: {sh.next_task or 'none'}",
                f"Last completed: {sh.last_completed_task or 'none'}",
                f"Session status: {sh.session_status}",
            ],
            CONTENT_WIDTH,
        )
    )
    recommended_lines = [
        f"{badge(action.risk_class)} {action.label}",
        (
            f"{badge('SAFE_DRY_RUN')} Ready for controlled execution."
            if action.executable
            else f"{badge('DISABLED')} Action requires manual command / future phase."
        ),
    ]
    if sh.decision_warning:
        recommended_lines.append(f"{badge('STALE')} {sh.decision_warning}")
    cards.extend(panel("Recommended Action", recommended_lines, CONTENT_WIDTH))
    cards.extend(panel("Provenance", provenance_lines(sh), CONTENT_WIDTH))
    cards.extend(
        panel(
            "Latest Artifacts",
            [
                f"Plan: {artifact_label(latest_plan)}",
                f"Assessment: {artifact_label(latest_assessment)}",
                f"Decision: {artifact_label(sh.latest_normal_decision)}",
                f"Review decision: {artifact_label(sh.latest_review_decision)}",
            ],
            CONTENT_WIDTH,
        )
    )
    cards.extend(
        panel(
            "Safety",
            [
                f"{badge(SAFETY_MODE)} Snapshot remains read-only.",
                *DISABLED_ACTIONS,
            ],
            CONTENT_WIDTH,
        )
    )
    if show_backend_command:
        cards.extend(panel("Backend Command", [action.command_text], CONTENT_WIDTH))
    action_lines = [
        "[1] Run Safe Dry-Run"
        if action.executable
        else "[disabled] Action requires manual command / future phase",
        "[2] View Latest Plan",
        "[3] View Latest Assessment",
        "[4] Hide Backend Command" if show_backend_command else "[4] Show Backend Command",
        "[5] Refresh",
        "[0] Back",
    ]
    cards.extend(panel("Actions", action_lines, CONTENT_WIDTH))
    return cards


def render_handoffs_main(dashboard: DashboardData) -> list[str]:
    return panel(
        "Recent Handoffs",
        visible_lines(dashboard.results["handoffs"].display_text, limit=12),
        CONTENT_WIDTH,
    )


def render_health_main(dashboard: DashboardData) -> list[str]:
    lines = [
        "Workstation readiness:",
        *visible_lines(dashboard.results["readiness"].display_text, limit=8),
        "",
        "Agent hygiene:",
        *visible_lines(dashboard.results["agent_hygiene"].display_text, limit=8),
    ]
    return panel("System Health", lines, CONTENT_WIDTH)


def render_plain_screen(
    dashboard: DashboardData,
    *,
    screen: str,
    show_backend_command: bool,
    notice: str | None = None,
) -> str:
    if screen == "learning":
        sh = first_learning_stronghold(dashboard)
        title = sh.title if sh else "Learning"
        return render_shell(
            dashboard,
            active="learning",
            breadcrumbs=f"Home > Learning > {title}",
            main_lines=render_learning_main(sh, show_backend_command=show_backend_command),
            controls="1 run | 2 plan | 3 assessment | 4 backend command | 5 refresh | 0 back | q quit",
            notice=notice,
        )
    if screen == "handoffs":
        return render_shell(
            dashboard,
            active="handoffs",
            breadcrumbs="Home > Handoffs",
            main_lines=render_handoffs_main(dashboard),
            controls="r refresh | 0 back | q quit",
            notice=notice,
        )
    if screen == "health":
        return render_shell(
            dashboard,
            active="health",
            breadcrumbs="Home > System Health",
            main_lines=render_health_main(dashboard),
            controls="r refresh | 0 back | q quit",
            notice=notice,
        )
    return render_shell(
        dashboard,
        active="home",
        breadcrumbs="Home",
        main_lines=render_home_main(dashboard),
        controls="1 learning | 2 handoffs | 3 health | r refresh | h help | q quit",
        notice=notice,
    )


def path_is_within(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def read_learning_artifact(sh: LearningStronghold, artifact_path: str | None) -> tuple[Path, str]:
    if not artifact_path:
        raise ValueError("No artifact is available for this slot.")

    candidate = Path(artifact_path).resolve()
    root = sh.path.resolve()
    if not candidate.is_file() or candidate.suffix.lower() != ".md":
        raise ValueError("Selected artifact is not a readable markdown file.")
    if not path_is_within(root, candidate):
        raise ValueError("Selected artifact is outside the learning stronghold.")
    lowered_parts = {part.lower() for part in candidate.parts}
    if lowered_parts.intersection(UNSAFE_ARTIFACT_PARTS):
        raise ValueError("Selected artifact resolves into a blocked unsafe path.")
    return candidate, candidate.read_text(encoding="utf-8")


def show_learning_artifact(sh: LearningStronghold, label: str, artifact_path: str | None) -> str | None:
    try:
        path, body = read_learning_artifact(sh, artifact_path)
    except ValueError as exc:
        return str(exc)

    print()
    print("\n".join(panel(f"Artifact Viewer - {label}", [str(path)], APP_WIDTH)))
    print(body.rstrip() or "(artifact is empty)")
    input("\nPress Enter to return to Learning...")
    return None


def run_plain_mode(notice: str | None = None) -> int:
    dashboard = collect_dashboard_data([])
    current_notice = notice
    screen = "home"
    show_backend_command = False

    while True:
        print(
            render_plain_screen(
                dashboard,
                screen=screen,
                show_backend_command=show_backend_command,
                notice=current_notice,
            ),
            end="",
        )
        current_notice = None
        try:
            choice = input("select action> ").strip().lower()
        except EOFError:
            print()
            return 0

        if choice == "q":
            return 0
        if choice == "h":
            current_notice = "Help: " + " | ".join(PLAIN_CONTROLS)
            continue

        if screen == "home":
            if choice == "1":
                screen = "learning"
                continue
            if choice == "2":
                screen = "handoffs"
                continue
            if choice == "3":
                screen = "health"
                continue
            if choice == "r":
                dashboard = collect_dashboard_data(dashboard.command_log)
                continue
            if choice == "0":
                return 0
            current_notice = "Unknown option. Use 1, 2, 3, r, h, or q from Home."
            continue

        if screen == "learning":
            sh = first_learning_stronghold(dashboard)
            latest_plan = latest_artifact(
                sh.latest_session_plan if sh else None,
                sh.latest_review_plan if sh else None,
            )
            latest_assessment = latest_artifact(
                sh.latest_assessment if sh else None,
                sh.latest_review_assessment if sh else None,
            )
            if choice in {"0"}:
                screen = "home"
                show_backend_command = False
                continue
            if choice in {"1", "x"}:
                dashboard, current_notice = execute_recommended_learning_action(dashboard)
                continue
            if choice == "2" and sh is not None:
                current_notice = show_learning_artifact(sh, "Latest Plan", latest_plan)
                continue
            if choice == "3" and sh is not None:
                current_notice = show_learning_artifact(
                    sh,
                    "Latest Assessment",
                    latest_assessment,
                )
                continue
            if choice == "4":
                show_backend_command = not show_backend_command
                continue
            if choice in {"5", "r"}:
                dashboard = collect_dashboard_data(dashboard.command_log)
                continue
            current_notice = "Unknown option. Use the numbered actions, x, or 0 to go back."
            continue

        if screen in {"handoffs", "health"}:
            if choice == "0":
                screen = "home"
                continue
            if choice == "r":
                dashboard = collect_dashboard_data(dashboard.command_log)
                continue
            current_notice = "Unknown option. Use r to refresh, 0 to go back, or q to quit."


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
    reveal = input("Show backend command before confirming? y/N> ").strip().lower()
    if reveal == "y":
        print("\n" + section("Backend Command", approved_action.command_text))
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
        "Expected mutation: learning stronghold runtime files only",
        "Expected files changed:",
    ]
    lines.extend(f"- {item}" for item in action.expected_writes)
    lines.append("Backend command: hidden until requested")
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

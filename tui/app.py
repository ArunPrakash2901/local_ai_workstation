#!/usr/bin/env python3
"""Read-only operator dashboard for the Local AI Workstation."""

from __future__ import annotations
import argparse
import json
import os
import re
import shutil
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
DEFAULT_STATUS_TIMEOUT_SECONDS = 12
DEBUG_ENABLED = os.environ.get("WS_TUI_DEBUG", "").strip() == "1"


def debug_log(phase: str) -> None:
    if DEBUG_ENABLED:
        print(f"[DEBUG] {phase}", file=sys.stderr, flush=True)


def status_timeout_seconds() -> int:
    raw = os.environ.get("WS_TUI_STATUS_TIMEOUT", str(DEFAULT_STATUS_TIMEOUT_SECONDS)).strip()
    try:
        seconds = int(raw)
    except ValueError:
        return DEFAULT_STATUS_TIMEOUT_SECONDS
    return max(1, min(seconds, 120))


def normalize_subprocess_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="replace")
        except Exception:
            return value.decode(errors="replace")
    if isinstance(value, str):
        return value
    return str(value)


def command_log_status(result: "CommandResult") -> str:
    if result.returncode == 124:
        return "TIMEOUT"
    if result.returncode == 0:
        return "OK"
    return "FAIL"


def readiness_badge(result: "CommandResult") -> str:
    if result.returncode == 124:
        return "TIMEOUT"
    if result.returncode != 0:
        return "CHECK"
    if "[FAIL]" in result.stdout or "[FAIL]" in result.stderr:
        return "DEGRADED"
    return "READY"


def append_command_log_entry(command_log: list[str], status: str, command_text: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    command_log.append(f"[{timestamp}] {status} {command_text}")


@dataclass(frozen=True)
class LayoutSpec:
    mode: str
    width: int
    content_width: int
    sidebar_width: int


@dataclass(frozen=True)
class IconSet:
    ok: str
    warning: str
    blocked: str
    run: str
    dry_run: str
    linked: str
    artifact: str
    disabled: str


@dataclass(frozen=True)
class LearningAction:
    label: str
    command_text: str
    args: tuple[str, ...]
    risk_class: str
    expected_writes: tuple[str, ...] = ()
    executable: bool = False


@dataclass(frozen=True)
class LearningArtifact:
    key: str
    label: str
    path: str | None
    timestamp: datetime | None
    exists: bool
    relative_path: str


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
        if self.returncode == 124:
            timeout_line = ""
            stderr_lines: list[str] = []
            for line in self.stderr.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith("[TIMEOUT]") and not timeout_line:
                    timeout_line = stripped
                    continue
                stderr_lines.append(stripped)
            parts: list[str] = []
            if timeout_line:
                parts.append(timeout_line)
            if self.stdout.strip():
                parts.append(self.stdout.strip())
            if stderr_lines:
                parts.append("\n".join(stderr_lines))
            return "\n".join(parts) or f"[TIMEOUT] {self.command_text} timed out."
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
    timeout_seconds = status_timeout_seconds()
    debug_log(f"collecting status: {command_text}")
    try:
        completed = subprocess.run(
            ["bash", str(WS_SCRIPT), *args],
            cwd=WS_HOME,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        timeout_message = f"[TIMEOUT] {command_text} did not complete within {timeout_seconds}s"
        partial_stdout = normalize_subprocess_text(exc.stdout)
        partial_stderr = normalize_subprocess_text(exc.stderr)
        stderr_parts = [timeout_message]
        if partial_stderr.strip():
            stderr_parts.append(partial_stderr.strip())
        result = CommandResult(
            label=label,
            args=args,
            stdout=partial_stdout,
            stderr="\n".join(stderr_parts),
            returncode=124,
        )
        append_command_log_entry(command_log, command_log_status(result), command_text)
        return result
    except OSError as exc:
        launch_message = f"[ERROR] {command_text} failed to start: {exc}"
        result = CommandResult(
            label=label,
            args=args,
            stdout="",
            stderr=launch_message,
            returncode=127,
        )
        append_command_log_entry(command_log, command_log_status(result), command_text)
        return result
    result = CommandResult(
        label=label,
        args=args,
        stdout=normalize_subprocess_text(completed.stdout),
        stderr=normalize_subprocess_text(completed.stderr),
        returncode=completed.returncode,
    )
    append_command_log_entry(command_log, command_log_status(result), command_text)
    return result


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
        stdout=normalize_subprocess_text(completed.stdout),
        stderr=normalize_subprocess_text(completed.stderr),
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
    debug_log("collecting status")
    results: dict[str, CommandResult] = {}
    for label, args in STATUS_COMMANDS:
        results[label] = run_status_command(label, args, log)
    debug_log("collecting learning strongholds")
    learning_strongholds = discover_learning_strongholds()
    return DashboardData(
        results=results,
        command_log=log,
        learning_strongholds=learning_strongholds,
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


def layout_spec() -> LayoutSpec:
    width = max(shutil.get_terminal_size((108, 24)).columns, 48)
    if width >= 110:
        sidebar = min(24, max(18, width // 5))
        return LayoutSpec(
            mode="wide",
            width=width,
            content_width=max(width - sidebar - 3, 42),
            sidebar_width=sidebar,
        )
    if width >= 78:
        return LayoutSpec(
            mode="medium",
            width=width,
            content_width=width,
            sidebar_width=0,
        )
    return LayoutSpec(
        mode="narrow",
        width=width,
        content_width=width,
        sidebar_width=0,
    )


def icon_mode() -> str:
    requested = os.environ.get("WS_TUI_ICONS", "auto").strip().lower()
    encoding = sys.stdout.encoding or ""
    unicode_supported = False
    if encoding:
        try:
            "✓⚠✕▶◇↔▣○".encode(encoding)
            unicode_supported = True
        except UnicodeEncodeError:
            unicode_supported = False
        except LookupError:
            unicode_supported = False
    if requested == "ascii":
        return "ascii"
    if requested == "unicode":
        if unicode_supported:
            return "unicode"
        debug_log(
            f"unicode icons requested but stdout encoding '{encoding or 'unknown'}' cannot render them; using ascii fallback"
        )
        return "ascii"
    return "unicode" if unicode_supported else "ascii"


def icons() -> IconSet:
    if icon_mode() == "unicode":
        return IconSet(
            ok="✓",
            warning="⚠",
            blocked="✕",
            run="▶",
            dry_run="◇",
            linked="↔",
            artifact="▣",
            disabled="○",
        )
    return IconSet(
        ok="[OK]",
        warning="[!!]",
        blocked="[X]",
        run="[Run]",
        dry_run="[Dry]",
        linked="[LINK]",
        artifact="[File]",
        disabled="[Disabled]",
    )


def merge_columns(left: list[str], right: list[str], spec: LayoutSpec) -> list[str]:
    height = max(len(left), len(right))
    output: list[str] = []
    for index in range(height):
        left_line = left[index] if index < len(left) else " " * spec.sidebar_width
        right_line = right[index] if index < len(right) else " " * spec.content_width
        output.append(f"{left_line.ljust(spec.sidebar_width)}   {right_line}")
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


def format_artifact_timestamp(timestamp: datetime | None) -> str:
    return timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "n/a"


def artifact_relative_path(sh: LearningStronghold, artifact_path: str | None) -> str:
    if not artifact_path:
        return "none"
    try:
        return str(Path(artifact_path).resolve().relative_to(sh.path.resolve()))
    except ValueError:
        return "outside stronghold"


def artifact_file_timestamp(path: str | None) -> datetime | None:
    if not path:
        return None
    candidate = Path(path)
    if not candidate.is_file():
        return None
    return datetime.fromtimestamp(candidate.stat().st_mtime)


def learning_artifact_catalog(sh: LearningStronghold) -> list[LearningArtifact]:
    specs = [
        (
            "latest_session_plan",
            "Latest Session Plan",
            sh.latest_session_plan,
            "last_learning_session_plan_at",
        ),
        (
            "latest_tutor_session",
            "Latest Tutor Session",
            sh.latest_tutor_session,
            "last_tutor_session_at",
        ),
        (
            "latest_answer_template",
            "Latest Answer Template",
            sh.latest_answer_template,
            None,
        ),
        (
            "latest_human_answers",
            "Latest Human Answers",
            sh.latest_imported_answers,
            "last_learning_answers_imported_at",
        ),
        (
            "latest_assessment",
            "Latest Assessment",
            sh.latest_assessment,
            "last_learning_assessment_at",
        ),
        (
            "latest_decision",
            "Latest Decision",
            sh.latest_normal_decision,
            "last_learning_decision_at",
        ),
        (
            "latest_review_plan",
            "Latest Review Plan",
            sh.latest_review_plan,
            "last_learning_review_plan_at",
        ),
        (
            "latest_review_tutor_session",
            "Latest Review Tutor Session",
            sh.latest_review_tutor_session,
            "last_review_tutor_session_at",
        ),
        (
            "latest_review_answer_template",
            "Latest Review Answer Template",
            sh.latest_review_answer_template,
            None,
        ),
        (
            "latest_review_answers",
            "Latest Review Answers",
            sh.latest_review_answers,
            "last_learning_review_answers_imported_at",
        ),
        (
            "latest_review_assessment",
            "Latest Review Assessment",
            sh.latest_review_assessment,
            "last_learning_review_assessment_at",
        ),
        (
            "latest_review_decision",
            "Latest Review Decision",
            sh.latest_review_decision,
            "last_learning_review_decision_at",
        ),
        (
            "progress_log",
            "Progress Log",
            str(sh.path / "progress.md"),
            None,
        ),
        (
            "practice_log",
            "Practice Log",
            str(sh.path / "practice_log.md"),
            None,
        ),
    ]
    artifacts: list[LearningArtifact] = []
    for key, label, path, state_key in specs:
        candidate = Path(path) if path else None
        timestamp = (
            sh.artifact_timestamp(state_key, path)
            if state_key
            else LearningStronghold.timestamp_from_path(path)
        )
        if timestamp is None:
            timestamp = artifact_file_timestamp(path)
        artifacts.append(
            LearningArtifact(
                key=key,
                label=label,
                path=path,
                timestamp=timestamp,
                exists=bool(candidate and candidate.is_file()),
                relative_path=artifact_relative_path(sh, path),
            )
        )
    return artifacts


def artifact_by_key(sh: LearningStronghold, key: str) -> LearningArtifact | None:
    return next((artifact for artifact in learning_artifact_catalog(sh) if artifact.key == key), None)


def latest_catalog_artifact(sh: LearningStronghold, keys: tuple[str, ...]) -> LearningArtifact | None:
    candidates = [
        artifact
        for artifact in learning_artifact_catalog(sh)
        if artifact.key in keys and artifact.path
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            item.timestamp or datetime.min,
            item.path or "",
        ),
    )


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
    readiness_state = readiness_badge(data.results["readiness"])
    sections = [
        "Local AI Workstation Operator Dashboard",
        f"Current safety mode: {SAFETY_MODE}",
        "",
        section(
            f"Workstation Readiness ({readiness_state})",
            data.results["readiness"].display_text,
        ),
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


def recent_learning_events(sh: LearningStronghold | None) -> list[str]:
    if sh is None:
        return ["No learning stronghold discovered."]
    loop_log = sh.path / "loop_log.md"
    if not loop_log.is_file():
        return ["No loop log found."]
    lines = [line.strip() for line in loop_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    return lines[-4:] or ["No recent learning events."]


def human_disabled_reason(action: LearningAction) -> str:
    if action.risk_class == "PURPLE":
        return "Requires local model execution; future phase."
    if action.label.startswith("Import"):
        return "Requires answer file picker; future phase."
    if action.label.startswith("Advance"):
        return "Requires manual approval; future phase."
    return "Requires manual command or a future phase."


def render_header(title: str, dashboard: DashboardData, spec: LayoutSpec) -> list[str]:
    readiness = dashboard.results["readiness"]
    readiness_state = readiness_badge(readiness)
    refreshed = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ico = icons()
    status = ico.ok if readiness_state == "READY" else ico.warning
    headline = f"{title} | {status} {readiness_state} | {badge(SAFETY_MODE)} {badge('SAFE_DRY_RUN')} | {refreshed}"
    return [fit_text(headline, spec.width)]


def render_sidebar(active: str, spec: LayoutSpec) -> list[str]:
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
    return panel("Nav", lines, spec.sidebar_width)


def render_log_drawer(dashboard: DashboardData, spec: LayoutSpec) -> list[str]:
    command_lines = dashboard.command_log[-4:] or ["No read-only commands recorded."]
    execution_lines = dashboard.execution_log[-3:] or ["No plain-mode executions recorded."]
    lines = [
        "Status reads:",
        *command_lines,
        "",
        "Execution log:",
        *execution_lines,
    ]
    return panel("Recent Events", lines, spec.width)


def render_shell(
    dashboard: DashboardData,
    *,
    active: str,
    breadcrumbs: str,
    main_lines: list[str],
    controls: str,
    spec: LayoutSpec,
    notice: str | None = None,
) -> str:
    blocks: list[str] = []
    if notice:
        blocks.extend(panel("Notice", [notice], spec.width))
    blocks.extend(render_header("Operator Cockpit", dashboard, spec))
    blocks.append(f"Path: {fit_text(breadcrumbs, max(spec.width - 6, 1))}")
    blocks.append("-" * spec.width)
    if spec.mode == "wide":
        blocks.extend(merge_columns(render_sidebar(active, spec), main_lines, spec))
    else:
        compact_menu = {
            "home": "[1] Learning  [2] Artifacts  [3] System",
            "learning": "[1] Learning  [2] Artifacts  [3] System",
            "artifacts": "[1] Learning  [2] Artifacts  [3] System",
            "handoffs": "[1] Learning  [2] Artifacts  [3] System",
            "health": "[1] Learning  [2] Artifacts  [3] System",
        }.get(active, "[1] Learning  [2] Artifacts  [3] System")
        blocks.append(compact_menu)
        blocks.append("-" * spec.width)
        blocks.extend(main_lines)
    blocks.extend(render_log_drawer(dashboard, spec))
    blocks.append(f"Keys: {fit_text(controls, max(spec.width - 6, 1))}")
    return "\n".join(blocks).rstrip() + "\n"


def terminal_section(title: str, lines: Iterable[str], width: int) -> list[str]:
    rendered = [f"{title}", "-" * min(len(title), width)]
    rendered.extend(wrap_lines(lines, width))
    rendered.append("")
    return rendered


def render_home_main(dashboard: DashboardData, spec: LayoutSpec) -> list[str]:
    width = spec.content_width
    lines: list[str] = []
    lines.extend(
        terminal_section(
            "System",
            visible_lines(dashboard.results["readiness"].display_text, limit=5),
            width,
        )
    )
    lines.extend(
        terminal_section(
            "Active Work",
            visible_lines(dashboard.results["strongholds"].display_text, limit=5),
            width,
        )
    )
    lines.extend(
        terminal_section(
            "Suggested",
            [
                "[1] Learning",
                "[2] Artifacts",
                "[3] System",
                "[q] Quit",
            ],
            width,
        )
    )
    return lines


def provenance_lines(sh: LearningStronghold) -> list[str]:
    ico = icons()
    if not sh.latest_tutor_session or not sh.latest_imported_answers:
        return [f"{ico.warning} No linked answers imported for the current session."]
    linked = sh.to_win(sh.linked_tutor_session)
    current = sh.to_win(sh.latest_tutor_session)
    if linked == current and sh.import_success:
        return [f"{ico.linked} Answers match the current tutor session."]
    lines = [f"{ico.warning} Answers are not linked to the current tutor session."]
    if linked != current:
        lines.append(f"Linked answers point to: {linked or 'none'}")
    return lines


def render_learning_main(
    sh: LearningStronghold | None,
    *,
    show_backend_command: bool,
    spec: LayoutSpec,
) -> list[str]:
    if sh is None:
        return terminal_section("Learning", ["No learning strongholds discovered."], spec.content_width)

    action = sh.compute_next_action()
    latest_plan = latest_catalog_artifact(
        sh,
        ("latest_session_plan", "latest_review_plan"),
    )
    latest_assessment = latest_catalog_artifact(
        sh,
        ("latest_assessment", "latest_review_assessment"),
    )
    ico = icons()
    width = spec.content_width
    lines: list[str] = []
    lines.extend(
        terminal_section(
            "Current Focus",
            [
                sh.title,
                f"Task: {sh.next_task or 'none'}",
                f"Last completed: {sh.last_completed_task or 'none'}",
                f"Session: {sh.session_status}",
            ],
            width,
        )
    )
    recommended_lines = [f"{ico.run if action.executable else ico.disabled} {action.label} [{action.risk_class}]"]
    if action.executable:
        recommended_lines.append(f"{ico.dry_run} Ready for controlled dry-run execution.")
    else:
        recommended_lines.append(human_disabled_reason(action))
    if sh.decision_warning:
        recommended_lines.append(f"{ico.warning} {sh.decision_warning}")
    lines.extend(terminal_section("Next Action", recommended_lines, width))
    lines.extend(terminal_section("Evidence / Provenance", provenance_lines(sh), width))
    lines.extend(
        terminal_section(
            "Artifact Shortcuts",
            [
                f"{ico.artifact} Plan: {artifact_label(latest_plan.path if latest_plan else None)}",
                f"{ico.artifact} Assessment: {artifact_label(latest_assessment.path if latest_assessment else None)}",
                f"{ico.artifact} Decision: {artifact_label(sh.latest_normal_decision)}",
                f"{ico.artifact} Review decision: {artifact_label(sh.latest_review_decision)}",
            ],
            width,
        )
    )
    lines.extend(terminal_section("Recent Learning Events", recent_learning_events(sh), width))
    if show_backend_command:
        lines.extend(
            terminal_section(
                "Backend Command Drawer",
                [action.command_text],
                width,
            )
        )
    action_lines = [
        f"[1] Run safe dry-run"
        if action.executable
        else f"[1 disabled] {human_disabled_reason(action)}",
        "[2] Open artifact browser",
        "[3] View Latest Plan",
        "[4] View Latest Assessment",
        "[5] Hide Backend Command" if show_backend_command else "[5] Show Backend Command",
        "[6] Refresh",
        "[0] Back",
    ]
    lines.extend(terminal_section("Human Actions", action_lines, width))
    return lines


def render_handoffs_main(dashboard: DashboardData, spec: LayoutSpec) -> list[str]:
    return terminal_section(
        "Recent Handoffs",
        visible_lines(dashboard.results["handoffs"].display_text, limit=12),
        spec.content_width,
    )


def render_health_main(dashboard: DashboardData, spec: LayoutSpec) -> list[str]:
    lines = [
        "Workstation readiness:",
        *visible_lines(dashboard.results["readiness"].display_text, limit=8),
        "",
        "Agent hygiene:",
        *visible_lines(dashboard.results["agent_hygiene"].display_text, limit=8),
    ]
    return terminal_section("System Health", lines, spec.content_width)


def render_plain_screen(
    dashboard: DashboardData,
    *,
    screen: str,
    show_backend_command: bool,
    notice: str | None = None,
) -> str:
    spec = layout_spec()
    if screen == "learning":
        sh = first_learning_stronghold(dashboard)
        title = sh.title if sh else "Learning"
        return render_shell(
            dashboard,
            active="learning",
            breadcrumbs=f"Home > Learning > {title}",
            main_lines=render_learning_main(
                sh,
                show_backend_command=show_backend_command,
                spec=spec,
            ),
            controls="1 run | 2 artifacts | 3 plan | 4 assessment | 5 command | 6 refresh | 0 back | ? help | q quit",
            spec=spec,
            notice=notice,
        )
    if screen == "handoffs":
        return render_shell(
            dashboard,
            active="handoffs",
            breadcrumbs="Home > Handoffs",
            main_lines=render_handoffs_main(dashboard, spec),
            controls="r refresh | 0 back | ? help | q quit",
            spec=spec,
            notice=notice,
        )
    if screen == "health":
        return render_shell(
            dashboard,
            active="health",
            breadcrumbs="Home > System Health",
            main_lines=render_health_main(dashboard, spec),
            controls="r refresh | 0 back | ? help | q quit",
            spec=spec,
            notice=notice,
        )
    return render_shell(
        dashboard,
        active="home",
        breadcrumbs="Home",
        main_lines=render_home_main(dashboard, spec),
        controls="[1] Learning | [2] Artifacts | [3] System | [r] Refresh | [?] Help | [q] Quit",
        spec=spec,
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


def render_learning_artifact_menu(sh: LearningStronghold, notice: str | None = None) -> str:
    spec = layout_spec()
    artifacts = learning_artifact_catalog(sh)
    lines = []
    if notice:
        lines.extend([f"Notice: {notice}", ""])
    for index, artifact in enumerate(artifacts, start=1):
        status = "exists" if artifact.exists else "missing"
        lines.append(
            f"[{index:>2}] {artifact.label} | {status} | {artifact.relative_path} | "
            f"{format_artifact_timestamp(artifact.timestamp)}"
        )
    lines.extend(
        [
            "",
            "Select an existing artifact by number.",
            "Copy path: read the displayed relative path and copy manually if needed.",
            "[0] Back",
        ]
    )
    return "\n".join(panel("Artifact Browser", lines, spec.width))


def render_artifact_page(
    artifact: LearningArtifact,
    path: Path,
    body_lines: list[str],
    *,
    page_index: int,
    page_size: int,
    show_all: bool,
) -> str:
    spec = layout_spec()
    total_lines = len(body_lines)
    if show_all:
        start = 0
        end = total_lines
        page_label = "all lines"
    else:
        start = page_index * page_size
        end = min(start + page_size, total_lines)
        page_count = max((total_lines + page_size - 1) // page_size, 1)
        page_label = f"page {page_index + 1}/{page_count}"
    visible = body_lines[start:end] or ["(artifact is empty)"]
    header = panel(
        f"Artifact Viewer - {artifact.label}",
        [
            f"Path: {path}",
            f"Relative path: {artifact.relative_path}",
            f"Timestamp: {format_artifact_timestamp(artifact.timestamp)}",
            f"Showing: {page_label} | lines {start + 1}-{end if end else 0} of {total_lines}",
            "Copy path manually from the Path line above.",
        ],
        spec.width,
    )
    numbered = [
        f"{line_number:>4}: {line}"
        for line_number, line in enumerate(visible, start=start + 1)
    ]
    controls = panel(
        "Viewer Controls",
        ["n next page | p previous page | a show all | b back"],
        spec.width,
    )
    return "\n".join([*header, *numbered, *controls])


def show_learning_artifact(sh: LearningStronghold, artifact: LearningArtifact | None) -> str | None:
    if artifact is None:
        return "No artifact is available for this slot."
    try:
        path, body = read_learning_artifact(sh, artifact.path)
    except ValueError as exc:
        return str(exc)

    body_lines = body.splitlines()
    if not body_lines:
        body_lines = ["(artifact is empty)"]
    page_index = 0
    page_size = 80
    show_all = False
    page_count = max((len(body_lines) + page_size - 1) // page_size, 1)
    notice: str | None = None

    while True:
        if notice:
            print("\n" + "\n".join(panel("Notice", [notice], layout_spec().width)))
            notice = None
        print()
        print(
            render_artifact_page(
                artifact,
                path,
                body_lines,
                page_index=page_index,
                page_size=page_size,
                show_all=show_all,
            )
        )
        choice = input("artifact viewer [n next, p previous, a all, b back]> ").strip().lower()
        if choice == "b":
            return None
        if choice == "a":
            show_all = True
            continue
        if choice == "n":
            if show_all:
                show_all = False
                page_index = min(1, page_count - 1)
                continue
            if page_index + 1 >= page_count:
                notice = "Already at the last page."
                continue
            page_index += 1
            continue
        if choice == "p":
            if show_all:
                show_all = False
                page_index = 0
                continue
            if page_index == 0:
                notice = "Already at the first page."
                continue
            page_index -= 1
            continue
        notice = "Unknown option. Use n, p, a, or b."


def show_learning_artifact_menu(sh: LearningStronghold) -> str | None:
    current_notice: str | None = None
    while True:
        artifacts = learning_artifact_catalog(sh)
        print()
        print(render_learning_artifact_menu(sh, current_notice))
        current_notice = None
        choice = input("artifact menu> ").strip().lower()
        if choice == "0":
            return None
        if not choice.isdigit():
            current_notice = "Unknown option. Choose an artifact number or 0 to go back."
            continue
        index = int(choice)
        if index < 1 or index > len(artifacts):
            current_notice = "Artifact selection is out of range."
            continue
        artifact = artifacts[index - 1]
        if not artifact.exists:
            current_notice = f"{artifact.label} is missing; no file was opened."
            continue
        current_notice = show_learning_artifact(sh, artifact)


def run_plain_mode(notice: str | None = None) -> int:
    debug_log("rendering header")
    print("plain mode [READ_ONLY] initializing dashboard...", flush=True)
    if notice:
        print(notice, flush=True)
    print("Collecting status commands with timeout protection.", flush=True)
    debug_log("collecting status")
    try:
        dashboard = collect_dashboard_data([])
    except KeyboardInterrupt:
        print("\nInterrupted during startup. Exiting plain dashboard.")
        return 130
    debug_log("entering plain loop")
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
            debug_log("waiting for input")
            choice = input("select action> ").strip().lower()
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print("\nInterrupted. Exiting plain dashboard.")
            return 130

        if choice == "q":
            return 0
        if choice in {"h", "?"}:
            current_notice = "Help: " + " | ".join(PLAIN_CONTROLS)
            continue

        if screen == "home":
            sh = first_learning_stronghold(dashboard)
            if choice == "1":
                screen = "learning"
                continue
            if choice == "2" and sh is not None:
                current_notice = show_learning_artifact_menu(sh)
                continue
            if choice == "3":
                screen = "health"
                continue
            if choice == "r":
                dashboard = collect_dashboard_data(dashboard.command_log)
                continue
            if choice == "0":
                return 0
            current_notice = "Unknown option. Use 1, 2, 3, r, ?, or q from Home."
            continue

        if screen == "learning":
            sh = first_learning_stronghold(dashboard)
            latest_plan = (
                latest_catalog_artifact(
                    sh,
                    ("latest_session_plan", "latest_review_plan"),
                )
                if sh
                else None
            )
            latest_assessment = (
                latest_catalog_artifact(
                    sh,
                    ("latest_assessment", "latest_review_assessment"),
                )
                if sh
                else None
            )
            if choice in {"0"}:
                screen = "home"
                show_backend_command = False
                continue
            if choice in {"1", "x"}:
                dashboard, current_notice = execute_recommended_learning_action(dashboard)
                continue
            if choice == "2" and sh is not None:
                current_notice = show_learning_artifact_menu(sh)
                continue
            if choice == "3" and sh is not None:
                current_notice = show_learning_artifact(sh, latest_plan)
                continue
            if choice == "4" and sh is not None:
                current_notice = show_learning_artifact(sh, latest_assessment)
                continue
            if choice == "5":
                show_backend_command = not show_backend_command
                continue
            if choice in {"6", "r"}:
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
    debug_log("starting app")
    debug_log("parsing args")
    args = parse_args(argv)
    if args.snapshot:
        debug_log("collecting status")
        data = collect_dashboard_data([])
        print(render_snapshot(data), end="")
        return 0

    if args.plain:
        debug_log("entering plain mode")
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
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
        sys.exit(130)

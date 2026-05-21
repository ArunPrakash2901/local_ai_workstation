from dataclasses import dataclass
from typing import Optional, Any
from app import (
    DashboardData,
    CommandSafetyManifest,
    CommandSafety,
    parse_readiness_summary,
    first_learning_stronghold,
    mode_allows_command,
    command_name_from_args,
)

@dataclass
class NextSafeAction:
    action_id: str
    label: str
    description: str
    reason: str
    safety_class: str
    command: Optional[str]
    tui_exposure: str
    confirmation: str
    enabled: bool
    disabled: bool
    hidden: bool
    blocker: Optional[str]
    stale_artifact: Optional[str]
    source: str
    confidence: str
    fallback_reason: Optional[str]

def compute_next_safe_action(state: DashboardData, manifest: CommandSafetyManifest, mode: str, screen_context: str = "home") -> NextSafeAction:
    if not manifest.loaded:
        return NextSafeAction(
            action_id="system.manifest_missing",
            label="No executable system action available",
            description="Command safety manifest unavailable.",
            reason="Manifest is missing or malformed.",
            safety_class="UNKNOWN",
            command=None,
            tui_exposure="visible",
            confirmation="none",
            enabled=False,
            disabled=True,
            hidden=False,
            blocker="command safety manifest unavailable.",
            stale_artifact=None,
            source="manifest",
            confidence="high",
            fallback_reason="Manifest missing, degraded safely."
        )

    readiness = state.results.get("readiness")
    if readiness:
        summary = parse_readiness_summary(readiness)
        if summary.get("state") in {"CHECK_FAILED", "UNAVAILABLE", "UNKNOWN", "DEGRADED", "PARTIAL"}:
            if screen_context == "system":
                # We are ON the system screen; recommend an actionable fix if allowed
                ready_cmd = manifest.commands.get("ws ready")
                if ready_cmd and mode.upper() != "READ_ONLY_STRICT":
                     # In safe modes, if allowed, we can dispatch ws ready
                     is_safe = ready_cmd.tui_dispatch_allowed and ready_cmd.tui_dispatch_policy == "system_only"
                     if is_safe:
                         return NextSafeAction(
                             action_id="system.ready.run",
                             label="Re-run readiness check",
                             description="Writes local readiness/status reports.",
                             reason="System readiness is degraded.",
                             safety_class=ready_cmd.safety_class,
                             command="ws ready",
                             tui_exposure=ready_cmd.tui_exposure,
                             confirmation=ready_cmd.confirmation,
                             enabled=True,
                             disabled=False,
                             hidden=False,
                             blocker=None,
                             stale_artifact=None,
                             source="readiness",
                             confidence="high",
                             fallback_reason=None
                         )

                # Fallback if ws ready is blocked by policy or mode
                return NextSafeAction(
                    action_id="system.safe_check.show",
                    label="Re-run readiness check disabled",
                    description="Run no-write local safety check outside the TUI.",
                    reason="READ_ONLY_STRICT does not allow local report writes." if mode.upper() == "READ_ONLY_STRICT" else "Action disabled by policy.",
                    safety_class="PURE_READ",
                    command=None,
                    tui_exposure="visible",
                    confirmation="none",
                    enabled=False,
                    disabled=True,
                    hidden=False,
                    blocker="READ_ONLY_STRICT does not allow local report writes." if mode.upper() == "READ_ONLY_STRICT" else "Action disabled by policy.",
                    stale_artifact=None,
                    source="readiness",
                    confidence="high",
                    fallback_reason=None
                )

            # Not on system screen: recommend navigation to System
            return NextSafeAction(
                action_id="system.readiness_unavailable",
                label="Open System screen for details",
                description="System readiness check failed or is unavailable.",
                reason="System readiness is degraded or unavailable.",
                safety_class="PURE_READ",
                command=None,
                tui_exposure="visible",
                confirmation="none",
                enabled=True,
                disabled=False,
                hidden=False,
                blocker="System readiness unavailable.",
                stale_artifact=None,
                source="readiness",
                confidence="high",
                fallback_reason=None
            )

    sh = first_learning_stronghold(state)
    if not sh:
        return NextSafeAction(
            action_id="system.no_stronghold",
            label="Open or choose a stronghold",
            description="Navigate to a stronghold view.",
            reason="No active stronghold discovered.",
            safety_class="PURE_READ",
            command=None,
            tui_exposure="visible",
            confirmation="none",
            enabled=True,
            disabled=False,
            hidden=False,
            blocker=None,
            stale_artifact=None,
            source="strongholds",
            confidence="high",
            fallback_reason=None
        )

    learning_action = sh.compute_next_action()
    cmd_name = command_name_from_args(learning_action.args) if learning_action.args else "UNKNOWN"
    cmd_safety = manifest.commands.get(cmd_name)
    
    if not cmd_safety:
        return NextSafeAction(
            action_id="learning.action.unknown",
            label=learning_action.label,
            description="Command not found in safety manifest.",
            reason="Missing or unclassified command.",
            safety_class="UNKNOWN",
            command=None,
            tui_exposure="hidden",
            confirmation="required",
            enabled=False,
            disabled=True,
            hidden=True,
            blocker="Missing command safety classification.",
            stale_artifact=None,
            source="manifest",
            confidence="high",
            fallback_reason="Command not classified."
        )

    is_safe = mode_allows_command(cmd_safety, mode)
    
    # 9. READ_ONLY_STRICT -> disable LOCAL_REPORT_WRITE
    if mode.upper() == "READ_ONLY_STRICT" and cmd_safety.safety_class == "LOCAL_REPORT_WRITE":
        is_safe = False

    # 5. unsafe commands
    if cmd_safety.safety_class in {"PROVIDER_CALL", "DESTRUCTIVE", "UNKNOWN", "GUARDED_WRITE"}:
        return NextSafeAction(
            action_id="learning.action.unsafe",
            label=learning_action.label,
            description="Action requires unsafe execution.",
            reason=f"{cmd_safety.safety_class} actions not recommended automatically.",
            safety_class=cmd_safety.safety_class,
            command=None,
            tui_exposure=cmd_safety.tui_exposure,
            confirmation=cmd_safety.confirmation,
            enabled=False,
            disabled=True,
            hidden=True,
            blocker=f"{cmd_safety.safety_class} execution blocked.",
            stale_artifact="decision" if sh.decision_warning else None,
            source="safety_policy",
            confidence="high",
            fallback_reason=None
        )

    blocker = None
    if sh.decision_warning:
        blocker = sh.decision_warning.replace("[WARN] ", "", 1)
    elif not is_safe:
        blocker = f"Disabled by {mode} safety mode."
    elif not learning_action.executable:
        blocker = "Action requires manual execution."

    return NextSafeAction(
        action_id="learning.action.next",
        label=learning_action.label,
        description="Proceed with current stronghold task.",
        reason=blocker if blocker else "Stronghold ready for next step.",
        safety_class=cmd_safety.safety_class,
        command=learning_action.command_text if (is_safe and learning_action.executable) else None,
        tui_exposure=cmd_safety.tui_exposure,
        confirmation=cmd_safety.confirmation,
        enabled=is_safe and learning_action.executable,
        disabled=not (is_safe and learning_action.executable),
        hidden=False,
        blocker=blocker,
        stale_artifact="decision" if sh.decision_warning else None,
        source="learning_stronghold",
        confidence="high",
        fallback_reason=None
    )

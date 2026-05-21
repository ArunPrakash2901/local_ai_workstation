import shlex
import subprocess
from dataclasses import dataclass
from typing import Optional, Callable
from next_action import NextSafeAction
from app import CommandSafetyManifest, CommandResult, normalize_subprocess_text, WS_SCRIPT, WS_HOME

@dataclass
class DispatchResult:
    status: str  # 'preview' | 'executed' | 'blocked' | 'disabled' | 'hidden' | 'error' | 'navigation'
    action_id: str
    label: str
    command: Optional[str]
    safety_class: str
    reason: str
    warning_label: str
    confirmation_required: str
    executed: bool
    stdout: str
    stderr: str
    log_line: str
    operator_message: str
    navigate_to: Optional[str] = None
    returncode: Optional[int] = None

def dispatch_next_safe_action(
    action: NextSafeAction,
    mode: str,
    manifest: CommandSafetyManifest,
    executor: Optional[Callable[[str], tuple[int, str, str]]] = None
) -> DispatchResult:
    # 10. Missing manifest
    if not manifest.loaded:
        return DispatchResult(
            status="blocked",
            action_id=action.action_id,
            label=action.label,
            command=action.command,
            safety_class="UNKNOWN",
            reason="Manifest is missing or malformed.",
            warning_label="",
            confirmation_required="none",
            executed=False,
            stdout="",
            stderr="",
            log_line="[BLOCKED] Execution prevented: command safety manifest unavailable.",
            operator_message="Cannot execute: command safety manifest unavailable."
        )

    # 1. Navigation actions
    if action.action_id.startswith("system.") and not action.command:
        navigate_target = "system"
        return DispatchResult(
            status="navigation",
            action_id=action.action_id,
            label=action.label,
            command=None,
            safety_class="PURE_READ",
            reason="Navigation action.",
            warning_label="",
            confirmation_required="none",
            executed=False,
            stdout="",
            stderr="",
            log_line=f"[NAVIGATE] Routed to {navigate_target} screen.",
            operator_message=f"Navigating to {navigate_target}...",
            navigate_to=navigate_target
        )

    # 11. Disabled NextSafeAction cannot dispatch
    if action.disabled or action.hidden or not action.enabled or not action.command:
        return DispatchResult(
            status="disabled",
            action_id=action.action_id,
            label=action.label,
            command=action.command,
            safety_class=action.safety_class,
            reason=action.blocker or "Action is disabled.",
            warning_label="",
            confirmation_required=action.confirmation,
            executed=False,
            stdout="",
            stderr="",
            log_line=f"[DISABLED] {action.label}: {action.blocker or 'Action is disabled.'}",
            operator_message=f"Action disabled: {action.blocker or 'Action is disabled.'}"
        )

    # Re-verify the command in the manifest
    cmd_name = None
    # We parse the command text. We assume the command starts with 'ws '
    if action.command.startswith("ws "):
        args = tuple(shlex.split(action.command[3:]))
        # Note: In a real implementation we would reuse command_name_from_args, 
        # but importing it from app here is fine.
        from app import command_name_from_args
        cmd_name = command_name_from_args(args)
    
    if not cmd_name:
        cmd_name = action.command

    cmd_safety = manifest.commands.get(cmd_name)
    if not cmd_safety:
        return DispatchResult(
            status="blocked",
            action_id=action.action_id,
            label=action.label,
            command=action.command,
            safety_class="UNKNOWN",
            reason="Command not found in safety manifest.",
            warning_label="",
            confirmation_required="required",
            executed=False,
            stdout="",
            stderr="",
            log_line=f"[BLOCKED] {action.command} is UNKNOWN to manifest.",
            operator_message="Command not classified in safety manifest."
        )

    # Check Blocked classes
    blocked_classes = {"UNKNOWN", "PROVIDER_CALL", "DESTRUCTIVE", "GUARDED_WRITE", "AGENT_RUN"}
    if cmd_safety.safety_class in blocked_classes:
        # Note: If there was a GUARDED_WRITE that was marked as DRY_RUN_ONLY we'd let it pass if safe,
        # but safety_class is the primary axis.
        return DispatchResult(
            status="blocked",
            action_id=action.action_id,
            label=action.label,
            command=action.command,
            safety_class=cmd_safety.safety_class,
            reason=f"command safety class {cmd_safety.safety_class} is not executable from TUI v1.",
            warning_label=cmd_safety.warning_label,
            confirmation_required=cmd_safety.confirmation,
            executed=False,
            stdout="",
            stderr="",
            log_line=f"[BLOCKED] {action.command} blocked by class {cmd_safety.safety_class}.",
            operator_message=f"Action blocked: command safety class {cmd_safety.safety_class} is not executable from TUI v1."
        )

    # 4. LOCAL_REPORT_WRITE
    if cmd_safety.safety_class == "LOCAL_REPORT_WRITE":
        if mode.upper() == "READ_ONLY_STRICT":
            return DispatchResult(
                status="disabled",
                action_id=action.action_id,
                label=action.label,
                command=action.command,
                safety_class=cmd_safety.safety_class,
                reason="LOCAL_REPORT_WRITE disabled under READ_ONLY_STRICT.",
                warning_label=cmd_safety.warning_label,
                confirmation_required=cmd_safety.confirmation,
                executed=False,
                stdout="",
                stderr="",
                log_line=f"[DISABLED] {action.command} disabled under READ_ONLY_STRICT.",
                operator_message="LOCAL_REPORT_WRITE disabled under READ_ONLY_STRICT."
            )
            
        policy = cmd_safety.tui_dispatch_policy
        allowed = cmd_safety.tui_dispatch_allowed
        scope = cmd_safety.report_write_scope
        
        if not cmd_safety.warning_label:
            return DispatchResult(
                status="blocked",
                action_id=action.action_id,
                label=action.label,
                command=action.command,
                safety_class=cmd_safety.safety_class,
                reason="LOCAL_REPORT_WRITE missing warning_label.",
                warning_label="",
                confirmation_required=cmd_safety.confirmation,
                executed=False,
                stdout="",
                stderr="",
                log_line=f"[BLOCKED] {action.command} missing warning_label.",
                operator_message="Action blocked: missing warning label."
            )

        if not scope or scope == "unknown":
            return DispatchResult(
                status="blocked",
                action_id=action.action_id,
                label=action.label,
                command=action.command,
                safety_class=cmd_safety.safety_class,
                reason="LOCAL_REPORT_WRITE missing report_write_scope.",
                warning_label=cmd_safety.warning_label,
                confirmation_required=cmd_safety.confirmation,
                executed=False,
                stdout="",
                stderr="",
                log_line=f"[BLOCKED] {action.command} missing report_write_scope.",
                operator_message="Action blocked: missing report write scope."
            )

        if not allowed or policy in {"preview_only", "hidden_local_report"}:
            return DispatchResult(
                status="disabled" if policy == "preview_only" else "blocked",
                action_id=action.action_id,
                label=action.label,
                command=action.command,
                safety_class=cmd_safety.safety_class,
                reason=f"Action policy is {policy}; not executable from TUI.",
                warning_label=cmd_safety.warning_label,
                confirmation_required=cmd_safety.confirmation,
                executed=False,
                stdout="",
                stderr="",
                log_line=f"[BLOCKED] {action.command} blocked by dispatch policy {policy}.",
                operator_message=f"Action blocked by policy: {policy}."
            )
        
        if policy == "system_only" and not action.action_id.startswith("system."):
            return DispatchResult(
                status="blocked",
                action_id=action.action_id,
                label=action.label,
                command=action.command,
                safety_class=cmd_safety.safety_class,
                reason="System-only action dispatched outside of System context.",
                warning_label=cmd_safety.warning_label,
                confirmation_required=cmd_safety.confirmation,
                executed=False,
                stdout="",
                stderr="",
                log_line=f"[BLOCKED] {action.command} is system_only but dispatched as {action.action_id}.",
                operator_message="Action blocked: system-only action dispatched outside of System context."
            )
            
        if policy == "learning_only" and not action.action_id.startswith("learning."):
            return DispatchResult(
                status="blocked",
                action_id=action.action_id,
                label=action.label,
                command=action.command,
                safety_class=cmd_safety.safety_class,
                reason="Learning-only action dispatched outside of Learning context.",
                warning_label=cmd_safety.warning_label,
                confirmation_required=cmd_safety.confirmation,
                executed=False,
                stdout="",
                stderr="",
                log_line=f"[BLOCKED] {action.command} is learning_only but dispatched as {action.action_id}.",
                operator_message="Action blocked: learning-only action dispatched outside of Learning context."
            )
        
    # Execute if preview/confirmation is handled
    # The dispatcher's default execution logic:
    if executor:
        returncode, stdout, stderr = executor(action.command)
    else:
        # Default executor
        if not action.command.startswith("ws "):
            return DispatchResult(
                status="error",
                action_id=action.action_id,
                label=action.label,
                command=action.command,
                safety_class=cmd_safety.safety_class,
                reason="Invalid command format.",
                warning_label=cmd_safety.warning_label,
                confirmation_required=cmd_safety.confirmation,
                executed=False,
                stdout="",
                stderr="",
                log_line="[ERROR] Invalid command format.",
                operator_message="Invalid command format."
            )
        args = shlex.split(action.command[3:])
        try:
            completed = subprocess.run(
                ["bash", str(WS_SCRIPT), *args],
                cwd=WS_HOME,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                check=False,
            )
            returncode = completed.returncode
            stdout = normalize_subprocess_text(completed.stdout)
            stderr = normalize_subprocess_text(completed.stderr)
        except Exception as e:
            return DispatchResult(
                status="error",
                action_id=action.action_id,
                label=action.label,
                command=action.command,
                safety_class=cmd_safety.safety_class,
                reason=f"Execution failed: {str(e)}",
                warning_label=cmd_safety.warning_label,
                confirmation_required=cmd_safety.confirmation,
                executed=False,
                stdout="",
                stderr=str(e),
                log_line=f"[ERROR] Execution failed: {str(e)}",
                operator_message=f"Execution failed: {str(e)}"
            )

    success = returncode == 0
    scope_str = f" [scope={cmd_safety.report_write_scope}]" if cmd_safety.safety_class == "LOCAL_REPORT_WRITE" else ""
    return DispatchResult(
        status="executed",
        action_id=action.action_id,
        label=action.label,
        command=action.command,
        safety_class=cmd_safety.safety_class,
        reason="Executed successfully" if success else f"Failed with exit code {returncode}",
        warning_label=cmd_safety.warning_label,
        confirmation_required=cmd_safety.confirmation,
        executed=True,
        stdout=stdout,
        stderr=stderr,
        log_line=f"[EXECUTED] {action.command}{scope_str} -> exit {returncode}",
        operator_message=f"Command executed (exit {returncode}).",
        returncode=returncode
    )

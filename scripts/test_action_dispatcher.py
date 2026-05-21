import os
import sys
from pathlib import Path

# Add project root and tui dir to sys.path so we can import app and action modules safely
project_root = Path(__file__).resolve().parents[1]
tui_dir = project_root / "tui"
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(tui_dir) not in sys.path:
    sys.path.insert(0, str(tui_dir))

from app import CommandSafetyManifest, CommandSafety
from next_action import NextSafeAction
from action_dispatcher import dispatch_next_safe_action

def make_manifest(commands: dict[str, CommandSafety], loaded: bool = True) -> CommandSafetyManifest:
    return CommandSafetyManifest(loaded=loaded, warning=None, commands=commands)

def mock_executor(cmd: str) -> tuple[int, str, str]:
    return 0, f"Simulated execution of {cmd}", ""

def run_tests():
    print("Testing Safe Action Dispatcher...")
    failures = []

    def check(name, condition, msg):
        if not condition:
            failures.append(f"FAIL: {name} - {msg}")
        else:
            print(f"PASS: {name}")

    def make_cmd(cmd: str, s_class: str, exposure="visible", conf="none", policy="hidden_local_report", allowed=False, scope="unknown", warn=""):
        return CommandSafety(
            command=cmd, safety_class=s_class, description="desc",
            writes_local_files=True if s_class == "LOCAL_REPORT_WRITE" else False,
            writes_project_files=True if s_class in ("GUARDED_WRITE", "DESTRUCTIVE") else False,
            invokes_agent_or_model=True if s_class == "AGENT_RUN" else False,
            external_provider_or_cloud=True if s_class == "PROVIDER_CALL" else False,
            read_only_strict=False, read_only_with_local_reports=True, safe_dry_run=True,
            tui_exposure=exposure, confirmation=conf, operator_label=cmd,
            warning_label=warn, evidence=(), confidence="high", notes="",
            tui_dispatch_policy=policy, tui_dispatch_allowed=allowed, report_write_scope=scope
        )

    # Set up some known commands
    commands = {
        "ws pure-read": make_cmd("ws pure-read", "PURE_READ", "visible", "none"),
        "ws dry-run": make_cmd("ws dry-run", "DRY_RUN_ONLY", "visible", "none"),
        "ws local-report": make_cmd("ws local-report", "LOCAL_REPORT_WRITE", "visible_with_label", "light", "safe_local_report", True, "audit", "Writes local report"),
        "ws preview-report": make_cmd("ws preview-report", "LOCAL_REPORT_WRITE", "visible_with_label", "light", "preview_only", False, "audit", "Writes local report"),
        "ws system-report": make_cmd("ws system-report", "LOCAL_REPORT_WRITE", "visible_with_label", "light", "system_only", True, "readiness", "Writes local report"),
        "ws learning-report": make_cmd("ws learning-report", "LOCAL_REPORT_WRITE", "visible_with_label", "light", "learning_only", True, "stronghold", "Writes local report"),
        "ws no-warn-report": make_cmd("ws no-warn-report", "LOCAL_REPORT_WRITE", "visible_with_label", "light", "safe_local_report", True, "audit", ""),
        "ws no-scope-report": make_cmd("ws no-scope-report", "LOCAL_REPORT_WRITE", "visible_with_label", "light", "safe_local_report", True, "", "Writes local report"),
        "ws do-unsafe": make_cmd("ws do-unsafe", "DESTRUCTIVE", "hidden", "destructive"),
        "ws call-provider": make_cmd("ws call-provider", "PROVIDER_CALL", "hidden", "provider"),
        "ws agent-run": make_cmd("ws agent-run", "AGENT_RUN", "hidden", "required"),
        "ws unknown-cmd": make_cmd("ws unknown-cmd", "UNKNOWN", "hidden", "required"),
    }
    manifest = make_manifest(commands)

    # 1. Navigation action changes route / returns navigation result without subprocess execution
    nav_action = NextSafeAction("system.readiness", "Go to system", "desc", "reason", "PURE_READ", None, "visible", "none", True, False, False, None, None, "source", "high", None)
    res = dispatch_next_safe_action(nav_action, "READ_ONLY", manifest, mock_executor)
    check("Navigation action", res.status == "navigation" and res.navigate_to == "system", "Should return navigation result")

    # 2. UNKNOWN action is blocked
    unk_action = NextSafeAction("test.unknown", "Unknown", "desc", "reason", "UNKNOWN", "ws unknown-cmd", "hidden", "none", True, False, False, None, None, "source", "high", None)
    res = dispatch_next_safe_action(unk_action, "READ_ONLY", manifest, mock_executor)
    check("UNKNOWN action blocked", res.status == "blocked", "Should block UNKNOWN")

    # 3. PROVIDER_CALL action is blocked
    prov_action = NextSafeAction("test.provider", "Provider", "desc", "reason", "PROVIDER_CALL", "ws call-provider", "visible", "none", True, False, False, None, None, "source", "high", None)
    res = dispatch_next_safe_action(prov_action, "READ_ONLY", manifest, mock_executor)
    check("PROVIDER_CALL action blocked", res.status == "blocked", "Should block PROVIDER_CALL")

    # 4. DESTRUCTIVE action is blocked
    dest_action = NextSafeAction("test.destructive", "Destructive", "desc", "reason", "DESTRUCTIVE", "ws do-unsafe", "visible", "none", True, False, False, None, None, "source", "high", None)
    res = dispatch_next_safe_action(dest_action, "READ_ONLY", manifest, mock_executor)
    check("DESTRUCTIVE action blocked", res.status == "blocked", "Should block DESTRUCTIVE")

    # 5. AGENT_RUN action is blocked in v1
    agent_action = NextSafeAction("test.agent", "Agent", "desc", "reason", "AGENT_RUN", "ws agent-run", "visible", "none", True, False, False, None, None, "source", "high", None)
    res = dispatch_next_safe_action(agent_action, "READ_ONLY", manifest, mock_executor)
    check("AGENT_RUN action blocked", res.status == "blocked", "Should block AGENT_RUN")

    # 6. LOCAL_REPORT_WRITE action is disabled under READ_ONLY_STRICT
    report_action = NextSafeAction("test.report", "Report", "desc", "reason", "LOCAL_REPORT_WRITE", "ws local-report", "visible", "none", True, False, False, None, None, "source", "high", None)
    res = dispatch_next_safe_action(report_action, "READ_ONLY_STRICT", manifest, mock_executor)
    check("LOCAL_REPORT_WRITE disabled under READ_ONLY_STRICT", res.status == "disabled", "Should disable LOCAL_REPORT_WRITE in STRICT")

    # 7. LOCAL_REPORT_WRITE action is visible and executes under READ_ONLY_WITH_LOCAL_REPORTS 
    res = dispatch_next_safe_action(report_action, "READ_ONLY_WITH_LOCAL_REPORTS", manifest, mock_executor)
    check("LOCAL_REPORT_WRITE executed with warnings under READ_ONLY_WITH_LOCAL_REPORTS", res.status == "executed" and res.executed, "Should execute LOCAL_REPORT_WRITE")
    check("Dispatcher log includes report_write_scope", "scope=audit" in res.log_line, "Log line should contain scope")

    # 8. DRY_RUN_ONLY action can dispatch through fake executor under SAFE_DRY_RUN
    dry_action = NextSafeAction("test.dry", "Dry", "desc", "reason", "DRY_RUN_ONLY", "ws dry-run", "visible", "none", True, False, False, None, None, "source", "high", None)
    res = dispatch_next_safe_action(dry_action, "SAFE_DRY_RUN", manifest, mock_executor)
    check("DRY_RUN_ONLY dispatches under SAFE_DRY_RUN", res.status == "executed" and res.executed, "Should execute DRY_RUN_ONLY")

    # 10. Missing manifest blocks execution
    bad_manifest = make_manifest({}, loaded=False)
    res = dispatch_next_safe_action(dry_action, "SAFE_DRY_RUN", bad_manifest, mock_executor)
    check("Missing manifest blocks execution", res.status == "blocked", "Should block execution if manifest is missing")

    # LOCAL_REPORT_WRITE specific boundary checks
    preview_action = NextSafeAction("test.preview", "Preview", "desc", "reason", "LOCAL_REPORT_WRITE", "ws preview-report", "visible", "none", True, False, False, None, None, "source", "high", None)
    res = dispatch_next_safe_action(preview_action, "READ_ONLY_WITH_LOCAL_REPORTS", manifest, mock_executor)
    check("LOCAL_REPORT_WRITE preview_only is disabled", res.status == "disabled", "Preview only should not execute")

    system_action = NextSafeAction("learning.system", "System", "desc", "reason", "LOCAL_REPORT_WRITE", "ws system-report", "visible", "none", True, False, False, None, None, "source", "high", None)
    res = dispatch_next_safe_action(system_action, "READ_ONLY_WITH_LOCAL_REPORTS", manifest, mock_executor)
    check("System-only action blocked in learning context", res.status == "blocked", "System only must be dispatched from system")

    learning_action = NextSafeAction("system.learning", "Learning", "desc", "reason", "LOCAL_REPORT_WRITE", "ws learning-report", "visible", "none", True, False, False, None, None, "source", "high", None)
    res = dispatch_next_safe_action(learning_action, "READ_ONLY_WITH_LOCAL_REPORTS", manifest, mock_executor)
    check("Learning-only action blocked in system context", res.status == "blocked" and "learning_only" in res.log_line, "Learning only must be dispatched from learning")

    no_warn_action = NextSafeAction("test.nowarn", "No Warn", "desc", "reason", "LOCAL_REPORT_WRITE", "ws no-warn-report", "visible", "none", True, False, False, None, None, "source", "high", None)
    res = dispatch_next_safe_action(no_warn_action, "READ_ONLY_WITH_LOCAL_REPORTS", manifest, mock_executor)
    check("Missing warning_label blocks execution", res.status == "blocked", "Must require warning label")

    no_scope_action = NextSafeAction("test.noscope", "No Scope", "desc", "reason", "LOCAL_REPORT_WRITE", "ws no-scope-report", "visible", "none", True, False, False, None, None, "source", "high", None)
    res = dispatch_next_safe_action(no_scope_action, "READ_ONLY_WITH_LOCAL_REPORTS", manifest, mock_executor)
    check("Missing report_write_scope blocks execution", res.status == "blocked", "Must require report write scope")

    # 11. Disabled NextSafeAction cannot dispatch
    disabled_action = NextSafeAction("test.disabled", "Disabled", "desc", "reason", "DRY_RUN_ONLY", "ws dry-run", "visible", "none", False, True, False, "manually disabled", None, "source", "high", None)
    res = dispatch_next_safe_action(disabled_action, "SAFE_DRY_RUN", manifest, mock_executor)
    check("Disabled NextSafeAction cannot dispatch", res.status == "disabled", "Should return disabled status")

    # 12. Dispatcher result produces a TUI event log line
    check("Dispatcher result produces log line", bool(res.log_line), "Should produce log_line")

    if failures:
        print("\nFailures:")
        for f in failures:
            print(f)
        sys.exit(1)
    else:
        print("\nAll tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    run_tests()

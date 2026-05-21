import os
import sys
from pathlib import Path

# Add project root and tui dir to sys.path so we can import app and next_action safely
project_root = Path(__file__).resolve().parents[1]
tui_dir = project_root / "tui"
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(tui_dir) not in sys.path:
    sys.path.insert(0, str(tui_dir))

from app import DashboardData, CommandResult, LearningStronghold, CommandSafetyManifest, CommandSafety, LearningAction
from next_action import compute_next_safe_action

def make_manifest(commands: dict[str, CommandSafety], loaded: bool = True) -> CommandSafetyManifest:
    return CommandSafetyManifest(loaded=loaded, warning=None, commands=commands)

def make_dashboard(
    readiness_state: str = "READY",
    stronghold: LearningStronghold | None = None
) -> DashboardData:
    readiness_output = f"[OK] Some check\n" if readiness_state == "READY" else "[FAIL] Something failed\n"
    return DashboardData(
        results={
            "readiness": CommandResult(
                label="readiness",
                args=("ready",),
                stdout=readiness_output,
                stderr="",
                returncode=0 if readiness_state == "READY" else 1,
            )
        },
        learning_strongholds=[stronghold] if stronghold else []
    )

class FakeStronghold(LearningStronghold):
    def __init__(self, decision_warning=None, mock_action=None):
        super().__init__(
            id="test-id",
            path=Path("/tmp/fake"),
            title="Test Stronghold",
        )
        self._mock_warning = decision_warning
        self._mock_action = mock_action

    @property
    def decision_warning(self):
        return self._mock_warning

    def compute_next_action(self):
        if self._mock_action:
            return self._mock_action
        return super().compute_next_action()

def run_tests():
    print("Testing Next Safe Action Engine...")
    failures = []

    # Helper to assert
    def check(name, condition, msg):
        if not condition:
            failures.append(f"FAIL: {name} - {msg}")
        else:
            print(f"PASS: {name}")

    # Case 2: missing manifest -> degrade safely
    dashboard = make_dashboard()
    bad_manifest = make_manifest({}, loaded=False)
    result = compute_next_safe_action(dashboard, bad_manifest, "READ_ONLY")
    check("Missing manifest degrades safely", result.safety_class == "UNKNOWN" and result.disabled, f"Got safety: {result.safety_class}")

    # Set up known manifest commands for the rest of the tests
    cmd_unsafe = CommandSafety("ws do-unsafe", "DESTRUCTIVE", "desc", False, True, False, False, False, False, False, "visible", "none", "Do unsafe", "", (), "high", "")
    cmd_provider = CommandSafety("ws call-provider", "PROVIDER_CALL", "desc", False, False, False, True, False, False, False, "visible", "none", "Call provider", "", (), "high", "")
    cmd_unknown = CommandSafety("ws unknown", "UNKNOWN", "desc", False, False, False, False, False, False, False, "hidden", "none", "Unknown", "", (), "low", "")
    cmd_report = CommandSafety("ws write-report", "LOCAL_REPORT_WRITE", "desc", True, False, False, False, False, True, True, "visible", "none", "Write report", "writes report", (), "high", "")
    cmd_pure = CommandSafety("ws read-only", "PURE_READ", "desc", False, False, False, False, True, True, True, "visible", "none", "Read", "", (), "high", "")
    cmd_dry = CommandSafety("ws dry-run", "DRY_RUN_ONLY", "desc", True, False, False, False, False, False, True, "visible", "none", "Dry run", "", (), "high", "")
    cmd_ready = CommandSafety("ws ready", "LOCAL_REPORT_WRITE", "desc", True, False, False, False, False, True, True, "visible", "none", "Ready", "writes status", (), "high", "", tui_dispatch_policy="system_only", tui_dispatch_allowed=True, report_write_scope="readiness")

    commands = {
        "ws do-unsafe": cmd_unsafe,
        "ws call-provider": cmd_provider,
        "ws unknown": cmd_unknown,
        "ws write-report": cmd_report,
        "ws read-only": cmd_pure,
        "ws dry-run": cmd_dry,
        "ws ready": cmd_ready
    }
    manifest = make_manifest(commands)

    # Case 8: no active stronghold -> safe navigation
    dashboard = make_dashboard(stronghold=None)
    result = compute_next_safe_action(dashboard, manifest, "READ_ONLY")
    check("No stronghold safe navigation", result.action_id == "system.no_stronghold" and result.enabled, "Should navigate safely")

    # Case 9: unavailable system readiness -> recommends safe validation/system review (from home context)
    dashboard = make_dashboard(readiness_state="UNAVAILABLE")
    result = compute_next_safe_action(dashboard, manifest, "READ_ONLY")
    check("Unavailable readiness safe validation", result.action_id == "system.readiness_unavailable" and result.command is None, "Should not run ws ready")

    # Case 9.1: unavailable system readiness -> recommends ws ready from system context
    result = compute_next_safe_action(dashboard, manifest, "READ_ONLY_WITH_LOCAL_REPORTS", screen_context="system")
    check("Unavailable readiness system context recommends ready", result.action_id == "system.ready.run" and result.command == "ws ready", "Should recommend ws ready")

    # Case 9.2: unavailable system readiness in STRICT -> disabled action
    result = compute_next_safe_action(dashboard, manifest, "READ_ONLY_STRICT", screen_context="system")
    check("Unavailable readiness STRICT disables ready", result.action_id == "system.safe_check.show" and result.disabled, "Should disable ws ready in strict")

    # Case 3: UNKNOWN command -> hidden/not recommended
    action_unknown = LearningAction("Unknown action", "ws unknown", ("unknown",), "BLUE", executable=True)
    sh_unknown = FakeStronghold(mock_action=action_unknown)
    result = compute_next_safe_action(make_dashboard(stronghold=sh_unknown), manifest, "READ_ONLY")
    check("UNKNOWN command not recommended", result.disabled and result.hidden, "Should hide UNKNOWN")

    # Case 4: PROVIDER_CALL command -> not recommended by default
    action_provider = LearningAction("Provider action", "ws call-provider", ("call-provider",), "BLUE", executable=True)
    sh_provider = FakeStronghold(mock_action=action_provider)
    result = compute_next_safe_action(make_dashboard(stronghold=sh_provider), manifest, "READ_ONLY")
    check("PROVIDER_CALL command not recommended", result.disabled and result.hidden, "Should hide PROVIDER_CALL")

    # Case 5: LOCAL_REPORT_WRITE under READ_ONLY_STRICT -> disabled
    action_report = LearningAction("Report action", "ws write-report", ("write-report",), "BLUE", executable=True)
    sh_report = FakeStronghold(mock_action=action_report)
    result = compute_next_safe_action(make_dashboard(stronghold=sh_report), manifest, "READ_ONLY_STRICT")
    check("LOCAL_REPORT_WRITE in STRICT is disabled", result.disabled, "Should disable in STRICT")

    # Case 6: LOCAL_REPORT_WRITE under READ_ONLY_WITH_LOCAL_REPORTS -> visible
    result = compute_next_safe_action(make_dashboard(stronghold=sh_report), manifest, "READ_ONLY_WITH_LOCAL_REPORTS")
    check("LOCAL_REPORT_WRITE with local reports is enabled", result.enabled, "Should enable with local reports allowed")

    # Case 7: DRY_RUN_ONLY under SAFE_DRY_RUN -> enabled
    action_dry = LearningAction("Dry run action", "ws dry-run", ("dry-run",), "BLUE", executable=True)
    sh_dry = FakeStronghold(mock_action=action_dry)
    result = compute_next_safe_action(make_dashboard(stronghold=sh_dry), manifest, "SAFE_DRY_RUN")
    check("DRY_RUN_ONLY under SAFE_DRY_RUN is enabled", result.enabled, "Should enable dry runs in SAFE_DRY_RUN")

    # Case 1 & 10: stale learning decision -> review action, blocker explains mismatch, label does not contradict
    action_review = LearningAction("Start review tutor", "ws dry-run", ("dry-run",), "BLUE", executable=True)
    sh_stale = FakeStronghold(decision_warning="[WARN] Older review decision does not match current session.", mock_action=action_review)
    result = compute_next_safe_action(make_dashboard(stronghold=sh_stale), manifest, "SAFE_DRY_RUN")
    check("Stale decision recommends review action", "review" in result.label.lower() and result.enabled, "Should recommend review")
    check("Stale decision blocker explains mismatch", "match" in result.blocker, "Blocker should mention mismatch")
    check("Action label and blocker do not contradict", result.label != result.blocker, "Label and blocker should be distinct")

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

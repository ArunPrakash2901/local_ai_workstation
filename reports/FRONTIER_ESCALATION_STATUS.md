# Frontier Escalation Status

Date: 2026-05-14

## Scope

Implemented explicit frontier sending for already-created safe packets. Local-first remains the default; no normal `ws ask`, `ws debug`, `ws audit`, or `ws task` command sends data to frontier CLIs.

## Commands

```bash
ws escalate gemini <packet_path|latest>
ws escalate codex <packet_path|latest>
ws escalate claude <packet_path|latest>
```

Behavior:

- resolves `latest` to the newest packet in `D:\_ai_brain\frontier\packets`
- runs `ws redact` before sending
- refuses to send unless redaction returns `SAFE`
- writes provider output to `D:\_ai_brain\frontier\responses`
- writes command logs to `D:\_ai_brain\frontier\logs`
- reports Claude as unavailable when the CLI is not installed

## Provider Notes

- Gemini CLI is detected, but the current WSL shim cannot run because `node` is not available in WSL. The Windows Gemini CLI also failed a help probe with `EPERM`, so the workstation reports a manual command instead of hanging.
- Codex CLI supports `codex exec` non-interactive mode and is wired through PowerShell with read-only sandbox flags.
- Claude CLI is not installed.

## Smoke Test Results

Created packet:

- `D:\_ai_brain\frontier\packets\20260514_013603_packet_global.md`

Redaction:

- `ws redact latest`: `SAFE`

Gemini:

- `ws escalate gemini latest` did not send.
- Reason: Gemini CLI is detected, but this environment cannot run it safely non-interactively.
- Response note: `D:\_ai_brain\frontier\responses\20260514_013643_gemini_20260514_013603_packet_global_response.md`
- Log: `D:\_ai_brain\frontier\logs\20260514_013643_gemini_20260514_013603_packet_global.log`

Codex:

- `ws escalate codex latest` sent the safe packet through `codex exec`.
- Response: `D:\_ai_brain\frontier\responses\20260514_013650_codex_20260514_013603_packet_global_response.md`
- Log: `D:\_ai_brain\frontier\logs\20260514_013650_codex_20260514_013603_packet_global.log`

Claude:

- `ws escalate claude latest` did not send.
- Reason: Claude CLI is not installed.

## Safety

Escalation is explicit only. The command sends only the selected markdown packet, never project folders, model files, `.env` files, credentials, raw datasets, databases, or project repositories.

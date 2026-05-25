# Adapter Profile Contract

Runtime adapter profiles describe manually operated runtimes that an operator may use outside this lane. Profiles are not launch instructions and do not grant execution authority.

Required fields:
- `adapter_id`
- `display_name`
- `launch_mode`
- `auth_mode`
- `quota_model`
- `approval_behavior`
- `supports_checkpointing`
- `supports_noninteractive_mode`
- `default_safe_use`
- `forbidden_assumptions`
- `notes`

Initial adapter profiles:
- `codex_cli`
- `gemini_cli`
- `ollama_local`
- `powershell_manual`
- `wsl_manual`

Codex CLI and Gemini CLI are represented as human-authenticated subscription CLI tools, not API integrations. Runtime Session Lane may record status and blockers for them, but it must not assume API access, unlimited quota, or permission to auto-approve prompts.


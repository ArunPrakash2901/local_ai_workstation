# Adapter Routing Contract

Routing targets in this contract:

- `codex_cli`
- `gemini_cli`
- `ollama_local`
- `powershell_manual`
- `wsl_manual`

## `codex_cli`

- Intended use: bounded technical review/planning workflows from approved artifacts.
- Allowed future task types: `code_review`, `implementation_planning`, `validation_review`, `documentation_update`.
- Quota/auth notes: human-authenticated CLI session with quota/session constraints.
- Approval behavior: may pause for permission prompts; operator approval required.
- Safety limitations: cannot assume API access or unattended control.
- Forbidden assumptions: not an API worker.

## `gemini_cli`

- Intended use: bounded review/planning workflows from approved artifacts.
- Allowed future task types: `product_review`, `design_review`, `documentation_update`, `local_model_summary`.
- Quota/auth notes: human-authenticated CLI session; quota/session limits vary by account/auth mode.
- Approval behavior: may pause for prompts; operator approval required.
- Safety limitations: cannot assume API access or unattended control.
- Forbidden assumptions: not an API worker.

## `ollama_local`

- Intended use: bounded local summarization/review assistance.
- Allowed future task types: `local_model_summary`, `validation_review`, `documentation_update`.
- Quota/auth notes: no external quota; constrained by local hardware.
- Approval behavior: operator-controlled runtime configuration.
- Safety limitations: limited context quality for high-level architecture decisions.
- Forbidden assumptions: not a replacement for approved human gates.

## `powershell_manual`

- Intended use: manual terminal execution context for operator workflows.
- Allowed future task types: `manual_operator_task`, `documentation_update`, `validation_review`.
- Quota/auth notes: none; terminal-only.
- Approval behavior: manual operator execution only.
- Safety limitations: commands must remain inside allowed write roots.
- Forbidden assumptions: not a model adapter.

## `wsl_manual`

- Intended use: manual Linux-shell execution context for operator workflows.
- Allowed future task types: `manual_operator_task`, `documentation_update`, `validation_review`.
- Quota/auth notes: none; terminal-only.
- Approval behavior: manual operator execution only.
- Safety limitations: commands must remain inside allowed write roots.
- Forbidden assumptions: not a model adapter.

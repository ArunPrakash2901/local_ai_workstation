# Slash Command Strategy

This document outlines the design philosophy for mapping user-friendly slash commands (e.g. `/status`) to the authoritative local workstation (`ws`) command surface.

*Note: Slash commands are not actively implemented yet. This is a design framework to guide future UI or alias implementations.*

## Philosophy: Thin Aliases Only
Slash commands must exist **strictly as thin aliases** to the underlying `scripts/ws` router. 
- They must not contain separate logic, state resolution, or configuration management.
- If a feature does not exist in `ws`, it cannot exist as a slash command.

## Why `scripts/ws` Remains the Source of Truth
The `scripts/ws` router acts alongside `registry/ws_command_safety.yaml`. Together, they enforce:
1. Deterministic behavior mapping.
2. Absolute safety-class validation (`check_local_safety.py`).
3. Single point of auditability.
Duplicating routing logic into a separate slash-command handler risks bypassing the `check_local_safety.py` manifests and exposing destructive or non-deterministic actions.

## Anti-Sprawl Rules
1. **No Magic Routing:** A slash command must map 1:1 to a specific `ws` command. 
2. **No Interactive Prompts:** If a `ws` command requires 5 flags, the slash command shouldn't try to "interactively ask" for them; it should map to a single sensible default or require standard arguments.
3. **Naming Convention:** Slash commands should drop the `ws` prefix and follow `/<domain> <action> <object>`.

## Proposed Mapping Table

| Slash Command Alias | Target `ws` Command | Safety Class | Expected Resource Load |
| :--- | :--- | :--- | :--- |
| `/status` | `ws status` | PURE_READ | Low |
| `/safety check` | `python scripts/check_local_safety.py` | PURE_READ | Low |
| `/quant idea new` | `ws quant idea new` | GUARDED_WRITE | Low |
| `/quant hypothesis draft` | `ws quant hypothesis draft` | GUARDED_WRITE | Low |
| `/quant backlog` | `ws quant backlog` | PURE_READ | Low |
| `/matfinog overview` | `ws matfinog overview` | PURE_READ | Low |
| `/matfinog prompts` | `ws matfinog prompts` | PURE_READ | Low |
| `/matfinog queue` | `ws matfinog queue` | PURE_READ | Low |
| `/matfinog validate`| `ws matfinog validate` | PURE_READ | Low |

## Safety Considerations
Before implementing a global slash-command alias file (e.g., `.bash_aliases` mapping `/status` to `ws status`):
- Ensure that the alias injection cannot overwrite native system commands (like `/bin/sh`).
- Treat the slash prefix simply as a keystroke saver. It conveys no extra privileges.
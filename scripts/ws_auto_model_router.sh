#!/bin/bash
set -euo pipefail

WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"
if [ -f "$WS_HOME/scripts/ws_env.sh" ]; then
    source "$WS_HOME/scripts/ws_env.sh"
fi
WS_HOME="${WS_HOME:-/mnt/d/_ai_brain}"

PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"
MODELS_YAML="$WS_HOME/registry/models.yaml"
ACTIVE_MODEL_YAML="$WS_HOME/registry/active_model.yaml"
ACTIVE_KV_YAML="$WS_HOME/registry/active_kv_profile.yaml"

"$PYTHON" - "$MODELS_YAML" "$ACTIVE_MODEL_YAML" "$ACTIVE_KV_YAML" "$@" <<'PY'
import argparse
import json
import sys
import urllib.request
from pathlib import Path

import yaml

models_yaml, active_model_yaml, active_kv_yaml = map(Path, sys.argv[1:4])
argv = sys.argv[4:]

parser = argparse.ArgumentParser(prog="ws_auto_model_router", add_help=False)
parser.add_argument("--profile", default="")
parser.add_argument("--planner-profile", default="")
parser.add_argument("--coder-profile", default="")
parser.add_argument("--reviewer-profile", default="")
args, extras = parser.parse_known_args(argv)
if extras:
    print(f"Unrecognized arguments: {' '.join(extras)}", file=sys.stderr)
    sys.exit(2)

registry = yaml.safe_load(models_yaml.read_text(encoding="utf-8")) or {}
active_model = yaml.safe_load(active_model_yaml.read_text(encoding="utf-8")) or {}
active_kv = yaml.safe_load(active_kv_yaml.read_text(encoding="utf-8")) or {}

profiles = registry.get("profiles", registry)

def installed_models():
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return {item.get("name") for item in payload.get("models", []) if item.get("name")}
    except Exception:
        return set()

available = installed_models()

def lookup_profile(profile_name: str):
    if not profile_name:
        return {}
    entry = profiles.get(profile_name)
    if isinstance(entry, dict):
        entry = dict(entry)
        entry.setdefault("profile", profile_name)
        entry.setdefault("model_name", profile_name)
        return entry
    return {
        "profile": profile_name,
        "model_name": profile_name,
        "role": "direct model name",
        "daily_safe": False,
        "lab_only": False,
    }

def resolve(requested: str, fallback_profile: str, allow_profile_override: bool = True):
    chosen = requested or fallback_profile
    entry = lookup_profile(chosen)
    if entry.get("lab_only") and chosen != fallback_profile:
        entry = lookup_profile(fallback_profile)
        entry["reason"] = "lab_only_not_enabled"
    model = entry.get("model_name", chosen)
    if available and model not in available:
        fallback = lookup_profile(fallback_profile)
        if fallback.get("model_name") in available or fallback_profile == chosen:
            entry = fallback
            model = entry.get("model_name", model)
            entry["reason"] = entry.get("reason") or "fallback_not_installed"
    entry["available"] = not available or model in available
    entry["selected_model"] = model
    return entry

if args.profile:
    planner = resolve(args.profile, "hermes_default")
    coder = resolve(args.profile, "hermes_default")
    reviewer = resolve(args.profile, "hermes_default")
else:
    planner = resolve(args.planner_profile, "hermes_default")
    coder = resolve(args.coder_profile, "qwen_coder_7b")
    reviewer = resolve(args.reviewer_profile, "phi35_fast")

payload = {
    "active": {
        "active_profile": active_model.get("active_profile", "unknown"),
        "active_model": active_model.get("active_model", "unknown"),
        "context_length": active_model.get("context_length", "unknown"),
        "mode": active_model.get("mode", "unknown"),
        "active_kv_profile": active_kv.get("active_profile", "unknown"),
        "kv_cache_type": active_kv.get("kv_cache_type", "unknown"),
    },
    "installed_models": sorted(available),
    "planner": planner,
    "coder": coder,
    "reviewer": reviewer,
}
print(json.dumps(payload, indent=2, sort_keys=True))
PY

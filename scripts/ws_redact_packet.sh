#!/bin/bash
set -euo pipefail

PACKET_FILE=${1:-}
PACKETS_DIR="/mnt/d/_ai_brain/frontier/packets"

if [ "$PACKET_FILE" = "latest" ]; then
    PACKET_FILE=$(ls -t "$PACKETS_DIR"/*.md 2>/dev/null | head -n 1 || true)
fi

if [ -z "$PACKET_FILE" ] || [ ! -f "$PACKET_FILE" ]; then
    echo "Usage: ws redact <packet_path|latest>"
    exit 1
fi

PYTHON="/mnt/d/_ai_brain/runtimes/workstation_venv/bin/python3"

"$PYTHON" - "$PACKET_FILE" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8", errors="replace")
scan_text = text.split("## Safety Notice", 1)[0]
scan_text = scan_text.split("Denied Files:", 1)[0]
lower = scan_text.lower()
size = len(text.encode("utf-8", errors="replace"))
lines = text.splitlines()

blocked = []
warnings = []

blocked_patterns = [
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key block"),
    (r"\bAKIA[0-9A-Z]{16}\b", "AWS access key id"),
    (r"\bghp_[A-Za-z0-9_]{20,}\b", "GitHub personal access token"),
    (r"\bgithub_pat_[A-Za-z0-9_]{20,}\b", "GitHub fine-grained token"),
    (r"\bsk-[A-Za-z0-9_-]{20,}\b", "OpenAI-style API key"),
    (r"(?i)\b(api[_-]?key|secret|token|password|passwd|pwd|broker[_-]?(key|secret|password)|credential)\b\s*[:=]\s*['\"]?[^'\"\s]{8,}", "credential-looking assignment"),
    (r"(?i)^\s*[A-Z0-9_]*(SECRET|TOKEN|PASSWORD|API_KEY|BROKER_KEY)[A-Z0-9_]*\s*=", ".env-style credential assignment"),
]

warning_patterns = [
    (r"(?i)\.env\b", ".env reference"),
    (r"(?i)\bpassword\b", "password reference"),
    (r"(?i)\btoken\b", "token reference"),
    (r"(?i)\bapi[_ -]?key\b", "API key reference"),
    (r"(?i)\bbroker\b", "broker credential reference"),
    (r"(?i)\bcredential", "credential reference"),
    (r"(?i)\bprivate key\b", "private key reference"),
]

for pattern, label in blocked_patterns:
    if re.search(pattern, scan_text, flags=re.MULTILINE):
        blocked.append(label)

for pattern, label in warning_patterns:
    if re.search(pattern, scan_text):
        warnings.append(label)

if size > 120_000:
    warnings.append(f"huge pasted content ({size} bytes)")
if len(lines) > 2_000:
    warnings.append(f"large line count ({len(lines)} lines)")

code_fence_count = text.count("```")
if code_fence_count >= 10 or lower.count("```python") + lower.count("```ts") + lower.count("```js") + lower.count("```tsx") > 4:
    warnings.append("possible full repo dump or excessive code paste")

raw_markers = [
    "dataframe", "parquet", "sqlite", "duckdb", ".csv", ".xlsx", "raw_data",
    "processed_data", "full dataset", "base64,", "node_modules/", ".git/",
]
if sum(1 for marker in raw_markers if marker in lower) >= 3:
    warnings.append("possible raw data dump or generated artifact content")

warnings = sorted(set(warnings))
blocked = sorted(set(blocked))

print(f"Packet: {path}")

if blocked:
    print("BLOCKED")
    print("Reasons:")
    for item in blocked:
        print(f"- {item}")
    if warnings:
        print("Additional warnings:")
        for item in warnings:
            print(f"- {item}")
    sys.exit(2)

if warnings:
    print("WARNING")
    print("Warnings:")
    for item in warnings:
        print(f"- {item}")
    sys.exit(1)

print("SAFE")
PY

#!/bin/bash

set -euo pipefail

if [ -f "/mnt/d/_ai_brain/scripts/ws_env.sh" ]; then
    # shellcheck source=/mnt/d/_ai_brain/scripts/ws_env.sh
    source "/mnt/d/_ai_brain/scripts/ws_env.sh"
fi

WS_HOME=${WS_HOME:-"/mnt/d/_ai_brain"}
STRONGHOLDS_DIR="$WS_HOME/strongholds"
PYTHON="$WS_HOME/runtimes/workstation_venv/bin/python3"

TYPE=""
TITLE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --type)
            TYPE="$2"
            shift 2
            ;;
        --title)
            TITLE="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

if [ -z "$TYPE" ] || [ -z "$TITLE" ]; then
    echo "Usage: ws stronghold-new --type learning|product|feature|research|trading-research --title \"<title>\""
    exit 1
fi

case "$TYPE" in
    learning|product|feature|research|trading-research) ;;
    *)
        echo "Error: Invalid type '$TYPE'. Allowed: learning, product, feature, research, trading-research"
        exit 1
        ;;
esac

to_wsl_path() {
    case "$1" in
        /*) printf '%s' "$1" ;;
        *) wslpath -u "$1" 2>/dev/null || printf '%s' "$1" ;;
    esac
}

to_windows_path() {
    wslpath -w "$1" 2>/dev/null || printf '%s' "$1"
}

# Slugify title
SLUG=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g' | sed -E 's/^-+|-+$//g')
if [ -z "$SLUG" ]; then
    SLUG="unnamed-stronghold"
fi

TARGET_DIR="$STRONGHOLDS_DIR/$TYPE/$SLUG"

if [ -d "$TARGET_DIR" ]; then
    # Add timestamp if slug already exists
    SLUG="${SLUG}-$(date +%Y%m%d-%H%M%S)"
    TARGET_DIR="$STRONGHOLDS_DIR/$TYPE/$SLUG"
fi

mkdir -p "$TARGET_DIR"
mkdir -p "$TARGET_DIR/evidence"
mkdir -p "$TARGET_DIR/prompts"
mkdir -p "$TARGET_DIR/responses"
mkdir -p "$TARGET_DIR/reports"
mkdir -p "$TARGET_DIR/runs"

NOW_TS=$(date +"%Y%m%d_%H%M%S")

# Create common files
cat <<EOF > "$TARGET_DIR/contract.md"
# Stronghold Contract: $TITLE

## Stronghold
- Title: $TITLE
- ID: $SLUG
- Type: $TYPE

## Objective
[Define the core goal here]

## Acceptance Criteria
- [Criteria 1]

## Allowed Files
- [List files or patterns]
EOF

cat <<EOF > "$TARGET_DIR/goals.md"
# Goals: $TITLE
- [Goal 1]
EOF

# Create constraints.md with domain-specific notes
if [ "$TYPE" = "trading-research" ]; then
    cat <<EOF > "$TARGET_DIR/constraints.md"
# Constraints: $TITLE

## Safety Boundaries
- RESEARCH ONLY.
- NO LIVE TRADING.
- NO CAPITAL DEPLOYMENT.
- NO BROKERAGE/API EXECUTION.
- Backtests and paper trading only until explicitly redesigned.

## Denied Files
- .env
- credentials
- private_keys
EOF
else
    cat <<EOF > "$TARGET_DIR/constraints.md"
# Constraints: $TITLE
- [Constraint 1]
EOF
fi

cat <<EOF > "$TARGET_DIR/success_criteria.md"
# Success Criteria: $TITLE
- [Criteria 1]
EOF

cat <<EOF > "$TARGET_DIR/plan.md"
# Plan: $TITLE
1. [Step 1]
EOF

cat <<EOF > "$TARGET_DIR/loop_log.md"
# Loop Log: $TITLE

## $NOW_TS - Stronghold Created
- Actor: local
- Type: $TYPE
- State: CREATED
EOF

# Create type-specific placeholder files
case "$TYPE" in
    learning)
        touch "$TARGET_DIR/syllabus.md"
        touch "$TARGET_DIR/skill_map.md"
        touch "$TARGET_DIR/practice_log.md"
        touch "$TARGET_DIR/assessment.md"
        ;;
    product)
        touch "$TARGET_DIR/product_brief.md"
        touch "$TARGET_DIR/roadmap.md"
        touch "$TARGET_DIR/feature_map.md"
        touch "$TARGET_DIR/release_report.md"
        ;;
    research)
        touch "$TARGET_DIR/literature_map.md"
        touch "$TARGET_DIR/hypothesis_log.md"
        touch "$TARGET_DIR/evidence_matrix.md"
        touch "$TARGET_DIR/research_summary.md"
        ;;
    trading-research)
        touch "$TARGET_DIR/paper_notes.md"
        touch "$TARGET_DIR/strategy_hypothesis.md"
        touch "$TARGET_DIR/backtest_plan.md"
        touch "$TARGET_DIR/risk_constraints.md"
        touch "$TARGET_DIR/paper_trading_report.md"
        ;;
    feature)
        touch "$TARGET_DIR/feature_brief.md"
        touch "$TARGET_DIR/allowed_files.md"
        touch "$TARGET_DIR/validation_plan.md"
        touch "$TARGET_DIR/implementation_report.md"
        ;;
esac

# Create state.json
LIVE_TRADING="false"
if [ "$TYPE" = "trading-research" ]; then
    LIVE_TRADING="false"
fi

cat <<EOF > "$TARGET_DIR/state.json"
{
  "stronghold_id": "$SLUG",
  "type": "$TYPE",
  "title": "$TITLE",
  "current_state": "CREATED",
  "created_at": "$NOW_TS",
  "provider_invocation": false,
  "browser_automation": false,
  "live_trading_enabled": $LIVE_TRADING
}
EOF

echo "Stronghold created: $(to_windows_path "$TARGET_DIR")"
echo "ID: $SLUG"
echo "Type: $TYPE"
echo "Next step: ws stronghold-status"

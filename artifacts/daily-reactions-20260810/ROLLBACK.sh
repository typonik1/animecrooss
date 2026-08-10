#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-$(pwd)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for rel in main.py config.py tests/test_scheduler_helpers.py; do
  mkdir -p "$ROOT/$(dirname "$rel")"
  cp "$SCRIPT_DIR/original/$rel.bak" "$ROOT/$rel"
done
rm -f "$ROOT/reactions.py" "$ROOT/tests/test_daily_reactions.py"
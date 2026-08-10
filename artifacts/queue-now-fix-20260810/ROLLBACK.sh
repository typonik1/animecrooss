#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-$(pwd)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for rel in admin.py builder.py storage.py tests/test_builder_selection.py tests/test_storage_filters.py tests/test_urgent_controls.py; do
  mkdir -p "$ROOT/$(dirname "$rel")"
  cp "$SCRIPT_DIR/original/$rel.bak" "$ROOT/$rel"
done
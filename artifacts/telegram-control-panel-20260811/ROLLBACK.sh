#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${1:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
VERIFY_MODE="${2:-}"
ORIGINAL="$ROOT/artifacts/telegram-control-panel-20260811/original"

cp "$ORIGINAL/admin.py.bak" "$ROOT/admin.py"
cp "$ORIGINAL/main.py.bak" "$ROOT/main.py"
cp "$ORIGINAL/config.py.bak" "$ROOT/config.py"
cp "$ORIGINAL/requirements.txt.bak" "$ROOT/requirements.txt"
cp "$ORIGINAL/tests/test_urgent_controls.py.bak" "$ROOT/tests/test_urgent_controls.py"
rm -f \
  "$ROOT/telegram_ui.py" \
  "$ROOT/botlogs.py" \
  "$ROOT/tests/test_telegram_ui.py" \
  "$ROOT/tests/test_botlogs.py" \
  "$ROOT/tests/test_admin_panel.py" \
  "$ROOT/tests/test_admin_startup.py"

printf 'ROLLBACK_APPLIED=%s\n' "$ROOT"

if [[ "$VERIFY_MODE" == "--verify" ]]; then
  verify_hash() {
    local relative="$1"
    local expected="$2"
    local actual
    actual="$(sha256sum "$ROOT/$relative" | awk '{print toupper($1)}')"
    if [[ "$actual" != "$expected" ]]; then
      printf 'RESTORED_HASH %s %s MATCH=False\n' "$relative" "$actual"
      exit 1
    fi
    printf 'RESTORED_HASH %s %s MATCH=True\n' "$relative" "$actual"
  }

  verify_hash "admin.py" "922C55E87C6FB6B5CF2196A039D7E284D4B563AB6AC73A4E286293CEFDBD1FDF"
  verify_hash "config.py" "49CA277946BA40F956A13B663D98A78C68994108538C05662BA7EF51DAD898F0"
  verify_hash "main.py" "6040AC2276162BCD0DC4990A6B6913F093C93095AC9DFE55A9C3345E2ACA16FC"
  verify_hash "requirements.txt" "2BDD034ABC2D8174C74397EC27D7D9BEF0E78B8F87A9D9E2BDBEB142163E7176"
  verify_hash "tests/test_urgent_controls.py" "49391051967A790967CF7D7130E27C2A3FD80E509DEA5169C74B8B92C522A67C"

  (
    cd "$ROOT"
    python -m pytest -q
  )
  printf 'ROLLBACK_TESTS_EXIT=0\n'
  printf 'RESTORED_BEHAVIOR=original command-only admin; telethon==1.36.0; baseline suite restored\n'
fi

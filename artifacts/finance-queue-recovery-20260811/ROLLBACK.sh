#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${1:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
VERIFY_MODE="${2:-}"
ORIGINAL="$ROOT/artifacts/finance-queue-recovery-20260811/original"

cp "$ORIGINAL/admin.py.bak" "$ROOT/admin.py"
cp "$ORIGINAL/builder.py.bak" "$ROOT/builder.py"
cp "$ORIGINAL/telegram_ui.py.bak" "$ROOT/telegram_ui.py"
cp "$ORIGINAL/config.py.bak" "$ROOT/config.py"
cp "$ORIGINAL/main.py.bak" "$ROOT/main.py"
cp "$ORIGINAL/tests/test_admin_panel.py.bak" "$ROOT/tests/test_admin_panel.py"
cp "$ORIGINAL/tests/test_admin_startup.py.bak" "$ROOT/tests/test_admin_startup.py"
cp "$ORIGINAL/tests/test_builder_selection.py.bak" "$ROOT/tests/test_builder_selection.py"
cp "$ORIGINAL/tests/test_telegram_ui.py.bak" "$ROOT/tests/test_telegram_ui.py"

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

  verify_hash "admin.py" "2282B9DF31BB0AD9B20AEAC9E02B6E55596FBF3CBBF70AF85F0FFA72FEFEC2B2"
  verify_hash "builder.py" "80D4471E27DCAE467C4F31DFE904D7063471A2253D3D307F3A8BD624E14E3BB3"
  verify_hash "telegram_ui.py" "829AEA4F14BF4CD11600DC67AA446519E39A8F26A22E5441CFDF1C843C087744"
  verify_hash "config.py" "1F83E0C3729B30E4CB738F57A23AA6449911B03A214A10886CA0A97AD238921B"
  verify_hash "main.py" "262EB10C1956FFCDA56F40CFA5309DD43D70D6F166042A5847A7420022D5259C"
  verify_hash "tests/test_admin_panel.py" "E12649355E8C46BF077F1567158033B820B82266841EAEE23E9062C51C78ECE3"
  verify_hash "tests/test_admin_startup.py" "AF23F600733406A5D7E7DE39996B0DEDC2B50C0EBAD9B34748CDD53A6B9C4BC1"
  verify_hash "tests/test_builder_selection.py" "A8503674572D9AADB972E901CA81192796729460AA674E2E110D7904D0A54845"
  verify_hash "tests/test_telegram_ui.py" "1B7CF015083022E160D023A042E0D5B6333DD8D8FE69FF131A5739BB25B0AE4A"

  (
    cd "$ROOT"
    python -m pytest -q
  )
  printf 'ROLLBACK_TESTS_EXIT=0\n'
  printf 'RESTORED_BEHAVIOR=ReactionsEmojiVK defaults; same-content edits raise; late manual build targets expired today only; 73-test baseline restored\n'
fi

#!/usr/bin/env bash
# CI guard: deprecated 列の新規参照を禁止
# 対象: trust_level / products.unit_price / customers.transaction_count
#
# ADR-SA-12 C-2/C-4: 既存ファイルの既存参照は温存し、
# 新規ファイル・新規変更での参照のみブロックする。

set -e

FAIL=0

check() {
  local label="$1"
  local pattern="$2"

  while IFS= read -r file; do
    # .py / .ts / .tsx ファイルのみ対象
    case "$file" in
      *.py|*.ts|*.tsx) ;;
      *) continue ;;
    esac

    [[ -f "$file" ]] || continue

    # migration ファイル・テストファイル・CI スクリプト自体はスキップ
    case "$file" in
      migrations/*|*.test.*|*.spec.*|.github/scripts/*) continue ;;
    esac

    # git diff で新規追加行のみチェック（+で始まる行）
    if git diff origin/develop...HEAD -- "$file" | grep '^+' | grep -v '^+++' | grep -q "$pattern" 2>/dev/null; then
      echo "DEPRECATED: $label found in new code in $file"
      FAIL=1
    fi
  done < <(git diff --name-only origin/develop...HEAD)
}

# trust_level
check "trust_level" "trust_level"

# products.unit_price (unit_price / unit_price_usd / unit_price_eur on products)
check "products.unit_price" "unit_price"

# customers.transaction_count
check "transaction_count" "transaction_count"

if [[ $FAIL -ne 0 ]]; then
  echo ""
  echo "The above deprecated columns must not be referenced in new code (ADR-SA-12 C-2/C-4)."
  echo "Existing references will be migrated in a separate batch."
  exit 1
fi

echo "deprecated columns check PASSED"

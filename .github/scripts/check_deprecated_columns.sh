#!/usr/bin/env bash
# CI guard: deprecated 列の新規参照を禁止
# 対象: trust_level / products.unit_price / customers.transaction_count
#
# ADR-SA-12 C-2/C-4: 既存ファイルの既存参照は温存し、
# 新規ファイル・新規変更での参照のみブロックする。

set -e

FAIL=0

# check <label> <pattern> [exempt-path-substring]
#   exempt-path-substring: このパス文字列を含むファイルはこのチェックのみ免除する（任意）。
#   免除を追加する場合は必ず理由と追跡 Issue 番号をコメントで記載すること。
check() {
  local label="$1"
  local pattern="$2"
  local exempt="${3:-}"

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

    # 明示的免除（ファイルパス部分一致）
    # 免除を追加する際は必ず: 理由 / 移植元 / 廃止完了時の撤去タスク を記載すること
    if [[ -n "$exempt" && "$file" == *"$exempt"* ]]; then
      continue
    fi

    # git diff で新規追加行のみチェック（+で始まる行）
    if git diff origin/develop...HEAD -- "$file" | grep '^+' | grep -v '^+++' | grep -q "$pattern" 2>/dev/null; then
      echo "DEPRECATED: $label found in new code in $file"
      FAIL=1
    fi
  done < <(git diff --name-only origin/develop...HEAD)
}

# trust_level
check "trust_level" "trust_level"

# products.unit_price: "products." + unit_price のみ（own_inventory.unit_price は別列で合法）
#
# 免除: frontend/src/pages/products/ProductEditPage.tsx
#   理由: ADR-122 Phase D で ProductsPage.tsx の既存モーダルを直接移植したファイル。
#         移植元 ProductsPage.tsx は「既存ファイルの既存参照は温存」ルールで通過済み。
#         ProductEditPage.tsx は新規ファイルだが内容は既存コードと等価（新機能追加なし）。
#         廃止完了の段取りと根拠（backend/app/services/inventory_search.py:337 →
#         frontend/src/pages/quote-create/quoteDraft.ts:96）は追跡 Issue #1850 に記録済み。
#         廃止完了後にこの免除行（exempt 引数）を削除すること（Issue #1850 クローズ時）。
check "products.unit_price" \
  "products\.unit_price\|p\.unit_price\|products\.unit_price_usd\|products\.unit_price_eur" \
  "frontend/src/pages/products/ProductEditPage.tsx"

# customers.transaction_count
check "transaction_count" "transaction_count"

if [[ $FAIL -ne 0 ]]; then
  echo ""
  echo "The above deprecated columns must not be referenced in new code (ADR-SA-12 C-2/C-4)."
  echo "Existing references will be migrated in a separate batch."
  exit 1
fi

echo "deprecated columns check PASSED"

#!/bin/bash
# check-migration-duplicate-registration.sh — run_all_migrations.sh の二重登録検出
#
# 目的:
#   - run_sql / run_py で同じファイルパスが複数回登録されていないかを確認する
#   - #3965 系調査で見つかった重複（20260831_110000_create_tcg_analysis_tables_t004.sql
#     が line 530 と 536 に登録されていた）の再発を防ぐ
#
# 使い方:
#   bash scripts/check-migration-duplicate-registration.sh [--migrations-script PATH]

set -euo pipefail

MIGRATIONS_SCRIPT="scripts/run_all_migrations.sh"

while [ $# -gt 0 ]; do
  case "$1" in
    --migrations-script)
      MIGRATIONS_SCRIPT="${2:-}"
      shift 2
      ;;
    -h|--help)
      echo "Usage: check-migration-duplicate-registration.sh [--migrations-script PATH]"
      exit 0
      ;;
    *)
      echo "❌ unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [ ! -f "$MIGRATIONS_SCRIPT" ]; then
  echo "❌ registration source not found: $MIGRATIONS_SCRIPT" >&2
  exit 1
fi

duplicates=$(grep -E '^run_(sql|py)[[:space:]]' "$MIGRATIONS_SCRIPT" \
  | awk '{print $2}' \
  | sort \
  | uniq -d || true)

if [ -n "$duplicates" ]; then
  echo "❌ MIGRATION DUPLICATE REGISTRATION CHECK FAILED"
  echo "以下のパスが scripts/run_all_migrations.sh に複数回登録されています:"
  echo "$duplicates" | while IFS= read -r dup; do
    echo " - $dup"
    grep -n "$dup" "$MIGRATIONS_SCRIPT" | sed 's/^/     /'
  done
  exit 1
fi

echo "✅ 二重登録なし"

#!/bin/bash
# 会社と連絡先の状態の4行を本番に入れる（1回だけのデータ変更・ADR-1007 決定1）。設計 design.md §4。
# PO が ! で流す。manual-only 鍵を使う（エージェントは流さない）。
# 順番: precheck（表があり0行）→ dryrun（入れて数えて取り消す）→ commit → verify
# 戻し方はこの台本に入れない（行を消すのは別の判断・PO 確認）。便2 の前なら行があっても何にも使われない。
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SSH=(ssh -F /dev/null -i "$HOME/.ssh/manual-only/id_ed25519" -o IdentitiesOnly=yes ubuntu@49.212.137.46)
PSQL="docker exec -i astro-webapp-postgres-1 psql -U jarvis -d jarvis_db -v ON_ERROR_STOP=1 -X"
SHOW="SELECT code, name_ja, name_en, sort_order, is_active, selectable_on_create FROM public.customer_statuses ORDER BY sort_order;"
step="${1:-}"
case "$step" in
  precheck)
    printf '%s\n' "SELECT to_regclass('public.customer_statuses') AS table_name;" "SELECT count(*) AS rows FROM public.customer_statuses;" | "${SSH[@]}" "$PSQL" ;;
  dryrun)
    { printf '%s\n' "BEGIN;" "SET LOCAL app.is_operator = 'true';"; cat "$HERE/insert-customer-statuses.sql"; printf '%s\n' "$SHOW" "ROLLBACK;"; } | "${SSH[@]}" "$PSQL" ;;
  commit)
    { printf '%s\n' "BEGIN;" "SET LOCAL app.is_operator = 'true';"; cat "$HERE/insert-customer-statuses.sql"; printf '%s\n' "$SHOW" "COMMIT;"; } | "${SSH[@]}" "$PSQL" ;;
  verify)
    printf '%s\n' "$SHOW" "SELECT count(*) AS rows FROM public.customer_statuses;" | "${SSH[@]}" "$PSQL" ;;
  *) echo "使い方: bash run-insert.sh precheck|dryrun|commit|verify" >&2; exit 2 ;;
esac

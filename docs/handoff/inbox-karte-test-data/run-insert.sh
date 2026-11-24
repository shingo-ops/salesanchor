#!/usr/bin/env bash
# PO が `! bash <このファイル>` で流す。テナント001にテストデータ3件を入れる。
# 1) 試し流し（最後に ROLLBACK）→ 3件が出ることを確かめる 2) 同じ SQL を COMMIT で流す 3) 数え直す
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
SQL="$DIR/insert.sql"
SSH=(ssh -i "$HOME/.ssh/manual-only/id_ed25519" -o BatchMode=yes ubuntu@49.212.137.46)
PSQL='docker exec -i astro-webapp-postgres-1 psql -U jarvis -d jarvis_db -v ON_ERROR_STOP=1'

echo "== 1) 試し流し（取り消す）"
DRY="$("${SSH[@]}" "$PSQL" < "$SQL")"
echo "$DRY"
if ! grep -q '(3 rows)' <<<"$DRY" || ! grep -q '^ROLLBACK' <<<"$DRY"; then
  echo "止めました: 試し流しで3件にならないか、取り消しが確かめられません"; exit 1
fi

echo "== 2) 本番に書き込む（COMMIT）"
sed 's/^ROLLBACK;$/COMMIT;/' "$SQL" | "${SSH[@]}" "$PSQL"

echo "== 3) 数え直す"
"${SSH[@]}" "docker exec -i astro-webapp-postgres-1 psql -U jarvis -d jarvis_db -At -c \"SELECT l.lead_code, l.status, m.message_id FROM tenant_001.leads l JOIN tenant_001.meta_messages m ON m.lead_id = l.id WHERE l.lead_code LIKE 'TST-KARTE-%' ORDER BY 1\""
echo "完了"

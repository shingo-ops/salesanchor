#!/bin/bash
# D2: 名簿に無い値の後始末（PO 2026-11-06）。設計 docs/handoff/channel-master-shared/design.md §3-2。
# PO が ! で流す。manual-only 鍵を使う（エージェントは流さない）。
# 順番: precheck → dryrun → backup → commit → verify（戻すとき: rollback と restore006 <写し>）
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SSH=(ssh -F /dev/null -i "$HOME/.ssh/manual-only/id_ed25519" -o IdentitiesOnly=yes ubuntu@49.212.137.46)
PSQL="docker exec -i astro-webapp-postgres-1 psql -U jarvis -d jarvis_db -v ON_ERROR_STOP=1 -X"
# 消す14の表だけを写す（残す表は写さない。戻すときに二重にならない）
TABLES="message_translations outbound_translation_drafts meta_messages lead_attachments lead_channels invoice_items invoices quote_items quotes order_financials orders contacts companies leads"
step="${1:-}"
case "$step" in
  precheck|dryrun|commit|verify|rollback)
    "${SSH[@]}" "$PSQL" < "$HERE/$step.sql" ;;
  backup)
    ts="$(date -u +%Y%m%dT%H%M%SZ)"
    out="/home/ubuntu/backups/tenant_drop/${ts}_tenant_006_d2_14tables.sql"
    targs=""
    for t in $TABLES; do targs="$targs -t tenant_006.$t"; done
    "${SSH[@]}" "mkdir -p /home/ubuntu/backups/tenant_drop && docker exec astro-webapp-postgres-1 pg_dump -U jarvis -d jarvis_db --data-only --no-owner --no-acl --disable-triggers $targs > $out && ls -l $out && grep -c '^COPY ' $out" ;;
  restore006)
    f="${2:?写しのファイルのパスを渡す}"
    "${SSH[@]}" "docker exec -i astro-webapp-postgres-1 psql -U jarvis -d jarvis_db -v ON_ERROR_STOP=1 -X --single-transaction < $f" ;;
  *) echo "使い方: bash run.sh precheck|dryrun|backup|commit|verify|rollback|restore006 <file>" >&2; exit 2 ;;
esac

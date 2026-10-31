#!/bin/bash
# run_all_migrations.sh — 全DBマイグレーションを1本で実行する統合ランナー
#
# 目的:
#   deploy.yml の migration ステップ（旧 part 1 / part 2）を統合し、
#   「新マイグレーション追加時は deploy.yml ではなくこのファイルに追記する」を
#   唯一のルール（SSoT）にする。
#
# 使い方（deploy.yml から呼ばれる）:
#   bash scripts/run_all_migrations.sh
#
# 注意:
#   - set -e により途中でエラーが出た時点で即座に停止する
#   - 全マイグレーションは冪等設計（何度実行しても安全）
#   - 新マイグレーションは末尾の「ここから追加」セクションに追加すること
#   - 番号付きログで失敗箇所を特定できる（エラー時に [N/NN] が表示される）
#
# 参考: docs/adr/ADR-082, docs/adr/ADR-045

set -e

REPO_DIR="${REPO_DIR:-/home/ubuntu/salesanchor}"
BACKEND="astro-webapp-backend-1"
POSTGRES="astro-webapp-postgres-1"
PSQL="psql -U jarvis -d jarvis_db -v ON_ERROR_STOP=1"

# 接続の名前の正本（deploy-db-stall §16-3）。cd の前に、このスクリプトの位置から読む。
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/lib/db-app-names.sh"

cd "${REPO_DIR}"

# SA-18 Phase2: bootstrap ステップが別 SSH セッションで .env に書いた
# ADMIN_DATABASE_URL を引き継ぐ。set -a でエクスポートして子プロセスに渡す。
if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

# ── 前処理: scripts / migrations をコンテナにコピー ──────────────────────────
echo ">>> [0] Syncing scripts/ and migrations/ into backend container..."
docker cp scripts "${BACKEND}:/app/"
docker cp migrations "${BACKEND}:/app/"

# ── ヘルパー関数 ──────────────────────────────────────────────────────────────
STEP=0


TOTAL=$(grep -cE '^run_(sql|py)[[:space:]]' "$0" 2>/dev/null || echo 0)

# 稼働中のアプリとロックを取り合ったら、同じファイルを流し直す（全 migration は冪等で、
# CI のドライラン2周目で再実行が通ることを確かめている）。ほかのエラーは今までどおり即停止。
# ロック待ちは1秒で諦める。待っている間は後から来た在庫表などの読み取りも止まるため（ADR-1037）。
# 再試行は3秒あけ、1回の実行全体で合計40回まで。1ファイルでもその40回まで使える（移行ステップの打ち切り10分に収める。ADR-1037 便1.1）。
SQL_LOCK_TIMEOUT="${SQL_LOCK_TIMEOUT:-1s}"
SQL_RETRY_MAX_ATTEMPTS="${SQL_RETRY_MAX_ATTEMPTS:-40}"
SQL_RETRY_SLEEP_SEC="${SQL_RETRY_SLEEP_SEC:-3}"
SQL_RETRY_BUDGET="${SQL_RETRY_BUDGET:-40}"
SQL_RETRY_USED=0
# 流し直しの判定に使う文字列（run_sql と run_py で共有。ADR-1037 の拡張）
SQL_RETRY_PATTERN="deadlock detected|canceling statement due to lock timeout"
# 鍵が取れなかったときの手がかり: 開始から1秒を超えて開いている接続（ADR-1037 便1.1）
# 公開リポジトリの Actions ログに出るため、SQL の文面・接続元アドレスは出さない（命令の先頭1語と表名だけ）
log_lock_holders() {
  echo ">>> [${STEP}/${TOTAL}] lock holders (xact > 1s):"
  docker exec -e PGOPTIONS="-c lock_timeout=1s -c statement_timeout=5s" "${POSTGRES}" ${PSQL} -At -F ' | ' -c "SELECT a.pid, a.usename, a.application_name, a.state, coalesce(a.wait_event_type, '-'), round(extract(epoch FROM now() - a.xact_start))::int AS xact_sec, upper(coalesce(substring(a.query from '^[[:space:]]*([A-Za-z]+)'), '-')) AS cmd, coalesce((SELECT string_agg(DISTINCT c.relname || ':' || l.mode, ',') FROM pg_locks l JOIN pg_class c ON c.oid = l.relation WHERE l.pid = a.pid AND l.granted AND l.database = (SELECT oid FROM pg_database WHERE datname = current_database()) AND c.relkind IN ('r', 'p', 'v')), '-') AS locks FROM pg_stat_activity a WHERE a.pid <> pg_backend_pid() AND a.backend_type = 'client backend' AND a.xact_start < now() - interval '1 second' ORDER BY a.xact_start" 2>&1 | sed "s/^/>>> [${STEP}\/${TOTAL}]   /" || true
}
# Python の移行は本物を直接ではなく入口 scripts/migration_py_entry.py 経由で動かす（ADR-1037 の拡張）。
# 入口が MIGRATION_LOCK_TIMEOUT を見て create_async_engine を差し替え、接続ごとにロック待ちを SQL_LOCK_TIMEOUT にする。
# 差し替えは暗黙なので、入口が終了時に「applied to N engine(s)」を標準エラーへ出す。移行本体は触らない。
# ロック待ちで失敗したら run_sql と同じ判定・回数・間隔・全体上限で同じファイルを流し直す。ほかのエラーは即停止。
run_py() {
  local script="$1"
  shift
  STEP=$((STEP + 1))
  echo ">>> [${STEP}/${TOTAL}] python ${script} $*"
  local attempt=1 rc errlog
  errlog="$(mktemp)"
  while true; do
    rc=0
    # SA-18 Phase2: Python マイグレーションは DDL を含むため ADMIN_DATABASE_URL で実行。
    # ADMIN_DATABASE_URL 未設定時は DATABASE_URL にフォールバック（後方互換）。
    docker exec \
      -e DATABASE_URL="${ADMIN_DATABASE_URL:-$DATABASE_URL}" \
      -e MIGRATION_LOCK_TIMEOUT="${SQL_LOCK_TIMEOUT}" \
      "$@" -w /app "${BACKEND}" python scripts/migration_py_entry.py "${script}" 2>"${errlog}" || rc=$?
    cat "${errlog}" >&2
    if [ "${rc}" -eq 0 ]; then
      rm -f "${errlog}"
      return 0
    fi
    if grep -qE "${SQL_RETRY_PATTERN}" "${errlog}"; then
      [ "${attempt}" -eq 1 ] && log_lock_holders
      if [ "${attempt}" -lt "${SQL_RETRY_MAX_ATTEMPTS}" ] && [ "${SQL_RETRY_USED}" -lt "${SQL_RETRY_BUDGET}" ]; then
        attempt=$((attempt + 1))
        SQL_RETRY_USED=$((SQL_RETRY_USED + 1))
        echo ">>> [${STEP}/${TOTAL}] lock conflict; retry ${attempt}/${SQL_RETRY_MAX_ATTEMPTS} in ${SQL_RETRY_SLEEP_SEC}s (total ${SQL_RETRY_USED}/${SQL_RETRY_BUDGET}): ${script}"
        sleep "${SQL_RETRY_SLEEP_SEC}"
        continue
      fi
      echo ">>> [${STEP}/${TOTAL}] lock conflict; retry limit reached (file ${attempt}/${SQL_RETRY_MAX_ATTEMPTS}, total ${SQL_RETRY_USED}/${SQL_RETRY_BUDGET}): ${script}"
      log_lock_holders
    fi
    rm -f "${errlog}"
    return "${rc}"
  done
}
run_sql() {
  local file="$1"
  STEP=$((STEP + 1))
  echo ">>> [${STEP}/${TOTAL}] psql < ${file}"
  local attempt=1 rc errlog
  errlog="$(mktemp)"
  while true; do
    rc=0
    docker exec -e PGAPPNAME="${SA_APPNAME_MIGRATION:-salesanchor_migration}" -e PGOPTIONS="-c lock_timeout=${SQL_LOCK_TIMEOUT}" -i "${POSTGRES}" ${PSQL} < "${REPO_DIR}/${file}" 2>"${errlog}" || rc=$?
    cat "${errlog}" >&2
    if [ "${rc}" -eq 0 ]; then
      rm -f "${errlog}"
      return 0
    fi
    if grep -qE "${SQL_RETRY_PATTERN}" "${errlog}"; then
      [ "${attempt}" -eq 1 ] && log_lock_holders
      if [ "${attempt}" -lt "${SQL_RETRY_MAX_ATTEMPTS}" ] && [ "${SQL_RETRY_USED}" -lt "${SQL_RETRY_BUDGET}" ]; then
        attempt=$((attempt + 1))
        SQL_RETRY_USED=$((SQL_RETRY_USED + 1))
        echo ">>> [${STEP}/${TOTAL}] lock conflict; retry ${attempt}/${SQL_RETRY_MAX_ATTEMPTS} in ${SQL_RETRY_SLEEP_SEC}s (total ${SQL_RETRY_USED}/${SQL_RETRY_BUDGET}): ${file}"
        sleep "${SQL_RETRY_SLEEP_SEC}"
        continue
      fi
      echo ">>> [${STEP}/${TOTAL}] lock conflict; retry limit reached (file ${attempt}/${SQL_RETRY_MAX_ATTEMPTS}, total ${SQL_RETRY_USED}/${SQL_RETRY_BUDGET}): ${file}"
      log_lock_holders
    fi
    rm -f "${errlog}"
    return "${rc}"
  done
}

# >>> read-probe begin
# ADR-1037 便1.2: 移行の間、在庫表の GET が読む表を2秒おきに読み、鍵待ちで何ms待たされるかを測る（K7）。
# 計測は読み取りだけ（ACCESS SHARE）。結果は止めるときに時刻・ms・回数だけをログに出す（SQL・表名は出さない）。
# 関数名は run_ で始めない（TOTAL は ^run_(sql|py) の行を数えるため）。
READ_PROBE_INTERVAL_SEC="${READ_PROBE_INTERVAL_SEC:-2}"
READ_PROBE_SLOW_MS="${READ_PROBE_SLOW_MS:-2000}"
READ_PROBE_STMT_TIMEOUT="${READ_PROBE_STMT_TIMEOUT:-3s}"
READ_PROBE_TABLES="${READ_PROBE_TABLES:-analysis_results extraction_items extraction_jobs source_messages supplier_channels item_corrections line_conditions products line_units product_search_keywords suppliers type_master tcg_distribution_settings users}"
READ_PROBE_PID=""
READ_PROBE_OUT=""
read_probe_start() {
  READ_PROBE_OUT="$(mktemp)" || { READ_PROBE_OUT=""; return 0; }
  READ_PROBE_PARENT=$$
  (
    set +e
    probe_args=()
    for probe_t in ${READ_PROBE_TABLES}; do
      probe_args+=(-c "SELECT 1 FROM public.${probe_t} LIMIT 1")
    done
    while :; do
      kill -0 "${READ_PROBE_PARENT}" 2>/dev/null || exit 0
      probe_t0=${EPOCHREALTIME/[.,]/}
      docker exec -e PGOPTIONS="-c lock_timeout=${READ_PROBE_STMT_TIMEOUT} -c statement_timeout=${READ_PROBE_STMT_TIMEOUT}" \
        -e PGAPPNAME=sa_read_probe "${POSTGRES}" \
        psql -X -q -At -U jarvis -d jarvis_db "${probe_args[@]}" >/dev/null 2>"${READ_PROBE_OUT}.err"
      probe_rc=$?
      probe_t1=${EPOCHREALTIME/[.,]/}
      probe_err="$(grep -c 'ERROR:' "${READ_PROBE_OUT}.err" 2>/dev/null)"
      [[ ${probe_err} =~ ^[0-9]+$ ]] || probe_err=0
      if [ "${probe_rc}" -ne 0 ] && [ "${probe_err}" -eq 0 ]; then probe_err=1; fi
      if [[ ${probe_t0} =~ ^[0-9]+$ ]] && [[ ${probe_t1} =~ ^[0-9]+$ ]]; then
        echo "$(( probe_t0 / 1000000 )) $(( (probe_t1 - probe_t0) / 1000 )) ${probe_err}" >>"${READ_PROBE_OUT}"
      else
        echo "0 - ${probe_err}" >>"${READ_PROBE_OUT}"
      fi
      sleep "${READ_PROBE_INTERVAL_SEC}"
    done
  ) </dev/null >/dev/null 2>&1 &
  READ_PROBE_PID=$!
}
read_probe_stop() {
  [ -n "${READ_PROBE_PID:-}" ] || return 0
  kill "${READ_PROBE_PID}" 2>/dev/null || true
  wait "${READ_PROBE_PID}" 2>/dev/null || true
  READ_PROBE_PID=""
  local probe_sum="" probe_kind="" pa="" pb="" pc="" pd="" pe="" probe_shown=0
  probe_sum="$(awk -v slow="${READ_PROBE_SLOW_MS}" '
    { n++; err += $3
      if ($2 == "-") { inv++ } else { if ($2 + 0 > max) max = $2 + 0; if ($2 + 0 > slow) { ns++; print "SLOW " $1 " " $2 } } }
    END { print "SUM " n + 0 " " ns + 0 " " err + 0 " " inv + 0 " " max + 0 }
  ' "${READ_PROBE_OUT}" 2>/dev/null)" || true
  while read -r probe_kind pa pb pc pd pe; do
    if [ "${probe_kind}" = "SLOW" ]; then
      if [ "${probe_shown}" -lt 20 ]; then
        echo ">>> [final] read probe slow: $(TZ=UTC printf '%(%Y-%m-%dT%H:%M:%SZ)T' "${pa}") ${pb}ms" || true
        probe_shown=$((probe_shown + 1))
      fi
    elif [ "${probe_kind}" = "SUM" ]; then
      echo ">>> [final] read probe: n=${pa} slow=${pb} error=${pc} invalid=${pd} max=${pe}ms"
    fi
  done <<< "${probe_sum:-SUM 0 0 0 0 0}" || true
  rm -f "${READ_PROBE_OUT}" "${READ_PROBE_OUT}.err" || true
  return 0
}
# <<< read-probe end

preflight_registered_files() {
  echo ">>> [0] Verifying registered migration files exist..."
  bash scripts/check-migration-registration-exists.sh \
    --mode container \
    --repo-root "${REPO_DIR}" \
    --backend-container "${BACKEND}"
}

preflight_registered_files

# ADR-1052 段1: ai_cloud（相談係用の伏せたビュー）も同じ理由で先頭で外す。ai_ro を外す前に置く
# （ここで失敗しても ai_ro は外れていないので、今の読む窓口は止まらない）。この行はずっと残す（戻すときも消さない）。
# 作成は下の EXIT trap が ai_ro とは別の手順で行う。
run_sql migrations/20261024_100200_drop_ai_cloud_views.sql

# ADR-1024: ai_ro ビューを一覧の先頭で外す。ビューが依存していると、後続 migration の
# DROP / ALTER（列削除・型変更・表の作り直し）が止まるため。作成は下の EXIT trap が最後に行う。
run_sql migrations/20261017_125900_drop_ai_ro_views.sql

# ADR-1024: ai_ro ビューの作成（秘密列を除く）。スクリプトの成否にかかわらず、常に最後に流す。
# 将来の migration が末尾に追記されても、作成は常に最後になる。
# 途中で失敗した場合も作り直す（拒否リストは流した時点の列名で決まり、途中の状態にも同じ判定が当たる。ADR-1024 改訂）。
# 作成の成否は終了コードを変えない（元の rc を返す）。待ちの上限は AI_RO_CREATE_TIMEOUT（1文ごと）。
# （TOTAL は ^run_ 行を数えるため、ここでは run_sql を使わず直接流す）
AI_RO_CREATE_SQL="migrations/20261017_130100_create_ai_ro_views.sql"
AI_RO_CREATE_TIMEOUT="${AI_RO_CREATE_TIMEOUT:-30s}"
# ADR-1052 段1: ai_cloud の作成（trap の中で ai_ro の後に別の手順で流す。ai_ro の失敗でも試す・逆も同じ）
AI_CLOUD_CREATE_SQL="migrations/20261024_100300_create_ai_cloud_views.sql"
AI_CLOUD_CREATE_TIMEOUT="${AI_CLOUD_CREATE_TIMEOUT:-30s}"
_ai_ro_create_on_exit() {
  local rc=$?
  trap - EXIT
  if declare -F read_probe_stop >/dev/null; then read_probe_stop || true; fi
  if [ "${rc}" -ne 0 ]; then
    echo ">>> [final] script failed rc=${rc}; recreating ai_ro views anyway"
  fi
  echo ">>> [final] psql < ${AI_RO_CREATE_SQL}"
  if [ ! -f "${REPO_DIR}/${AI_RO_CREATE_SQL}" ]; then
    echo "⚠️ ${AI_RO_CREATE_SQL} が見つかりません（ai_ro は外れたまま＝AI は読めない）"
  # ビューは AI が読むための補助。作成に失敗しても入れ替えの成否は変えず、「読めない」側に倒す
  # 1文ごとの上限。打ち切り（57014）は作成 SQL の WHEN others に捕まらず、全体が戻って下の警告に入る
  # VERBOSITY=terse: エラーは重さ・本文・位置だけにし、CONTEXT（SQL 文）を公開ログに出さない
  elif ! docker exec -e PGOPTIONS="-c statement_timeout=${AI_RO_CREATE_TIMEOUT}" -i "${POSTGRES}" ${PSQL} -v VERBOSITY=terse < "${REPO_DIR}/${AI_RO_CREATE_SQL}"; then
    echo "⚠️ ai_ro views の作成に失敗（ai_ro は外れたまま＝AI は読めない）"
  fi
  # ADR-1052 段1: ai_cloud は ai_ro の結果に関わらず試す（失敗しても終了コードは変えない）
  echo ">>> [final] psql < ${AI_CLOUD_CREATE_SQL}"
  if [ ! -f "${REPO_DIR}/${AI_CLOUD_CREATE_SQL}" ]; then
    echo "⚠️ ${AI_CLOUD_CREATE_SQL} が見つかりません（ai_cloud は外れたまま＝相談係は読めない）"
  elif ! docker exec -e PGOPTIONS="-c statement_timeout=${AI_CLOUD_CREATE_TIMEOUT}" -i "${POSTGRES}" ${PSQL} -v VERBOSITY=terse < "${REPO_DIR}/${AI_CLOUD_CREATE_SQL}"; then
    echo "⚠️ ai_cloud views の作成に失敗（ai_cloud は外れたまま＝相談係は読めない）"
    # 全体が戻ると build_log に書けないため、ここで失敗の 1 行を書く（これも失敗したら警告だけ）
    if ! docker exec -e PGOPTIONS="-c statement_timeout=${AI_CLOUD_CREATE_TIMEOUT}" -i "${POSTGRES}" ${PSQL} -v VERBOSITY=terse -c "INSERT INTO ai_cloud_meta.build_log(ok, error_class) VALUES (false, 'psql_failed')"; then
      echo "⚠️ ai_cloud_meta.build_log への失敗の記録にも失敗"
    fi
  fi
  # ADR-1052 段2: ai_unmask_owner の権限を今の ai_cloud の元の表に合わせて付け直す（違う表だけ変える）
  # ai_cloud の作成が失敗した回も呼ぶ（build_columns は前のまま残るので、前と同じ表に付く）。終了コードは変えない
  echo ">>> [final] grant ai_unmask_owner"
  local _gu_start=${SECONDS}
  if ! docker exec -e PGOPTIONS="-c statement_timeout=${AI_CLOUD_CREATE_TIMEOUT}" -i "${POSTGRES}" ${PSQL} -v VERBOSITY=terse -c 'SELECT ops_case.grant_unmask_owner();'; then
    echo "⚠️ ai_unmask_owner の権限の付け直しに失敗（値を返す口は前の権限のまま）"
  fi
  echo ">>> [final] grant ai_unmask_owner done in $((SECONDS - _gu_start))s"
  exit "${rc}"
}
trap _ai_ro_create_on_exit EXIT
# deploy-db-stall §16-2: TERM・HUP・INT は backup.sh と同じく exit に変える（EXIT の trap が動く）。
# 前面の docker exec が終わってから trap が動くので、ai_ro の作り直しは止めた文と同時に走らない。
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP
# ADR-1037 便1.2: trap の後で計測を始める（どこで落ちても上の trap が止める）
read_probe_start

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# マイグレーション一覧（順序厳守・冪等必須）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Meta Webhook Phase 2
run_py  scripts/migrate_meta.py
run_sql migrations/013_add_meta_webhook_idempotency.sql

# Phase 1 再設計
run_sql migrations/014_create_current_tenant_id_function.sql
run_sql migrations/018_extend_permissions_with_menu_grain.sql
run_sql migrations/023_fix_system_admin_is_system_flag.sql
run_sql migrations/024_add_staff_bots_permissions.sql
run_sql migrations/025_resync_owner_admin_all_permissions.sql

# Phase 1-B-1: customer_contact_channels
run_sql migrations/026_create_customer_contact_channels.sql
run_sql migrations/027_backfill_customer_contact_channels.sql

# Phase 1-B-2: companies / contacts
run_sql migrations/028_create_companies.sql
run_sql migrations/029_create_contacts.sql
run_sql migrations/030_create_company_contact_subtables.sql
run_sql migrations/031_create_customer_migration_map.sql
run_sql migrations/032_add_company_contact_to_downstream.sql
run_sql migrations/033_drop_companies_is_individual.sql
run_sql migrations/034_add_unique_new_contact_id_to_customer_migration_map.sql
run_sql migrations/035_drop_customer_id_from_downstream.sql
run_sql migrations/036_drop_customer_migration_map.sql
run_sql migrations/037_add_pending_dedup_review_to_contacts_check.sql
run_sql migrations/038_add_products_phase1c_columns.sql

# Meta App Review
run_sql migrations/039_create_data_deletion_logs.sql

# Phase 1-D
run_py  scripts/migrate_meta_inbox_phase1d.py
run_py  scripts/migrate_meta_inbox_phase1d_sprint4.py
run_py  scripts/migrate_meta_page_routing.py
run_py  scripts/migrate_meta_messages_page_id.py

# ADR-015 leads
run_py  scripts/migrate_adr015_lead_foundation.py  -e TENANT_CODE=highlife-jpn

# ロール移行
# [2026-06-28 停止] migrate_roles_gas_compat.py — 役目終了のため非稼働（GO #2658 Shingo承認済み）
#   停止理由:
#     1. メンバー→CS 移行・メンバー削除は全テナント完了済み（5テナントで「メンバー」0件 / 2026-06-28確認）
#     2. 既存テナントへの seed が DEFAULT_ROLES 変更のたびに新名ロールを全テナントに INSERT し
#        旧名ロールと重複する事故が再発（tenant_001/003/004/005/006 で旧新ロール重複 / 2026-06-28解消済み）
#     3. 新テナントの初期ロール seed は create 経路が個別に担保:
#        admin.py:68 → create_tenant_schema → tenant.py:1650 await seed_system_roles()
#        scripts/setup_tenant.py:184 await seed_system_roles()
#        scripts/setup_review_tenant.py:197 await seed_system_roles()
#   将来 DEFAULT_ROLES を変更する場合:
#     毎デプロイ自動ではなく --tenant-id 必須の明示スクリプト（migrate_*_stage_*.py 型）で人が意図して実行する。
#   スクリプト本体（migrate_roles_gas_compat.py）は履歴用に残置。削除は別便で検討。
# run_py  scripts/migrate_roles_gas_compat.py

# ADR-021
run_py  scripts/migrate_adr021_sprint2_financials.py
run_py  scripts/migrate_adr021_sprint3_shipping.py
run_py  scripts/migrate_adr021_sprint4_purchase.py
run_py  scripts/migrate_adr021_sprint5_commissions.py
run_py  scripts/migrate_adr021_remove_confirmed_status.py

# ADR-026 / ADR-027 / ADR-033
run_py  scripts/migrate_meta_messages_message_id_to_text.py
run_sql migrations/053_add_users_locale.sql
run_sql migrations/054_add_users_theme.sql

# ADR-041 / ADR-045
run_py  scripts/migrate_adr041_granted_scopes.py

# Phase 4 / Phase 5 テナントテーブル
run_py  scripts/migrate_009_phase4_tenant_tables.py
run_py  scripts/migrate_011_phase5_tenant_tables.py

# Inventory Sprint 1〜9
run_py  scripts/migrate_inventory_sprint1.py
run_py  scripts/migrate_inventory_sprint2.py
run_py  scripts/migrate_inventory_sprint5_to_7.py
run_py  scripts/migrate_inventory_sprint8.py
run_py  scripts/migrate_inventory_sprint9.py

# Security Hardening
run_sql migrations/071_create_data_access_events.sql
run_sql migrations/072_add_retention_indexes.sql

# CRM
run_py  scripts/migrate_073_lead_status.py
run_py  scripts/migrate_074_rename_english_name_to_nickname.py
run_sql migrations/075_create_goals.sql
run_sql migrations/076_add_google_calendar_config.sql
run_sql migrations/077_calendar_sync_mode_and_webhook_subscriptions.sql
run_sql migrations/078_create_calendar_events_tenant.sql
run_py  scripts/migrate_20260620_080000_calendar_category_backfill.py
run_sql migrations/080_phase_b_migration.sql

# Inventory 拡張
run_sql migrations/081_create_inventory.sql
run_sql migrations/082_extend_products_box_attributes.sql
run_sql migrations/083_add_staff_phone.sql
run_sql migrations/084_add_unit_to_inventory.sql
run_sql migrations/20260620_010000_create_inventory_aggregation_rules.sql
run_sql migrations/20260622_020000_add_inventory_raw_condition.sql
run_sql migrations/20260623_010000_add_inventory_axes_columns.sql
run_sql migrations/20260623_040000_make_inventory_condition_nullable.sql
run_sql migrations/20260623_020000_create_inventory_offer_v2_unique_key.sql
# HELD: 旧キー削除は新コードデプロイ後に手動GOで適用。run_all_migrations.sh では自動実行しない。
# run_sql migrations/20260623_030000_drop_inventory_offer_key.sql
# HELD: inventory.condition の削除は backfill とコード切替完了後に手動GOで適用。run_all_migrations.sh では自動実行しない。
# run_sql migrations/20260623_050000_drop_inventory_condition.sql
run_sql migrations/20260623_020000_drop_products_category_classification.sql
run_sql migrations/085_create_tcg_type_master.sql
run_sql migrations/086_seed_additional_tcg_types.sql
run_sql migrations/087_create_supplier_prompts.sql

# Lead / Discord / Meta 拡張
run_sql migrations/090_add_lead_contact_links.sql
run_sql migrations/091_add_leads_discord_messaging_columns.sql
run_sql migrations/092_add_meta_messages_discord_index.sql
run_sql migrations/093_rename_order_statuses.sql
run_sql migrations/094_create_message_translations.sql
run_sql migrations/20260623_040000_add_tenant_id_to_message_translations.sql
run_sql migrations/095_add_lead_social_links.sql
run_sql migrations/096_add_deal_lead_source.sql

# ADR-089 Discord 顧客管理
run_sql migrations/097_create_company_discord.sql
run_sql migrations/098_migrate_customer_discord_to_company_discord.sql
run_sql migrations/099_add_discord_guild_config.sql

# 受信箱画像送信
run_sql migrations/100_add_meta_messages_image_columns.sql

# タイムスタンプ形式（101番以降）
run_sql migrations/20260601_140000_drop_customers_tables.sql
run_sql migrations/20260602_000000_add_products_central_columns.sql
run_sql migrations/20260602_010000_repoint_downstream_fk_to_public_products.sql
run_sql migrations/20260602_020000_add_products_tcg_type.sql
run_sql migrations/20260602_030000_add_products_unit.sql
run_sql migrations/20260602_040000_backfill_products_unit_condition_from_inbound.sql
run_sql migrations/20260602_120000_add_discord_ticket_config.sql

# ADR-091 KPI5: テナントごとの Discord チャンネル設定（小口/大口）
run_sql migrations/20260602_150000_add_discord_scale_channels.sql

# ADR-091 KPI7: Discord ロール名カラム追加
run_sql migrations/20260602_160000_add_discord_role_names.sql

# ADR-093 PR1: 商品マスタ 発送ラベル/検索/分類用 7 列追加
run_sql migrations/20260602_170000_add_products_master_label_columns.sql

# ADR-093 Phase 3a: inventory offer_type / ship_timing + UNIQUE キー拡張
run_sql migrations/20260602_180000_add_inventory_offer_type_ship_timing.sql

# ADR-093 Phase 4: 在庫表ユーザー別フィルタ設定テーブル
run_sql migrations/20260602_190000_create_user_inventory_filters.sql

# ADR-091: Discord 接続者スタッフID記録カラム追加
run_sql migrations/20260602_200000_add_discord_config_connected_by_staff.sql

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# >>> 新マイグレーションはここより下に追加してください <<<
# 形式:
#   run_sql migrations/YYYYMMDD_HHMMSS_description.sql
#   run_py  scripts/migrate_description.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ADR-093: 商品マスタに「商品種類」(product_kind, 値='TCG' 等) を追加
run_sql migrations/20260603_000000_add_products_product_kind.sql

# ADR-093: 仕入元に LINE名 + 構造化住所を追加
run_sql migrations/20260603_010000_add_suppliers_line_and_address.sql

# ADR-106: テナントポリシー列を追加（標準エンジン＋テナント変数の土台）
run_sql migrations/20260604_050000_add_tenant_policy_columns.sql

# ドラゴンボール フュージョンワールド 商品マスタ投入（Booster/Starter 26件）
run_sql migrations/20260603_030000_seed_dragonball_products.sql

# ADR-093: 商品マスタ セット種別(set_type)
run_sql migrations/20260603_040000_add_products_set_type.sql

# 廃止（PO 2026-10-09）: 20260604_010000_seed_product_marks.sql は毎デプロイで商品マスタの mark を上書きし、画面で直した値を戻したためファイルごと削除。値の正はマスタ（画面・CSV）。ADR-155

# ADR-093: 全商品の発送ラベル既定値を一括設定（品目=Playing card / HSコード=9504400000 / 素材=Paper）
run_sql migrations/20260604_020000_backfill_products_shipping_defaults.sql

# ADR-093 海外顧客向け明細: quote_items / invoice_items に name_en/condition/unit を追加
run_sql migrations/20260604_030000_add_quote_invoice_item_overseas_columns.sql

# 8 TCG シリーズの商品マスタを中央カタログへ投入（UA/遊戯王/ガンダム/ヴァイス/デジモン/ホロライブ/ロルカナ/ポケSV 計1049件・ADR-090）
run_sql migrations/20260604_040000_seed_tcg_products_8series.sql

# ADR-021 受注ステータスフロー: orders に paid_at（支払済フラグ）を追加
run_sql migrations/20260604_050000_add_orders_paid_at.sql

# C-1: deals に選択式失注理由(lost_reason_code)を追加
run_sql migrations/20260604_060000_add_lost_reason_code.sql

# C-2/C-4: deprecated 列コメント追加（trust_level / products.unit_price系）
run_sql migrations/20260604_070000_deprecate_columns.sql

# ADR SA-04/05: A在庫テナント私有化（own_inventory）+ B専用source_kind明示
run_sql migrations/20260604_140000_create_own_inventory.sql
run_sql migrations/20260604_150000_add_inventory_source_kind.sql

# ADR SA-06: 解析ログ永続化 + ドリフト検知ビュー
run_sql migrations/20260604_110000_create_ingestion_jobs.sql
run_sql migrations/20260604_120000_create_parse_logs.sql
run_sql migrations/20260604_130000_create_supplier_parse_stats_view.sql

# ADR SA-02: 会話ログテーブル + 会社集計ビュー（contact粒度・RLSはtenant_id直接列）
run_sql migrations/20260604_090000_create_conversation_logs.sql
run_sql migrations/20260604_100000_create_company_stats_view.sql

# ADR-SA-03: 顧客登録トークン基盤（署名検証・期限・単回使用）
run_sql migrations/20260604_080000_create_registration_tokens.sql

# ADR SA-07: 請求書スナップショット（C-6）+ 為替レート記録（C-7）
run_sql migrations/20260604_160000_add_invoice_snapshot_columns.sql

# ADR SA-05: リンクテンプレート SSOT + contact チャンネル guild_id（C-3）
run_sql migrations/20260604_090000_create_link_templates.sql
run_sql migrations/20260604_100000_add_guild_id_to_contact_channels.sql


# 各種マスタ: 商品の選択肢系マスタ (商品種類/セット種別/レアリティ/言語/単位/HSコード/品目/素材)
run_sql migrations/20260604_170000_create_product_attribute_masters.sql

# ADR-107 (SA-14): 分析エージェント(A) 顧客優先度付け テーブル群
run_sql migrations/20260604_180000_analytics_agent_a_tables.sql

# ADR-110: 翻訳サブシステム — グロッサリ + 確信度 + 送信下訳テーブル
run_sql migrations/20260604_220000_create_translation_glossary.sql

# 商品マスタ一覧の手動並び替え（行ドラッグ）: public.products に display_order 追加
run_sql migrations/20260605_000000_add_products_display_order.sql

# ADR-SA-17: translation_glossary に RLS 追加（I-8 DB層隔離）
run_sql migrations/20260605_010000_rls_translation_glossary.sql

# ADR-SA-17: RLS ポリシー NULLIF 修正（空文字列→NULL変換でINTEGERキャストエラー修正）
run_sql migrations/20260605_020000_fix_translation_glossary_rls_cast.sql

# SA-18: salesanchor_app ロール作成＋public スキーマ付与
run_sql migrations/20260605_030000_create_salesanchor_app_role.sql

# SA-18: 既存 tenant_NNN スキーマ全件に salesanchor_app を付与
run_sql migrations/20260605_040000_grant_salesanchor_app_tenant_schemas.sql

# API連携: テナント Google Drive OAuth 連携設定テーブル（カレンダー雛形ミラー）
run_sql migrations/20260606_010000_add_google_drive_config.sql

# SA-18 Phase2 前提条件: RLS ポリシー変数名修正（app.current_tenant_id → app.tenant_id, true）
run_sql migrations/20260607_000000_fix_rls_policy_variable_name.sql

# ADR-109: status SSOT化 — 日本語ステータスを不変英字コードへ移行
run_py  scripts/migrate_adr109_status_codes.py

# ADR-119: lead_channels テーブル作成（1 lead : N platforms 名寄せ）
run_sql migrations/20260607_120000_create_lead_channels.sql

# ADR-119: lead_channels バックフィル（leads.source / discord_user_id → lead_channels）
run_py  scripts/migrate_adr119_lead_channels_backfill.py

# API連携: テナント別 配送キャリア(FedEx/DHL/UPS) 認証情報テーブル
run_sql migrations/20260608_080000_add_carrier_credentials.sql

# ADR-125: tenant_carrier_credentials に RLS ポリシー追加（テナント分離強化）
run_sql migrations/20260609_090000_add_carrier_credentials_rls.sql
# ADR-125 ロールバック用（手動実行のみ・本番デプロイでは実行しない）: migrations/20260609_090001_add_carrier_credentials_rls_down.sql

# ADR-125 D2: tenant_carrier_credentials に account_number_encrypted カラム追加
run_sql migrations/20260609_100000_add_carrier_account_number.sql

# API連携: テナント別 PayPal 決済連携 認証情報テーブル（Model A）
run_sql migrations/20260610_071110_add_paypal_config.sql

# オーナーロール色修正: 赤（危険予約色）→ インディゴ（権限レベル色）— 全テナント冪等適用
run_sql migrations/20260611_010000_fix_owner_role_color.sql

# ADR-101 PayPal mode1: invoices に決済リンク列（order_id/approval_url/fee）追加 — 全テナント冪等・nullable
run_sql migrations/20260611_020000_add_invoice_paypal_columns.sql

# SA-02 Stage 1: channel_masters テーブル作成（手動チャネルマスタ＋デフォルトシード）
run_sql migrations/20260611_100000_create_channel_masters.sql

# ADR-128: order_shipping_details に Ship/Pickup 用カラム追加
run_sql migrations/20260611_110000_extend_order_shipping_for_ship_api.sql

# SA-02 Stage 3: conversation_logs に手動記録用カラム追加（deleted_at + recorded_by_user_id）
run_sql migrations/20260611_120000_add_conv_log_manual_columns.sql

# SA-02 Stage 3: v_company_stats に論理削除除外フィルタ追加（deleted_at IS NULL）
# 依存: 20260611_120000 で deleted_at カラムが追加済みであること
run_sql migrations/20260611_130000_fix_v_company_stats_deleted_at.sql

# SA-02 Stage 2 前提: conversation_logs に is_manual カラム追加（Stage 2 移行スクリプトが参照）
run_sql migrations/20260611_140000_add_conv_log_is_manual.sql

# ADR-101 PayPal webhook (Increment 2.5): tenant_paypal_config に webhook_id 追加 — public 単一・nullable
run_sql migrations/20260611_150000_add_paypal_webhook_id.sql

# ADR-127: registration_tokens.type CHECK 制約に change_billing を追加
run_sql migrations/20260612_090000_extend_registration_tokens_change_billing.sql

# ADR-101 改訂(2) Inc1: invoices に PayPal 写しPDF 関連列を追加
run_sql migrations/20260612_131520_add_invoice_copypdf.sql

# ADR-129: tenant_carrier_credentials の UNIQUE 制約を (tenant_id, carrier, environment) に変更
run_sql migrations/20260612_200000_fedex_creds_unique_env.sql

# SA-04 (ADR-098): contact_contact_channels に UNIQUE(contact_id,channel,COALESCE(purpose,'')) + guild_id catch-up
run_sql migrations/20260612_100000_add_contact_channel_unique.sql

# SA-04 (ADR-098): company_discord.guild_id VARCHAR(50) 追加
run_sql migrations/20260612_110000_add_company_discord_guild_id.sql

# ADR-101 改訂(2) Inc4 Step A: paypal_disputes テーブル作成
run_sql migrations/20260612_154322_create_paypal_disputes.sql

# ADR-136 前提: paid_at / voided_at バックフィル（必ず view 変更より前に実行）
run_sql migrations/20260612_050000_backfill_invoice_timestamps.sql

# ADR-136: v_company_stats SSOT 修正（フィルタを paid_at IS NOT NULL AND voided_at IS NULL に変更）
run_sql migrations/20260612_120000_fix_company_stats_ssot.sql

# password_hash 列廃止（PO決定 2026-06-12: 認証は Firebase 担当、DB への保存不要）
run_sql migrations/20260612_150000_drop_password_hash.sql

# ── ファネルダッシュボード PR1（ADR-138 §D1）─────────────────────────────────

# ADR-138 §D1-1: deals.closed_at 追加（成約・失注の確定タイムスタンプ）
run_sql migrations/20260613_010000_funnel_deals_closed_at.sql

# ADR-138 §D1-2: close_reasons / deal_close_reasons 作成 + deals.lost_reason* 廃止
run_sql migrations/20260613_020000_funnel_close_reasons.sql

# ADR-138 §D1-3: leads.source 廃止 + channel_type / initiative 追加
run_sql migrations/20260613_030000_funnel_leads_initiative_channel.sql

# ADR-138 §D1-4: goals.kpi_type CHECK 制約拡張（won_count / gross_profit 追加）
run_sql migrations/20260613_040000_funnel_goals_kpi_extend.sql

# ADR-138: order_financials.purchase_cost を NULL 許容・DEFAULT 削除
run_sql migrations/20260613_050000_funnel_purchase_cost_nullable.sql

# A4: carrier credentials 接続テスト結果を保存（last_tested_at / last_test_ok / last_test_message）
run_sql migrations/20260614_030000_add_carrier_test_result.sql

# テナント削除 中央監査ログ（public.tenant_deletion_audit 新設）
run_sql migrations/20260614_040137_add_tenant_deletion_audit.sql

# ADR-108 Phase B-1: sales_form 複数選択 — tenant_sales_form_options / lead_sales_form_selections テーブル追加
run_sql migrations/20260614_100000_create_sales_form_tables.sql

# ポケモンカードゲーム MEGA シリーズ 商品マスタ投入（14件 product_code あり + 11件 なし）
run_sql migrations/20260615_235900_seed_pokemon_mega_products.sql

# tcg_type_master 重複 code 統合（pokemon/weiss → pokemon_booster_box/weiss_schwarz）
run_sql migrations/20260616_000000_fix_tcg_type_dedup.sql

# Foundation F1: 国台帳 public.countries（ISO alpha-2 / 全テナント共有）
run_sql migrations/20260621_010000_create_countries_master.sql

# SSOT 統合①: meta_messages に master 履歴列を追加（追加のみ）
run_sql migrations/20260622_010000_add_meta_messages_master_history_columns.sql

# SSOT 統合②: conversation_logs の conv 専用行を実在 lead のみ meta_messages に移送
run_sql migrations/20260622_020000_migrate_conv_only_into_meta_messages.sql

# Foundation F2: lead.country を ISO alpha-2 に backfill（危険変更）
run_py  scripts/migrate_20260621_020000_backfill_lead_country.py


# SSOT cleanup 2: products.tcg_type を tcg_type_master.code に固定
run_sql migrations/20260623_060000_add_products_tcg_type_fk.sql

# SA-18 Phase2 ③-b(5): message_translations に RLS 有効化（tenant スキーマ全件）
run_sql migrations/20260623_100000_rls_message_translations.sql

# 送信ガード土台: meta_messages.original_language を message_translations から backfill
run_sql migrations/20260624_120000_backfill_meta_messages_original_language.sql

# D-1: public.inventory(B在庫) を v2形へ収束（冪等・本番no-op）。180000(L221)が offer_key を再作成するため末尾で除去。ADR-143。
run_sql migrations/20260624_140000_converge_inventory_v2.sql

# 段階A: outbound_translation_drafts に送信メッセージ紐付け＋is_edited 列を追加
run_sql migrations/20260626_100000_add_outbound_draft_message_link.sql

# ADR-146 B方式: tenant_discord_config.guild_id に UNIQUE 制約追加（1Guild=1Tenant保証）
run_sql migrations/20260626_120000_add_unique_guild_id_to_tenant_discord_config.sql

# ADR-145 段階2: public.products に FORCE-RLS + 4ポリシー（共通=運営のみ/固有=自テナント）
run_sql migrations/20260626_130000_force_rls_public_products.sql

# テナント単位フィーチャーフラグ (public.tenant_features) テーブル新設 + RLS
run_sql migrations/20260627_120000_add_tenant_features_table.sql

# スコープ②Phase2 backfill: products.unit DROP 前に inventory.unit へ退避（空欄のみ・冪等）
run_sql migrations/20260629_010000_backfill_inventory_unit_from_products.sql

# 為替レート SSOT (public.app_fx_rates) テーブル新設 + RLS（読み取り全許可・書き込みoperatorのみ）
run_sql migrations/20260628_170000_add_app_fx_rates.sql

# 便1a: 取引フロー背骨の必須化（遡及lead逆造成 backfill + 条件付き NOT NULL）
run_sql migrations/20260703_010000_txn_backbone_ben1a.sql

# スコープ②Phase2 DROP: products から redundant な condition/unit 列を物理削除（IF EXISTS・冪等）
run_sql migrations/20260629_020000_drop_products_condition_unit.sql

# 便1b: conversation_logs の背骨必須化（echo穴埋め + 遡及backfill + NOT NULL）
run_sql migrations/20260703_020000_conv_backbone_ben1b.sql
run_sql migrations/20260715_100000_add_conversation_logs_lead_fk.sql
# deals廃止 段階①: leads へ商談列追加
run_sql migrations/20260718_100000_leads_add_deal_columns.sql

# deals廃止 段階②(D3): orders.deal_id の NOT NULL 解除
run_sql migrations/20260720_100000_orders_deal_id_drop_not_null.sql
run_sql migrations/20260721_100000_close_reasons_quotes_add_lead_id.sql
run_sql migrations/20260721_120000_close_reasons_quotes_leadid_notnull.sql
run_sql migrations/20260723_120000_dcr_dealid_nullable.sql

# 便2: order_items 新設＋仕入接続
run_sql migrations/20260703_030000_order_items_ben2.sql

# orders.deal_id と対応するFKを全tenantから削除（冪等）
run_sql migrations/20260724_074500_drop_orders_deal_id.sql

# quotes.deal_id と対応するFKを全tenantから削除（冪等）
run_sql migrations/20260724_131500_quotes_drop_deal_id.sql

# deal-removal: deal_close_reasons の deal_id 依存を撤去し、lead_id/reason_id を一意化
run_sql migrations/20260724_170000_dcr_drop_deal_id.sql

# leads.converted_deal_id と対応するFKを全tenantから削除（冪等）
run_sql migrations/20260726_180000_leads_drop_converted_deal_id.sql

# 便E: deals テーブル本体を全tenantから削除（本番適用済み 2026-07-29・冪等）
run_sql migrations/20260729_043520_drop_deals.sql

# Phase 2c 前処理: tcg_products 参照 FK をクリーンアップ（冪等）
run_sql migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql

# Fix: Phase 2a missed public/tenant_004.analysis_results FK (blocks Phase 2c)
run_sql migrations/20260922_050000_fix_phase2c_fk_drop_only.sql

# TCG MIG-04: tenant_004 TCG解析テーブル 18本 作成（冪等）
run_sql migrations/20260831_110000_create_tcg_analysis_tables_t004.sql

# TCG MIG-04: conditions に R1〜R4 解決列追加 + seed（additive-only・冪等）
run_sql migrations/20260901_090000_add_condition_resolution_columns.sql

# TCG MIG-04 E3a/E5: analysis_results に unit_inferred/unit_basis/unit_confidence/unit_infer_reason 追加（additive-only・冪等）
run_sql migrations/20260901_120000_add_unit_inference_columns_t004.sql

# attachment-storage 便2: 添付ファイル保管台帳 (tenant_NNN.lead_attachments) + RLS
run_sql migrations/20260902_100000_create_lead_attachments.sql

# TCG MIG-04: 分類マスタ 4テーブル作成＋GAS実データ seed（tenant_004 専用・冪等）
run_sql migrations/20260902_110000_tcg_classification_masters.sql

# TCG MIG-04: tcg_products に分類 ID FK を設定し 268件全行を GAS 実データで更新（冪等）
run_sql migrations/20260902_110100_tcg_products_classification_ids.sql


# PARITY-02 A-2: 単位証拠ルール 4件 seed（tcg_unit_evidence_rules 新規テーブル・冪等）
run_sql migrations/20260903_120000_tcg_unit_evidence_rules_t004.sql

# PARITY-02 A-3: 注記マスタ 22件 seed（tcg_note_master 新規テーブル・冪等）
run_sql migrations/20260903_130000_tcg_note_master_t004.sql
# TCG PARITY-02 A-4: ステータスマスタ 9件（tenant_004 専用・冪等）
run_sql migrations/20260903_150000_tcg_status_master_t004.sql

# TCG PARITY-02 A-1: 正規化ルール 135件（tenant_004 専用・冪等）
run_sql migrations/20260903_160000_tcg_normalization_rules_t004.sql

# PARITY-03: tcg_products に mark / english_title 列を追加し 268件を充填（冪等）
run_sql migrations/20260903_180000_tcg_products_mark_en_t004.sql

# PARITY-03 Phase 3 Stage 3: 修正履歴テーブル（tenant_004 専用・冪等）
run_sql migrations/20260903_170000_item_corrections_t004.sql

# DIST-01 A': NR0008 全角＠除去ルール追加（price_normalized NULL 91→3件）
run_sql migrations/20260903_190000_tcg_normalization_rules_nr0136.sql

# DIST-01 B: 配信先マスタ（tenant_004 専用・冪等）
run_sql migrations/20260903_200000_tcg_distribution_targets_t004.sql

# DIST-01 C: 配信全体設定（tenant_004 専用・冪等）
run_sql migrations/20260903_210000_tcg_distribution_settings_t004.sql

# HIST-01: 再解析履歴テーブル（analysis_runs / analysis_run_snapshots・tenant_004 専用・冪等）
run_sql migrations/20260903_220000_create_tcg_analysis_history_t004.sql
run_sql migrations/20260904_160000_tcg_magazine_promo_products_t004.sql
run_sql migrations/20260905_010000_tcg_pokemon_master_batch1_t004.sql
run_sql migrations/20260905_020000_tcg_fix_product_names_t004.sql

# REVIEW-STAGE: import_jobs に確認工程カラムを追加（pending_messages/window/unresolved_names/review_status）
run_sql migrations/20260905_140000_import_jobs_review_stage_t004.sql

# SUP-R2: 仕入元 15件 新規登録（SP0188〜SP0202）+ LINE チャンネル行（tenant_004 専用・冪等）
run_sql migrations/20260905_120000_register_15_suppliers_t004.sql

# RECORD-01: 直接SQL復旧の記録（SP0007/SP0184 name修正・SP0203/SP0204 新規登録）（tenant_004 専用・冪等）
run_sql migrations/20260905_150000_record_manual_supplier_fixes_t004.sql

# QA-03: tenant_001 に TCG 全テーブル 27 本を作成 + 分類マスタ seed + テスト仕入元 3 件（QA 専用・冪等）
# tenant_006 は Meta App Review 専用（QA 禁止）→ QA は tenant_001 を使用
run_sql migrations/20260906_120000_create_tcg_tables_t001.sql

# SEC-01: extraction_jobs.error_message に残る Gemini APIキー付きURL 24行を定型文に置換（tenant_004 専用・冪等）
run_sql migrations/20260906_230000_redact_extraction_error_keys_t004.sql

# NOTE-EXPAND-A: tcg_note_master 固定札26件追加＋既存2行の検索語更新（tenant_004 専用・冪等）
run_sql migrations/20260907_100000_tcg_note_master_expand_t004.sql
run_sql migrations/20260907_120000_tcg_dist_stale_jobs_terminate_t004.sql

# KW-HYGIENE: 商品マスタ キーワード整備 11項目（除外語の自己矛盾解消・壁追加・PM0146無効化）（tenant_004 専用・冪等）
run_sql migrations/20260907_140000_tcg_keyword_hygiene_t004.sql

# IMPORT-01: 商品マスタCSV取り込み履歴（tenant_004 専用・冪等）
run_sql migrations/20260906_130000_create_tcg_product_import_history_t004.sql

# IMPORT-01 QA: 同上（tenant_001 専用・冪等）
run_sql migrations/20260906_130100_create_tcg_product_import_history_t001.sql

# ADR-158: neutralized exclude-keyword inserts (data applied via app/CSV per ADR-155)
run_sql migrations/20260925_120000_add_product_exclude_keywords.sql

echo ""
echo "============================================"
echo "✅ 全マイグレーション完了 (${TOTAL}ステップ)"
echo "============================================"

# LMI-SP0136-REQUEUE: SP0136 の残す1件の抽出ジョブを error→pending に戻す（tenant_004 専用・冪等）
run_sql migrations/20260908_130000_tcg_sp0136_requeue_extraction_t004.sql
run_sql migrations/20260908_170000_tcg_keyword_v4_t004.sql

# LMI-SP0136-CLEANUP: SP0136 の古い在庫メッセージ c5ad04aa を無効化（tenant_004 専用・冪等）
run_sql migrations/20260908_210000_tcg_sp0136_supersede_old_message_t004.sql

# PHASE-2B: public.products Phase 2b columns prerequisite (work_id, unit, condition, etc.)
run_sql migrations/20260909_000000_public_products_phase2b_columns.sql

# NOTE-B2: 値を運ぶ備考札＋正規化拡張（tenant_004 専用・冪等）
run_sql migrations/20260909_130000_tcg_note_b2_t004.sql

# PMG import progress: TCG schemas only, additive, no backfill
run_sql migrations/20260910_010000_tcg_import_message_links.sql

# LINE work evidence before v3 code; dictionary filter is independently idempotent.
run_sql migrations/20260910_160000_tcg_work_evidence.sql
run_sql migrations/20260910_160100_tcg_normal_deck_coro_exclusion.sql
run_sql migrations/20260910_170000_tcg_keyword_false_positive_guards.sql
run_sql migrations/20260910_180000_tcg_interrupted_jobs_recovery_t004.sql
run_sql migrations/20260910_200000_tcg_condition_note_delivery_t004.sql
run_sql migrations/20260912_020000_tcg_resolved_work_id.sql
run_sql migrations/20260912_160000_line_import_devices.sql
run_sql migrations/20260912_170000_line_supplier_source_names.sql

# ドラゴンボール フュージョンワールド 商品マスタ v2（55件：英語名補完+未登録29件追加+検索/除外キーワード付与）
run_sql migrations/20260913_010000_seed_dragonball_products_v2.sql
run_sql migrations/20260913_020000_seed_onepiece_products.sql
run_sql migrations/20260913_030000_seed_unregistered_products.sql
run_sql migrations/20260913_150000_tcg_empty_box_condition.sql
run_sql migrations/20260913_200000_tcg_cardset_exclusion.sql
run_sql migrations/20260913_210000_tcg_cardset_bundle_registration.sql

# ABBREV-01: tenant_004 略語キーワード追加（検索語・除外語）— PR #3495
run_sql migrations/20260914_080000_add_abbreviation_keywords_t004.sql

# CARD09: persist extraction attempts before adopting new results.
run_sql migrations/20260914_010000_tcg_extraction_attempts.sql

# UNIFY-2A: tcg_products → public.products 統合（ADR-1001 Phase 2a）— スキーマ拡張 + データ移行 + FK 張替え
run_sql migrations/20260914_140000_unify_tcg_products_to_public.sql

# Fix: Phase 2c blocker — initial FK fix draft (public.analysis_results stale FK DROP + re-add)
# NOTE: superseded by 050000 for the DROP step, but registered here to satisfy migration guard
run_sql migrations/20260922_040000_fix_phase2c_fk_blocker.sql

# UNIFY-2C: tcg_products テーブル DROP（ADR-1001 Phase 2c）— SSOT 完了後のクリーンアップ
run_sql migrations/20260915_010000_drop_tcg_products_phase2c.sql

# ADR-1002 Phase B: FK付替え UUID→INTEGER + SEQUENCE（冪等）
run_sql migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql

# ADR-1002 Phase C: public.products.tcg_uuid カラム・制約・インデックス削除
run_sql migrations/20260916_120000_phase_c_drop_tcg_uuid.sql

# work_id NOT NULL 制約追加
run_sql migrations/20260916_130000_work_id_not_null.sql

# Gemini v5: extraction_items に resolved_product_code 列追加
run_sql migrations/20260917_010000_add_product_code_to_extraction.sql

# C92: 完売ルール・日付ルール共通テーブル 13表（tenant_001 専用・冪等）
run_sql migrations/20260917_000000_create_analysis_rule_tables.sql

# 仕入元マスタ SSOT Sprint 1: tcg_suppliers → public.suppliers コピー + supplier_channels FK UUID→INTEGER + line_supplier_source_names DROP
run_sql migrations/20260917_020000_supplier_ssot_migration.sql

# 仕入元マスタ SSOT Phase 2 Sprint 1: public.suppliers に tenant_id 追加 + purchase_orders/products FK 張り替え
run_sql migrations/20260918_030000_supplier_ssot_phase2.sql

# Master SSOT Phase 1a: public.products.work_id を UUID→INTEGER へ再キャスト（冪等）
run_sql migrations/20260919_010000_master_ssot_work_id_recast.sql

# VIEW → TABLE 修正: 手動作成VIEWをDROPし実体テーブルをRENAME（本番デプロイ252番失敗の修正）
run_sql migrations/20260919_015000_fix_view_to_table_rename.sql

# Master SSOT Phase 1b: 共用マスタ public テーブル群を作成（冪等）
run_sql migrations/20260919_020000_master_ssot_public_tables.sql

# Master SSOT Phase 2: FK work_id → tcg_type_master（冪等）
run_sql migrations/20260919_030000_master_ssot_fk_work_id.sql

# Fix extraction_items.resolved_work_id UUID→INTEGER 型修正（冪等）
run_sql migrations/20260919_190000_fix_extraction_work_id_type.sql

# Master SSOT Phase 3: unit_id/condition_id FK UUID→INTEGER + product_category_id UUID→INTEGER（冪等）
run_sql migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql

# Supplier dedup: LINE インポートで同じ仕入先が重複登録される問題を修正（UPSERT + UNIQUE インデックス）
run_sql migrations/20260920_020000_supplier_line_name_unique.sql

# Conditions master SSOT Phase 1: public.conditions に tenant_id 追加 + deal_statuses/work_items FK 張り替え
run_sql migrations/20260920_040000_conditions_ssot_phase1.sql

# 単位マスタ public.units に tenant_id 追加（NULL=共用/LINE解析用、数値=テナント個別）
run_sql migrations/20260920_030000_units_add_tenant_id.sql

# ステータスマスタ public.tcg_status_master に tenant_id 追加（NULL=共用/LINE解析用、数値=テナント個別）
run_sql migrations/20260920_050000_status_master_add_tenant_id.sql

# 備考マスタ public.tcg_note_master に tenant_id 追加（NULL=共用/LINE解析用、数値=テナント個別）
run_sql migrations/20260920_060000_note_master_tenant_id.sql

# product_categories tenant_id
run_sql migrations/20260920_070000_product_categories_tenant_id.sql

# analysis_rule 13テーブルをpublicスキーマに新設（CREATE TABLE IF NOT EXISTS・冪等）
run_sql migrations/20260920_120000_analysis_rule_public_tables.sql

# 商品分類マスタ新設: product_lines（小分類）+ product_formats（細分類）+ products FK カラム追加
run_sql migrations/20260920_130000_create_product_classification.sql

# analysis_rule 13テーブルを全スキーマから削除（SSOT を tcg_status_master に統合・PR #3621）
run_sql migrations/20260921_010000_drop_analysis_rule_tables.sql

# ADR-156: 商品分類ツリー Phase 1 — 大分類・type_master rename・小分類FK・コンディション定義・解析マスタFK
run_sql migrations/20260921_060000_create_product_kinds.sql
run_sql migrations/20260921_070000_rename_tcg_type_master_to_type_master.sql
run_sql migrations/20260921_080000_product_lines_add_type_id.sql
run_sql migrations/20260921_090000_create_condition_definitions.sql
run_sql migrations/20260921_100000_add_analysis_master_fk.sql

# Step 1/5: パイプライン 17テーブル を public スキーマに作成（DDL-only・冪等）
run_sql migrations/20260921_110000_pipeline_tables_public.sql

# Step 5/5: tenant_004 スキーマのパイプライン 17テーブル + バックアップ 2テーブルを DROP（ADR-1002）
run_sql migrations/20260921_050000_drop_tenant004_pipeline_tables.sql

# ADR-156 Phase 3A: products に product_kind_id（INTEGER FK → public.product_kinds）追加
run_sql migrations/20260921_120000_add_products_product_kind_id.sql

# 共用Knowledge抽出語彙シード: block_delimiter / skip_condition / status_keyword
run_sql migrations/20260924_040000_seed_knowledge_extraction_vocab.sql

# 仕入元 Knowledge リンクテーブル新設（supplier_knowledge_links）
run_sql migrations/20260924_050000_create_supplier_knowledge_links.sql

# ADR-156 Phase 5: tenant_004 マスタテーブルのコピーを DROP（全コードが public SSOT を参照済み）
run_sql migrations/20260921_130000_drop_tenant004_master_copies.sql

# ADR-156 Phase 6: 小分類→大分類FK / 入数マスタ / 重量マスタ / products FK追加
run_sql migrations/20260921_140000_product_classification_masters.sql

# ADR-157: 買取相場ログ（外部買取店の価格定期取得テーブル）
run_sql migrations/20260922_000000_create_buyback_tables.sql

# ADR-156 Phase 7: 細分類→大分類FK /（商品→中分類FK は ADR-1026 で削除）
run_sql migrations/20260922_010000_product_format_kind_id_and_products_type_master_id.sql

# ADR-156 Phase 8: 細分類→中分類 多対多中間テーブル
run_sql migrations/20260922_030000_product_format_game_links.sql

# Rule Test System: テストケース管理 + テスト実行
run_sql migrations/20260922_020000_create_rule_test_tables.sql

# 販売単位・状態マスタ連鎖プルダウン基盤
run_sql migrations/20260922_060000_product_unit_condition_infra.sql

# LINE解析テーブルリネーム Phase 1（RENAME + 後方互換VIEW）
run_sql migrations/20260922_080000_rename_line_analysis_tables.sql

# ADR-156 Phase 9: 細分類(product_formats)に type_master_id 直接リンク追加（カードゲーム別フィルタリング）
run_sql migrations/20260923_010000_product_formats_add_type_master_id.sql

# 残存 TCG マスタ 3 テーブルを public schema にプロモート
run_sql migrations/20260923_030000_promote_remaining_tcg_tables.sql

# line_import_devices.tcg_schema を tenant_004 → public に更新
run_sql migrations/20260923_040000_update_device_tcg_schema.sql

# public.analysis_results に欠落インデックスを追加（ON CONFLICT 修正）
run_sql migrations/20260923_050000_add_indexes_public_analysis_results.sql

# public.analysis_results に work_id カラムを追加（Gemini 精度計測用）
run_sql migrations/20260923_120000_add_work_id_to_analysis_results.sql

# ADR-157: 買取価格変動アラートルール
run_sql migrations/20260924_000000_create_buyback_alert_rules.sql

# public.suppliers に仕入元ごとの抽出ルール列を追加
run_sql migrations/20260924_010000_add_supplier_extraction_rules.sql

# public.suppliers に例文テキスト列を追加（Gemini プロンプト注入用）
run_sql migrations/20260924_030000_add_extraction_example_text.sql

# ADR-157 Phase 3: 買取商品と自社マスタの自動紐付け（product_id型変更・match列追加）
run_sql migrations/20260924_100000_buyback_product_matching.sql

# analysis_run_snapshots.unit_id / condition_id: UUID → INTEGER 型修正
# analysis_results が INTEGER 型のためスナップショット保存時の型不一致を解消
run_sql migrations/20260924_110000_fix_analysis_run_snapshots_unit_condition_type.sql

# Supplier name dedup: 同一name重複21組を統合（旧SUP-xxx → 新SP-xxxxx）
run_sql migrations/20260924_060000_cleanup_supplier_name_duplicates.sql

# ADR-158: analysis_results に is_current カラムを追加（商品単位の差分更新）
run_sql migrations/20260924_120000_add_analysis_results_is_current.sql

# conditions テーブルに match_type / effect カラムを追加（tcg_status_master パターン統一）
run_sql migrations/20260925_010000_conditions_add_match_type.sql

# line_conditions に condition_def_id / unit_id / note 追加（ConditionsMasterPanel v2）
run_sql migrations/20260925_020000_conditions_add_def_unit_note.sql

# ADR-158 Phase 2: extraction_items に raw_product_code カラム追加（Gemini v6 型番抽出）
run_sql migrations/20260926_010000_add_raw_product_code.sql

# Gemini 抽出プロンプト設定テーブル新設（管理画面から編集可能）
run_sql migrations/20260926_080000_create_extraction_prompt_config.sql

# product_id=61 の product_code='-' を 'S-PS' に修正（30th BOX バグ根本原因）
run_sql migrations/20260926_080100_fix_product_code_dash.sql

# tcg_distribution_settings に max_age_hours=48 設定を追加（配信時の最大経過時間フィルタ）
run_sql migrations/20260927_120000_add_max_age_hours_setting.sql

# extraction_attempts に Gemini APIトークン数・コストカラムを追加（透明化）
run_sql migrations/20260927_130000_add_extraction_token_cost_columns.sql

# ADR-009 M7: Discord リアクション保存テーブル新設（RLS有効・冪等）
run_sql migrations/20260927_100000_create_meta_message_reactions.sql

# skip_condition カテゴリ全件（13件）を削除（Gemini が既に判断するため重複ルール撤去、PO決定 2026-09-28）
run_sql migrations/20260928_100000_delete_skip_condition_rules.sql

# PR-B1: 試運転用の表（extraction_shadow_runs/results）と仕入元の発送日の書き方欄を追加（A/B専用・既存クエリ非改変）
run_sql migrations/20260928_110000_create_extraction_shadow_tables.sql

# ADR-158: source_messages.received_at を採用本文の投稿時刻にそろえる（冪等）
run_sql migrations/20260929_120000_fix_source_messages_received_at.sql

# PR-CLEAN: 旧仕入元別Geminiプロンプトテーブルを廃止（ADR-085機能撤去、PO決定 2026-09-28）
run_sql migrations/20260930_120000_drop_supplier_prompts.sql

# Discord チケットのウェルカム文の DB 既定値を英語へ（顧客向け文言の英語化・PO決定 2026-09-30・冪等）
run_sql migrations/20260930_130000_set_discord_welcome_template_english.sql

# ADR-1004 A1: LLM 使用量台帳（llm_usage_events）新設（表のみ。バックフィルは A2 で別PR）
run_sql migrations/20260930_150000_create_llm_usage_events.sql

# ADR-1004 A2: LLM 使用量台帳（llm_usage_events）過去分バックフィル（SSOT化、A1マージ後に適用）
run_sql migrations/20260930_160000_backfill_llm_usage_events.sql

# ADR-159 便A: staff.avatar_token 追加（担当者アイコンの公開 URL token・additive・冪等）
run_sql migrations/20261001_120000_add_staff_avatar_token.sql

# ADR-159 便B: discord_channel_webhooks 作成（担当者名義 webhook 送信・token 暗号化・冪等）
run_sql migrations/20261001_150000_create_discord_channel_webhooks.sql

# §D01: 決済手数料設定マスタ（public.payment_fee_settings）新設（NULLパターン・PayPal初期データ込み・冪等）
run_sql migrations/20261002_160000_create_payment_fee_settings.sql

# §D01補完: payment_fee_settings カラムコメント付与
run_sql migrations/20261002_180000_comment_payment_fee_settings_columns.sql

# Discord 在庫取り込み機能（削除済み・PO GO 待ち）の残置テーブル3件 + ビュー削除（冪等・不可逆）
run_sql migrations/20261002_170000_drop_discord_inventory_tables.sql

# ADR-148 追補 PR-A: public.app_fx_rate_history 新設（為替レート履歴・追記専用・表のみ。書込/読取切替はPR-Bで実施）
run_sql migrations/20261003_100000_create_app_fx_rate_history.sql

# roles.system_key 追加（全テナント・additive・冪等。owner/admin の権限を役割名ではなく安定キーで判定するため）
run_sql migrations/20261005_150000_add_roles_system_key.sql

# 新しい仕組み専用の仕入元ルール2列（extraction_layout_rules / extraction_hard_cases）。本番v7は読まない
run_sql migrations/20261006_170200_add_supplier_new_system_rules.sql

# 試作版 v102: 単位にしない言い回しマスタ line_unit_ignore_phrases 新設（構造のみ・値は画面から登録・冪等）
run_sql migrations/20261008_100000_create_line_unit_ignore_phrases.sql

# 試作版 v102: 中分類マスタ type_master に match_by_code（型番で決めるかの印）を追加（構造のみ・値は運用で付ける・冪等）
run_sql migrations/20261009_100000_type_master_match_by_code.sql

# 試作版 v102: 中分類マスタ type_master に code_only_match（型番だけでも決めてよいかの印）を追加（構造のみ・値は運用で付ける・冪等）
run_sql migrations/20261009_150000_type_master_code_only_match.sql

# 便B: v102 本番エンジン用の列（extraction_items に source_lines・gemini_index、extraction_jobs に gemini_unsure・review_reasons）。構造のみ・冪等（ADR-1007）
run_sql migrations/20261009_180000_v102_engine_columns.sql

# 便A: 要確認の理由コード表 review_reason_codes 新設（構造のみ・初期行は data/review_reason_codes/ の1回だけのデータ変更・冪等・ADR-1007）
run_sql migrations/20261009_200000_create_review_reason_codes.sql

# 便2-1: v102 の〆が完売にする2つ目以降の (商品, 状態) の表 analysis_soldout_extra_targets 新設（構造のみ・冪等・ADR-1007）
run_sql migrations/20261010_120000_create_analysis_soldout_extra_targets.sql

# v102 価格の行の決め方の印 price_basis 列（構造のみ・冪等・ADR-1007）
run_sql migrations/20261011_150000_add_analysis_results_price_basis.sql

# extraction_jobs に v102 システム要確認の明細の列を足す（段1）
run_sql migrations/20261012_100000_add_extraction_jobs_system_review_detail.sql

# extraction_attempts に Gemini の思考要約の列を足す（構造のみ）
run_sql migrations/20261012_200000_add_extraction_attempts_thought_summaries.sql

# tcg_distribution_targets に要確認タブ名の列を足す（構造のみ・冪等。値は docs/handoff/review-sheet-export/data/ の1回だけのデータ変更）
run_sql migrations/20261012_210000_add_tcg_distribution_targets_review_sheet_name.sql

# companies.sales_rep_id の参照先を public.users(id) に付け替える（ADR-1008 P1・構造のみ・冪等）
run_sql migrations/20261013_100000_repoint_companies_sales_rep_to_users.sql

# bots/order_commissions/calendar_owner_settings/tenant_meta_config/meta_messages の「人」列の参照先を public.users(id) に付け替える（ADR-1008 P2・構造のみ・冪等）
run_sql migrations/20261013_110000_repoint_person_columns_to_users.sql

# staff.user_id を NOT NULL にする（ADR-1008 P3・構造のみ・冪等。NULL 行のあるテナントは WARNING で飛ばす）
run_sql migrations/20261013_120000_staff_user_id_not_null.sql

# staff.role_id の NOT NULL を外す（ADR-1008 P4a・構造のみ・冪等。ロールの正本は user_roles）
run_sql migrations/20261013_130000_staff_role_id_nullable.sql

# analysis_results に発送日の専用列（ship_ja・ship_en）を足す（構造のみ・冪等）
run_sql migrations/20261013_140000_add_analysis_results_ship_ja_ship_en.sql

# tcg_note_master に REGEX の行の英語の書式（label_template_en）を足す（構造のみ・冪等）
run_sql migrations/20261013_140100_add_tcg_note_master_label_template_en.sql

# 名簿のメールの正本を users.email にする: staff.primary_email の NOT NULL を外し v_senders を作り直す（ADR-1008 P4b・構造のみ・冪等）
run_sql migrations/20261013_150000_staff_email_from_users.sql

# ログイン自社化の置き場（users に 4 列・新表 3 つ。構造のみ・冪等。ADR-1013 便1）
run_sql migrations/20261013_160000_add_self_hosted_auth_tables.sql

# 試運転（shadow）の表2件の削除（画面・API・書き込み経路は #4218 で削除済み・PO GO 待ち・冪等・不可逆）
run_sql migrations/20261013_180000_drop_extraction_shadow_tables.sql

# 受信箱「新規」バッジの置き場（leads に 1 列。構造＋既存行の埋め直し・冪等・不可逆操作なし。expand/contract の先行便）
run_sql migrations/20261015_090000_add_leads_assignment_opened_at.sql

run_sql migrations/20261015_130000_add_permissions_rls.sql
run_sql migrations/20261016_010000_add_google_config_rls.sql
run_sql migrations/20261016_020000_add_suppliers_rls.sql

# 閲覧専用アカウントの表4つ（構造のみ・冪等。ADR-1019 段1）
run_sql migrations/20261016_150000_add_viewer_accounts.sql

# ADR-1012 段階2 便A: 障害記録の表 3 つ（空・RLS は運用者だけ・記録は消せない）
run_sql migrations/20261016_100000_create_ops_incident_tables.sql

run_sql migrations/20261016_160000_add_paypal_regtoken_write_rls.sql

run_sql migrations/20261016_170000_add_tenants_write_rls.sql

run_sql migrations/20261016_180000_add_users_write_rls.sql

# ADR-1020 便1: 共用商品の「調べたが無い」の記録の表（空・構造のみ・冪等）
run_sql migrations/20261016_190000_create_product_blank_confirmations.sql

# ADR-1019 段4c: 閲覧者の Discord 受付の設定の表（空・構造のみ・冪等）
run_sql migrations/20261017_100000_add_viewer_discord_config.sql
# ADR-1023: 状態マスタの価値順の列（構造のみ。値は docs/handoff/condition-value-rank/data/ の SQL で入れる）
run_sql migrations/20261017_120000_line_conditions_value_rank.sql
# ADR-1024: AI 用の読み取り専用ユーザー ai_reader（パスワードなし。ログインは便3bまで不可）
run_sql migrations/20261017_130000_create_ai_reader_role.sql
# ADR-1025 便1: 解析の誤り報告の表3つ（空・構造のみ・冪等）
run_sql migrations/20261017_140000_create_analysis_error_report_tables.sql
# ADR-1026: 使われていない作品欄 products.type_master_id を取り除く（FK・索引ごと。冪等）
run_sql migrations/20261017_210000_drop_products_type_master_id.sql
# ADR-1027 便1: まとめ売りのまとめの数の列（NULL 許可・構造のみ・冪等）
run_sql migrations/20261017_220000_add_analysis_results_bundle_size.sql
# ADR-1027 便1: 単位マスタの呼び名の列（NULL 許可・構造のみ・冪等。値は docs/handoff/bundle-sale/data/ の SQL で入れる）
run_sql migrations/20261017_220100_add_line_units_display_names.sql
# ADR-1028 便1: 商品の荷姿の表（空・構造のみ・冪等）
run_sql migrations/20261018_100000_create_product_packagings.sql
# ADR-1030: 使われていない作品の写し products.tcg_type を取り除く（FK・索引ごと。冪等）
run_sql migrations/20261018_110000_drop_products_tcg_type.sql
run_sql migrations/20261019_100000_line_conditions_value_group_add_promo_single.sql
# ADR-1035: 状態の価値の群に booklet を許す（CHECK の作り直しのみ。冪等）
run_sql migrations/20261020_100000_line_conditions_value_group_add_booklet.sql
# ADR-1035 追補: 状態の価値の群に supply を許す（CHECK の作り直しのみ。冪等）
run_sql migrations/20261020_110000_line_conditions_value_group_add_supply.sql
# ADR-1019 段11 便1: 閲覧者向け文面のテンプレート表（空・構造のみ・冪等）
run_sql migrations/20261020_120000_create_viewer_message_templates.sql
# ADR-1038 便2: products(細分類, 中分類) → product_format_game_links の複合 FK（事前点検つき・冪等）
run_sql migrations/20261022_100000_products_format_in_work_fk.sql
# ADR-1038 便3b: 旧列 product_formats.type_master_id を取り除く（FK・索引ごと。冪等。親子の正本は links）
run_sql migrations/20261022_110000_product_formats_drop_type_master_id.sql
# ADR-1043 便1: 精度測定の正解表の表 2 つ（空の表を作るだけ。値は書かない・冪等）
run_sql migrations/20261023_180000_create_accuracy_gold.sql
# ADR-1052 段1: 相談係用 ai_cloud の部品（分類表・記録・生成関数。値は入らない・冪等）。ai_reader の後に置く
run_sql migrations/20261024_100000_create_ai_cloud_meta.sql
# ADR-1052 段1: 相談係用の読み取り専用ロール ai_reader_cloud（パスワードは PO が別途設定・冪等）
run_sql migrations/20261024_100100_create_ai_reader_cloud_role.sql
# ADR-1013 便6: ログイン直後のパスキー登録の案内のスキップ記録（空の表を作るだけ・冪等）
run_sql migrations/20261031_200000_add_passkey_enroll_prompt_skips.sql
# ADR-1052 段2: 相談係の件・申請・値を1回だけ返す関数（スキーマ ops_case・ロール ai_unmask_owner / ai_unmask。パスワードは PO が別途設定・冪等）
run_sql migrations/20261031_210000_create_ops_case.sql
# ADR-1055 段A: 知らない機械からのログインの許可の置き場（表3つ＋列4つ・追加のみ・値は入らない・冪等）
run_sql migrations/20261101_120000_add_new_device_approval.sql

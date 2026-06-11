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


TOTAL=124

run_py() {
  local script="$1"
  shift
  STEP=$((STEP + 1))
  echo ">>> [${STEP}/${TOTAL}] python ${script} $*"
  # SA-18 Phase2: Python マイグレーションは DDL を含むため ADMIN_DATABASE_URL で実行。
  # ADMIN_DATABASE_URL 未設定時は DATABASE_URL にフォールバック（後方互換）。
  docker exec \
    -e DATABASE_URL="${ADMIN_DATABASE_URL:-$DATABASE_URL}" \
    "$@" -w /app "${BACKEND}" python "${script}"
}

run_sql() {
  local file="$1"
  STEP=$((STEP + 1))
  echo ">>> [${STEP}/${TOTAL}] psql < ${file}"
  docker exec -i "${POSTGRES}" ${PSQL} < "${REPO_DIR}/${file}"
}

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
run_py  scripts/migrate_roles_gas_compat.py

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
run_sql migrations/080_phase_b_migration.sql

# Inventory 拡張
run_sql migrations/081_create_inventory.sql
run_sql migrations/082_extend_products_box_attributes.sql
run_sql migrations/083_add_staff_phone.sql
run_sql migrations/084_add_unit_to_inventory.sql
run_sql migrations/085_create_tcg_type_master.sql
run_sql migrations/086_seed_additional_tcg_types.sql
run_sql migrations/087_create_supplier_prompts.sql

# Lead / Discord / Meta 拡張
run_sql migrations/090_add_lead_contact_links.sql
run_sql migrations/091_add_leads_discord_messaging_columns.sql
run_sql migrations/092_add_meta_messages_discord_index.sql
run_sql migrations/093_rename_order_statuses.sql
run_sql migrations/094_create_message_translations.sql
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

# ADR-093: 商品マスタ 型番(mark) をシート B列で更新（日本語タイトル一致・125件）
run_sql migrations/20260604_010000_seed_product_marks.sql

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

# SA-02 Stage 1: channel_masters テーブル作成（手動チャネルマスタ＋デフォルトシード）
run_sql migrations/20260611_100000_create_channel_masters.sql

# SA-02 Stage 3: conversation_logs に手動記録用カラム追加（deleted_at + recorded_by_user_id）
run_sql migrations/20260611_120000_add_conv_log_manual_columns.sql

echo ""
echo "============================================"
echo "✅ 全マイグレーション完了 (${TOTAL}ステップ)"
echo "============================================"

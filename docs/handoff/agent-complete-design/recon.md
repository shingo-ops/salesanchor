# エージェント完結の設計体制 — recon

> この文書は何か(1行): エージェント完結の設計体制テーマの現在地調査(recon)。
> 理想は docs/specs/agent-complete-design/ を参照、本書は事実のみ。

調査日: 2026-07-03
HEAD: 2ed5826af4296278b2b6a8477d5119d9f6c0a061
origin/main: 2ed5826af4296278b2b6a8477d5119d9f6c0a061

## 調査1: 領域の切り方（F5）

### git ls-tree origin/main --name-only
```text
.claude-pipeline
.claude
.codex
.github
backend
docs
frontend
lp
migrations
monitoring
nginx
ops
questions
scripts
tasks
tests
www
```

### git ls-tree origin/main --name-only のうち 2階層まで
```text
"docs/\343\203\225\343\202\247\343\203\274\343\202\2721_\343\202\273\343\202\255\343\203\245\343\203\252\343\203\206\343\202\243\345\237\272\347\233\244_\345\256\237\350\243\205\343\202\254\343\202\244\343\203\211.docx"
.claude-pipeline/active-work.md
.claude-pipeline/step5d-plan.md
.claude/agent-config.sh
.claude/settings.json
.codex/config.toml
.deploy-stamp
.env.example
.env.monitoring.example
.github/CODEOWNERS
.github/PULL_REQUEST_TEMPLATE.md
.github/brand-icon-versions.json
.gitignore
.gitleaks.toml
.hadolint.yaml
AGENTS.md
CLAUDE.md
CONTRIBUTING.md
README.md
backend/.dockerignore
backend/AGENTS.md
backend/CLAUDE.md
backend/Dockerfile
backend/Makefile
backend/pyproject.toml
backend/requirements-dev.txt
backend/requirements.txt
docker-compose.exporters.yml
docker-compose.monitoring.yml
docker-compose.test.yml
docker-compose.yml
docs/ACCESS_CONTROL.md
docs/ADR-009_discord_gateway.md
docs/B-04_incident_response_playbook.md
docs/B-06_cloudflare_setup.md
docs/B-09_restore_test_procedure.md
docs/B-10_access_review_procedure.md
docs/B-11_credential_management_policy.md
docs/B-12_offboarding_procedure.md
docs/B-13_mgmt-vps-governance.md
docs/B-2_discord_setup_guide_for_shingo.docx
docs/BRANCH_PROTECTION_SETUP.md
docs/CC_UI_GOVERNANCE.md
docs/D-06_firebase_credentials_setup.md
docs/DATA_CLASSIFICATION.md
docs/DEVELOPMENT_GUIDE_FOR_SHINGO.md
docs/ENVIRONMENT_VARIABLES.md
docs/FEATURE_SPECIFICATION.md
docs/FEEDBACK_FORM_DESIGN.md
docs/FIREBASE_API_KEY_RESTRICTION_GUIDE.md
docs/FIREBASE_CUSTOM_AUTH_DOMAIN_SETUP.md
docs/INCIDENT_RESPONSE.md
docs/INTERNAL_TEST_FEEDBACK_TEMPLATE.md
docs/INTERNAL_TEST_GUIDE.md
docs/INTERNAL_TEST_RECORD.md
docs/META_APP_REVIEW_PRE_RECORDING_CHECKLIST.md
docs/META_APP_REVIEW_SCREENCAST_SCRIPT.md
docs/PARALLEL_TERMINAL_GUIDE.md
docs/PHASE1_DEPLOYMENT.md
docs/PHASE5_DOMAIN_CUTOVER_RUNBOOK.md
docs/PHASE_1D_META_INBOX_OVERVIEW.md
docs/PHASE_1D_RELEASE_NOTES.md
docs/PHASE_1E_FOLLOW_UP_BACKLOG.md
docs/SECURITY.md
docs/SECURITY_ENHANCEMENT_ROADMAP.md
docs/STANDARD-WORKFLOW.md
docs/TEST_ADMIN_PASSWORD_CHANGE_PROCEDURE.md
docs/USE_CASE_DESCRIPTIONS_v1.1_DRAFT.md
docs/UX_IMPROVEMENTS.md
docs/ZERO_TRUST_POLICY.md
docs/dark_mode_3value_phase2_proposal.md
docs/data_deletion_callback_design.md
docs/external-state-contract.yml
docs/feedback_form_to_github.gs
docs/handover.html
docs/products_design.md
docs/seed-data-tenant-review.md
feedback.md
frontend/.dockerignore
frontend/.env.example
frontend/.stylelintrc.json
frontend/AGENTS.md
frontend/CLAUDE.md
frontend/Dockerfile
frontend/eslint.config.js
frontend/index.html
frontend/nginx.conf
frontend/package-lock.json
frontend/package.json
frontend/playwright.config.ts
frontend/tsconfig.json
frontend/tsconfig.node.json
frontend/vite.config.ts
frontend/vitest.shims.d.ts
frontend/vitest.unit.config.ts
lp/.gitignore
lp/README.md
lp/astro.config.mjs
lp/package-lock.json
lp/package.json
lp/tailwind.config.mjs
lp/tsconfig.json
migrations/001_create_auth_events.sql
migrations/002_add_permissions_master.sql
migrations/003_add_phase1_tenant_tables.sql
migrations/004_add_phase2_permissions.sql
migrations/005_add_phase2_tenant_tables.sql
migrations/006_add_phase3_permissions.sql
migrations/007_add_phase3_tenant_tables.sql
migrations/008_add_phase4_permissions.sql
migrations/009_add_phase4_tenant_tables.sql
migrations/010_add_phase5_permissions.sql
migrations/011_add_phase5_tenant_tables.sql
migrations/012_add_meta_tenant_tables.sql
migrations/013_add_meta_webhook_idempotency.sql
migrations/014_create_current_tenant_id_function.sql
migrations/015_replace_customers_schema.sql
migrations/016_customers_rls_policies.sql
migrations/017_rewire_quotes_invoices_to_new_customers.sql
migrations/018_extend_permissions_with_menu_grain.sql
migrations/019_create_staff_tables.sql
migrations/020_create_bots_and_senders_view.sql
migrations/021_seed_roles_and_role_permissions.sql
migrations/022_staff_bots_rls_policies.sql
migrations/023_fix_system_admin_is_system_flag.sql
migrations/024_add_staff_bots_permissions.sql
migrations/025_resync_owner_admin_all_permissions.sql
migrations/026_create_customer_contact_channels.sql
migrations/027_backfill_customer_contact_channels.sql
migrations/028_create_companies.sql
migrations/029_create_contacts.sql
migrations/030_create_company_contact_subtables.sql
migrations/031_create_customer_migration_map.sql
migrations/032_add_company_contact_to_downstream.sql
migrations/033_drop_companies_is_individual.sql
migrations/034_add_unique_new_contact_id_to_customer_migration_map.sql
migrations/035_drop_customer_id_from_downstream.sql
migrations/036_drop_customer_migration_map.sql
migrations/037_add_pending_dedup_review_to_contacts_check.sql
migrations/038_add_products_phase1c_columns.sql
migrations/039_create_data_deletion_logs.sql
migrations/040_create_tenant_meta_config.sql
migrations/041_extend_meta_messages.sql
migrations/042_seed_meta_inbox_permissions.sql
migrations/043_create_meta_page_routing.sql
migrations/044_create_meta_page_routing_trigger.sql
migrations/045_add_meta_messages_page_id.sql
migrations/046_adr015_lead_foundation.sql
migrations/047_create_order_financials.sql
migrations/048_create_order_shipping_details.sql
migrations/049_create_order_purchase_details.sql
migrations/050_add_commissions.sql
migrations/051_remove_confirmed_status.sql
migrations/051_remove_confirmed_status_down.sql
migrations/052_alter_meta_messages_message_id_to_text.sql
migrations/052_alter_meta_messages_message_id_to_text_down.sql
migrations/053_add_users_locale.sql
migrations/053_add_users_locale_down.sql
migrations/054_add_users_theme.sql
migrations/055_add_granted_scopes.sql
migrations/055_add_granted_scopes_down.sql
migrations/056_add_suppliers_type_and_promote_public.sql
migrations/057_create_supplier_aliases.sql
migrations/058_create_knowledge_rules.sql
migrations/059_create_discord_inbound_messages.sql
migrations/060_create_supplier_discord_routing.sql
migrations/061_create_tcg_and_dex_masters.sql
migrations/062_create_inventory_movements_and_budget.sql
migrations/063_tenant_rbac_extensions.sql
migrations/064_add_users_is_super_admin.sql
migrations/065_seed_central_admin_permissions.sql
migrations/066_add_tenant_llm_budgets_notification_dedupe.sql
migrations/067_add_inbound_review_version_and_permissions.sql
migrations/067_add_inbound_review_version_and_permissions_down.sql
migrations/068_add_inventory_search_indexes.sql
migrations/068_add_inventory_search_indexes_down.sql
migrations/069_create_tenant_profile.sql
migrations/069_create_tenant_profile_down.sql
migrations/070_add_spreadsheet_phase.sql
migrations/070_add_spreadsheet_phase_down.sql
migrations/071_create_data_access_events.sql
migrations/072_add_retention_indexes.sql
migrations/073_update_lead_status_for_inbox_tabs.sql
migrations/074_rename_english_name_to_nickname.sql
migrations/075_create_goals.sql
migrations/076_add_google_calendar_config.sql
migrations/077_calendar_sync_mode_and_webhook_subscriptions.sql
migrations/078_create_calendar_events_tenant.sql
migrations/079_remove_buddy_badges.sql
migrations/080_phase_b_migration.sql
migrations/081_create_inventory.sql
migrations/082_extend_products_box_attributes.sql
migrations/083_add_staff_phone.sql
migrations/084_add_unit_to_inventory.sql
migrations/085_create_tcg_type_master.sql
migrations/086_seed_additional_tcg_types.sql
migrations/087_create_supplier_prompts.sql
migrations/088_standardize_unit_values.sql
migrations/089_standardize_condition_values.sql
migrations/090_add_lead_contact_links.sql
migrations/091_add_leads_discord_messaging_columns.sql
migrations/092_add_meta_messages_discord_index.sql
migrations/093_rename_order_statuses.sql
migrations/094_create_message_translations.sql
migrations/095_add_lead_social_links.sql
migrations/096_add_deal_lead_source.sql
migrations/097_create_company_discord.sql
migrations/098_migrate_customer_discord_to_company_discord.sql
migrations/099_add_discord_guild_config.sql
migrations/100_add_meta_messages_image_columns.sql
migrations/20260601_140000_drop_customers_tables.sql
migrations/20260602_000000_add_products_central_columns.sql
migrations/20260602_010000_repoint_downstream_fk_to_public_products.sql
migrations/20260602_020000_add_products_tcg_type.sql
migrations/20260602_030000_add_products_unit.sql
migrations/20260602_040000_backfill_products_unit_condition_from_inbound.sql
migrations/20260602_120000_add_discord_ticket_config.sql
migrations/20260602_150000_add_discord_scale_channels.sql
migrations/20260602_160000_add_discord_role_names.sql
migrations/20260602_170000_add_products_master_label_columns.sql
migrations/20260602_180000_add_inventory_offer_type_ship_timing.sql
migrations/20260602_190000_create_user_inventory_filters.sql
migrations/20260602_200000_add_discord_config_connected_by_staff.sql
migrations/20260603_000000_add_products_product_kind.sql
migrations/20260603_010000_add_suppliers_line_and_address.sql
migrations/20260603_030000_seed_dragonball_products.sql
migrations/20260603_040000_add_products_set_type.sql
migrations/20260604_010000_seed_product_marks.sql
migrations/20260604_020000_backfill_products_shipping_defaults.sql
migrations/20260604_030000_add_quote_invoice_item_overseas_columns.sql
migrations/20260604_040000_seed_tcg_products_8series.sql
migrations/20260604_050000_add_orders_paid_at.sql
migrations/20260604_050000_add_tenant_policy_columns.sql
migrations/20260604_060000_add_lost_reason_code.sql
migrations/20260604_070000_deprecate_columns.sql
migrations/20260604_080000_create_registration_tokens.sql
migrations/20260604_090000_create_conversation_logs.sql
migrations/20260604_090000_create_link_templates.sql
migrations/20260604_100000_add_guild_id_to_contact_channels.sql
migrations/20260604_100000_create_company_stats_view.sql
migrations/20260604_110000_create_ingestion_jobs.sql
migrations/20260604_120000_create_parse_logs.sql
migrations/20260604_130000_create_supplier_parse_stats_view.sql
migrations/20260604_140000_create_own_inventory.sql
migrations/20260604_150000_add_inventory_source_kind.sql
migrations/20260604_160000_add_invoice_snapshot_columns.sql
migrations/20260604_170000_create_product_attribute_masters.sql
migrations/20260604_180000_analytics_agent_a_tables.sql
migrations/20260604_220000_create_translation_glossary.sql
migrations/20260605_000000_add_products_display_order.sql
migrations/20260605_010000_rls_translation_glossary.sql
migrations/20260605_020000_fix_translation_glossary_rls_cast.sql
migrations/20260605_030000_create_salesanchor_app_role.sql
migrations/20260605_040000_grant_salesanchor_app_tenant_schemas.sql
migrations/20260606_010000_add_google_drive_config.sql
migrations/20260607_000000_fix_rls_policy_variable_name.sql
migrations/20260607_120000_create_lead_channels.sql
migrations/20260608_080000_add_carrier_credentials.sql
migrations/20260609_090000_add_carrier_credentials_rls.sql
migrations/20260609_090001_add_carrier_credentials_rls_down.sql
migrations/20260609_100000_add_carrier_account_number.sql
migrations/20260610_071110_add_paypal_config.sql
migrations/20260611_010000_fix_owner_role_color.sql
migrations/20260611_020000_add_invoice_paypal_columns.sql
migrations/20260611_100000_create_channel_masters.sql
migrations/20260611_110000_extend_order_shipping_for_ship_api.sql
migrations/20260611_120000_add_conv_log_manual_columns.sql
migrations/20260611_130000_fix_v_company_stats_deleted_at.sql
migrations/20260611_140000_add_conv_log_is_manual.sql
migrations/20260611_150000_add_paypal_webhook_id.sql
migrations/20260612_050000_backfill_invoice_timestamps.sql
migrations/20260612_090000_extend_registration_tokens_change_billing.sql
migrations/20260612_100000_add_contact_channel_unique.sql
migrations/20260612_110000_add_company_discord_guild_id.sql
migrations/20260612_120000_fix_company_stats_ssot.sql
migrations/20260612_131520_add_invoice_copypdf.sql
migrations/20260612_150000_drop_password_hash.sql
migrations/20260612_154322_create_paypal_disputes.sql
migrations/20260612_200000_fedex_creds_unique_env.sql
migrations/20260613_010000_funnel_deals_closed_at.sql
migrations/20260613_020000_funnel_close_reasons.sql
migrations/20260613_030000_funnel_leads_initiative_channel.sql
migrations/20260613_040000_funnel_goals_kpi_extend.sql
migrations/20260613_050000_funnel_purchase_cost_nullable.sql
migrations/20260614_030000_add_carrier_test_result.sql
migrations/20260614_040137_add_tenant_deletion_audit.sql
migrations/20260614_100000_create_sales_form_tables.sql
migrations/20260615_235900_seed_pokemon_mega_products.sql
migrations/20260616_000000_fix_tcg_type_dedup.sql
migrations/20260620_010000_create_inventory_aggregation_rules.sql
migrations/20260621_010000_create_countries_master.sql
migrations/20260621_020000_add_schedule_calendar_category_and_owner_settings.sql
migrations/20260622_010000_add_meta_messages_master_history_columns.sql
migrations/20260622_020000_add_inventory_raw_condition.sql
migrations/20260622_020000_migrate_conv_only_into_meta_messages.sql
migrations/20260623_010000_add_inventory_axes_columns.sql
migrations/20260623_020000_create_inventory_offer_v2_unique_key.sql
migrations/20260623_020000_drop_products_category_classification.sql
migrations/20260623_030000_drop_inventory_offer_key.sql
migrations/20260623_040000_add_tenant_id_to_message_translations.sql
migrations/20260623_040000_make_inventory_condition_nullable.sql
migrations/20260623_050000_drop_inventory_condition.sql
migrations/20260623_060000_add_products_tcg_type_fk.sql
migrations/20260623_100000_rls_message_translations.sql
migrations/20260624_120000_backfill_meta_messages_original_language.sql
migrations/20260624_140000_converge_inventory_v2.sql
migrations/20260626_100000_add_outbound_draft_message_link.sql
migrations/20260626_120000_add_unique_guild_id_to_tenant_discord_config.sql
migrations/20260626_130000_force_rls_public_products.sql
migrations/20260627_120000_add_tenant_features_table.sql
migrations/20260628_170000_add_app_fx_rates.sql
migrations/20260629_010000_backfill_inventory_unit_from_products.sql
migrations/20260629_020000_drop_products_condition_unit.sql
migrations/20260703_010000_txn_backbone_ben1a.sql
migrations/20260703_020000_conv_backbone_ben1b.sql
migrations/20260703_030000_order_items_ben2.sql
monitoring/tokens.yml
monitoring/uptime-kuma-monitors.yml
nginx/nginx.conf
questions/Q01-adr-015-scope-and-status-collision.md
questions/Q02-adr-020-pipeline-mismatch.md
scripts/aeon-delivery.sh
scripts/aeon-dispatch.sh
scripts/aeon-release.sh
scripts/archive_audit_logs.sh
scripts/backfill-active-work-done.sh
scripts/backup.sh
scripts/backup_tenant_before_drop.sh
scripts/backup_to_s3.sh
scripts/blue-green-cutover.sh
scripts/build_shingo_guide.py
scripts/check-active-work-format.sh
scripts/check-condition-vocab.js
scripts/check-dangling-routes.js
scripts/check-doc-heading-duplicates.sh
scripts/check-hooks.sh
scripts/check-migration-registration-exists.sh
scripts/check-process-artifacts.js
scripts/check-stale-tasks.py
scripts/check-stale-worktrees.sh
scripts/check-task-state.sh
scripts/check-ui-governance.js
scripts/check_priority_scoring_state.py
scripts/check_schema_catchup_sync.py
scripts/claude-dispatch.sh
scripts/cleanup-worktree.sh
scripts/codex-architect.sh
scripts/codex-auth-check.sh
scripts/codex-evaluator.sh
scripts/codex-exec.sh
scripts/codex-generator.sh
scripts/codex-planner.sh
scripts/codex-research.sh
scripts/codex-reviewer.sh
scripts/detect-external-api-change.js
scripts/download-brand-assets.js
scripts/dry-run-blue-green.sh
scripts/export_inventory_for_sheet.py
scripts/f2-cleanup.sh
scripts/generate-adr-index.js
scripts/gh-pr-create-safe.sh
scripts/gh-pr-merge-safe.sh
scripts/lint_tenant_schema.py
scripts/migrate_009_phase4_tenant_tables.py
scripts/migrate_011_phase5_tenant_tables.py
scripts/migrate_073_lead_status.py
scripts/migrate_074_rename_english_name_to_nickname.py
scripts/migrate_079_remove_buddy_badges.py
scripts/migrate_089_drop_customers_tables.py
scripts/migrate_20260620_080000_calendar_category_backfill.py
scripts/migrate_20260621_020000_backfill_lead_country.py
scripts/migrate_20260621_030000_backfill_lead_channel_type.py
scripts/migrate_6roles_stage_a.py
scripts/migrate_adr015_lead_foundation.py
scripts/migrate_adr021_remove_confirmed_status.py
scripts/migrate_adr021_sprint2_financials.py
scripts/migrate_adr021_sprint3_shipping.py
scripts/migrate_adr021_sprint4_purchase.py
scripts/migrate_adr021_sprint5_commissions.py
scripts/migrate_adr041_granted_scopes.py
scripts/migrate_adr109_status_codes.py
scripts/migrate_adr119_lead_channels_backfill.py
scripts/migrate_discord_b2c.py
scripts/migrate_inventory_sprint1.py
scripts/migrate_inventory_sprint2.py
scripts/migrate_inventory_sprint5_to_7.py
scripts/migrate_inventory_sprint8.py
scripts/migrate_inventory_sprint9.py
scripts/migrate_meta.py
scripts/migrate_meta_inbox_phase1d.py
scripts/migrate_meta_inbox_phase1d_sprint4.py
scripts/migrate_meta_messages_message_id_to_text.py
scripts/migrate_meta_messages_page_id.py
scripts/migrate_meta_page_routing.py
scripts/migrate_phase1.py
scripts/migrate_phase1_redesign.py
scripts/migrate_phase2.py
scripts/migrate_phase3.py
scripts/migrate_phase4.py
scripts/migrate_phase5.py
scripts/migrate_roles_gas_compat.py
scripts/migrate_sa02_stage2_meta_to_conv_logs.py
scripts/new-worktree.sh
scripts/nmap_scan.sh
scripts/permit-danger.sh
scripts/preflight_step5d.sh
scripts/reaper-worktree.sh
scripts/register-pr.sh
scripts/rehearsal_phase2.sh
scripts/release-worktree.sh
scripts/restore.sh
scripts/run_all_migrations.sh
scripts/security_check.sh
scripts/seed_discord_inbound_from_api_analysis.py
scripts/seed_inventory_from_output.py
scripts/seed_pokemon_dex.py
scripts/seed_pokemon_dex_from_sheet.py
scripts/seed_products_from_master.py
scripts/seed_supplier_prompts_from_sheet.py
scripts/seed_suppliers_from_line_master.py
scripts/seed_suppliers_from_sheet.py
scripts/seed_tcg_series.py
scripts/seed_tcg_series_from_pokemon_bb.py
scripts/seed_tcg_series_from_sheets.py
scripts/setup-claude-monitor-user.sh
scripts/setup-vps-runner.sh
scripts/setup_review_tenant.py
scripts/setup_single_test_user.py
scripts/setup_tenant.py
scripts/setup_test_users.py
scripts/setup_unattended_upgrades.sh
scripts/setup_uptime_kuma.sh
scripts/smoke_test_post_deploy.sh
scripts/sop-health-collector.js
scripts/test_lint_tenant_schema.py
scripts/test_pre_commit_hook.py
scripts/test_rollback_simulation.sh
scripts/validate-pr-ownership.sh
scripts/validate-worktree-start.sh
scripts/verify_sa02_stage2_count_check.py
tasks/lessons.md
tasks/todo.md
```

### 領域候補と実在パス
- DB: migrations/, backend/app/models/, backend/app/schemas/
- フロントエンド: frontend/src/, frontend/public/
- インフラ・deploy: .github/workflows/, docker-compose.yml, docker-compose.monitoring.yml, docker-compose.test.yml, scripts/blue-green-cutover.sh, scripts/run_all_migrations.sh
- GitHub運用: .github/PULL_REQUEST_TEMPLATE.md, .github/CODEOWNERS, scripts/gh-pr-create-safe.sh, scripts/gh-pr-merge-safe.sh, scripts/register-pr.sh
- API: backend/app/routers/, backend/app/services/
- 外部接続: backend/app/services/google_calendar.py, backend/app/services/google_drive_oauth.py, backend/app/services/discord_rest.py, backend/app/services/discord_sender.py, backend/app/discord_gateway/main.py, backend/app/discord_gateway/client.py, backend/app/discord_gateway/ticket_channel_creator.py
- 保守運用: docs/runbooks/, monitoring/, scripts/sop-health-collector.js, scripts/qa/reset-tenant.sh
- セキュリティ: backend/app/auth/, migrations/022_staff_bots_rls_policies.sql, migrations/005_add_phase2_tenant_tables.sql, migrations/063_tenant_rbac_extensions.sql, docs/SECURITY.md

### フォルダ単位で切り出せるか
- DB と API は backend/ 配下で重なりあり
- 外部接続は backend/app/services/ と backend/app/discord_gateway/ に分散し、API と重なりあり
- フロントエンドは frontend/ 配下で独立
- インフラ・deploy は .github/ と scripts/ と docker-compose*.yml に分散
- GitHub運用は .github/ と scripts/ に分散
- 保守運用は docs/runbooks/ と monitoring/ と scripts/ に分散
- セキュリティは backend/app/auth/ と migrations/ と docs/ に分散

## 調査2: 親リンクと隣接テーマの突合材料

### docs/specs/README.md
```text
     1	# 設計仕様書 索引（あるべき姿の地図）
     2	
     3	> この一覧は「どの領域の開発で、どの設計仕様書（あるべき姿）を正本にするか」を引くための地図。
     4	> ルールの正本は [`docs/STANDARD-WORKFLOW.md`](../STANDARD-WORKFLOW.md) §1.5。
     5	> **索引に載る領域に触れる開発は、その設計仕様書を先に読む（無ければ作る）。**
     6	
     7	## 一覧
     8	
     9	| 領域 | 設計仕様書（あるべき姿） | 状態 |
    10	|---|---|---|
    11	| ブランチ運用（develop 廃止後の開発環境） | [branch-operations/README.md](branch-operations/README.md) | 公開 |
    12	| 文書の親子構造 標準ルール化 | doc-parent-child/README.md (doc-parent-child/README.md) | 公開 |
    13	| 商品マスタ | [product-master/README.md](product-master/README.md) | 公開 |
    14	| 設計パートナー長期安定体制（循環の形） | [design-partner-loop/README.md](design-partner-loop/README.md) | 公開 |
    15	| エージェント完結の設計体制 | [agent-complete-design/README.md](agent-complete-design/README.md) | 公開 |
    16	| GO記録の自動転記 | [go-record-transcription/](../handoff/go-record-transcription/) | 草案 |
    17	| 画面部品の標準（component-standard） | [component-standard.md](component-standard.md) | 公開 |
    18	| 在庫管理 | [inventory-management/spec.md](inventory-management/spec.md) | 公開（親README未・棚卸し待ち） |
    19	| ├ 種類分けマスタ（tcg_type） | （作成予定） | 未 |
    20	| ├ 品目マスタ（item） | （作成予定） | 未 |
    21	| ├ HTSコードマスタ | （作成予定） | 未 |
    22	| ├ 素材マスタ | （作成予定） | 未 |
    23	| ├ 状態マスタ（condition） | （作成予定） | 未 |
    24	| └ 単位マスタ（unit） | （作成予定） | 未 |
    25	| 取引フロー（lead→deal→company→order・SSOT） | [transaction-flow/README.md](transaction-flow/README.md) | KGI承認済 2026-07-02 |
    26	| 文書体系（ナレッジベース） | [doc-estate/README.md](./doc-estate/README.md) | KGI承認済 |
    27	| カレンダー（schedule。全予定の見える化・源泉SSOT参照・やることフィード共有） | [schedule/README.md](schedule/README.md) | KGI承認済 2026-07-03 |
    28	| ダッシュボード（dashboard。羅針盤・やることフィード・目標カスケード・AI提案） | [dashboard/README.md](dashboard/README.md) | KGI承認済 2026-07-03 |
    29	| 在庫（自社在庫／ドロップシッピングの2種。接点：order_item の出どころ参照） | （仕様書未作成） | **pending** |
    30	| 予約販売（接点：order の派生フロー） | （仕様書未作成） | **pending** |
    31	| 送料マスタ（接点：見積送料の算出） | （仕様書未作成） | **pending** |
    32	| 請求先/配送先の住所区別（接点：company/order の住所） | （仕様書未作成） | **pending** |
    33	| 為替レート | （仕様書未作成・関連ADR: ADR-148） | 未 |
    34	| 翻訳送信・グロッサリ（接点: conversation_logs。会話ログの紐付けは取引フロー） | （仕様書未作成・関連: ADR-110） | 未 |
    35	| Discord連携 | （仕様書未作成・関連: ADR-009, 014, 100, 091） | 未 |
    36	| Meta（FB/IG）連携 | （仕様書未作成・関連: ADR-024, 025, 041, 026） | 未 |
    37	| 認証・権限・ロール | （仕様書未作成・関連: ADR-023, 032, 138） | 未 |
    38	| テナント管理・RLS | （仕様書未作成・関連: ADR-072, 034, 036） | 未 |
    39	| 出荷キャリア連携（接点: order_shipping_details。発送の事実は取引フロー） | （仕様書未作成・関連: ADR-103, 123, 128） | 未 |
    40	
    41	
    42	## specs外に散在する仕様書（存在の記録のみ・中身の判定は棚卸し便で）
    43	以下は docs/ 直下に置かれた仕様書らしきファイル。生きているか古いかは未確認。移動・削除はここではしない。
    44	- docs/FEATURE_SPECIFICATION.md
    45	- docs/FEEDBACK_FORM_DESIGN.md
    46	- docs/data_deletion_callback_design.md
    47	- docs/products_design.md
    48	
    49	## 追加のしかた
    50	新しい設計仕様書を作ったら、この表に「領域名｜相対リンク｜状態」を1行足す。
    51	状態は「公開＝読める／未＝これから作る」の2値で書く。
    52	凡例（暫定・正規化は棚卸し便で実施）: 未＝枠のみ／pending＝接点記載済み・仕様書未作成／草案＝作成中／KGI承認済＝あるべき姿とKGIがPO承認済み。
```

### design-partner-loop の README（あるべき姿・KGI）
```text
    14	## 1. あるべき姿（PO自筆の言葉から・情景のまま）
    15	「エージェント含めて全ての開発・構築には、あるべき姿・KGI・KGI達成進捗表・ADR・KPI・recon・design・designの子ども（開発履歴と進捗表）・維持する仕組みがあり、全て紐づいていて、長期的に誰が見ても引き継いでも理解してキャッチアップできる状態」。
    16	
    17	## 2. KGI（○×で測る・数値化 確定版）
    18	
    19	前提（測る範囲の線引き）: KGI-2・KGI-3は2026-07-02以降の新規・変更のみを対象とする（§3-4 蛇口→床の原則。過去資産＝既存テーマ・ADR153件・正本宣言約30個への遡及採点はしない。棚卸しは別便）。
    20	
    21	| # | 合格条件 | 測り方 | 合格ライン |
    22	|---|---|---|---|
    23	| 1 | 索引に未登録の設計テーマ 0件 | docs/specs/ 配下に実在するテーマ（フォルダ＋直置き仕様書ファイル）と、索引 docs/specs/README.md の行を突合し、索引に行が無いものを数える | 0件 |
    24	| 2 | 無断新規 0（蛇口） | 2026-07-01以降に新規作成された設計仕様書ごとに、「索引確認の記録」節（①索引を確認した ②なぜ既存で足りないか1行 ③索引に登録した）が本文に在る=1／無い=0。合計÷新規数 | 満数 |
    25	| 3 | 記録一式の充足（床） | 2026-07-02以降に門番が振り分け判定したテーマごとに、下の段階別チェックリストで必要物すべて在る=1／欠け=0。合格テーマ数÷対象テーマ数。対象0件の間は「n/a（判定保留）」と表示し、0/0を満数とは扱わない | 満数 |
    26	
    27	KGI-3 段階別チェックリスト（○×の物差し）:
    28	
    29	| 振り分け | 必要物（すべて在る/無いで数えられるもの） |
    30	|---|---|
    31	| 新規テーマ（フルセット） | design-partner.md §5テンプレの10点: 1行説明／あるべき姿（PO自筆）／KGI表／KPI行／recon／design／弊害欄／外部・過去事例欄／受入基準／維持の仕組み節。在る点数 10/10 で合格 |
    32	| 既存の延長・修正 | 既存の子（design.md または開発履歴）に追記行が在り、PRから辿れる=1 |
    33	| 軽微（1行修正等） | 台帳1行＋PRリンクが在る=1 |
    34	
    35	KPI: 達成KGI数 ◯/3（KGI-3がn/aの間は「◯/2＋n/a」と表示する）。
    36	
    37	弊害と維持の仕組み（守り手の名指し・宛先明記）:
    38	- KGI-1の限界: specs外に新設された仕様書は検知できない。守り手＝置き場SSOT＋増産防止便（§5-5）で関所（process-artifacts gate）に実ファイルと索引の突合検査を追加して機械強制。それまでは人手で守る（理由: gate実装のreconが未実施のため、推測での関所設計を避ける）。
    39	- KGI-2/3の限界: 「在る」までしか測れず、節が空でも1と数え得る。空欄・抽象語（統一/改善/正常等）の残存検知は維持の仕組み必須化便（§5-5）で機械化。中身の質は機械では原理的に判定できないため、PO目視3点（§6）で守る。
    40	- KGI-3のn/a: 欠陥ではなく蛇口→床の帰結。早期に実数化する場合は§5-4ステップ3（基幹領域のあるべき姿便の先行・優先順はPO選定）。
    41	- 判定の機械化全般: 維持の仕組み必須化便（§5-5）。新しい関所は作らず、既存gateへの検査追加とする。
    42	
    43	承認注記: 本§2の数値化はPO承認済み（確定PR: #2718）。現状の測定値は正本に書かず、各PR本文と検証記録（evidence-registry）に残す。
```

### 停止ゼロ／無駄な停止の grep
```text

```
該当文書なし

### 近接する停止関連の文書
```text
    34	- 柱3 整合は掲示板（正本文書）経由のみ: 窓同士の直接通信は存在しない前提で設計し、
    35	  親子リンク・素人向け1行説明を全文書に義務づける。
    36	- 柱4 PO関門は3つだけ: あるべき姿の自筆／KGI承認／GO。それ以外の停止・介入を発生させない。
    37	- 柱5 維持は三重: KGI⑥守り手名指し＋KGI⑦変更一巡＋本書§9。
    38	- 柱6 セッション開始の自動キャッチアップ（public非依存）: 部品1=実装側の記帳義務（記帳なくして完了なし）、
    39	  部品2=常設指示による正本→必読→進捗表の自動読込、部品3=鮮度確認（public期間中は直接取得を
    40	  補助輪として併用可。private後は記帳規律＋窓の同期を主とし、実物検証は認証を持つ実装役が代行）。
    41	- 成長回路の原則（あるべき姿4対応）: 不具合・違反・停止は「開発中」「関所」「本番」の
    42	  3箇所で捕捉し、track-record と5W2Hで蓄積層（リポジトリの文書と関所）に記録する。

   156	- 実行役の自己修正禁止: テスト赤・エラー時に実行役（CC）が指示なく修正・コミットへ進んではならない。停止して生ログを提示し、修正の採否はPlannerがdiff検証で決める（2026-07-02 維持の仕組み便: 無断修正は内容妥当でも手順違反）。
   157	- カードの停止条件は肯定形で一義に書く: 「〜以外なら停止」等の否定形は読み違いによる誤停止を生む（2026-07-02 同便で2回発生）。「Xを含む❌が在る場合のみ停止、他は続行」の形で書く。
```

## 調査3: 重さの地図

### トップ階層ディレクトリごとのサイズ
```text
7.8M	docs/
7.2M	frontend/
5.3M	backend/
1.5M	scripts/
1.3M	migrations/
1.3M	lp/
480K	.github
296K	monitoring/
 72K	tests/
 36K	tasks/
 20K	nginx/
 16K	questions/
4.0K	ops/
  0B	www/
```

### サイズ上位ファイル20件
```text
-rw-r--r--  1 tanizawashingo  staff  444107 Jul  3 21:54 frontend/package-lock.json
-rw-r--r--  1 tanizawashingo  staff  323549 Jul  3 21:54 frontend/public/images/fedex-setup/step1-04-api-checklist.png
-rw-r--r--  1 tanizawashingo  staff  311030 Jul  3 21:54 lp/public/og-image.png
-rw-r--r--  1 tanizawashingo  staff  290871 Jul  3 21:54 lp/scripts/og-image.html
-rw-r--r--  1 tanizawashingo  staff  288337 Jul  3 21:54 frontend/public/og-image.png
-rw-r--r--  1 tanizawashingo  staff  223582 Jul  3 21:54 lp/package-lock.json
-rw-r--r--  1 tanizawashingo  staff  218447 Jul  3 21:54 docs/handoff/txn-flow-asis-recon/recon.md
-rw-r--r--  1 tanizawashingo  staff  216391 Jul  3 21:54 lp/public/logo.png
-rw-r--r--  1 tanizawashingo  staff  209308 Jul  3 21:54 frontend/public/images/fedex-setup/step1-07-overview-v2.png
-rw-r--r--  1 tanizawashingo  staff  202121 Jul  3 21:54 docs/handoff/status-ssot/screenshots/ja-leads-existing-customer.png
-rw-r--r--  1 tanizawashingo  staff  198288 Jul  3 21:54 frontend/public/images/fedex-setup/step1-02-purpose.png
-rw-r--r--  1 tanizawashingo  staff  198134 Jul  3 21:54 migrations/20260604_040000_seed_tcg_products_8series.sql
-rw-r--r--  1 tanizawashingo  staff  193249 Jul  3 21:54 docs/handoff/status-ssot/screenshots/ja-leads-negotiating.png
-rw-r--r--  1 tanizawashingo  staff  188391 Jul  3 21:54 frontend/public/images/fedex-setup/step1-05-config.png
-rw-r--r--  1 tanizawashingo  staff  186338 Jul  3 21:54 docs/handoff/status-ssot/screenshots/leads-list.png
-rw-r--r--  1 tanizawashingo  staff  183369 Jul  3 21:54 frontend/tests-e2e/funnel-dashboard-subpages.spec.ts-snapshots/leads-page-chromium-darwin.png
-rw-r--r--  1 tanizawashingo  staff  180771 Jul  3 21:54 frontend/public/images/fedex-setup/step1-03-api-cards.png
-rw-r--r--  1 tanizawashingo  staff  179724 Jul  3 21:54 frontend/tests-e2e/funnel-dashboard-subpages.spec.ts-snapshots/follow-ups-page-chromium-darwin.png
-rw-r--r--  1 tanizawashingo  staff  178006 Jul  3 21:54 backend/app/assets/Label-Cover-Sheet-form.pdf
-rw-r--r--  1 tanizawashingo  staff  174232 Jul  3 21:54 frontend/public/images/fedex-setup/step1-06-confirm.png
```

### docs/ 配下の内訳（サブフォルダ別サイズ）
```text
1.1M	docs/handoff/status-ssot
232K	docs/handoff/txn-flow-asis-recon
136K	docs/specs/inventory-management
 88K	docs/ai-agents/evidence-registry.md
 60K	docs/handoff/design-site
 52K	docs/specs/transaction-flow
 52K	docs/specs/product-master
 48K	docs/handoff/paypal-invoice-epic
 48K	docs/handoff/decision-layer-01
 40K	docs/handoff/karte-input-format-phase-b
 40K	docs/handoff/funnel-dashboard-stage1
 40K	docs/handoff/fedex-png-zpl-labels
 36K	docs/specs/agent-complete-design
 36K	docs/handoff/ui-standardization
 32K	docs/handoff/record-drawer-rollout
 32K	docs/handoff/realpage-standardization
 32K	docs/handoff/discord-auto-setup
 32K	docs/handoff/datatable-standardization
 32K	docs/adr/ADR-021-order-management.md
 28K	docs/runbooks/monitoring-vps-migration.md
 28K	docs/handoff/zero-downtime-deploy
 28K	docs/handoff/sa-02-stage2-migration
 28K	docs/handoff/mobile-shell-pr-r2
 28K	docs/handoff/karte-input-format
 28K	docs/handoff/dashboard-funnel-kgi
 28K	docs/adr/README.md
 24K	docs/handoff/translation-pipeline
 24K	docs/handoff/nginx-resolver-adr133
 24K	docs/handoff/mobile-shell-pr-r2b
 24K	docs/handoff/mobile-responsive
 24K	docs/handoff/migration-013-guard
 24K	docs/handoff/karte-visual-gate
 24K	docs/handoff/fedex-ship-stage2
 24K	docs/handoff/drawer-pilot
 24K	docs/handoff/company-stats-ssot
 24K	docs/adr/ADR-035-external-state-verification.md
 20K	docs/handoff/zero-downtime-polish
 20K	docs/handoff/ui-consistency-b
 20K	docs/handoff/ui-consistency-a
 20K	docs/handoff/sop-kpi2-phase2
 20K	docs/handoff/rehearsal-env
 20K	docs/handoff/incident-paypal-invoicing-false-complete
 20K	docs/handoff/fedex-sandbox-label-validation-smoke
 20K	docs/handoff/fedex-rates-stage1
 20K	docs/handoff/fedex-label-validation-readiness
 20K	docs/handoff/carrier-credential-form-refactor
 20K	docs/handoff/branch-operations
 20K	docs/ai-agents/design-partner.md
 20K	docs/adr/ADR-039-generator-codebase-reconnaissance.md
 20K	docs/adr/ADR-029-self-hosted-runner-fleet.md
 16K	docs/specs/doc-estate
 16K	docs/specs/dashboard
 16K	docs/specs/component-standard.md
 16K	docs/runbooks/adr-019-english-ui-temporary-deploy.md
 16K	docs/handoff/sop-touch-files-guard
 16K	docs/handoff/sop-kpi2
 16K	docs/handoff/sop-delete-detect
 16K	docs/handoff/session-freshness-hook
 16K	docs/handoff/sa02-r1-r2-convlog-links
 16K	docs/handoff/sa-02-stage2-preflight-fix
 16K	docs/handoff/runtime-config-audit
 16K	docs/handoff/responsive-ux-pr-r1
 16K	docs/handoff/products-rls-stage1
 16K	docs/handoff/paypal-webhook
 16K	docs/handoff/paypal-payment-link
 16K	docs/handoff/paypal-invoicing
 16K	docs/handoff/nginx-inode-deploy
 16K	docs/handoff/mobile-shell-pr-r2d
 16K	docs/handoff/mobile-shell-pr-r2c
 16K	docs/handoff/meta-screencast-handoff-2026-05-09.md
 16K	docs/handoff/login-ux-phase1
 16K	docs/handoff/inbox-ui-text-j1-j5
 16K	docs/handoff/fedex-pr-a4
 16K	docs/handoff/fedex-etd-adr-draft
 16K	docs/handoff/etd-scaffold-adr137
 16K	docs/handoff/design-site-visual-fit
 16K	docs/handoff/datatable-batch2
 16K	docs/handoff/chromatic-full-removal
 16K	docs/handoff/billing-display-name-fix
 16K	docs/handoff/auto-back-merge
 16K	docs/handoff/adr090-pr4-tenant-products-deprecation
 16K	docs/adr/karte_reference.html
 16K	docs/adr/ADR-126-registration-form-input-contract-v2.md
 16K	docs/adr/ADR-091-discord-bot-scope-definition.md
 16K	docs/adr/ADR-057-lp-premium-restyle.md
 16K	docs/adr/ADR-056-human-in-the-loop-minimization.md
 16K	docs/adr/ADR-049-lp-section-completion.md
 16K	docs/adr/ADR-048-web-claude-external-planner.md
 16K	docs/adr/ADR-047-lp-copy-refocus.md
 16K	docs/adr/ADR-042-guardrails-and-release-flow.md
 16K	docs/adr/ADR-014-inventory-management.md
 12K	docs/specs/schedule
 12K	docs/specs/design-partner-loop
 12K	docs/runbooks/vps-runner-setup.md
 12K	docs/runbooks/qa-smoke-operations.md
 12K	docs/runbooks/external-state-operations.md
 12K	docs/runbooks/discord-role-order-guide.md
 12K	docs/handoff/wall0-tenant-ddl-commit
 12K	docs/handoff/ui-std-pr-b
 12K	docs/handoff/ui-governance-gate
 12K	docs/handoff/ticket-welcome-en
 12K	docs/handoff/tenant-create-fix
 12K	docs/handoff/send-error-messaging
 12K	docs/handoff/schedule-grid-sticky-restore
 12K	docs/handoff/schedule-css-height-restore
 12K	docs/handoff/sa04-impl
 12K	docs/handoff/review-mail-discord-notifier
 12K	docs/handoff/qa-smoke-scene-09
 12K	docs/handoff/products-rls-stage2
 12K	docs/handoff/products-price-deprecation
 12K	docs/handoff/prod1-auto-cleanup
 12K	docs/handoff/paypal-test-invoice
 12K	docs/handoff/paypal-connection-test
 12K	docs/handoff/paypal-auto-confirm
 12K	docs/handoff/mobile-shell-pr-r2a
 12K	docs/handoff/migration-030000-rename
 12K	docs/handoff/karte-sales-form-b1
 12K	docs/handoff/inventory-ui-cleanup
 12K	docs/handoff/inbox-received-image-display
 12K	docs/handoff/i18n-missing-keys-fill
 12K	docs/handoff/go-record-transcription
 12K	docs/handoff/funnel-dashboard-live-switch
 12K	docs/handoff/fedex-guide-step1-7
 12K	docs/handoff/fedex-etd-stamp-recon
 12K	docs/handoff/dryrun-gap-recon
 12K	docs/handoff/doc-parent-child
 12K	docs/handoff/design-site-understanding-flow
 12K	docs/handoff/design-partner-loop-maintenance-gate
 12K	docs/handoff/datatable-batch3
 12K	docs/handoff/carrier-credentials-reset-tenant-ctx
 12K	docs/handoff/adr-126-impl
 12K	docs/ai-agents/kpi.md
 12K	docs/adr/ADR-SA-17-translation-bidirectional-glossary-two-layer.md
 12K	docs/adr/ADR-138-funnel-dashboard-stage1.md
 12K	docs/adr/ADR-131-tenant-context-auto-reset.md
 12K	docs/adr/ADR-127-registration-post-forms.md
 12K	docs/adr/ADR-114-worktree-auto-cleanup.md
 12K	docs/adr/ADR-110-sa-translation-subsystem.md
 12K	docs/adr/ADR-108-inbox-karte-panel-redesign.md
 12K	docs/adr/ADR-107-sa-analytics-agent-a-customer-priority.md
 12K	docs/adr/ADR-101-sa-quotation-invoice-generation.md
 12K	docs/adr/ADR-095-sa-ssot-two-backbone-architecture.md
 12K	docs/adr/ADR-090-products-central-unification.md
 12K	docs/adr/ADR-080-monitoring-vps-separation.md
 12K	docs/adr/ADR-072-tenant-schema-prefix-enforcement.md
 12K	docs/adr/ADR-067-design-token-enforcement.md
 12K	docs/adr/ADR-054-lp-hubspot-style-restructure.md
 12K	docs/adr/ADR-051-claude-pipeline-full-automation.md
 12K	docs/adr/ADR-050-release-pr-workflow-standardization.md
 12K	docs/adr/ADR-046-lp-redesign.md
 12K	docs/adr/ADR-038-qa-smoke-suite.md
 12K	docs/adr/ADR-026_meta_messages_message_id_text.md
 12K	docs/adr/ADR-015.md
 12K	docs/adr/ADR-011.md
8.0K	docs/specs/branch-operations
8.0K	docs/specs/README.md
8.0K	docs/runbooks/weekly-stale-tasks.md
8.0K	docs/runbooks/tenant-deletion-operations.md
8.0K	docs/runbooks/shingo-cc-bot-setup.md
8.0K	docs/runbooks/meta-domain-verification-dns.md
8.0K	docs/runbooks/funnel-pr1-deploy.md
8.0K	docs/runbooks/discord-gateway-operations.md
8.0K	docs/runbooks/claude-monitor-access.md
8.0K	docs/handoff/w2-pr3-frontend
8.0K	docs/handoff/w2-conversion-by-attribute
8.0K	docs/handoff/txn-flow-ben2
8.0K	docs/handoff/translation-model-flashlite
8.0K	docs/handoff/translation-double-lang-a1
8.0K	docs/handoff/translation-context-batch
8.0K	docs/handoff/ticket-hide-start
8.0K	docs/handoff/tenant001-investigation
8.0K	docs/handoff/tenant-deletion-cache-fix
8.0K	docs/handoff/submenu-link-mode
8.0K	docs/handoff/sop-gate-self-protect
8.0K	docs/handoff/smoke-health-retry
8.0K	docs/handoff/sidebar-hover-suppression
8.0K	docs/handoff/send-guard-phase-a
8.0K	docs/handoff/send-error-permission-denied
8.0K	docs/handoff/send-error-message-log
8.0K	docs/handoff/select-control-pilot
8.0K	docs/handoff/select-arrow-padding
8.0K	docs/handoff/schedule-settings-i18n-fix
8.0K	docs/handoff/schedule-nowrap-sticky
8.0K	docs/handoff/schedule-8issues-fix
8.0K	docs/handoff/sa-foundation-recon-audit
8.0K	docs/handoff/sa-03-change-billing
8.0K	docs/handoff/sa-02-r1-r2
8.0K	docs/handoff/review-tenant-password-reset-guard
8.0K	docs/handoff/review-mail-discord-mention
8.0K	docs/handoff/revert-schedule-to-2443
8.0K	docs/handoff/restore-weekly-advisor-defensive
8.0K	docs/handoff/remove-review-locale-en
8.0K	docs/handoff/remove-chromatic-ci
8.0K	docs/handoff/release-pr-migration-manifest
8.0K	docs/handoff/prod1-image-volume-cleanup
8.0K	docs/handoff/process-artifacts-adr-precision-fix
8.0K	docs/handoff/paypal-test-hint-i18n
8.0K	docs/handoff/paypal-invoicer-view-url
8.0K	docs/handoff/password-hash-removal
8.0K	docs/handoff/page-header-sticky-revert
8.0K	docs/handoff/node24-actions
8.0K	docs/handoff/node-exporter-port-fix
8.0K	docs/handoff/nginx-reload-total-autocount
8.0K	docs/handoff/modal-select-fields
8.0K	docs/handoff/mobile-nav-css
8.0K	docs/handoff/migration-timestamp-dup-guard
8.0K	docs/handoff/migration-full-dryrun
8.0K	docs/handoff/migration-080-fix
8.0K	docs/handoff/migrate-lead-edit-select
8.0K	docs/handoff/migrate-edit-pages-select
8.0K	docs/handoff/merge-back-adr128-sa02-stage3
8.0K	docs/handoff/mc-hub-submenu
8.0K	docs/handoff/main-deploy-stamp
8.0K	docs/handoff/inventory-ui-tweaks
8.0K	docs/handoff/inventory-release-date-tab
8.0K	docs/handoff/inventory-aggregated-main
8.0K	docs/handoff/incident-20260613-password-hash
8.0K	docs/handoff/inbox-header-ui
8.0K	docs/handoff/hotfix-css-mediaq-safari
8.0K	docs/handoff/gate-process-artifacts-precision-fix
8.0K	docs/handoff/gate-message-clarify
8.0K	docs/handoff/gate-diff-3dot
8.0K	docs/handoff/gate-dangerous-require-approval
8.0K	docs/handoff/fx-rate-ssot
8.0K	docs/handoff/foundation-f3-channel-control
8.0K	docs/handoff/foundation-f2-country-control
8.0K	docs/handoff/foundation-f1-countries-master
8.0K	docs/handoff/fix-z-drawer-close
8.0K	docs/handoff/fix-ticket-ch-bot-overwrite
8.0K	docs/handoff/fedex-smoke-switch
8.0K	docs/handoff/fedex-pr-a3
8.0K	docs/handoff/fedex-pr-a2
8.0K	docs/handoff/fedex-pickup-carriercod-fix
8.0K	docs/handoff/fedex-page-redesign-pr-a
8.0K	docs/handoff/fedex-modal-connection
8.0K	docs/handoff/fedex-label-validation-wizard
8.0K	docs/handoff/fedex-guide-ui-fixes
8.0K	docs/handoff/fedex-guide-step1-7-cta
8.0K	docs/handoff/fedex-guide-fullscreen
8.0K	docs/handoff/fedex-guide-b1
8.0K	docs/handoff/fedex-etd-ux-improvements
8.0K	docs/handoff/fedex-etd-step1-guide
8.0K	docs/handoff/etd-guide-substep-spacing-nav
8.0K	docs/handoff/etd-guide-step1-advance
8.0K	docs/handoff/etd-guide-scroll-fix
8.0K	docs/handoff/etd-guide-screenshot-fix
8.0K	docs/handoff/etd-guide-screenshot-cachebust
8.0K	docs/handoff/etd-guide-remove-back
8.0K	docs/handoff/etd-guide-nav-left
8.0K	docs/handoff/etd-guide-nav-center
8.0K	docs/handoff/etd-guide-layout
8.0K	docs/handoff/etd-guide-header-inline
8.0K	docs/handoff/etd-guide-detail-center
8.0K	docs/handoff/dryrun-2pass
8.0K	docs/handoff/discord-ticket-lang-refactor
8.0K	docs/handoff/discord-ticket-gateway-visibility
8.0K	docs/handoff/discord-oauth-rls-fix
8.0K	docs/handoff/discord-gateway-db-url
8.0K	docs/handoff/dev-workflow-desk-check
8.0K	docs/handoff/design-site-smoke-autoblock
8.0K	docs/handoff/deploy-timeout-fix
8.0K	docs/handoff/delete-carrier-credentials-reset-tenant-ctx
8.0K	docs/handoff/deal-removal-track-a
8.0K	docs/handoff/datatable-step2
8.0K	docs/handoff/datatable-batch5
8.0K	docs/handoff/datatable-batch4
8.0K	docs/handoff/datatable-batch1
8.0K	docs/handoff/data-deletion-admin-lockdown
8.0K	docs/handoff/d2-own-inventory-provisioning
8.0K	docs/handoff/d1-inventory-v2-converge
8.0K	docs/handoff/crm-hub-submenu
8.0K	docs/handoff/conv-logs-direction-guard
8.0K	docs/handoff/condition-vocab-ssot
8.0K	docs/handoff/common-6roles-stage-a
8.0K	docs/handoff/codex-schedule-i18n-main
8.0K	docs/handoff/cleanup-feature-demo
8.0K	docs/handoff/auth-lockout-bystander-fix
8.0K	docs/handoff/audit-log-coverage-medium
8.0K	docs/handoff/audit-log-coverage-high
8.0K	docs/handoff/analytics-rls-session-fix
8.0K	docs/handoff/analytics-priority-prospects
8.0K	docs/handoff/advisor-weekly
8.0K	docs/handoff/advisor-phase1
8.0K	docs/handoff/adr090-pr3-fk-remap
8.0K	docs/handoff/adr-127-phase2c
8.0K	docs/handoff/adr-127-phase2
8.0K	docs/handoff/adr-127-phase1
8.0K	docs/handoff/adr-127
8.0K	docs/handoff/adr-126-error-handling
8.0K	docs/handoff/adr-126-contact-optional
8.0K	docs/handoff/admin-bypass-removal
8.0K	docs/handoff/_templates
8.0K	docs/adr/FEATURE-INDEX.md
8.0K	docs/adr/ADR-SA-19-verification-gates.md
8.0K	docs/adr/ADR-145-public-products-force-rls.md
8.0K	docs/adr/ADR-144-ui-component-governance.md
8.0K	docs/adr/ADR-143-send-guard.md
8.0K	docs/adr/ADR-137-nginx-config-deploy-reliability.md
8.0K	docs/adr/ADR-137-fedex-etd-paperless-trade.md
8.0K	docs/adr/ADR-136-cc-bot-github-identity.md
8.0K	docs/adr/ADR-135-release-stowaway-prevention.md
8.0K	docs/adr/ADR-134-design-site-delivery.md
8.0K	docs/adr/ADR-133-nginx-resolver-proxy-pass-variable.md
8.0K	docs/adr/ADR-132-background-tasks-tenant-context.md
8.0K	docs/adr/ADR-125-fedex-rates-stage1.md
8.0K	docs/adr/ADR-123-carrier-integrator-provider.md
8.0K	docs/adr/ADR-121-sop-process-artifacts-gate.md
8.0K	docs/adr/ADR-119-lead-channels-and-lead-merge.md
8.0K	docs/adr/ADR-113-two-mode-dev-flow.md
8.0K	docs/adr/ADR-110-karte-reference-alignment.md
8.0K	docs/adr/ADR-109-leads-status-ssot-immutable-codes.md
8.0K	docs/adr/ADR-099-sa-inventory-model.md
8.0K	docs/adr/ADR-093-inventory-table-product-master-redesign.md
8.0K	docs/adr/ADR-089-deprecate-customers-unify-to-companies.md
8.0K	docs/adr/ADR-086-parallel-development-standardization.md
8.0K	docs/adr/ADR-082-generator-executor-codex-fallback.md
8.0K	docs/adr/ADR-082-deploy-skip-migrations-on-frontend-only.md
8.0K	docs/adr/ADR-081-remove-design-review-gate.md
8.0K	docs/adr/ADR-081-monitoring-vps-final-operational-design.md
8.0K	docs/adr/ADR-079-claude-code-monitoring-access.md
8.0K	docs/adr/ADR-078-vps-runner-registration.md
8.0K	docs/adr/ADR-077-github-actions-metrics.md
8.0K	docs/adr/ADR-076-claude-md-hierarchy.md
8.0K	docs/adr/ADR-074-worktree-agent-enforcement.md
8.0K	docs/adr/ADR-068-platform-brand-asset-policy.md
8.0K	docs/adr/ADR-065-asyncpg-prepared-statement-cache-disable.md
8.0K	docs/adr/ADR-063-inbox-page-level-tab-header.md
8.0K	docs/adr/ADR-060-rename-company-to-client-profile.md
8.0K	docs/adr/ADR-055-playwright-mcp-setup.md
8.0K	docs/adr/ADR-053-claude-pipeline-decision-parsing-fix.md
8.0K	docs/adr/ADR-045-migration-055-deploy-automation.md
8.0K	docs/adr/ADR-041-meta-page-connection-fallback-implementation.md
8.0K	docs/adr/ADR-040-claude-code-guardrail-investigation.md
8.0K	docs/adr/ADR-037-meta-page-connection-investigation.md
8.0K	docs/adr/ADR-034-tenant-migration-automation.md
8.0K	docs/adr/ADR-028-screencast-tenant-isolation.md
8.0K	docs/adr/ADR-027-ui-internationalization.md
8.0K	docs/adr/ADR-025_meta_integration_operational_hardening.md
8.0K	docs/adr/ADR-024_meta_integration_structural_fix.md
8.0K	docs/adr/ADR-023_staff_lifecycle_three_layer_sync.md
8.0K	docs/adr/ADR-012-what-how-separation.md
4.0K	docs/specs/doc-parent-child
4.0K	docs/runbooks/secret-rotation.md
4.0K	docs/runbooks/review-tenant-operations.md
4.0K	docs/runbooks/monitoring-step7-vps.md
4.0K	docs/runbooks/images
4.0K	docs/handoff/txn-flow-ben1b
4.0K	docs/handoff/send-guard-phase-b
4.0K	docs/handoff/sa-02-stage1
4.0K	docs/handoff/modal-xl-test-data
4.0K	docs/handoff/go-record-transcription-draft.md
4.0K	docs/handoff/discord-integration
4.0K	docs/handoff/agent-guardrails
4.0K	docs/ai-agents/task-template.md
4.0K	docs/ai-agents/agent-roles.md
4.0K	docs/ai-agents/aeon-routing.md
4.0K	docs/ai-agents/aeon-release.md
4.0K	docs/ai-agents/aeon-operation.md
4.0K	docs/ai-agents/aeon-delivery.md
4.0K	docs/ai-agents/adr-template.md
4.0K	docs/adr/ADR-SA-18-app-db-least-privilege.md
4.0K	docs/adr/ADR-999-pipeline-test.md
4.0K	docs/adr/ADR-149-submenu-ssot-link-mode.md
4.0K	docs/adr/ADR-148-fx-rate-ssot.md
4.0K	docs/adr/ADR-147-common-6roles-standardization.md
4.0K	docs/adr/ADR-143-inventory-public-v2-canonical.md
4.0K	docs/adr/ADR-142-tenant-provisioning-completeness.md
4.0K	docs/adr/ADR-141-inbound-translation-entry.md
4.0K	docs/adr/ADR-140-mobile-nav-bottom-tabs.md
4.0K	docs/adr/ADR-139-funnel-kgi-dashboard-frontend.md
4.0K	docs/adr/ADR-138-remove-password-hash.md
4.0K	docs/adr/ADR-137-v-company-stats-ssot-filter.md
4.0K	docs/adr/ADR-136-company-stats-ssot.md
4.0K	docs/adr/ADR-134-invoice-billing-display-name.md
4.0K	docs/adr/ADR-130-nginx-reload-policy.md
4.0K	docs/adr/ADR-129-github-actions-node-version-tracking.md
4.0K	docs/adr/ADR-129-fedex-label-validation-wizard.md
4.0K	docs/adr/ADR-129-audit-log-coverage-medium.md
4.0K	docs/adr/ADR-128-audit-log-coverage-high.md
4.0K	docs/adr/ADR-127-auth-lockout-bystander-fix.md
4.0K	docs/adr/ADR-124-sop-health-reporter.md
4.0K	docs/adr/ADR-122-realpage-modal-standardization.md
4.0K	docs/adr/ADR-120-status-presentation-ssot.md
4.0K	docs/adr/ADR-116-main-deploy-stamp.md
4.0K	docs/adr/ADR-115-deploy-safety.md
4.0K	docs/adr/ADR-112-workflow-redesign-design-origin-flow.md
4.0K	docs/adr/ADR-111-runner-label-isolation.md
4.0K	docs/adr/ADR-106-sa-multitenant-policy.md
4.0K	docs/adr/ADR-105-sa-trouble-refund.md
4.0K	docs/adr/ADR-104-sa-payment-confirmation-status-pnl.md
4.0K	docs/adr/ADR-103-sa-shipping-dispatch-timing.md
4.0K	docs/adr/ADR-102-sa-order-management.md
4.0K	docs/adr/ADR-1000-external-api-smoke-mandatory.md
4.0K	docs/adr/ADR-100-sa-ingestion-analysis-pipeline.md
4.0K	docs/adr/ADR-098-sa-multi-channel-identity-resolution.md
4.0K	docs/adr/ADR-097-sa-customer-registration-form.md
4.0K	docs/adr/ADR-096-sa-customer-master-crm-data-model.md
4.0K	docs/adr/ADR-094-sales-management-page.md
4.0K	docs/adr/ADR-094-crm-definition-and-deals-reorganization.md
4.0K	docs/adr/ADR-093-sales-management-page.md
4.0K	docs/adr/ADR-092-deploy-concurrency-control.md
4.0K	docs/adr/ADR-087-hub-shell-layout-standard.md
4.0K	docs/adr/ADR-085-supplier-prompts.md
4.0K	docs/adr/ADR-084-pokeapi-dex-import.md
4.0K	docs/adr/ADR-083-tcg-type-master.md
4.0K	docs/adr/ADR-076-pipeline-efficiency-improvements.md
4.0K	docs/adr/ADR-075-github-secrets-only-policy.md
4.0K	docs/adr/ADR-073-design-system-kgi-rubric.md
4.0K	docs/adr/ADR-071-orders-nav-placement.md
4.0K	docs/adr/ADR-070-grafana-monitoring-integration.md
4.0K	docs/adr/ADR-069-uptime-kuma-activation.md
4.0K	docs/adr/ADR-066-dark-mode-logo-invert.md
4.0K	docs/adr/ADR-064-inbox-meta-exact-replica.md
4.0K	docs/adr/ADR-061-inbox-meta-style-layout.md
4.0K	docs/adr/ADR-059-lead-nav-unified-tabs.md
4.0K	docs/adr/ADR-058-remove-contacts-from-sidebar.md
4.0K	docs/adr/ADR-044-ci-health-recovery.md
4.0K	docs/adr/ADR-036-tenant-schema-integrity.md
4.0K	docs/adr/ADR-033-app-theme-switching.md
4.0K	docs/adr/ADR-032.md
4.0K	docs/adr/ADR-022.md
4.0K	docs/adr/ADR-020.md
4.0K	docs/adr/ADR-019.md
4.0K	docs/adr/ADR-019-screencast-test-data-creation.md
4.0K	docs/adr/ADR-018_instagram_send_endpoint_fix.md
4.0K	docs/adr/ADR-018.md
4.0K	docs/adr/ADR-017.md
4.0K	docs/adr/ADR-016.md
4.0K	docs/adr/ADR-013.md
4.0K	docs/adr/ADR-009-discord-gateway.md
  0B	docs/runbooks/external-evidence
  0B	docs/handoff/agent-complete-design
```

## 調査4: ルール遵守と停止の実態

### docs/ai-agents/evidence-registry.md の抽出
```text
EV-20260701-001	1078	lessons: "①マージ方式はリポ設定に合わせる(squash禁止→merge commit)。②GO発行者は英字表記(Shingo/shingo-ops)、ひらがな不可。③正本等の危険ファイル変更PRは『触るファイル:』『削除するファイル:』欄を平打ち(行頭空白・ダッシュなし)で必須。④マージ直後にMERGEDを実測してから台帳DONE・片付け(成否未確認で進むと未完なのにDONEの記録齟齬が発生)。"
EV-20260701-002	1089	lessons: "①CC が別worktree・本店へ勝手に台帳/GO を書き込む逸脱を複数回。生ログ照合と名指し1ファイル撤去で対処。②GO記録はしんご自筆のみ・代筆厳禁を再確認。③main宛PRのブランチ名は release/ または hotfix/ が必須（fix/ は関所で弾かれる）。"
EV-20260702-002	1119	lessons: "①CCが赤テストを無断で自己修正しコミットまで進める逸脱（修正内容は事後diff検証で採用可だったが手順違反）。②カードの停止条件は肯定形で一義に書く（『〜以外なら停止』は読み違いを誘発、2回停止）。③pushを飛ばしたPR作成は Head sha blank で失敗する。④机は AGENT_WORKTREE_BASE(~/worktrees)配下が必須、worktree move で中身ごと移設可能。"
EV-20260702-003	1132	## 2026-07-03: develop廃止・現在地スナップショット（複数セッションの誤報告防止）（EV-20260703-001）
EV-20260703-001	1146	scope: "develop廃止計画の進捗に関する全争点の一括実測。別セッションからの『未完』報告2件（worktree検問main未発火・完了記録なし・new-worktree.sh develop起点）が古いmainを見た誤判定だったため、照合基準を1枚に固定する。"
EV-20260703-002	1160	problem: "エージェントが読む案内書がdevelop前提のままで、並行セッションが古い世界観で動く（誤報告2件の真因・EV-20260703-001）。"
EV-20260703-007	1249	follow_up: "便3（段階・成約の自動判定）へ。本セッションのCC違反2件（無断migration修正push・無断PR本文上書き）はB+C便のgenerator.md改定入力として扱う"
```

| id | 行番号 | 1行要約 |
|---|---:|---|
| EV-20260701-001 | 1078 | lessons: "①マージ方式はリポ設定に合わせる(squash禁止→merge commit)。②GO発行者は英字表記(Shingo/shingo-ops)、ひらがな不可。③正本等の危険ファイル変更PRは『触るファイル:』『削除するファイル:』欄を平打ち(行頭空白・ダッシュなし)で必須。④マージ直後にMERGEDを実測してから台帳DONE・片付け(成否未確認で進むと未完なのにDONEの記録齟齬が発生)。" |
| EV-20260701-002 | 1089 | lessons: "①CC が別worktree・本店へ勝手に台帳/GO を書き込む逸脱を複数回。生ログ照合と名指し1ファイル撤去で対処。②GO記録はしんご自筆のみ・代筆厳禁を再確認。③main宛PRのブランチ名は release/ または hotfix/ が必須（fix/ は関所で弾かれる）。" |
| EV-20260702-002 | 1119 | lessons: "①CCが赤テストを無断で自己修正しコミットまで進める逸脱（修正内容は事後diff検証で採用可だったが手順違反）。②カードの停止条件は肯定形で一義に書く（『〜以外なら停止』は読み違いを誘発、2回停止）。③pushを飛ばしたPR作成は Head sha blank で失敗する。④机は AGENT_WORKTREE_BASE(~/worktrees)配下が必須、worktree move で中身ごと移設可能。" |
| EV-20260702-003 | 1132 | ## 2026-07-03: develop廃止・現在地スナップショット（複数セッションの誤報告防止）（EV-20260703-001） |
| EV-20260703-001 | 1146 | scope: "develop廃止計画の進捗に関する全争点の一括実測。別セッションからの『未完』報告2件（worktree検問main未発火・完了記録なし・new-worktree.sh develop起点）が古いmainを見た誤判定だったため、照合基準を1枚に固定する。" |
| EV-20260703-002 | 1160 | problem: "エージェントが読む案内書がdevelop前提のままで、並行セッションが古い世界観で動く（誤報告2件の真因・EV-20260703-001）。" |
| EV-20260703-007 | 1249 | follow_up: "便3（段階・成約の自動判定）へ。本セッションのCC違反2件（無断migration修正push・無断PR本文上書き）はB+C便のgenerator.md改定入力として扱う" |

### design-partner.md §6 の教訓（由来した失敗の種類）
- 実行役の自己修正禁止: テスト赤・エラー時に実行役（CC）が指示なく修正・コミットへ進んではならない。停止して生ログを提示し、修正の採否はPlannerがdiff検証で決める（2026-07-02 維持の仕組み便: 無断修正は内容妥当でも手順違反）。
- カードの停止条件は肯定形で一義に書く: 「〜以外なら停止」等の否定形は読み違いによる誤停止を生む（2026-07-02 同便で2回発生）。「Xを含む❌が在る場合のみ停止、他は続行」の形で書く。
- 影響範囲recon のgrepは拡張子で絞らない: エージェント案内書（.md）も実行系として対象（2026-07-02 案内書4枚未更新が並行セッション誤報告2件の真因）。
- 動線・手順を変える便は案内書の同時更新までがスコープ: コードと案内書の時間差＝矛盾窓を作らない。
- 検証・報告には実測時の origin/main SHA を併記: SHAなしの「未完」報告は鮮度不明として扱う（EV-20260703-001）。
- エージェントにとって案内書は実行される命令: 案内書の古さはコードのバグと同格（EV-20260703-001）。
- PR本文の「削除するファイル」欄はプレーンなパスのみ書く。注記を同じ行に付けると関所の照合が落ちる（2026-07-02 PR #2734で実測）。
- 指示文が参照する成果物は、実装役が到達できる場所に置く（チャット本文に全文同梱するか、リポジトリ内パスを指す）。到達不能な原本参照は独自実装か停止を招く（2026-07-02 PR #2735で実測）。
- 実装役が作成した関所スクリプト等は、配布原本との逐語一致をdiffで検収する。善意の書き直しが検出漏れを生む（2026-07-02 PR #2735で実測: 独自版は「## 2.」形式の重複を素通し）。

### track-record.md 現時点の集計
ROWS 4
A {'○': 3, '×': 1}
B {'○': 3, '（マージ後に記入）': 1}
C {'○': 3, '△': 1}
D {'−': 4}
E {'−': 2, '○': 2}
LABELS {'設計': 2, '実装（記憶圧縮）': 1}

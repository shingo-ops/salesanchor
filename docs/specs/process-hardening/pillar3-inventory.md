# 柱3-c 既存複製一覧（機械生成・手で編集しない）

> この文書は何か（専門用語なしの1行）:
> テストが本番のテーブル定義をコピーしている箇所の全件リスト。片付けの進み具合を数える表。

親: docs/specs/process-hardening/kgi.md（柱3-c）
設計: docs/specs/process-hardening/design-pillar3.md
生成元SHA: f6bb82694d2906cc649e4b9f96086ac6c9e51356
生成: python3 scripts/check_test_schema_dup.py --write-inventory <sha> docs/specs/process-hardening/pillar3-inventory.md
照合: python3 scripts/check_test_schema_dup.py --check-inventory docs/specs/process-hardening/pillar3-inventory.md <sha>

合計: 29ファイル・71件

## 一覧

| ファイル | 行 | 元の表記 | 束ねた名前 |
|---|---|---|---|
| backend/tests/rls_bootstrap.py | 78 | public.tenants | public.tenants |
| backend/tests/rls_bootstrap.py | 103 | public.users | public.users |
| backend/tests/test_502_paths.py | 64 | tenant_meta_config | tenant_meta_config |
| backend/tests/test_502_paths.py | 86 | staff | staff |
| backend/tests/test_502_paths.py | 93 | audit_logs | audit_logs |
| backend/tests/test_adr119_backfill_source_guard.py | 66 | {expr}.leads | leads |
| backend/tests/test_adr119_backfill_source_guard.py | 80 | {expr}.lead_channels | lead_channels |
| backend/tests/test_analytics.py | 899 | conversation_logs | conversation_logs |
| backend/tests/test_analytics.py | 925 | data_access_events | data_access_events |
| backend/tests/test_analytics_conversion_by_attribute_rls.py | 42 | {expr}.leads | leads |
| backend/tests/test_analytics_conversion_by_attribute_rls.py | 75 | {expr}.leads | leads |
| backend/tests/test_channel_type_control.py | 52 | tenant_006.leads | leads |
| backend/tests/test_channel_type_control.py | 103 | tenant_006.channel_masters | channel_masters |
| backend/tests/test_channel_type_control.py | 114 | tenant_006.tenant_sales_form_options | tenant_sales_form_options |
| backend/tests/test_channel_type_control.py | 126 | tenant_006.lead_sales_form_selections | lead_sales_form_selections |
| backend/tests/test_conv_backbone_ben1b.py | 25 | leads | leads |
| backend/tests/test_conv_backbone_ben1b.py | 44 | lead_channels | lead_channels |
| backend/tests/test_conv_backbone_ben1b.py | 57 | tenant_meta_config | tenant_meta_config |
| backend/tests/test_conv_backbone_ben1b.py | 69 | tenants | tenants |
| backend/tests/test_conv_backbone_ben1b.py | 77 | conversation_logs | conversation_logs |
| backend/tests/test_conversations.py | 72 | leads | leads |
| backend/tests/test_conversations.py | 111 | meta_messages | meta_messages |
| backend/tests/test_countries_master.py | 204 | {expr}.country_probe | country_probe |
| backend/tests/test_discord_d2.py | 36 | tenant_discord_config | tenant_discord_config |
| backend/tests/test_discord_inbox.py | 46 | leads | leads |
| backend/tests/test_discord_inbox.py | 98 | meta_messages | meta_messages |
| backend/tests/test_discord_inbox.py | 123 | staff | staff |
| backend/tests/test_discord_oauth.py | 78 | tenant_discord_config | tenant_discord_config |
| backend/tests/test_discord_oauth_rls.py | 42 | public.tenants | public.tenants |
| backend/tests/test_discord_oauth_rls.py | 65 | {expr}.audit_logs | audit_logs |
| backend/tests/test_inventory_aggregated.py | 160 | public.suppliers | public.suppliers |
| backend/tests/test_inventory_aggregated.py | 175 | public.products | public.products |
| backend/tests/test_inventory_aggregated.py | 203 | public.inventory | public.inventory |
| backend/tests/test_message_image_send.py | 45 | leads | leads |
| backend/tests/test_message_image_send.py | 97 | meta_messages | meta_messages |
| backend/tests/test_message_image_send.py | 124 | tenant_meta_config | tenant_meta_config |
| backend/tests/test_message_image_send.py | 146 | staff | staff |
| backend/tests/test_message_send.py | 63 | leads | leads |
| backend/tests/test_message_send.py | 115 | meta_messages | meta_messages |
| backend/tests/test_message_send.py | 142 | tenant_meta_config | tenant_meta_config |
| backend/tests/test_message_send.py | 164 | staff | staff |
| backend/tests/test_messages.py | 61 | leads | leads |
| backend/tests/test_messages.py | 114 | meta_messages | meta_messages |
| backend/tests/test_messages.py | 140 | staff | staff |
| backend/tests/test_meta_channels.py | 72 | tenant_meta_config | tenant_meta_config |
| backend/tests/test_meta_channels.py | 95 | staff | staff |
| backend/tests/test_meta_channels.py | 675 | tenant_997.tenant_meta_config | tenant_meta_config |
| backend/tests/test_meta_oauth_endpoints.py | 76 | tenant_meta_config | tenant_meta_config |
| backend/tests/test_meta_oauth_endpoints.py | 98 | staff | staff |
| backend/tests/test_meta_oauth_endpoints.py | 105 | audit_logs | audit_logs |
| backend/tests/test_outbound_draft_send.py | 41 | leads | leads |
| backend/tests/test_outbound_draft_send.py | 93 | meta_messages | meta_messages |
| backend/tests/test_outbound_draft_send.py | 121 | tenant_meta_config | tenant_meta_config |
| backend/tests/test_outbound_draft_send.py | 143 | staff | staff |
| backend/tests/test_outbound_draft_send.py | 151 | outbound_translation_drafts | outbound_translation_drafts |
| backend/tests/test_outbound_draft_send.py | 169 | audit_logs | audit_logs |
| backend/tests/test_outbound_draft_send.py | 182 | message_translations | message_translations |
| backend/tests/test_own_inventory.py | 39 | own_inventory | own_inventory |
| backend/tests/test_priority_prospects_pg_rls.py | 203 | {expr}.leads | leads |
| backend/tests/test_products_cross_tenant_fk.py | 70 | {expr}.quote_items | quote_items |
| backend/tests/test_rls_carrier_credentials.py | 83 | {expr} | {expr} |
| backend/tests/test_rls_invariants.py | 57 | {expr} | {expr} |
| backend/tests/test_rls_tenant_meta_config.py | 92 | {expr}.staff | staff |
| backend/tests/test_rls_tenant_meta_config.py | 100 | {expr}.tenant_meta_config | tenant_meta_config |
| backend/tests/test_rls_translation_glossary.py | 69 | {expr} | {expr} |
| backend/tests/test_tenant_schema_integrity.py | 71 | {schema}.sample_table | sample_table |
| backend/tests/test_webhook_instagram.py | 49 | leads | leads |
| backend/tests/test_webhook_instagram.py | 93 | meta_messages | meta_messages |
| backend/tests/test_webhook_instagram.py | 122 | tenant_meta_config | tenant_meta_config |
| backend/tests/test_webhook_instagram.py | 145 | tenants | tenants |
| backend/tests/test_webhook_instagram.py | 161 | lead_channels | lead_channels |

## 集計（束ねた名前ごと・多い順）

| 名前 | 件数 |
|---|---|
| leads | 13 |
| tenant_meta_config | 10 |
| staff | 9 |
| meta_messages | 7 |
| audit_logs | 4 |
| lead_channels | 3 |
| {expr} | 3 |
| conversation_logs | 2 |
| public.tenants | 2 |
| tenant_discord_config | 2 |
| tenants | 2 |
| channel_masters | 1 |
| country_probe | 1 |
| data_access_events | 1 |
| lead_sales_form_selections | 1 |
| message_translations | 1 |
| outbound_translation_drafts | 1 |
| own_inventory | 1 |
| public.inventory | 1 |
| public.products | 1 |
| public.suppliers | 1 |
| public.users | 1 |
| quote_items | 1 |
| sample_table | 1 |
| tenant_sales_form_options | 1 |

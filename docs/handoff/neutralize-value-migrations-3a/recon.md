# recon：値を書く migration の無効化 PR-3a（ADR-1007 段3）

この文書は何か（1行）: 毎デプロイで値を書き戻していた migration のうち、先に無効化できる 18 本について、外した文の場所と試験結果を、行番号つきの事実だけで記録したもの。

親: ADR-1007（PR #3985。決定2「既存の値を書く migration は無効にする」）。設計: docs/handoff/neutralize-value-migrations-3a/design.md
実測時の origin/main: 57090e457（2026-10-07）。以下の行番号は、この SHA の migrations/ のもの。
土台: 段2（PR #4015、release/tests-own-seed-data）を merge した上に積んでいる。#4015 より先にはマージしない。
既存 ADR の検索: 機能キーワード（migration seed、ADR-155、neutralize）で docs/adr/ と docs/adr/FEATURE-INDEX.md を引いた結果、直接の ADR は ADR-155（migration で値を操作しない）。前例は PR #3544（2026-09-18。データだけの 13 本を無効化）。

## 1. 前例と形

- 前例（#3544）: migrations/20260604_040000_seed_tcg_products_8series.sql:27-35。ヘッダを残し、「NEUTRALIZED」の印のコメントと、NOTICE だけの DO ブロック。前例の 13 本は、すべて DDL を持たないファイル。
- 本 PR の形: 全体が値だけのファイルは前例どおり。構造と値が混ざったファイルは、DDL と存在確認を一字も変えず、値を書く文だけを「-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07)」のコメントと NOTICE に置き換えた。

## 2. 外した文（ファイル:行、origin/main 57090e457）

| ファイル | 外した範囲 | 外した文 | 残した構造 |
|---|---|---|---|
| migrations/20260620_010000_create_inventory_aggregation_rules.sql | :25-35 | INSERT 4 行＋ON CONFLICT DO UPDATE（updated_at = NOW()） | :15-23 CREATE TABLE |
| migrations/20260621_010000_create_countries_master.sql | :31-226 | INSERT 190 行＋ON CONFLICT DO UPDATE | :6-29（表・索引・関数・トリガー）、:228 COMMENT |
| migrations/085_create_tcg_type_master.sql | :48-56 | INSERT の EXECUTE（6 種別） | :32-42 CREATE TABLE、:44-46 INDEX、:58-以降 関数・トリガー・COMMENT、CHECK 撤廃 |
| migrations/086_seed_additional_tcg_types.sql | :11-36 | DO ブロック全体（6 種別の INSERT） | なし（データだけのファイル） |
| migrations/20260611_100000_create_channel_masters.sql | :71-82 | デフォルトチャネル 6 行の INSERT の EXECUTE | :30-33 のセレクタを含むループ、CREATE TABLE、RLS、ポリシー（:66-69）、:84-89 |
| migrations/20260611_010000_fix_owner_role_color.sql | :27-62 | DO ブロック全体（roles の color を更新） | なし |
| migrations/20260616_000000_fix_tcg_type_dedup.sql | :20-67 | DO ブロック全体（products.tcg_type の更新、type_master の削除） | なし |
| migrations/20260928_100000_delete_skip_condition_rules.sql | :13-14 | DELETE FROM public.knowledge_rules | なし |
| migrations/20260924_040000_seed_knowledge_extraction_vocab.sql | :5-30、:42-54 | knowledge_rules への INSERT 2 本（block_delimiter 17 語、status_keyword 4 語） | なし（:32-40 の経緯のコメントは残した） |
| migrations/20260923_030000_promote_remaining_tcg_tables.sql | :42-50、:78-86、:117-125 | tenant_004 からのコピーの DO ブロック 3 つ | CREATE TABLE 3 つ、COMMENT、INDEX、完了の NOTICE |
| migrations/20260927_120000_add_max_age_hours_setting.sql | :2-4 | INSERT INTO public.tcg_distribution_settings | なし |
| migrations/20260602_020000_add_products_tcg_type.sql | :9-23 | UPDATE 7 本（tcg_type の補完） | :7 ALTER TABLE ADD COLUMN、:25 CREATE INDEX |
| migrations/20260603_000000_add_products_product_kind.sql | :19-20 | UPDATE（product_kind の補完） | :16-17 ALTER TABLE ADD COLUMN |
| migrations/20260604_020000_backfill_products_shipping_defaults.sql | :17-37 | DO ブロック全体（products の item・hs_code・material の補充） | なし |
| migrations/20260605_000000_add_products_display_order.sql | :19-20 | UPDATE（display_order の補完） | :12-18、:21-22（存在確認と ALTER TABLE ADD COLUMN） |
| migrations/20260916_130000_work_id_not_null.sql | :8-32 | Phase 1（work_id_old_uuid からの work_id 補完の UPDATE を含む IF） | Phase 2（:34-47。NOT NULL の付与と RAISE EXCEPTION） |
| migrations/20260604_090000_create_link_templates.sql | :22-29 | INSERT 5 チャネル | :13-20 CREATE TABLE |
| migrations/20260613_020000_funnel_close_reasons.sql | :118-144 | 成約 7 行・失注 8 行の INSERT の EXECUTE 2 つ | :24-117（ループ、deals の存在確認、CREATE TABLE close_reasons、deals の列の変更）、:146-149 |

- 新テナントへの影響の確認: migrations/20260613_020000_funnel_close_reasons.sql:37-44 は、deals 表の無いテナントを CONTINUE で飛ばす。backend/app/services/tenant.py:425-426 に「deals テーブルDDL・インデックス・FK は新規テナント作成定義から除去済み（2026-07-28）」とある。tenant.py:810 は close_reasons の表を作るが、行は入れない。新しく作るテナントは、この migration から close_reasons を得ていない（今日の時点）。
- セレクタ行: migrations/20260611_100000_create_channel_masters.sql:32 は先頭に空白 8 つ。ファイルの該当 5 行（:30-34）を cat -vet で確認し、無効化の前後で同じ（この PR の差分に :30-34 は含まれない）。
- DDL の削除が無いことの確認: 差分の削除行に、CREATE TABLE・CREATE INDEX・CREATE TRIGGER・ALTER TABLE・ADD COLUMN・COMMENT ON・SET NOT NULL・SET DEFAULT の文字列を含む行が 0 件（grep の結果）。

## 3. 試験（追加と結果）

### 3-1 追加した試験（backend/tests/test_value_migrations_neutralized.py）
- 静的（DB 不要）: 無効化した 18 本それぞれに「印の文」があり、コメントを除いた本文に INSERT INTO／UPDATE … SET／DELETE FROM／ON CONFLICT が無い（18 本のパラメータ試験）。セレクタ行が 1 回だけ残る試験 1 本。
- PG（RLS_ADMIN_DATABASE_URL か TEST_PG_URL があるとき。1 つのトランザクションで確かめて巻き戻す）:
  - 国: JP の dial_code を '+9999' に変えて migration 全文を流しても、'+9999' のまま（以前は DO UPDATE で '+81' に戻した）。
  - 集計ルール: Case の price_tolerance を 1234 に変えて migration 全文を流しても、1234 のまま（以前は DO UPDATE で 1000 に戻した）。
  - type_master: union_arena と xross_stars を消して 085・086 を流しても、再挿入されない。表は残る。
- 無効化の前（元の migration）に対する RED: 18 failed, 1 passed, 3 skipped。

### 3-2 SQLite・DB なし（backend で pytest -n0 --no-cov -q）
- 基準（#4015 の先頭、6 ファイル: test_seed_data、test_countries_master、test_inventory_aggregation、test_inventory_aggregated、test_rls_bootstrap_ordering、test_lead_country_control）: 23 passed, 9 skipped
- 変更後（上に test_value_migrations_neutralized を加えた 7 ファイル）: 42 passed, 12 skipped（+19 passed、+3 skipped は新しい PG 試験）

### 3-3 ローカルの使い捨て PostgreSQL 16（CI と同じ環境変数。GITHUB_ACTIONS=true、RLS_ADMIN_DATABASE_URL、RLS_TEST_DATABASE_URL。TEST_PG_URL は未設定）
- 関連 14 ファイル（test_value_migrations_neutralized を先頭に、段2 の 12 ファイルと test_seed_data）: 3 failed, 239 passed, 1 skipped in 88.65s。失敗は test_tcg_condition_review.py::test_raw_update_waits_for_review_source_lock、test_tcg_work_matching_integration.py::test_condition_note_lock_timeout、test_tcg_work_matching_integration.py::test_interrupted_recovery_lock_timeout_and_settings。この 3 本は、段2（#4015）の基準でも失敗していた同じ名前。
- ファイルの順序が違う比較: 段2 の基準は 6 failed, 214 passed, 1 skipped（test_value_migrations_neutralized を含まない順）。上の 3 failed との差（test_rls_bootstrap_ordering 2 本と test_products_tcg_type_fk 1 本）は、実行順の違い（新しいファイルを先頭に置いたこと）によるものか、本 PR の変更によるものかを分けるため、次の同順の比較を行った。
- 同じファイル・同じ順序（test_countries_master、test_lead_country_control、test_inventory_aggregation、test_inventory_aggregated、test_rls_bootstrap_ordering、test_products_tcg_type_fk）で、元の migration と無効化後を比較:
  - 元の migration: 3 failed, 22 passed, 1 skipped in 4.83s
  - 無効化後: 3 failed, 22 passed, 1 skipped in 4.95s
  - 失敗した 3 本は同じ名前（test_rls_bootstrap_schema_and_migration_share_one_transaction[None]、同 [tenant_9951]、test_products_tcg_type_validation_and_fk_enforcement_under_tenant_006）
- 先頭に置いた実行で上の 3 本が失敗しなかった原因は調べていない（未確認）。

### 3-4 他の検査
- ruff check（backend/tests/test_value_migrations_neutralized.py）: All checks passed。

## 4. 未確認
- CI での結果（Migration SQL Test が変更した migration を 2 回流す、全件ドライラン、pytest）。
- 無効化した 18 本のうち、ローカルの PG で実際に流れていないファイル（20260611_010000、20260928_100000、20260924_040000、20260923_030000、20260927_120000、20260604_020000、20260916_130000、20260604_090000、20260613_020000）。静的な試験で値を書く文が無いことは確認したが、SQL として流した確認は CI に任せる。
- 本番への影響（この PR のマージ・デプロイ後に、本番で max(updated_at) が動かないことを読み取りで確認する。デプロイ前は未実施）。
- 段2（#4015）のマージ前にこの PR をマージすると、試験が seed を失って落ちる見込み（#4015 に依存する 4 本: 20260620_010000、20260621_010000、085、086）。

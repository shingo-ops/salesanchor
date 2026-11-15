---
mode: handoff
---
# 前調査 5-0：本番の会社ごとの形（Opus・読み取り専用の道・2026-11-15）

- 道: reader 鍵（`ssh -i ~/.ssh/salesanchor-reader ... ubuntu@49.212.137.46`、1回1文、TSV、200行で黙って切れるため一覧は `LIMIT 150`）。
- 台本: scratchpad の `prod-shape.sh`（その1）・`prod-shape2.sh`（その2）。生の出力: `/tmp/CC報告ファイル/deploy-lock-1113/prod-shape/*.txt`（手元のみ）。
- `information_schema.tables` / `columns` / `sequences` は見出しだけで中身が0行だった（reader の権限で絞られる。`pg_catalog` は絞られない）。数は `pg_catalog` で取った。

## 1. 会社の一覧
`pg_namespace` の `tenant_%`: tenant_001・tenant_003・tenant_004・tenant_005・tenant_006 の5つ（tenant_002 は無い）。

## 2. 種類ごとの数（`pg_class.relkind`）

| 会社 | 表 r | 索引 i | 連番 S | ビュー v | 列（表の、消した列を除く） |
|---|---|---|---|---|---|
| tenant_001 | 109 | 328 | 74 | 2 | 1271 |
| tenant_003 | 79 | 256 | 72 | 2 | 1006 |
| tenant_004 | 101 | 256 | 69 | 2 | 1172 |
| tenant_005 | 79 | 243 | 69 | 2 | 1006 |
| tenant_006 | 79 | 242 | 69 | 2 | 1006 |

その1の数（`pg_constraint`・`pg_trigger`（内部を除く）・`pg_policies`・`pg_proc`）:

| 会社 | 制約 | トリガ | 方針 | 関数 |
|---|---|---|---|---|
| tenant_001 | 337 | 28 | 64 | 15 |
| tenant_003 | 264 | 28 | 64 | 15 |
| tenant_004 | 275 | 28 | 64 | 15 |
| tenant_005 | 262 | 28 | 64 | 15 |
| tenant_006 | 262 | 29 | 64 | 15 |

## 3. 003・005・006 の違い
- 表の名前: 3社に共通の表は 79（3社とも 79 なので、表の名前は完全に一致）。列の数も3社とも 1006。
- 索引: 003 にあって 005 に無い 13 件 = idx_invoices_status, idx_leads_assigned_to, idx_leads_status, leads_tenant_id_lead_code_key, idx_products_category, idx_products_status, idx_po_status, idx_po_supplier, idx_quotes_status, idx_shipping_rates_lookup, idx_team_members_team, idx_team_members_user, idx_user_roles_user。006 はこの 13 件に加えて idx_bots_status も無い。005・006 にあって 003 に無い索引は 0 件。
- 制約: 003 にあって 005 に無い 2 件 = fk_orders_invoice（外部キー）・leads_tenant_id_lead_code_key（一意）。
- トリガ: 006 にあって 003 に無い 1 件 = lead_playbook の trg_lead_playbook_updated_at。
- 権限: 5社とも、全ての表に権限の設定がある（`relacl IS NULL` の表は 0）。中身の比べ合わせはまだしていない。

## 4. tenant_001・tenant_004 だけにある表（P7 の本番側）
- tenant_001 にあって 003 に無い 30 表: analysis_results, analysis_run_snapshots, analysis_runs, audit_log, condition_aliases, conditions, extraction_attempts, extraction_items, extraction_jobs, import_job_messages, import_jobs, item_corrections, item_notes, product_exclude_keywords, product_search_keywords, products_logistics, source_messages, supplier_channels, tcg_distribution_settings, tcg_distribution_targets, tcg_major_categories, tcg_manufacturers, tcg_product_categories, tcg_product_import_jobs, tcg_product_import_rows, tcg_series, tenant_suppliers, unit_aliases, units, unparsed_lines。
- tenant_004 にあって 003 に無い 22 表: item_notes, products_logistics, tcg_manufacturers, tcg_series, tcg_suppliers, tcg_unit_evidence_rules, tenant_suppliers, unparsed_lines と、日付つきの控え 14 表（product_exclude_keywords_bak_20260901/0904/0904b/0907, product_search_keywords_bak_20260901/0904/0904b, tcg_products_bak_20260901/0903/0904/0904b/0905/0906/0907）。
- repo 側（5-0a の `recon-5-0a/p07.md`）との突き合わせ（下の 4-1・4-2）。

### 4-1. tenant_001 の 30 表
- 27 表は移行で作られた物: `20260906_120000_create_tcg_tables_t001.sql`（登録 :794）の 27 表のうち 25 表と、`20260906_130100_create_tcg_product_import_history_t001.sql`（:810）の 2 表。
- 残り 3 表のうち 2 表は「全社を回す形」の移行で作られた: extraction_attempts（`20260914_010000_tcg_extraction_attempts.sql:188` `FOR target IN SELECT nspname FROM pg_namespace WHERE nspname LIKE 'tenant_%'`・:198 で作る。登録 :858）、import_job_messages（`20260910_010000_tcg_import_message_links.sql:6-7` で `^tenant_[0-9]{3}$` を回し、:9-10 で import_jobs と source_messages がある会社だけ・:21 で作る。登録 :834）。どちらも「前提の表がある会社だけ」に作るため、tenant_001 にだけある。
- 残り 1 表 tenant_suppliers は、`migrations/` に作る文も名前を変える文も無い（`git grep -nE 'RENAME TO tenant_suppliers|tenant_suppliers'` の当たりは試験3本の `ALTER TABLE IF EXISTS ... tcg_suppliers RENAME TO tenant_suppliers` と `docs/handoff/fix-supplier-table-name/design.md:21`「適用済み」の記述と ai_cloud のビューの一覧だけ）。手で名前を変えた表。
- 移行で作ったのに今の tenant_001 に無い表: tcg_products・tcg_suppliers（`20260906_120000` :144・:165）。本番の読み取り（`p7-check.txt`）で tenant_001 に両方とも無い。tcg_suppliers は上の名前の変更で tenant_suppliers になった物（設計文書の記述による・本番の履歴は確かめていない）。tcg_products が無くなった移行はまだ特定していない。
- `20260917_000000_create_analysis_rule_tables.sql` の 13 表は、今の tenant_001 に無い（30 表の一覧に無い）。`20260921_010000_drop_analysis_rule_tables.sql`（:934）が消す物と名前が合う（中身の照合は 5-0b）。

### 4-2. tenant_004 の 22 表
- 7 表は移行で作られた: item_notes・products_logistics・tcg_suppliers・unparsed_lines（`20260831_110000` :341・:189・:111・:358）、tcg_manufacturers・tcg_series（`20260902_110000` :53・:39）、tcg_unit_evidence_rules（`20260903_120000` :25）。
- tenant_suppliers: 4-1 と同じく手で名前を変えた表。ただし tenant_004 には tcg_suppliers も残っている（`p7-check.txt`: tenant_004 に tcg_suppliers と tenant_suppliers の両方）。
- 日付つきの控え 14 表: `migrations/` のコメント（例 `20260904_160000_tcg_magazine_promo_products_t004.sql:6-8`・`20260905_010000_tcg_pokemon_master_batch1_t004.sql:8-10`）に名前と件数が書かれているが、作る文はコメント以外の本文に無い（`git grep -nE '_bak' -- 'migrations/2026090*.sql'` からコメント行を除くと0件）。手で作った控え。
- `20260831_110000` の残り 11 表などは今の tenant_004 に無い。`20260921_050000`（:947）・`20260921_130000`（:959）が消す物と名前が合うかは 5-0b で照合する。

### 4-3. 分かったこと（事実）
- 会社ごとの形の違いは、(1) 会社を名指しして作る移行、(2) 「前提の表がある会社だけ」に作る移行、(3) 手で足した物（名前の変更1種・控え14表）の3つから来ている。
- (3) は移行の記録から作り直せない。済んだ移行を飛ばす直しでは、(3) を「移行が作る形」に数えない。

## 5. まだ分からないこと
- 003 の 13 索引・2 制約が、移行の登録にある文から来たのか、手で足された物か（repo の文と突き合わせる。5-0b）。
- 会社ごとの権限の中身の違い。
- tenant_001 の tcg_products が無くなった移行の特定。
- 会社を新しく作る道（`backend/app/services/tenant.py`）で作った形と 003 の違い（P1。使い捨ての DB で 5-0b）。

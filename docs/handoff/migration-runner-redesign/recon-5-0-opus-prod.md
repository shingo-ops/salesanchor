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
- 移行で作ったのに今の tenant_001 に無い表: tcg_products・tcg_suppliers（`20260906_120000` :144・:165）。本番の読み取り（`p7-check.txt`）で tenant_001 に両方とも無い。tcg_suppliers は上の名前の変更で tenant_suppliers になった物（設計文書の記述による・本番の履歴は確かめていない）。tcg_products は `20260915_010000` が消した（4-2b）。
- `20260917_000000_create_analysis_rule_tables.sql` の 13 表は、今の tenant_001 に無い（30 表の一覧に無い）。`20260921_010000_drop_analysis_rule_tables.sql`（:934）が消す物と名前が合う（4-2b）。

### 4-2. tenant_004 の 22 表
- 7 表は移行で作られた: item_notes・products_logistics・tcg_suppliers・unparsed_lines（`20260831_110000` :341・:189・:111・:358）、tcg_manufacturers・tcg_series（`20260902_110000` :53・:39）、tcg_unit_evidence_rules（`20260903_120000` :25）。
- tenant_suppliers: 4-1 と同じく手で名前を変えた表。ただし tenant_004 には tcg_suppliers も残っている（`p7-check.txt`: tenant_004 に tcg_suppliers と tenant_suppliers の両方）。
- 日付つきの控え 14 表: `migrations/` のコメント（例 `20260904_160000_tcg_magazine_promo_products_t004.sql:6-8`・`20260905_010000_tcg_pokemon_master_batch1_t004.sql:8-10`）に名前と件数が書かれているが、作る文はコメント以外の本文に無い（`git grep -nE '_bak' -- 'migrations/2026090*.sql'` からコメント行を除くと0件）。手で作った控え。
- 移行で作ったのに今の tenant_004 に無い表は、消す移行と名前が合う（4-2b）。

### 4-2b. 消す移行との照合（Opus・repo を読んだ。2026-11-15）
- tenant_001 の tcg_products: `20260915_010000_drop_tcg_products_phase2c.sql`（登録 :868）が消す。`:32-39` で `nspname LIKE 'tenant_%'` を全部回し、`:72` 以降で「まだ指している外部キーが0本」のときだけ `:86` 付近の `DROP TABLE %I.tcg_products` を流す。`20260906_120000` の `:38` に「tcg_products が不在 = Phase 2c で意図的に DROP 済み」とあり、作り直さない形になっている。
- tenant_004 の照合: `20260831_110000` は 18 表、`20260902_110000` は 4 表、`20260903_120000` は 1 表を作る（`CREATE TABLE IF NOT EXISTS %I.<名>` の文）。合わせて 23 表のうち 15 表（`20260831_110000` の 13 表と `20260902_110000` の tcg_major_categories・tcg_product_categories）を `20260921_050000`（:947）・`20260921_130000`（:959）が消し、tcg_products を `20260915_010000` が消す。残りは item_notes・products_logistics・tcg_suppliers・unparsed_lines・tcg_manufacturers・tcg_series・tcg_unit_evidence_rules の 7 表。4-2 の「移行で作られた 7 表」と名前が全部合う。
- 解析の規則の 13 表: `20260917_000000_create_analysis_rule_tables.sql`（登録 :883）が tenant_001 に作り（`:15` `_schema TEXT := 'tenant_001'`）、`20260921_010000_drop_analysis_rule_tables.sql`（登録 :934）が public・tenant_004・tenant_001 から消す。作る 13 表と消す 13 表の名前は全部同じ。
- 気づいたこと: 登録の順は「:883 で作る → :934 で消す」。`20260917_000000` の `:21` は会社のスキーマがあるかだけを見る。本番反映のたびに 13 表を作って消している疑いがある（まだ確かめていない。5-0b の P8 で、:883 の直後と :934 の直後に表の数を数えて確かめる）。

### 4-3. 分かったこと（事実）
- 会社ごとの形の違いは、(1) 会社を名指しして作る移行、(2) 「前提の表がある会社だけ」に作る移行、(3) 手で足した物（名前の変更1種・控え14表）の3つから来ている。
- (3) は移行の記録から作り直せない。済んだ移行を飛ばす直しでは、(3) を「移行が作る形」に数えない。

## 5. P3：制約・関数・連番・権限の差（台本 `prod-shape3.sh`・生の出力 `prod-shape3-summary.txt`）
- 制約: 005 にあって 003 に無い制約は 0 件。同じ名前で定義が違う制約（003 と 005、会社名を伏せて比べた）も 0 件。
- 制約の名前の違い（005 と 006）: 同じ3本の外部キーの名前が違う。005 = `companies_lead_id_fkey`・`contacts_lead_id_fkey`・`products_supplier_default_id_fkey`（自動でついた名前）／006 = `fk_companies_lead`・`fk_contacts_lead`・`fk_products_supplier_default`（`backend/app/services/tenant.py:443-457`・`:1009-1012` が付ける名前）。005 の名前がどの文から来たかはまだ確かめていない。
- 関数: 5社とも同じ 15 個の名前。本文（会社名を伏せて比べた）も 003 と 005・006 で違いは 0 件。
- 連番: 003 にだけ `customer_code_seq`・`deal_code_seq`・`lead_code_seq` がある（`migrations/003_add_phase1_tenant_tables.sql:26-28` が作る物）。005・006 の間の差は 0 件。
- 表の権限: 003 と 005 は全ての表で同じ（違う表 0 件）。006 は全 79 表に `qa_tenant006_rw=arwdD` が足されている。それ以外は 005 と同じ。
- `qa_tenant006_rw` を与える文は `migrations/`・`backend/` に無い（`git grep` の当たりは `docs/` の4ファイルだけ）。手で足した権限。
- スキーマの権限: 5社とも `jarvis=UC`・`salesanchor_app=U`・`ai_unmask_owner=U`。006 だけ `qa_tenant006_rw=U` が多い。
- 既定の権限: public と5社とも、jarvis が作る表に `salesanchor_app=arwd`、連番に `salesanchor_app=rU`。006 だけ `qa_tenant006_rw` の分が多い。
- 持ち主: 5社とも全ての表が jarvis。

## 6. まだ分からないこと（5-0b の結果で更新・2026-11-15）
- 会社を新しく作る道で作った形と 003 の違い: 分かった。ひな形だけで表 53（003 は 79）・差 691/30/72 件（`recon-5-0b/p01.md:29-43`・`:87-102`）。
- 003 の 13 索引・2 制約・3 連番: ひな形にも CI の全件ドライランの後にも無い（`recon-5-0b/p01.md:45-68`）。連番 3 は `migrations/003_add_phase1_tenant_tables.sql:26-28` が作る物（§5）。13 索引・2 制約がどの文から来たかは、まだ確かめていない。
- 005 の自動の外部キー名がどの文から来たか: まだ確かめていない。
- 解析の規則の 13 表を反映のたびに作って消しているか（§4-2b）: 使い捨ての DB では ○（`recon-5-0b/p08.md:77-87`）。本番では確かめていない。

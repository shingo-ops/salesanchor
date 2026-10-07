# 毎回実行リストの確認（run_py 26 本、テナントごとのビュー 3 本、ADR-1005 の C 22 件）

この文書は何か（1行）: ledger の「毎回実行リスト」に載せてよいものがあるかを、実物（コード）を読んで 1 件ずつ確かめた結果の記録（事実だけ）。

親: docs/handoff/migration-ledger/design.md、recon.md。基準: origin/main 768c69d71 を土台にしたブランチ release/migration-ledger（2026-10-07）。
機械で取った生の数: scripts/migrate_*.py の本文と、そこから読み込む migrations/*.sql を、文字の照合で数えた（DML＝INSERT INTO／UPDATE … SET／DELETE FROM、DDL＝CREATE／ALTER／DROP／RENAME。コメントを除く）。

## 0. 判断の基準と結論

- (a) 毎回の再適用が必要か: 効果が 1 回の適用で持続せず、デプロイのたびに適用し直さないと失われるもの。構造（CREATE ... IF NOT EXISTS、ADD COLUMN IF NOT EXISTS など）は 1 回で持続する。新テナントに届かないのは、ひな形の遅れ（段階1）の問題で、毎回実行の理由にはしない。
- (b) 値を書くか（ADR-155）: INSERT／UPDATE／DELETE で行の値を書く。上書き型（既存の値を変える）と補充型（無い行・空の値だけ埋める）を区別する。
- 載せる条件: (a) がコードで証明できたものだけ。
- **結論【事実】: (a) がコードで証明できたものは 0 件。毎回実行リスト scripts/migration-ledger/every-run.list は 0 件のまま。**
- ADR-1005 の C 22 件【事実】: main の docs/handoff/migration-runner-redesign/recon.md:50 に「C 毎回の実行に意味があるもの：22」と件数だけがある。名前の一覧は、recon.md・design.md（同フォルダ）・docs/adr/ADR-1005-migration-run-once-ledger.md のどこにも無い（recon.md:113「生の調査結果（317 行の分類表）は設計担当の作業領域に保存」）。したがって、22 件との 1 件ずつの照合は【未確認】。以下は、実物から 22 件とは独立に確かめたもの。

## 1. run_py の 26 本（scripts/run_all_migrations.sh の登録行）

構造だけ（値を書かない）のもの: DB に持続する構造を足す。(a)=いいえ、(b)=いいえ。

| 登録行 | スクリプト（読み込む SQL） | 内容（file:line） | (a) 毎回の再適用 | (b) 値を書く | リスト |
|---|---|---|---|---|---|
| :80 | scripts/migrate_meta.py（migrations/012_add_meta_tenant_tables.sql） | 全テナントに meta_messages 等の表を作る。scripts/migrate_meta.py:60-61 でテナントごとに適用 | 持続する構造。いいえ | いいえ（DDL 6、DML 0） | 載せない |
| :111 | scripts/migrate_meta_inbox_phase1d.py（040、042） | 040 は tenant_meta_config の作成（DDL 8）。**042 は値を書く（下）** | 040: いいえ | 042: はい（下） | 載せない |
| :112 | scripts/migrate_meta_inbox_phase1d_sprint4.py（041） | 全テナントの meta_messages に列と索引（DDL 3） | いいえ | いいえ | 載せない |
| :113 | scripts/migrate_meta_page_routing.py（043、044） | 043 は public.meta_page_routing の作成（DDL 3）。**044 は値を書く（下）** | 043: いいえ | 044: はい（下） | 載せない |
| :114 | scripts/migrate_meta_messages_page_id.py（045） | 全テナントの meta_messages に page_id 列と索引 | いいえ | いいえ | 載せない |
| :117 | scripts/migrate_adr015_lead_foundation.py（046） | leads・customer_contact_channels に列、lead_playbook の作成（DDL 31） | いいえ | いいえ | 載せない |
| :135 | scripts/migrate_adr021_sprint2_financials.py（047） | 全テナントに order_financials と索引と RLS（DDL 10） | いいえ | いいえ | 載せない |
| :136 | scripts/migrate_adr021_sprint3_shipping.py（048） | order_shipping_details（DDL 11） | いいえ | いいえ | 載せない |
| :137 | scripts/migrate_adr021_sprint4_purchase.py（049） | order_purchase_details（DDL 11） | いいえ | いいえ | 載せない |
| :138 | scripts/migrate_adr021_sprint5_commissions.py（050） | staff.is_employee 列、tenant_commission_settings（DDL 18）。migrations/050_add_commissions.sql | いいえ | いいえ | 載せない |
| :142 | scripts/migrate_meta_messages_message_id_to_text.py（052） | meta_messages.message_id を VARCHAR(100) から TEXT に変更（ALTER 1）。型は 1 回で持続する | いいえ | いいえ | 載せない |
| :150 | scripts/migrate_009_phase4_tenant_tables.py（009） | 全テナントに Phase 4 の表（DDL 15） | いいえ | いいえ | 載せない |
| :151 | scripts/migrate_011_phase5_tenant_tables.py（011） | 全テナントに shifts・erp_sync_logs（DDL 8） | いいえ | いいえ | 載せない |
| :166 | scripts/migrate_074_rename_english_name_to_nickname.py | leads.english_name があるときだけ `RENAME COLUMN english_name TO nickname`（:87）。1 回で持続し、列が無ければ何もしない（:61-71 の存在確認） | いいえ | いいえ | 載せない |

構造と値が混ざる（読み込む SQL が値を書く）ものと、Python が直接値を書くもの:

| 登録行 | スクリプト → 値を書く文（file:line） | 種類 | (a) 毎回の再適用 | (b) 値を書く | リスト |
|---|---|---|---|---|---|
| :111 | scripts/migrate_meta_inbox_phase1d.py → migrations/042_seed_meta_inbox_permissions.sql:30-35 `INSERT INTO public.permissions … ON CONFLICT (key) DO NOTHING`（4 キー）。:42- のテナントのループで owner/admin に付与 | 補充型 | 未確認（コードに、毎回でないと失われる効果が無い。付与は ON CONFLICT DO NOTHING） | はい | 載せない |
| :113 | scripts/migrate_meta_page_routing.py → migrations/044_create_meta_page_routing_trigger.sql:82-90 `INSERT INTO public.meta_page_routing … ON CONFLICT (tenant_id, config_id) DO UPDATE SET …`（tenant_meta_config からの backfill）。:78 のトリガーは `AFTER INSERT OR UPDATE OR DELETE ON {schema}.tenant_meta_config` で同期を持続させる（:44-64） | 上書き型（backfill）。トリガーは構造 | 未確認（トリガーが同期を持続させるので、backfill の毎回の再適用は証明できない。新テナントにトリガーが無い点はひな形の遅れ） | はい | 載せない |
| :139 | scripts/migrate_adr021_remove_confirmed_status.py → migrations/051_remove_confirmed_status.sql:45-48 `UPDATE {schema}.orders SET status = 'pending' WHERE status = 'confirmed'` | 上書き型 | 未確認（'confirmed' を書く側が残っているかを読んでいない） | はい | 載せない |
| :147 | scripts/migrate_adr041_granted_scopes.py → migrations/055_add_granted_scopes.sql:31-33 `UPDATE {schema}.tenant_meta_config SET granted_scopes = '[…]' WHERE granted_scopes IS NULL`（ALTER :27-28 は構造） | 補充型 | 未確認（NULL の行だけ） | はい | 載せない |
| :154 | scripts/migrate_inventory_sprint1.py → migrations/056_add_suppliers_type_and_promote_public.sql:125-144 `INSERT INTO public.suppliers … ON CONFLICT (supplier_code) DO NOTHING`（テナントの仕入元を public に昇格）、migrations/063_tenant_rbac_extensions.sql:34-51（public.permissions の INSERT）、:84-88（role_permissions） | 補充型 | 未確認 | はい | 載せない |
| :155 | scripts/migrate_inventory_sprint2.py → migrations/064_add_users_is_super_admin.sql:54-59 `UPDATE public.users SET is_super_admin = TRUE WHERE email IN ('…')`（列追加 :32-37 は構造）。migrations/065_seed_central_admin_permissions.sql:38- `INSERT INTO public.permissions … ` | 064: **上書き型**（毎デプロイ、指定のメールのユーザーを super_admin に戻す。人が外しても戻る）。065: 補充型 | 未確認（064 は「戻る」効果があるが、それを意図した毎回の再適用かは、コードの記述からは証明できない） | はい | 載せない |
| :156 | scripts/migrate_inventory_sprint5_to_7.py → migrations/066_add_tenant_llm_budgets_notification_dedupe.sql:45-51（public.tenant_llm_budgets の INSERT ON CONFLICT DO NOTHING）、067_add_inbound_review_version_and_permissions.sql:43-52（permissions） | 補充型 | 未確認 | はい | 載せない |
| :157 | scripts/migrate_inventory_sprint8.py → migrations/069_create_tenant_profile.sql:55-64（permissions）、:100（tenant_profile の初期行）、:114-117（role_permissions） | 補充型 | 未確認 | はい | 載せない |
| :158 | scripts/migrate_inventory_sprint9.py → migrations/070_add_spreadsheet_phase.sql:75-77 `INSERT INTO public.tenant_settings (tenant_id, spreadsheet_phase) SELECT id, 'A' FROM public.tenants ON CONFLICT (tenant_id) DO NOTHING`、:96-101（permissions） | 補充型（'A' の行を、無いテナントに入れる） | 未確認。**段3b の 080（phase 'A' を 'B' にする UPDATE）の無効化との関係**: 070 が行の無いテナントに 'A' を入れ、080 が無いと 'B' に直らない（#4012 が新テナントの作成時に 'B' の行を入れるので、行の無いテナントは出ない見込み） | はい | 載せない |
| :165 | scripts/migrate_073_lead_status.py:60、:63、:66 `UPDATE {schema}.leads SET status = '商談中' WHERE status = '案件化'` ほか 2 本 | 上書き型（旧い値を新しい値へ） | 未確認（旧い値を書く側が残っているかを読んでいない） | はい | 載せない |
| :171 | scripts/migrate_20260620_080000_calendar_category_backfill.py:112-115 `UPDATE {schema}.calendar_events … WHERE id = :id`（:88 `WHERE category IS NULL` の行だけ） | 補充型 | 未確認 | はい | 載せない |
| :336 | scripts/migrate_adr109_status_codes.py:182 `UPDATE {schema}.leads SET status = :new_val, updated_at = NOW() WHERE status = :old_val`（:124 で DISTINCT status を読み、日本語・旧い英語の値を不変の英字コードへ） | 上書き型 | 未確認（旧い値を書く側が残っているかを読んでいない） | はい | 載せない |
| :342 | scripts/migrate_adr119_lead_channels_backfill.py:92、:116 `INSERT INTO {schema}.lead_channels … ON CONFLICT (platform, external_id) DO NOTHING`（leads.source、discord_user_id から） | 補充型 | 未確認（:58-59、:70-71 は存在確認。leads.source は廃止済み） | はい | 載せない |
| :451 | scripts/migrate_20260621_020000_backfill_lead_country.py:94 `UPDATE {schema}.leads SET country = :country WHERE id = :id`（:76 で country が NULL でない全行を走査し、ISO alpha-2 に正規化。解決できない値は NULL にする）。backend/tests/test_lead_country_control.py が backfill_schema を import している | 上書き型（解決不能は NULL） | 未確認（backend/app/routers/leads.py:152-170 が書き込みを alpha-2 に検証するので、再適用の必要は証明できない） | はい | 載せない |

数（登録行 26）: 構造だけ 12 本、値を書く（読み込む SQL か Python 自体が書く）もの 14 本。:111 と :113 は構造と値の両方を含み、上の 2 つの表の両方に出る（12 + 14 = 26）。

## 2. テナントごとのビュー 3 本（v_company_stats）

【事実】registered 順: :292 migrations/20260604_100000_create_company_stats_view.sql、:374 migrations/20260611_130000_fix_v_company_stats_deleted_at.sql、:404 migrations/20260612_120000_fix_company_stats_ssot.sql。3 本とも、テナントのループ（`nspname ~ '^tenant_\d+$'`）の中で同じビュー名 v_company_stats を作る。

| ファイル | 内容（file:line） | (a) 毎回の再適用 | (b) 値を書く | リスト |
|---|---|---|---|---|
| 20260604_100000_create_company_stats_view.sql | companies と deals の両方がある（:30-33、:40-42）テナントにだけ `CREATE OR REPLACE VIEW %I.v_company_stats`（:61-62） | いいえ（ビューの定義は持続する。後のファイルが上書きする） | いいえ（DML 0） | 載せない |
| 20260611_130000_fix_v_company_stats_deleted_at.sql | 同上（companies と deals が要る。:27-35、:48-50）の `CREATE OR REPLACE VIEW`（:68-69） | いいえ | いいえ | 載せない |
| 20260612_120000_fix_company_stats_ssot.sql | companies があるテナント（:31-33）に `DROP VIEW IF EXISTS %I.v_company_stats CASCADE`（:42）のあと `CREATE VIEW %I.v_company_stats`（:44-45） | いいえ（最後の定義が残る。毎回 DROP して作り直すのは、1 回で足りる定義を繰り返しているだけ） | いいえ | 載せない |

- 【事実】backend/app/services/tenant.py に v_company_stats は 0 件（grep）。新テナントには、ひな形に取り込むまで届かない（段階1。毎回実行の理由ではない）。
- 【事実】3 本のうち後ろの 1 本が、前 2 本の定義を DROP して作り直す。登録順どおりに 1 回ずつ実行すれば、最後の定義が残る。
- 【事実】20260612_120000 は、毎デプロイ `DROP VIEW … CASCADE` するので、ledger で 1 回にすると、この毎回の DROP が止まる（意図した変化）。

## 3. 新しく分かったこと（段3 の範囲外の値の書き込み）

【事実】段3（ADR-1007、SQL の 27 本）は run_py を対象にしていない。run_py が読み込む SQL と Python 自体に、毎デプロイ届く値の書き込みが 14 件（登録行）ある（§1 の下の表）。とくに次の 3 つは上書き型。
- migrations/064_add_users_is_super_admin.sql:54-59（指定のメールの users.is_super_admin を TRUE に戻す）。
- migrations/044_create_meta_page_routing_trigger.sql:82-90（public.meta_page_routing を tenant_meta_config から DO UPDATE で上書き）。
- scripts/migrate_20260621_020000_backfill_lead_country.py:94、scripts/migrate_adr109_status_codes.py:182、scripts/migrate_073_lead_status.py:60-66、migrations/051_remove_confirmed_status.sql:45-48（旧い値を新しい値へ。解決不能は NULL）。
これらは、ledger で「1 回だけ」になれば、毎回の書き戻しは止まる（ADR-1005 段階2）。ledger が入る前は、毎デプロイ届く。段3 のような無効化の対象にするかは、設計担当の判断（本書では決めない）。

## 4. 未確認
- ADR-1005 の C 22 件の名前（分類表が repo に無い）。
- (a)「未確認」の各行: 旧い値や NULL を書き戻す側（アプリや別の入口）が今も残っているか。残っていれば、毎回の再適用に意味がある可能性がある。1 件ずつ、書き込み側のコードを読む必要がある。
- run_py が、ADMIN_DATABASE_URL で実行されること（scripts/lib/migration_ledger.sh の ledger_exec_py）以外の実行時の挙動。実際に実行はしていない。

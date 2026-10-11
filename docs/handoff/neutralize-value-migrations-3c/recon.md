# recon：run_py が毎デプロイ届ける値の書き込みの無効化 PR-3c（ADR-1007 段3）

この文書は何か（1行）: scripts/run_all_migrations.sh の run_py が毎デプロイ流す SQL と Python の「値を書く文」14 件について、外した場所と本番との比較と試験結果を、行番号つきの事実だけで記録したもの。

親: ADR-1007（PR #3985。決定2）、ADR-155。設計: docs/handoff/neutralize-value-migrations-3c/design.md。super admin の手順: docs/handoff/neutralize-value-migrations-3c/super-admin-bootstrap.md
実測時の origin/main: 85122fb40（2026-10-07。#3998 のマージ後）。以下の「変更前」の行番号は、この SHA のもの（対象 17 ファイルは 768c69d71 から変更なし）。
既存 ADR の検索: 機能キーワード（migration seed、is_super_admin、ADR-155）で docs/adr/ と docs/adr/FEATURE-INDEX.md を引いた結果、直接の ADR は ADR-155 と ADR-1007（PR #3985）、前例は PR #3544、段3a（#4018）、段3b（#4017）。
base: origin/main（積んでいない）。段3a（#4018）・3b（#4017）とファイルの重複なし。

## 1. 外した値の書き込み（ファイル:行、変更前）

| 登録行 | ファイル | 外した範囲 | 外した文 | 残した構造 |
|---|---|---|---|---|
| :111 | migrations/042_seed_meta_inbox_permissions.sql | :29-85 | permissions 4 キーの INSERT、オーナー／システム管理者への付与 | なし（データだけ） |
| :113 | migrations/044_create_meta_page_routing_trigger.sql | :81-95 | meta_page_routing への既存行の backfill（DO UPDATE） | 同期の関数とトリガー（:76-79 ほか） |
| :139 | migrations/051_remove_confirmed_status.sql | :41-52 | orders の 'confirmed' を 'pending' へ UPDATE | なし |
| :147 | migrations/055_add_granted_scopes.sql | :30-33 | granted_scopes の NULL への補充 UPDATE | :27-28 ALTER、:35-36 COMMENT |
| :154 | migrations/056_add_suppliers_type_and_promote_public.sql | :99-154 | テナントの suppliers から public.suppliers へのコピー | 表・制約・トリガー |
| :154 | migrations/063_tenant_rbac_extensions.sql | :33-51、:53-100 | permissions 4 キーの INSERT、オーナー／システム管理者への付与 | :102 以降（purchase_orders の snapshot 列） |
| :155 | migrations/064_add_users_is_super_admin.sql | :44-59 | users.is_super_admin を TRUE に戻す UPDATE | :32-37 ALTER・索引、:39-42 COMMENT |
| :155 | migrations/065_seed_central_admin_permissions.sql | :38-63 | permissions 6 キーの INSERT | なし |
| :156 | migrations/066_add_tenant_llm_budgets_notification_dedupe.sql | :39-51 | tenant_llm_budgets の tenant 4・6 の行の INSERT | 列追加・COMMENT |
| :156 | migrations/067_add_inbound_review_version_and_permissions.sql | :42-52 | permissions 2 キーの INSERT | 列追加・COMMENT |
| :157 | migrations/069_create_tenant_profile.sql | :54-64、:98-102、:106-122 | permissions 2 キー、tenant_profile の既定行、オーナー／システム管理者への付与 | 表の作成、CHECK 制約 |
| :158 | migrations/070_add_spreadsheet_phase.sql | :74-77、:93-101 | tenant_settings の phase 'A' の行、phase.switch の INSERT | 列追加、トリガー、COMMENT |
| :165 | scripts/migrate_073_lead_status.py | `async def main()`（:36-80） | leads.status の UPDATE 3 本（:60、:63、:66） | `if __name__ == "__main__":` と登録 |
| :171 | scripts/migrate_20260620_080000_calendar_category_backfill.py | `async def main()`（:127-） | calendar_events.category の補充 | 同上。`resolve_backfill_category`（:43）、`backfill_schema`（:62）は残す |
| :336 | scripts/migrate_adr109_status_codes.py | `async def main()`（:86-268） | leads.status のコード変換 UPDATE（:182）と、想定外の値でのデプロイの停止（:136、:262 の `sys.exit(1)`） | 同上 |
| :342 | scripts/migrate_adr119_lead_channels_backfill.py | `async def main()`（:150-） | lead_channels への INSERT の呼び出し | 同上。`backfill_schema`（:50）は、試験が import するので残す |
| :451 | scripts/migrate_20260621_020000_backfill_lead_country.py | `async def main()`（:102-） | leads.country の正規化 UPDATE の呼び出し | 同上。`backfill_schema`（:42）は、試験が import するので残す |

- 形（SQL）: ヘッダを残し、値を書く文だけを「-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07)」のコメントと NOTICE に置き換えた（段3a と同じ）。差分の削除行に、CREATE／ALTER／ADD COLUMN／COMMENT ON／DROP TRIGGER を含む行は 0 件（grep の結果）。
- 形（Python）: 前例なし（scripts に NEUTRALIZED は 0 件）。`main()` の本文を、印のコメントと print 1 行に置き換えた。`if __name__ == "__main__": asyncio.run(main())` と、run_py の登録（scripts/run_all_migrations.sh）は変えない。以前は DATABASE_URL が無いと `sys.exit(1)` で migration を止めたが、無効化後は何もせず終わる。
- 外したもの以外: 試験が import する `backfill_schema` の定義、migration-test.yml:1575-1608 の静的な検査が見る has_source ガード。

## 2. 本番との比較（読み取り。2026-10-07。5 テナント: tenant_001・003・004・005・006）
- permissions 19 キー（042 の 4、063 の 4、065 の 6、067 の 2、069 の 2、070 の 1）: 本番に **19/19** あり。
- オーナー／システム管理者への付与（042・063・069 の 10 キー）の欠け: 全テナント **0**。
- 044 の backfill で差のある行: **0**（tenant_meta_config の行数は 0/0/14/0/1）。
- 051 の status='confirmed' の行: **0**。055 の granted_scopes が NULL の行: **0**。
- 056: どのテナントにも表 `suppliers` が無く（`tenant_suppliers` が tenant_001・004 にあるだけ）、DO ブロックは全テナントを飛ばしていた。
- 064: 指定のメールに一致するユーザー 1 人のうち、is_super_admin が FALSE の行は **0**（フリップ 0）。users 全体 10 人、is_super_admin が TRUE は 3 人（件数のみ。身元は PO が確認する）。
- 066: tenant_id が 4・6 の行は **2/2** あり。069: 各テナントの tenant_profile は 1 行。070: tenant_settings の行が無いテナント 0、phase は B が 5 件。
- 073 の旧い status の leads: **0**。calendar の category が NULL の行: **0**。
- adr109: leads.status の分布は existing_customer 8、lead 109、lost 5、negotiating 7、out_of_scope 2（すべて VALID_STATUS_CODES）。adr119 で lead_channels に無い discord の leads: **0**。
- country: country が NULL でない行は tenant_006 の 8 行で、alpha-2 形式でないもの 0、public.countries に無いもの 0。
- 結論: どの書き込みも、今の本番では 1 行も変えない。

## 3. 依存【事実】
- scripts/setup_tenant.py:209、:253、:262 と scripts/db/sync_tenant_schema.py:324、:347、:354 が 042、044、051 を catch-up に使う（.github/workflows/schema-check.yml が setup_tenant.py を流す）。無効化後も 044 のトリガーは残る。新テナントの作成が付けるトリガーは backend/app/services/tenant.py:1459-1500 にもある。042 の付与の代わりは tenant.py:1504-1541（オーナーは全権限、システム管理者は system.manage 以外）。
- is_super_admin を TRUE にする経路は、migrations/064 の UPDATE（:54-56）以外に、アプリ・スクリプト・テナント作成・管理 API に 0 件（git grep）。登録 API（backend/app/routers/auth.py:74）は role="user" で作り、is_super_admin は既定の False。読む側は backend/app/auth/dependencies.py:421-471 ほか。CI・試験で 064 に頼って super admin を作るものは 0 件（migration-test.yml:987-1002 は DEFAULT の確認だけ）。
- 試験: 値を書く文を入力にしていた TEST_PG_URL だけの試験 3 ファイル（test_inventory_sprint1_migrations.py、test_inventory_visibility_permissions.py、test_inventory_sprint8_migrations.py）を、試験が自分でキー・既定行を入れる形に直した（新規 backend/tests/seed_inventory_data.py）。CI では TEST_PG_URL が無く動かない（test.yml:222-231）ので、この変更の結果は PG では未確認。`backfill_schema` を import する試験（test_adr119_backfill_source_guard.py:165、:199、:233、test_lead_country_control.py:18）は、関数を残したので変わらない。
- scripts/migrate_inventory_sprint1.py は、migration-test.yml:893、:1555 で流れる。056・063 の値を外しても、表の作成は残る。

## 4. 試験（TDD）
- 先に backend/tests/test_value_migrations_neutralized_3c.py を書き、無効化の前に実行した（RED）: 23 failed, 2 passed（passed の 2 は、`backfill_schema` が関数として残っていること）。
- 無効化後（SQLite・DB なし。ローカルの PG は使っていない）: 27 passed。内訳: SQL 11 本の「印がある・値を書く文が無い・構造が残る」、044（トリガーと関数が残り、backfill が無い）、064（列を残し、UPDATE も本文のメールも無い）、Python 5 本の main() が DB に触れずに終わる、DATABASE_URL が無くても終わる、`backfill_schema` が残る 2 本、seed の SQL 2 本。
- 関連する他の試験（backend/tests の test_value_migrations_neutralized_3c、test_inventory_sprint8_migrations、test_inventory_sprint1_migrations、test_inventory_visibility_permissions、test_lead_country_control、test_adr119_backfill_source_guard）: 28 passed, 18 skipped（skipped は PG が要る試験）。
- scripts/check_test_schema_dup.py: 「テストへの新規スキーマ複製なし(pass)」（最初に出た 1 件は、静的な試験の中の文字列だったので、文字列を変えた）。
- ruff check（backend/tests/seed_inventory_data.py）: All checks passed。

## 5. #4020（ledger）への申し送り（本 PR では #4020 を編集しない）
本 PR のデプロイ後に baseline を取る。scripts/migration-ledger/step3-neutralized.list に、後で次の 17 本を足す（Python の印は「NEUTRALIZED (ADR-」の形）:
migrations/042_seed_meta_inbox_permissions.sql、migrations/044_create_meta_page_routing_trigger.sql、migrations/051_remove_confirmed_status.sql、migrations/055_add_granted_scopes.sql、migrations/056_add_suppliers_type_and_promote_public.sql、migrations/063_tenant_rbac_extensions.sql、migrations/064_add_users_is_super_admin.sql、migrations/065_seed_central_admin_permissions.sql、migrations/066_add_tenant_llm_budgets_notification_dedupe.sql、migrations/067_add_inbound_review_version_and_permissions.sql、migrations/069_create_tenant_profile.sql、migrations/070_add_spreadsheet_phase.sql、scripts/migrate_073_lead_status.py、scripts/migrate_20260620_080000_calendar_category_backfill.py、scripts/migrate_adr109_status_codes.py、scripts/migrate_adr119_lead_channels_backfill.py、scripts/migrate_20260621_020000_backfill_lead_country.py。
（#4020 の check-migration-immutability と baseline は、無効化の後の内容で取る前提。）

## 6. 未確認
- CI での結果（migration-test.yml の全件ドライラン・変更した migration の 2 回実行、schema-check、pytest）。
- TEST_PG_URL だけで動く 3 ファイルの、PG での実行結果。
- 5 テナント以外（新しい環境）での挙動。
- 044 のトリガーの関数が、無効化後も新規行を同期すること（構造は変えていないが、実行は未確認）。

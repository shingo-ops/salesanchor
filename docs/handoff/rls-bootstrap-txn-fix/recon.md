# recon — rls-bootstrap txn fix

**仕事名**: rls-bootstrap-txn-fix
**日付**: 2026-07-19
**対象ADR**: ADR-108
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|---|---|
| `backend/tests/rls_bootstrap.py:164-203` | `bootstrap_tenant_schema()` が tenant schema 作成と migration 適用を同一 `conn` に寄せる修正点。run 29656181169 で露見した「別トランザクション適用」の修正対象 |
| `migrations/20260614_100000_create_sales_form_tables.sql:49-68` | `lead_sales_form_selections` が `leads(id)` を参照する FK を持ち、`leads` 未作成だと失敗することの根拠（sales_form 系 migration の出自は ADR-108） |
| `backend/tests/test_priority_prospects_pg_rls.py:111-120` | `bootstrap_tenant_schema(admin_engine, _TENANT_ID)` を実呼び出ししており、RLS PG テストが bootstrap 順序に依存していることの再現経路 |

## ADR 検索結果

- ADR-108 該当（sales_form migration の出自）

## 補足

- run 29656181169 では `tenant_998.leads` が存在しないまま `lead_sales_form_selections` の作成に入って失敗した。
- したがって、本件の真因は「tenant 構築と migration 適用の順序・接続境界」である。

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|---|---|---|
| 1 | 同一 `conn` 化の実装で sales_form の FK 競合が消えるか | `backend/tests/test_rls_bootstrap_ordering.py` の実測 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み


## 2026-09-10追補: 別テスト領域へのmigration干渉

基点: 760532a9a57c4661672468e26beed8d071b6f6d4。以前の完了記載は当時の同一接続化の結果で、本追補の修正完了を意味しない。

- PR #3397 HEAD 0c8c643ecfea7f1891c367bfb27be44040d44c65 のrun 34429316341、job 102721277863・再実行102722150842は、ともに1 failed / 2377 passed / 93 skipped。失敗はtest_rls_bootstrap_schema_and_migration_share_one_transaction、tenant_871.leads不存在。
- backend/tests/rls_bootstrap.py:67-73 は正本SQL全体を実行し、:231-232のtenant用2本にも対象schemaを渡していない。
- migrations/20260611_100000_create_channel_masters.sql:32 と20260614_100000_create_sales_form_tables.sql:26は全tenant領域を走査。後者:58は各領域のleadsへのFKが必要。
- backend/tests/test_tcg_import_progress_pg.py:47以降はtenant_871/872を部分的に作成する。leadsは作らず、bootstrap側の共有lockを取らない。同ファイルは本便で変更しない。
- 並行したDB操作の時刻はログにない。干渉するコード経路と2回の障害は確認済みだが、操作時刻を実測したとは扱わない。
- rgでbackend・migrations・本テーマ文書のtenant_9951参照は0件。回帰試験ではCREATE SCHEMAを存在確認なしで実行し、既存なら失敗する。作成成功時だけ後始末する。
- 旧release/rls-bootstrap-txn-fixの台帳はIN_PROGRESSだがPR #2966はMERGED、登録worktreeとopen PRなし。残存branchの未統合非merge commitは0件。旧台帳の状態は本便で書き換えない。
- 外部事例は不要。既存SQL・CI失敗と再現テストで判定する。新規ライブラリ/APIの導入や仕様変更はない。
- 手元はDocker/pytest依存がない。純粋な文字列変換と構文を確認し、実PostgreSQLの成功判定はCIに残す。

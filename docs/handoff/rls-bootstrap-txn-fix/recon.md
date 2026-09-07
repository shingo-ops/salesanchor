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

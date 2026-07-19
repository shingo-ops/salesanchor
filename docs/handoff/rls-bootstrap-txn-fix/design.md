# Design — rls-bootstrap txn fix

**対象ADR**: ADR-108  
**recon**: docs/handoff/rls-bootstrap-txn-fix/recon.md  
**日付**: 2026-07-19  
**担当**: Planner

## 外部・過去事例の参照と我々への応用

- 該当なし。今回はテスト基盤固有の競合修正であり、外部事例の新規参照を増やすよりも、`run 29656181169` の実測と既存 RLS テストの流儀をそのまま守る方が安全。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| `bootstrap_tenant_schema()` が 1 回の呼び出しで完走する | `pytest backend/tests/test_priority_prospects_pg_rls.py backend/tests/test_rls_bootstrap_ordering.py -q --no-cov -o addopts=''` を通す |
| `leads` / `lead_sales_form_selections` / `tenant_sales_form_options` が新規テナントで全て実在する | `backend/tests/test_rls_bootstrap_ordering.py` で `information_schema.tables` を確認する |
| `lead_sales_form_selections.lead_id` の FK が `leads(id)` を参照する | `pg_constraint` / `information_schema` で FK 定義を確認する |
| `tenant_998.leads` 不在系の `UndefinedTableError` を再発させない | `backend/tests/test_rls_bootstrap_ordering.py` と `pytest backend/tests/test_priority_prospects_pg_rls.py ...` が両方緑になる |

## 技術 How

- `backend/tests/rls_bootstrap.py` の `bootstrap_tenant_schema()` は、テナント schema 作成と migration 適用を同じ `conn` 上で完了させる。
- これにより、`tenant_998.leads` がまだ存在しない状態で `lead_sales_form_selections` の FK 付き migration が先行してしまう競合を止める。
- `backend/tests/test_rls_bootstrap_ordering.py` で、新規テナント 1 件に対して bootstrap を走らせ、テーブル実在と FK 実在を確認する。

## KPI

- `run 29656181169` 型の `tenant_998` エラーを再発させない。
- `pytest (SQLite + PostgreSQL RLS)` が緑になる。
- 新規回帰テストが通り、bootstrap 順序の破綻を検出できる。

## 弊害・トレードオフ

- テナント bootstrap は同一 `conn` 上で直列化されるため、構築時間は数秒程度増える可能性がある。
- ただし、migration と schema 作成の境界ズレで落ちるより、毎回同じ順序で完走する方が優先度は高い。

## 計画票

| 手順 | 内容 | 状態 |
|---|---|---|
| 1 | `bootstrap_tenant_schema()` を同一 `conn` 化 | 完了 |
| 2 | `test_rls_bootstrap_ordering.py` を追加 | 完了 |
| 3 | `pytest backend/tests/test_priority_prospects_pg_rls.py backend/tests/test_rls_bootstrap_ordering.py -q --no-cov -o addopts=''` を実行 | 完了 |
| 4 | PR #2966 の本文を新規 docs パスへ更新 | 進行中 |

## 維持の仕組み

- 守り手: `backend/tests/test_rls_bootstrap_ordering.py`
- 対象: テナント schema 作成と migration 適用が別トランザクションに戻る変更
- 再発防止: `bootstrap_tenant_schema()` を触る変更は、この回帰テストを通さないと気づけるようにする
- 監視: `pytest (SQLite + PostgreSQL RLS)` と当該回帰テストを CI で確認する

## 継続

- 今回の修理はテスト基盤固有の競合を潰す段階で止める。
- sales_form 系 migration の出自は ADR-108 に従い、今後の構築順序変更も同じ `conn` 前提で扱う。

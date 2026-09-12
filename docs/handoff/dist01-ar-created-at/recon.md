# recon — dist01 ar.created_at バグ修正

## 調査対象

DIST-01（#3250）の `GET /api/v1/tcg/distribution/preview` が 500 エラーを返す。

## 根本原因の特定

`backend/app/services/tcg_distribution_svc.py:349`

```python
# 問題箇所（修正前）:
AND ar.created_at >= NOW() - INTERVAL '30 days'
```

`tenant_004.analysis_results` に `created_at` カラムは存在しない。

### information_schema.columns 実測（2026-09-04）

実行クエリ:
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'tenant_004'
  AND table_name IN ('analysis_results', 'item_corrections')
ORDER BY table_name, ordinal_position;
```

**analysis_results の時刻カラム:**
- `computed_at` (timestamp with time zone)
- `updated_at` (timestamp with time zone)
- `created_at` → **存在しない**

**item_corrections の参照列（全件確認）:**
- `ic.id` (bigint) ✓
- `ic.extraction_item_id` (uuid) ✓
- `ic.corrected_at` (timestamp with time zone) ✓
- `ic.analysis_result_id` → 存在しない（クエリ内で未参照）

## 影響範囲

- 修正箇所: `backend/app/services/tcg_distribution_svc.py:349`（1行のみ）
- 他に `ar.created_at` を参照している箇所: なし（grep 確認済み）
- `tcg_distribution_targets.created_at` は実在する（lines 455/467/486/519 は別テーブル、問題なし）

## 修正内容

`ar.created_at` → `ar.updated_at`（1行変更）


## 2026-09-12 設計補完の追加調査

調査基点: main adc8bc4d67a94e8ede45a1e9c0ee9f28d28bb70b、PR #3258 HEAD 3df471abbe7dfeba8adc6a0723ae0a272dc0f163。既存内容は調査当時の記録として保持。本節は設計相談の追補。

- migrations/20260903_210000_tcg_distribution_settings_t004.sql:29–41は「直近30日間のFLAG_SINGLE行数」、50件、5%、3週連続、PO承認を記載。computed_at/updated_atの選択は明記していない。
- backend/app/services/tcg_analyzer_svc.py:1301–1302,1325–1326は両日時を再解析のnowへ更新する。一方、item_corrections_svc.py:54–70の商品手修正、tcg_unit_recovery_svc.py:869–875,987–992,1057–1059,1171–1177の後処理は日時列を更新しない。updated_atを「人の修正も含むすべての更新日時」と説明する根拠はない。DB全トリガーを実機確認した結果ではない。
- 正規の実PG試験の既存例はbackend/tests/test_tcg_product_list_pg.py:23–53。localhostのjarvis_test_dbだけを許可し、ランダムなschemaとトランザクションrollbackで隔離、正規migrationを試験用schemaへ適用している。
- .github/workflows/test.yml:220–224は既存のテスト用PostgreSQL管理者接続を提供している。本補完案はこの既存検証経路を使い、CI設定変更を含めない。
- backend/app/routers/tcg_distribution.py:154–160のpreviewはread-onlyサービス呼出し。サービスを模擬しないAPI試験が必要。
- item_correctionsの正規migration（20260903_170000_item_corrections_t004.sql）はfield_nameごとの追記方式。1明細複数修正が可能で、既存JOIN/COUNTは複数行になる。これは既存集計の別論点として記録し、日時1行修正へ無断で集計方式変更を混載しない。全体の精度ゲートの意味が正しいと本便だけで宣言しない。

POに提示した未決事項は「直近30日」の基準日時1件。最後に解析した日時（computed_at）を推奨案、更新日時（updated_at、既存PR案）を代替として提示。回答未受領。どちらも承認済みと扱わない。


## 2026-09-12 computed_at確定と指摘訂正

推奨「最後に解析した日時」を提示後のPO原文「進める」を受領しcomputed_at採用へ確定。設計は同日改訂版を正とする。
削除宣言の前回指摘は誤りだった。scripts/check-process-artifacts.js:797–817はnumstatのdeletions>0を宣言対象にし、810行に1行の変更も含むと明記する。PR #3258のサービス記載は正しい。公開本文は変更していない。
正規DDLのFKとNOT NULLを確認済み: 解析fixtureはsource_messages→extraction_jobs→extraction_items→analysis_resultsを作り、analysis_results必須booleanとengine_versionを明示する。
自己審査APPROVEは限定設計のみ。製品・試験実装なし、代理GO・マージ・本番反映なし。

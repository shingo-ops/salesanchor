# design: 在庫表 GET /inventory を1文にする（便 inventory-single-query）

設計者: Opus（カード: /tmp/CC報告ファイル/same-post-rows/sp2/perf2/CARD-inventory-single-query.md）。recon: [recon.md](/docs/handoff/inventory-single-query/recon.md)。
関連 ADR: ADR-093、ADR-1014（決定は変えない・性能のみ）。新規 ADR なし。

## 設計
- backend/app/services/tcg_distribution_svc.py: `distribution_rows_parts(*, include_flag_single, age_condition, merge_same_post) -> (head, final_select)` を追加。`distribution_rows_sql` は `f"{head}\n        {final}"` を返し、文字列は変更前と同一。`distribution_final_select_plain()` を追加（まとめなしの最終 SELECT。facets 用）。
- backend/app/routers/inventory_offers.py: `_build_inventory_view_sql` を追加し、`list_inventory_view` の3文を dist_base 共有の1文（total 枝・page 枝・facet 枝の UNION ALL）に置き換える。experiment2.py の s2_sql と同じ形。facets の元は merge 時 rows_xp（まとめなし）、非 merge 時 rows_x。
- 利用者入力は SQL 文字列に入れない。WHERE は `_build_view_filters` の bind のみ、並びは `_SORT_COLUMNS` の固定値。
- 触らない: fetch_output_rows、配信プレビュー、GAS 出力、frontend、migrations、deploy.yml、nginx、`_build_view_filters`・`_project_inventory_rows`・`_SORT_COLUMNS` の中身。
- 戻し方: PR を revert（または list_inventory_view を3文に戻す）。

## 受入基準

| 基準 | 検証方法 |
|---|---|
| distribution_rows_sql の文字列が不変 | test_distribution_rows_sql_is_byte_identical_to_before（4通りの長さ+SHA-256 固定、head+final の組み立て一致） |
| 配信行に `__` で始まる別名が無い | test_distribution_sql_has_no_double_underscore_alias（静的）、PG テストで返却列の `__` 列が想定の8本だけであることを検査 |
| 1文の結果が旧3文と全条件で一致（total・page・facets、merge ON/OFF、絞り込み、最終頁+1） | CI の PG テスト test_single_statement_equals_the_previous_three_statements（8通り）。デプロイ後に本番 measure.py T1/T2（Opus） |
| facets が絞り込みに影響されない | test_facets_are_not_affected_by_filters（PG） |
| 1回の表示で dist_base 計算が1回 | 本番 EXPLAIN（Opus） |
| 表示時間 ≤0.7秒（ON/OFF とも） | 本番 measure.py T7（Opus） |

## 外部・過去事例の参照と我々への応用
不要: 本番実測で判定済み（perf2/RESULT-experiment2.md）。新しい技術選択・依存追加なし。

## 手元テスト
手元は PG 無し。DB 不要のテストと既存テストの結果: /tmp/CC報告ファイル/same-post-rows/sp2/perf2/impl/pytest.txt。PG 必須テストは CI で実行（手元は skip）。

## 維持の仕組み
- 文字列固定テストが distribution_rows_sql の意図しない変更を CI で止める。
- PG テストが旧3文との全項目一致を CI で固定する。

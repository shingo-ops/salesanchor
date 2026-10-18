# recon: 在庫表「24時間以内」の絞り込みを配信行の計算の内側へ移す（在庫表の高速化 便2）

基準: origin/main 165e316a7（2026-10-18 fetch 後）。生出力: /tmp/CC報告ファイル/inventory-speed/bin2/recon/（svc.txt・router.txt）、/tmp/CC報告ファイル/inventory-speed/recon3/timings.txt

## 既存 ADR 検索
- `git grep -il "fresh_only\|24時間以内" docs/adr/` → `docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md:38`（改訂 2026-10-14 で「24時間以内」(`fresh_only`、既定 ON、画面側のみ・保存しない)、窓は `FRESH_WINDOW_HOURS = 24`）
- 絞り込み候補（facet）が絞り込みの影響を受けない、と明記した ADR 本文は無い。現行の振る舞いは試験 `backend/tests/test_inventory_distribution_rows_pg.py:374`（test_facets_are_not_affected_by_filters）が固定している
- ADR-1016（即時反映）は本便で触らない

## 現在の配線【事実】
- 窓の定数: `backend/app/services/tcg_distribution_svc.py:214` `FRESH_WINDOW_HOURS = 24`
- 配信行の年齢窓: `backend/app/services/tcg_distribution_svc.py:217` `_age_window(max_age_hours)` が `AND sm.line_posted_at >= NOW() - make_interval(hours => :max_age_hours)` を返す
- 配信行の組立: `backend/app/services/tcg_distribution_svc.py:304` `distribution_rows_parts(*, include_flag_single, age_condition, merge_same_post)`。dist_base の WHERE 末尾 `backend/app/services/tcg_distribution_svc.py:375` が `AND {sold_out_filter}{age_condition}`
- 並びの番号: `backend/app/services/tcg_distribution_svc.py:348` `ROW_NUMBER() OVER (ORDER BY result_order_sql()) AS sort_ord`（dist_base 全行に対して計算）
- 在庫表 API の「24時間以内」は dist_base の外（rows_f）で絞っている: `backend/app/routers/inventory_offers.py:258` から3行
  ```python
      if fresh_only:  # 「24時間以内」。件数とページ送りに連動させるため WHERE 側で絞る
          conditions.append("d.posted_ts >= NOW() - make_interval(hours => :fresh_hours)")
          params["fresh_hours"] = FRESH_WINDOW_HOURS
  ```
- `_build_view_filters` の定義 `backend/app/routers/inventory_offers.py:187`、呼び出しは1か所 `backend/app/routers/inventory_offers.py:376`
- 年齢窓の受け渡し: `backend/app/routers/inventory_offers.py:374` `age_condition, age_params = _age_window(max_age_hours)` → `backend/app/routers/inventory_offers.py:387` `distribution_rows_parts(..., age_condition=age_condition, ...)`
- 1文の組立: `backend/app/routers/inventory_offers.py:283` `_build_inventory_view_sql`。rows_f は `backend/app/routers/inventory_offers.py:300`、facet の元は rows_x / rows_xp（`backend/app/routers/inventory_offers.py:299`）で rows_f より前＝絞り込み前
- API の既定 `fresh_only=False`（`backend/app/routers/inventory_offers.py:348`）、画面の既定 true（`frontend/src/pages/inventory/InventoryPage.tsx:145`）

## 時間の内訳（本番 reader・2026-10-18）【事実】
| 計測 | 時間 | 出典 |
|---|---|---|
| 現行の1文（fresh_only=true） | 1,270〜1,935ms | recon3/timings.txt |
| dist_base の件数だけ（48h窓） | 1,319ms | 同 |
| dist_base を24h窓で計算 | 801ms | 同 |
| ROW_NUMBER を外した場合 | 約950ms | 同 |
| 検索語の照合を外した場合 | 約1,110ms | 同 |

→ 時間の大半は dist_base（配信行の重い計算）で、行数に比例する。24h 窓を内側に入れると計算対象が減る。

## 窓を内側へ移したときに変わるもの・変わらないもの【事実：コードからの導出】
- 並び: `result_order_sql()` は ei.id で終わる全順序。sort_ord の値は変わるが同順位の決着にだけ使うので、表示順は変わらない
- まとめ（merge）: グループキーに ej.id を含み ej→sm は1対1。同じグループの行は投稿時刻が同じなので、窓でグループが割れない
- 件数（total）・ページ: rows_f の条件と同じ集合になるので同じ
- 絞り込み候補（facet）: rows_x / rows_xp が24h内だけになるので、候補が24h内に存在する値だけに縮む（PO 承認済み 2026-10-18「y」）

## 影響する試験【事実】
- `backend/tests/test_inventory_distribution_rows.py:46` test_fresh_window_is_24_hours_and_fresh_filter_is_bound
- `backend/tests/test_inventory_distribution_rows.py:209` test_distribution_rows_sql_is_pinned
- `backend/tests/test_inventory_distribution_rows.py:219` test_parts_head_has_dist_base_and_final_is_plain_when_not_merged
- `backend/tests/test_inventory_distribution_rows_pg.py:351` test_single_statement_equals_the_previous_three_statements
- `backend/tests/test_inventory_distribution_rows_pg.py:374` test_facets_are_not_affected_by_filters
- `backend/tests/test_inventory_distribution_rows_pg.py:426` test_bin1_fresh_only_excludes_rows_older_than_24_hours_and_total_follows

## 未確認
- 本番での新旧 SQL の結果一致・時間（実装後に reader で計測する。design.md の KGI）

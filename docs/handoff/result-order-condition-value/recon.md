# recon: 同じ商品の中の並びを「状態の価値の高い順」にする

基準: origin/main（2026-10-18 fetch 後、f5c54b8a2）。生出力: /tmp/CC報告ファイル/inventory-value-order/recon/（q1.txt・q2_*.txt・q3_conditions.txt・q4_*.txt・q5_*.txt）。

## 既存 ADR 検索
- docs/adr/ADR-1023-condition-value-rank.md: value_group / value_rank は「v102 の状態の判定（_resolve_condition）だけが使う」（:35, :43）、「v102 以外の経路は変えない」（:48）、「管理画面での表示・編集は別便」（:49）。並び順に使う記述は無い。value_rank は 1＝価値が高い、群（box/case/pack）の中の順位で、群をまたぐ順位は定義なし。
- docs/adr/ADR-1021（Bulk）: Bulk は箱・パックの順位を持たず、既知の状態の直後・未登録値の前に置く（tcg_result_order.py のコメント）。
- docs/adr/ADR-1014（在庫表は配信行を表示）: 並びの最終キーは d.sort_ord。

## 現在の並び（同じ商品の中）
- backend/app/services/tcg_result_order.py:8-19 RESULT_CONDITION_ORDER = Case, Damaged case, Sealed box, Damaged sealed box, No shrink box, Opened box, Unsearched pack, Searched pack, Bulk。
- tcg_result_order.py:22-34 result_order_sql: `p.release_date DESC NULLS LAST, p.id ASC NULLS LAST, CASE cr.canonical WHEN … ELSE 9 END, cr.canonical COLLATE "C" ASC NULLS LAST, ar.price_normalized ASC NULLS LAST, ei.id ASC`。
- 表に無い Opened case・Searched box・AR confirmed pack は ELSE（9）となり、Bulk より後ろに文字順で並ぶ。

## 呼び出し元（result_order_sql を変えると並びが変わる箇所）
- backend/app/services/tcg_analysis_review_svc.py:249, :308（LINE解析の結果画面）
- backend/app/services/tcg_distribution_svc.py:348（配信行の sort_ord）→ :444 fetch_output_rows → GAS 在庫一覧のシート書込（:693）、backend/app/line_import_admin.py:117、:396-401 まとめ行の MIN(sort_ord)、backend/app/routers/inventory_offers.py（最終キー d.sort_ord）
- backend/app/services/tcg_import_progress.py:122（取込進捗の一覧）
- RESULT_CONDITION_ORDER を直接参照するのは試験だけ（backend/tests/test_tcg_result_order.py:360-363）

## 別名 cr
- backend/app/services/tcg_condition_review_svc.py:251-271 review_joins() の `CROSS JOIN LATERAL (…) cr`。列 canonical（確認済み・空箱明示・解析値の順で差し替え済みの値）、condition_id 等。value_group / value_rank は cr に無い。
- public.conditions は view（`CREATE OR REPLACE VIEW public.conditions AS TABLE public.line_conditions`、migrations/20261017_120000_line_conditions_value_rank.sql 内で新しい列を含めて再作成）。

## 本番の値（ADR-1024 読み取り専用の道・q3_conditions.txt・16 行・canonical 重複なし・全て有効）
| canonical | value_group | value_rank |
|---|---|---|
| Case / Damaged case / Opened case | case | 1 / 2 / 3 |
| Sealed box / Damaged sealed box / No shrink box / Opened box / Searched box | box | 1 / 2 / 3 / 4 / 5 |
| Unsearched pack / Searched pack / AR confirmed pack | pack | 1 / 2 / 3 |
| Bulk / Empty box / 空箱 Case / FLAG_SINGLE / Error | NULL | NULL |

## 試験
- backend/tests/test_tcg_result_order.py（実 PG）: :67（8状態×価格×商品の96行の順を固定）、:121、:158、:183、:359-363（RESULT_CONDITION_ORDER の末尾が Bulk・SQL 文字列）。
- backend/tests/test_inventory_distribution_rows.py:190-200 `_GOLDEN`（distribution_rows_sql の長さ＋SHA-256、4通り。:190 に RESULT_CONDITION_ORDER 変更時の再生成の前例）。
- backend/tests/test_inventory_distribution_rows_pg.py:84, :117, :285, :307-309（sort_ord を使用）。

## GAS 在庫一覧（~/tcg-viewer-1hc-release/index.html）
- :1388-1418 の比較関数は同じ英語名・同じ比較値のとき 0 を返す（Array.prototype.sort は ES2019 以降安定）→ その範囲は配信順（sort_ord）のまま。

## 未確認
- 試験用 DB の line_conditions に value_group / value_rank の値が入っているか（値は migration でなく記録 SQL で本番投入。ADR-1023:41-44）。
- line_conditions.canonical に UNIQUE 制約があるか。

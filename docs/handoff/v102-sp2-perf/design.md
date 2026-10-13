# design: 在庫表（配信行 SQL）の高速化（便 SP2-perf）

設計者: Opus（承認済み）。PO 決定（2026-10-14）: 「速くする修正を急いで作る」。recon: [recon.md](/docs/handoff/v102-sp2-perf/recon.md)。
関連: [v102-same-post-rows-sp2/design.md](/docs/handoff/v102-same-post-rows-sp2/design.md)、[review-speed/design.md](/docs/handoff/review-speed/design.md)。ADR: ADR-093（在庫表の再設計。決定は変えない・性能のみ）。新規 ADR なし。

## 設計
- `review_joins(..., fenced: bool = False)` を追加（backend/app/services/tcg_condition_review_svc.py）。既定 False は従来と同一の文字列。
- fenced=True のとき、SQL 正本（同関数の f-string）を1か所の変換関数 `_fence_review_joins` で次の3点だけ変える。各置換の個数を検査し、想定と違えば RuntimeError。
  1. cr_input・cr_hash・cr_valid・cr_reasons・cr の5本の閉じ括弧の前に ` OFFSET 0`。
  2. `CROSS JOIN LATERAL (SELECT to_jsonb(ei) AS j OFFSET 0) cr_ei` を cr_product の結合の直前に置き、`to_jsonb(ei)->` を `cr_ei.j->` にする。
  3. cr_arc の結合の直後に cr_js を置き、5つの別名の `to_jsonb(<alias>)` を `cr_js.j_<alias>` にする。
- backend/app/services/tcg_distribution_svc.py:314（配信行 SQL）だけ fenced=True。要確認ページ・取り込み進捗・context_sql・配信プレビュー(:408/:451)は不変（要確認の全件が 0.09秒→0.6秒に遅くなるのを避ける）。
- 触らない: フロントエンド、migration、deploy、DB。
- 戻し方: tcg_distribution_svc.py:314 の `fenced=True` を外す（1行）、または PR を revert。

## 受入基準

| 基準 | 検証方法 |
|---|---|
| P1 fenced=False の文字列が変更前と1文字も違わない | 手元で origin/main 版と schema=None/tcg/public で完全一致を確認（impl/p1-check.txt）。テスト test_default_is_unfenced_and_unchanged |
| P2 fenced=True が experiment.py の c3 と一致 | backend/tests/test_tcg_condition_review_fenced.py（テスト内に c3 相当を独立実装して一致比較）と構造検査 |
| P3 配信行の全行一致（ON/OFF）・fetch_output_rows が旧版と一致 | CI の PG テスト（test_inventory_distribution_rows_pg.py ほか）全緑。デプロイ後に本番で measure.py T1・T2 を再実行 |
| P4 在庫表1回分（COUNT＋ページ＋facets）の合計が ON・OFF とも2秒以内 | デプロイ後 measure.py T7（実験値: 1回 約0.5秒 ×3） |
| P5 要確認ページの問い合わせは変わらない | P1 で担保 |

## 外部・過去事例の参照と我々への応用
外部事例は不要。PostgreSQL の OFFSET 0 による最適化の壁は本リポジトリ内に前例がある（review-speed/design.md、tcg_condition_review_svc.py の cr_data）。新しい技術選択・依存追加が無いため。

## 手元テスト
手元は PG 無し・argon2 無し。DB 不要の新規テスト3件は全緑。PG 必須テストは CI で実行（未実施）。結果: impl/pytest.txt。

## 維持の仕組み
- 文字列検査テスト（backend/tests/test_tcg_condition_review_fenced.py）が、既定の文字列不変（P1）と fenced の構造（P2）を CI で固定する。
- 変換関数は置換の個数が想定と違えば RuntimeError。review_joins の SQL を変えて変換が合わなくなると CI のテストと配信で即失敗する。
- 本番の再測定（measure.py T1・T2・T7）で P3・P4 を確認する。

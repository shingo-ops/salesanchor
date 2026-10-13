# recon: 在庫表（配信行 SQL）の速度（便 SP2-perf）

実測時の origin/main: 0819129aa8e4702aa0dd0a9ea94dfed0a8d88391。事実のみ。調査の原本は /tmp/CC報告ファイル/same-post-rows/sp2/perf/recon-perf.md、本番実測は同 experiment-prod.txt・explain-prod.txt（リポジトリ外・設計者保管）。

## 対象 ADR 検索
- `git grep -i "review_joins\|OFFSET 0" docs/adr/ docs/adr/FEATURE-INDEX.md` は新規 ADR を要する決定を含まない。関連する前例は /Users/tanizawashingo/salesanchor/docs/handoff/review-speed/design.md（OFFSET 0 の根拠）。ADR-1002 は product_id の件で無関係。

## 事実
- 在庫表 1回の表示 = 配信行 SQL を3回（COUNT・ページ・facets）。本番 ON 約11秒・OFF 約9秒。
- 土台の結合 0.017秒、dist_base 2.549秒。重いのは review_joins。
- OFFSET 0 の壁があるのは cr_data だけ: backend/app/services/tcg_condition_review_svc.py:129-130（変更前）。cr_input・cr_hash・cr_valid・cr_reasons・cr の5本（同:146-202）は壁が無く親へ展開され、to_jsonb(ei) などが参照のたびに再計算される。
- 配信行 SQL の review_joins 呼び出し: backend/app/services/tcg_distribution_svc.py:314。ほかの呼び出し: 同:408・同:451（配信プレビュー）、要確認ページ（tcg_analysis_review_svc.py の _BASE_FROM）、取り込み進捗、context_sql。
- 既存テストが固定: backend/tests/test_tcg_condition_review.py:675-686（`AS ar OFFSET 0) cr_data` の存在）。backend/tests/test_inventory_distribution_rows_pg.py:105 は review_joins を直接使う。
- 実験（本番・読み取り専用・各3回）: 現行 C0 は配信 ON 4.0〜4.3秒・OFF 2.4〜2.5秒・要確認全件 0.09秒・needs_review 0.77秒。C3 は ON 0.49秒・OFF 0.49〜0.52秒・要確認全件 0.60秒（遅くなる）・needs_review 0.58〜0.65秒。全行一致 True。

## 未確認
- 在庫表 API が画面から2回呼ばれる疑い（未実測。本便の対象外）。

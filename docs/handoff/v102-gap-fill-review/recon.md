# recon: v102 取りこぼし疑いを要確認の理由にする（段2a）

- 基準: origin/main `d465983235b952f5728955498c7f12d8e60b66c5`（2026-10-12）
- 調査: Sonnet（読み取りのみ）＋ Opus の本番読み取り。生出力はリポジトリ外の社外秘の記録（仕入元データを含むため。集計値と行番号だけをここに写す）。
- 前の段: 段1（記録）`docs/handoff/v102-gap-detect-record/design.md`。PR #4150（列）・#4151（書き込み、merge 9f71e3cb）本番反映済み。

## 1. ADR の検索
- `git grep -il "review_reason\|needs_review\|要確認" origin/main -- docs/adr/` の結果は2件:
  - `docs/adr/ADR-057-lp-premium-restyle.md`（LP の文言で無関係）
  - `docs/adr/ADR-154-tcg-parity02-gas-python-migration.md`：:70「配信はneeds_review=falseの行に限定する」、:57「配信・本番反映は本提案に含めない」、:76「旧判断を自動上書きしない」
- `docs/adr/FEATURE-INDEX.md` に LINE解析・要確認の行は無い（近いのは :19 の「取り込み / 解析 / パイプライン」ADR-100 / ADR-014）。
- `docs/adr/ADR-1007-migration-structure-only-run-once.md`：:29-36「値の操作は migration に書かない。1回だけのデータ変更は PO 合意・DRY-RUN → COMMIT・docs/handoff/<topic>/ に SQL と記録」。
- 要確認の理由の種類の追加や配信の専用の決まりを書いた ADR は、上の検索の範囲では無い。

## 2. 解析の流れ（本番経路）
- `backend/app/services/line_analysis_v102_svc.py:275-315` `run_v102_pipeline`：
  - :290-293 `extract_items(..., review_reasons=True, gemini_trust=True, ...)`
  - :297 Gemini の迷い → :298-304 `_with_review_sources`
  - :305 `_gap_detail`（:263-272）＝段1の記録。`build_gap_detail(fields["v102_items"], 行, masters["product_first"], post_review)`。例外は None にして解析を止めない。
- 段1の候補の作り方 `backend/app/services/v102_gap_lines.py`：
  - :146-151 `_is_target`：raw_price と raw_quantity の写しがあり（none・空でない）、`match_status == "unmatched"` の件だけ。
  - :178-211 `gap_name_candidates`：件ごとに `gemini_index`・`gap_lines`・`support_lines`・`candidates`。
  - :242-262 `to_stored_detail`：gemini_index → 件の id に置き換えて `extraction_jobs.system_review_detail` に書く（`backend/app/services/line_analysis_v102_svc.py:885`）。
- 本番での記録（読み取り、2026-10-11 23:02 UTC の新しい2投稿）：両方とも非 NULL・`unmapped` 0。gap_name は 14件と1件。

## 3. 件の理由 → 要確認 → 配信
- `backend/app/services/line_analysis_v102_svc.py:589-619` `_analysis_values`：
  - :592 `matched = product_id is not None and match_status in _RESOLVED_MATCH_STATUSES`（:584-586。matched・matched_context・matched_followup・matched_soldout_ref）
  - :605 理由＝件の `review` の kind 名・Gemini の迷い・値の範囲外を、出た順・重複なしでカンマ結合
  - :607 `"product_id": product_id if matched else None, "pid_resolved": bool(matched)`
  - :616 `"needs_review": reasons is not None, "review_reasons": reasons`
- 配信 `backend/app/services/tcg_distribution_svc.py:290-296`（:361-367 の件数も同じ）：`ar.pid_resolved = TRUE AND ar.is_current = TRUE AND cr.needs_review IS FALSE ...`
- 最新の行の決め方 `backend/app/services/tcg_analyzer_svc.py:1744-1879` `_merge_supplier_products`：`pid_resolved = TRUE AND product_id IS NOT NULL` の行だけで順位を付け、is_current を書く。
- よって、`match_status == "unmatched"` の件は pid_resolved が FALSE になり、配信にも、最新の行の順位付けにも入らない（:592・:607、distribution :290、analyzer :1744-1879）。
- 人の「このままで良い」：`backend/app/routers/item_corrections.py:177-206` → `v102_human_decisions_svc.py:64-68, :243-258`（item_corrections に記録）→ 再解析で `backend/app/services/line_analysis_v102_svc.py:717-736` `_apply_decisions` がその kind を外す。
- 人の商品の訂正：`backend/app/routers/item_corrections.py:127-169` → `backend/app/services/item_corrections_svc.py:59-73` で product_id・`pid_basis='MANUAL'`・`pid_resolved=TRUE`。

## 4. 本番の読み取りで分かった危険（段2a の形を決めた事実）
2026-10-11 23:02 UTC の投稿 6e135e76 の「候補が1つ」の 9件の商品は、すべて同じ仕入れ先の別の投稿 a1a5dcbe（同じ 18:09 投稿）に、要確認の理由なし・is_current の行がある（読み取り SQL の結果。商品 440301・440302・440476 等）。
- もし候補1つの件を matched（pid_resolved=TRUE）にすると、同じ時刻の行どうしで computed_at の新しい方が is_current を取り（analyzer :1744-1879 の順位 `received_at DESC, computed_at DESC`）、今配信されている行が要確認の行に置き換わって集計リストから消える恐れがある。
- これは「配信は変えない」という段2a の前提（Fable 案）と食い違う。→ 段2a では商品を当てない（design.md §2）。

## 5. 理由の種類を足すときに触るもの
- `backend/tests/test_review_reason_codes_consistency.py`：
  - :60 seed のコード集合＝ja.json の `reviewReason` の鍵＝en.json の同じ鍵（unknown・source・separator を除く）
  - :66 コード側の定数（:38-57 `_code_side_constants()` に列挙）がすべて seed にある
  - :71 seed の各コードが backend/app の .py に `"code"` のリテラルで出る
- seed：docs/handoff/v102-prod-switch/data/review_reason_codes/seed_*.sql（seed_*.sql の名前でないと拾われない）。前例は `docs/handoff/v102-prod-switch/data/review_reason_codes/seed_20261011b_unit_price_mismatch.sql` と up_precheck / up_dryrun / up_commit / up_verify / up_rollback.sql、README の記録欄。
- 本番の表（読み取り、2026-10-12）：36行（最後は unit_price_mismatch、2026-10-11 06:50 UTC）。
- fix_stage の効き目：`backend/app/services/v102_transcription_svc.py:47` 投稿の一覧（書き写しを直す画面）の対象は「件の理由に fix_stage='extraction' のコードがある」投稿。
- 「このままで良い」で外せない理由の置き場所：`backend/app/services/review_reason_codes_svc.py:16`（condition_unknown だけ）。

## 6. 画面（段2a の PR-B で使う）
- 要確認の一覧 `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx:339-355` → `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:71-95` の理由の表示は `reviewReasonLabel(t, code)` だけで、行番号は持たない。
- API `backend/app/routers/tcg_analysis_review.py:72-76`（理由は {code, source, fix_stage, ackable}）、:85-96 `AnalysisResultItem`。SQL `backend/app/services/tcg_analysis_review_svc.py:38-44` は extraction_jobs を JOIN 済み。SELECT は :147-327。
- 投稿の画面 `backend/app/routers/tcg_v102_posts.py:68-82`（lines[{number,text}]・items[...review_reason_details]）、値は `backend/app/services/v102_transcription_svc.py:32, :233`。
- `system_review_detail` を返す API は無い（grep は書き込み4行と migration 2行だけ）。
- 差し込み付きの i18n の前例：`reviewItem.sourceLine`（ja.json:3754 `{{source}}`、frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:75）。理由の区切りは `reviewReason.separator`（ja.json :3759-3802 の範囲）。
- 金型：`frontend/src/components/Badge.tsx`、`frontend/src/components/Callout.tsx`、`frontend/src/components/Stack.tsx`。ReviewItemDrawer は Button・Callout・Drawer・Stack を使う。

## 7. 未確認
- 1,021回の保存応答で、対象の件（unmatched・価格数量あり・間の行あり）のうち、今は要確認でない件の数 → 実装後の前後比較で数える（design.md §5 受入1）。
- frontend の ja/en の鍵の同一を検査する CI の有無（backend の整合テストは :60 で ja/en をそろえる）。

# recon: v102 間の行の検知の記録（段1）

基準: origin/main 8f9a2b19796c3c669a6140e6972deeb5bc8c2709（worktree release/v102-gap-detect-record）。
社外秘の原文は載せない（投稿IDの先頭8桁・行番号・商品IDのみ）。詳しい根拠の控えは社外秘のためリポジトリ外（PO の手元）に置く。

## 1. 既存 ADR の検索
- `git grep -i -n "needs_review\|possible_missing\|review_reason" origin/main -- docs/adr`：配信の関門は `docs/adr/ADR-154-tcg-parity02-gas-python-migration.md:70`「配信はneeds_review=falseの行に限定する」。
- migration の決まり：`docs/adr/ADR-1007-migration-structure-only-run-once.md:31-36`（構造だけ・値の操作は書かない）、`:103`（migrations を含む PR は PO の「GO #番号」）。
- 危険 PR の GO 手順：`docs/adr/ADR-135-release-stowaway-prevention.md:57-60`、`docs/adr/ADR-136-cc-bot-github-identity.md:49-69`。
- `possible_missing`・`review_reason` を決めた ADR は無い（設計書は `docs/handoff/v102-no-silent-drop/design.md:34-45`）。

## 2. 今の仕組み（観測事実）
- 投稿ごとの要確認の理由は `backend/app/services/gemini_raw_copy_v101.py:1313-1318` `_post_review_reasons` が `{"kind", "line"}` で作る。
- 保存は種類名だけ。`backend/app/services/line_analysis_v102_svc.py:648-649` `_job_review_reasons` が kind をカンマで結び、`:641-645` `_set_job_review_reasons` が `extraction_jobs.review_reasons`（TEXT）に書く。呼び出しは `_write_results` の `:843`。行番号は DB に残らない。
- `v102_flags`（`possible_missing_item`・`quantity_no_number`・`possible_footer_line`・`post_review`・`gemini_review`）は DB に保存されない（`backend/app/services/gemini_raw_copy_v101.py:1377-1380`、`:1388`、`backend/app/services/line_analysis_v102_svc.py:288`）。
- `run_v102_pipeline`（`backend/app/services/line_analysis_v102_svc.py:262-300`）は、原文（`ctx.raw_text`）とマスタ（`masters["product_first"]`）の両方を持つ。`_write_results`（`:807-844`）は原文を持たない。
- 本番の商品照合の入口は `backend/app/services/gemini_raw_copy_v102_product_first.py:552-553`（`product_match_text(block, "", name)` → `match_text_g2(match_text, masters)`）。
- 既存の JSONB 列の前例：`migrations/20261009_180000_v102_engine_columns.sql`（`extraction_jobs.gemini_unsure` JSONB、`ADD COLUMN IF NOT EXISTS`＋`COMMENT ON COLUMN`）。
- 本番 `public.extraction_jobs` の列（2026-10-11 読み取り）：id, source_message_id, status, extracted_at, error_message, prompt_version, created_at, work_reference_snapshot, work_reference_sha256, gemini_unsure, review_reasons。
- デプロイ順：コンテナの入れ替え（`.github/workflows/deploy.yml:348-397`）が migration（`.github/workflows/deploy.yml:504-518`）より先。列の追加と、その列への書き込みは別の PR にする（前例 #4141・#4144）。
- 人の判断（`item_corrections`）は `extraction_items.id` で結ぶ（`backend/app/services/v102_human_decisions_svc.py:49-54`、`backend/app/services/line_analysis_v102_svc.py:1070`）。

## 3. 測定（手元の保存データ・Gemini なし。2026-10-11）
- 今の本番の指示書 f_ct の 125投稿×2回（fct2）と、BASE SHOP の 7投稿×3回（bs1）で測った。
- 規則 H2（間の行を、次の間の行までの下の件すべてに効かせる。直後の件が価格・数量あり・unmatched のときだけ動く。間の行がそれ1行だけで商品に当たるときは使わない）の結果：
  - fct2 で最初の件より前の行も含める場合：動いた件 480、候補1つ 100、候補なし 380。
  - 動いた件はすべて、今すでに要確認だった（配信が変わる件は 0）。
  - BASE SHOP の 3投稿（48bc0989 L31・9c58a14d L39・46aec157 L1）は、全回 440415（PM0199）だった。
- 件と件のあいだに、価格と数量が同じ行にある行（式 F2_price_and_qty）：fct2 では、件と件のあいだに限ると 0回。最初の件より前の行まで含めると 4回立ったが、4回とも取りこぼしではなかった。
- 測定の写しは社外秘のため、リポジトリ外に置いた。

# recon: v102 で「分けて届く投稿」の商品を直前の投稿から決める

- 基準: origin/main 9d23d78f1（#4086）。読み取りのみ（Sonnet 調査2本、Opus 確認）。
- 既存 ADR 検索: docs/adr/ADR-158-product-level-supersession.md（is_current は (商品,状態) 単位で最新の投稿が勝つ）、docs/adr/ADR-154（配信は needs_review が偽の件だけ）。前後の商品で作品を決める既存の仕組み（#4037 matched_context）がある。

## 1. PO の決定
- 2026-10-09「y」：同じ仕入元の直前の投稿が1時間以内、かつ今の投稿が10行以下のとき、今の投稿で商品が決まらない件を直前の投稿の「商品が1つに決まった行」から決める（試算 followup-ref-sim の prev1_T1h_L10：決まらない行 316 のうち 20 行が決まる・疑い 0）。
- 2026-10-09 追加要件「完売や残り100などの数量変更のみの更新も前の在庫情報を削除せずに既存の数量とステータスのみ変更する」→ 本便の対象外（§5、別便。PO 確認事項あり）。

## 2. v102 の流れ（事実）
- 入口: backend/app/tasks/tcg_extraction.py:433 `_run_v102_extraction` → :445 `run_v102_analysis`。再解析は backend/app/services/tcg_analyzer_svc.py:1220-1226 で prompt_version が `v102:` 始まりなら `run_v102_analysis`。
- backend/app/services/line_analysis_v102_svc.py:611-652 `run_v102_analysis(session, extraction_job_id)`：job 単位。読むのは `load_extraction_context`（backend/app/tasks/tcg_extraction.py:226-264：raw_text・仕入元ルール・supplier_id）と extraction_items。`supplier_channel_id`・`line_posted_at`・source_message_id は読まない。session は引数にあるので直前の投稿を DB から読める。
- backend/app/services/line_analysis_v102_svc.py:229-263 `run_v102_pipeline` → backend/app/services/gemini_raw_copy_v101.py `extract_v101_items`（純粋関数、DB を持たない）。
- 行番号は空行込み：backend/app/services/gemini_extraction_svc.py:230-233 `annotate_lines` と backend/app/services/gemini_raw_copy_v101.py:198 の `raw_text.split("\n")`。
- 商品照合: backend/app/services/gemini_raw_copy_v102_product_first.py:210-232 `match_product_g2`（候補0→unmatched、2以上→ambiguous、1→matched）、呼び出し :482 `resolve_product_first`（照合文は `product_match_text(block, "", name)`）。
- 前後の商品で作品を決める仕組み: backend/app/services/gemini_raw_copy_v102_context_work.py:34-36（定数）・:137-153 `decide_by_context`、適用 backend/app/services/gemini_raw_copy_v101.py:1022-1044 `_apply_context_work`（決まった件は `build(i, product_id)` で作り直し `match_status=matched_context`）、呼び出し :1163。
- 書き込み: backend/app/services/line_analysis_v102_svc.py:521-543 `_analysis_values`（matched / matched_context のとき product_id・pid_resolved=True、pid_basis=`V102:<match_status>`）、:546-565 UPSERT、:650 `_merge_supplier_products`（ADR-158）。
- 配信: backend/app/services/tcg_distribution_svc.py:260-267（pid_resolved・is_current・needs_review 偽・excluded でない・単位あり・価格あり）。

## 3. 試算の部品と backend の対応
- 試算: ~/CC報告ファイル-keep/session-20261007b/followup-ref-sim/refsim.py（手元・社外秘）。型番 `CODE_RE` を fold 後の行に当て `_strict_code_pattern` で厳格型番だけ、名前は `[ァ-ヴー]{4,}|[一-龥々]{4,}|[A-Za-zＡ-Ｚａ-ｚ]{4,}` を normalize した4文字以上。直前の投稿で「1商品に決まった行」に、型番は厳格パターンで・名前は部分一致で当たる商品が1つだけなら決める。
- backend: `fold_for_match` backend/app/services/extraction_judgement_svc.py:22-28、`normalize_for_match` :31-44、`_strict_code_pattern` :152-168。
- 試算との違い: 試算は空行を捨てた行・形F で照合した。本実装は v102 の照合部品（形G2）を使うので、件数は実装後に測り直す。

## 4. 本番の今
- extraction_jobs の prompt_version に `v102:` 始まりは無い（v6 系のみ）。docker-compose.yml:218 `LINE_ANALYSIS_ENGINE=${LINE_ANALYSIS_ENGINE:-v6}`。→ 本便は本番の配信を変えない。

## 5. 完売・残り数の投稿（本便の対象外・事実のみ）
- backend/app/services/tcg_analyzer_svc.py:1743 `_merge_supplier_products` は価格を見ずに (商品,状態) ごとに最新の投稿の行を is_current にする。価格の無い新しい行が勝つと、前の価格の行は is_current=FALSE、配信は price_normalized NOT NULL を求める（backend/app/services/tcg_distribution_svc.py:265）ので、その商品は配信から消える。
- 本番 public.analysis_results で is_current かつ価格 NULL：468行（In Stock 255・Sold out 211・その他 2）。
- 過去の PO 決定（2026-09-29、docs/handoff/fix-received-at-latest/design.md:6）「B. 前の値段を引き継ぐ」「Y. 値段のある直前の投稿」、実装はまだ無い。

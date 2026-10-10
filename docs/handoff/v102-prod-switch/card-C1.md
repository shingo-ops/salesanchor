# 実装カード 便C1: Gemini の書き写しを直す API（backend）

- 設計: docs/handoff/v102-prod-switch/design.md §13-3・§13-5 の 1・§13-7 の C-K1・C-K2（main に #4089 で入っている）
- 発行: 2026-10-09 Claude Opus。PO: 2026-10-09「便C・便D を進める」「PRマージ、デプロイまで完走」
- 前提: 便D1（#4089）が main に入っていること（enqueue_v102_reanalyze・v102_human_decisions_svc・review_reason_details の作り方を使う）

## 0. 着手前（読むだけ。file:line で報告。前提違いは NEEDS_DECISION）
1. `cd /Users/tanizawashingo/salesanchor && git fetch origin && bash scripts/new-worktree.sh release/v102-transcription-edit-api --claude`（--claude の Error は無視可）。以降 worktree 内。preflight。origin/main に #4089 が入っていること（git log）。
2. Gemini に渡す原文の行番号の数え方（1始まりか・改行の扱い・空行を数えるか）: gemini_raw_copy_v101.py で原文に行番号を付ける関数と、frontend の sourceRawLines（features/tcg-analysis-review/sourceRawNavigation.ts）。両者が同じ数え方か。違えば止まる。
3. 原文の読み方（source_messages.raw_text、load_extraction_context）と、要確認 API が件の review_reason_details を作る関数（review_reason_codes_svc.build_review_reason_details）。
4. D1 の enqueue_v102_reanalyze・v102_job_id_of_item・advisory lock の鍵（'v102_analysis:<job_id>'）・TRANSCRIPTION_FIELDS 等の定数名（v102_human_decisions_svc.py）。
5. 既存ルーターの置き場所と super_admin の付け方・ADR-072（commit 直後の reset_tenant_context）の扱い（routers/item_corrections.py に合わせる）。

## 1. 変更内容（新規 `backend/app/routers/tcg_v102_posts.py` と `backend/app/services/v102_transcription_svc.py`。main.py に登録）
### 1-1. GET /api/v1/tcg/v102/posts（super_admin）
- クエリ: limit（1〜200、既定50）・offset（0以上）。
- 対象: prompt_version が `v102:` 始まりの extraction_jobs のうち、(a) extraction_jobs.review_reasons が NULL でない、または (b) その投稿の件の analysis_results.review_reasons に review_reason_codes.fix_stage='extraction' のコードがある。
- 返す: job_id・source_message_id・provider（要確認 API と同じ仕入元名の出し方）・line_posted_at・job_review_reason_details（投稿の理由を build_review_reason_details で）・item_count・extraction_item_count（(b) に当たる件の数）・total。並びは line_posted_at の新しい順、同時刻は job_id。

### 1-2. GET /api/v1/tcg/v102/posts/{job_id}（super_admin）
- v102 でなければ 409、無ければ 404。
- 返す: job_id・source_message_id・provider・line_posted_at・lines（[{number, text}]、0-2 の数え方）・job_review_reason_details・gemini_unsure（そのまま）・items（gemini_index 順: id・gemini_index・source_lines・raw_price・raw_quantity・review_reason_details（analysis_results から、無ければ []））。

### 1-3. PUT /api/v1/tcg/v102/posts/{job_id}/items（super_admin）
- body: source_message_id（UUID）・items（1件以上）: [{id: UUID|null, source_lines: int[]（1件以上）, raw_price: str|null（200字以内）, raw_quantity: str|null（200字以内）}]。
- 検査（どれか違反で 422・何も書かない）: source_message_id がこの投稿のもの／行番号は整数・1〜原文の行数・件の中で重複なし（保存時は昇順に並べる）／id はこの投稿の件／同じ id の重複なし。v102 でなければ 409、無ければ 404。
- 1つのトランザクションで、最初に D1 と同じ advisory lock（'v102_analysis:<job_id>'）を取る。
  - 既存の件で値が変わったもの: その場で UPDATE（source_lines・line_start=min・line_end=max・raw_price・raw_quantity）。id は変えない。変わった項目ごとに item_corrections に1行（field_name v102_lines / v102_price / v102_quantity、system_value=前の値・human_value=後の値。lines は JSON 配列の文字列、None は ''）。
  - body に無い既存の件: DELETE（analysis_results は ON DELETE CASCADE）。item_corrections に field_name='v102_item_deleted'、system_value=前の件の JSON、human_value='{}'。
  - id なしの件: INSERT（id=uuid4、extraction_job_id、created_at=now）。item_corrections に field_name='v102_item_added'、system_value=''、human_value=件の JSON。
  - gemini_index を、全件を（最小の行番号、元の gemini_index（新しい件は元の件の後ろ）、body の順）で並べて 0 から振り直す。
  - corrected_by は認証ユーザー（item_corrections の既存の書き方）。
- 何も変わっていなければ書かず、積まず、changed=false を返す。
- 変わったら commit 後に enqueue_v102_reanalyze(job_id)（D1）。返す: changed・item_ids（並び順）・enqueued。
- field_name の文字列は v102_human_decisions_svc の定数を使う（二重定義しない。足りない定数はそこに足す）。

## 2. テスト（PG は *_pg、Celery はモック）
- C-K1: 変えていない件の id が変わらない／変えた件・追加・削除が item_corrections にすべて残る／gemini_index が行番号順に振り直される／enqueue が1回。
- C-K2: 行番号 0・行数超え・重複・整数でない・空、price 201字、他の投稿の id、source_message_id 不一致 → 422 で何も書かない（件・item_corrections の件数が不変）。
- v6 の投稿 409、無い投稿 404、変更なしで changed=false・enqueue 0回。
- GET 2つの形（一覧の対象条件 (a)(b)、詳細の lines の数え方が 0-2 と同じ）。
- 書き写しを直した後、その件の古い商品の判断が無効になる（D1 の有効性）ことを1本。

## 3. 触らない
D1 のロジック・試作版の判定・配信・frontend（openapi.json の再生成は除く）・migrations・deploy.yml・.github/workflows。

## 4. 完了
非PG pytest（--no-cov）・ruff → openapi.json を CI と同じ条件（/tmp/CC報告ファイル/v102-binA/venv312、Python 3.12＋固定版）で再生成し、差分が新しい3つの API と型だけか確認 → commit（Co-Authored-By なし）→ push → `gh pr create --draft --base main`（worktree 内から。テンプレート起点。標準ワークフロー確認：recon docs/handoff/v102-prod-switch/recon.md、設計 docs/handoff/v102-prod-switch/design.md、対象ADR ADR-154。触るファイル・削除するファイルは実測からパスのみ・openapi.json も含める。維持の仕組み欄に守り手。PR 本文のファイルは先に作ってから別コマンドで gh pr create）。CI を待たない。最終行 DONE / BLOCKED: / NEEDS_DECISION:。

## 5. 止まる条件
フック・権限に止められた（言い換えず文面を貼る）／0 の前提違い／カードに無いファイルを触る必要／2通り以上に分かれる。

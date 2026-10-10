# 実装カード 便CD2: 要確認ページの「投稿」タブ（書き写しを直す）と、本番タブの行から直す Drawer（frontend＋小さな backend）

- 設計: docs/handoff/v102-prod-switch/design.md §13-5 の 2・3、§13-7 CD-K1。前提: 便D1（#4089）・便C1（#4091）が main に入っていること
- 発行: 2026-10-09 Claude Opus。PO: 2026-10-09「便C・便D を進める」「フロントエンドのパーツもデザイントークンとデザインシステムを遵守して、金型登録のないハードコードを禁止する」「PRマージ、デプロイまで完走」
- 厳守: 金型（frontend/src/components/）だけを使う。生 input/select/button・自作タブ・色や px の直値・新しい ui-allow・新しい金型の追加は**禁止**（必要になったら止まって NEEDS_DECISION）。画面の文字はすべて t()（ja/en 同じ鍵）。docs/CC_UI_GOVERNANCE.md・frontend/CLAUDE.md を最初に読む。

## 0. 着手前（読むだけ。file:line で報告。前提違いは NEEDS_DECISION）
1. `cd /Users/tanizawashingo/salesanchor && git fetch origin && bash scripts/new-worktree.sh release/v102-review-screens --claude`（--claude の Error は無視可）。以降 worktree 内。preflight。origin/main に #4089・#4091 が入っていること。`cd frontend && npm ci`（node_modules が無ければ）。
2. 金型の props: Tabs・DataTable（onRowClick・page 系）・Modal（size xl・footer）・Drawer（footer）・TextField（inputMode が渡せるか）・Button・Callout・EmptyState。ShadowSourcePane（features/tcg-analysis-review/ShadowSourcePane.tsx の rawText・blockRange）。
3. 本番タブ（pages/super-admin/components/NeedsReviewTabsPanel.tsx）のタブ・列・データの取り方。訂正の既存部品（ItemComparison・ConditionReviewPanel・ProductMasterDrawer）の props と、SupplierDetailView.tsx での使い方（そのまま再利用できるか）。
4. API 型の作り方（frontend/api-contract/openapi.json → npm run generate:api-types、型の置き場所）と、既存の API 呼び出しの書き方（fetch のラッパー）。
5. 要確認 API の件（AnalysisResultItem）に「v102 の件か」が分かる項目が無いこと（tcg_analysis_review.py）。

## 1. backend（小さな変更）
- AnalysisResultItem に `is_v102: bool` を足す。値はその件の extraction_jobs.prompt_version が v102 の判定（line_analysis_v102_svc の is_v102_prompt_version と同じ規則。SQL では同じ接頭辞の定数から作り、文字列を二重に書かない）。既存項目は変えない。
- v102_transcription_svc の PUT の入力で raw_price・raw_quantity の空文字（前後の空白だけを含む）を None にそろえてから比較・保存する（#4091 審査 MEDIUM）。テスト1本（None で保存済み → "" を送っても changed=false）。
- openapi.json を CI と同じ条件（/tmp/CC報告ファイル/v102-binA/venv312）で再生成し、差分が is_v102 だけか確認。frontend の型も再生成。

## 2. frontend
### 2-1. 「投稿」タブ（NeedsReviewTabsPanel にタブを1つ足すだけ。中身は新しいファイル）
- 新規 `features/tcg-analysis-review/V102PostsTab.tsx`: GET /api/v1/tcg/v102/posts を DataTable で（列: 仕入元・投稿時刻・投稿の理由（reviewReasonsText）・直す件の数／件数）。ページ送りは DataTable の page 系。0件は EmptyState。行を押すと 2-2 を開く。
- タブの鍵 `posts`、ラベル `needsReview.tabs.posts`。

### 2-2. 書き写しを直す Modal（新規 `features/tcg-analysis-review/V102PostEditModal.tsx`）
- GET /api/v1/tcg/v102/posts/{job_id}。Modal（xl）。左に原文（ShadowSourcePane、rawText は lines の text を "\n" で結ぶ。選んだ件の行の最小〜最大を blockRange）、右に件の表（DataTable）。
- 件の行: 行番号（TextField、「3,5,7」の形。inputMode numeric）・価格（TextField）・数量（TextField）・理由（reviewReasonsText）・削除（Button danger）。表の下に「件を追加」（Button）。フッターに「やめる」「保存」（Button）。
- 保存前に画面でも検査（行番号は整数・1〜行数・件の中で重複なし・1つ以上、価格・数量は200字以内、件は1件以上）。だめな行は TextField の error で示し、保存しない。空欄の価格・数量は null で送る。
- PUT /api/v1/tcg/v102/posts/{job_id}/items。成功で changed=true なら Callout（info）「保存しました。解析をやり直しています」、false なら「変更はありません」。422 は API のメッセージを Callout（warning）で。保存後は一覧を読み直す。

### 2-3. 本番タブの行から直す Drawer（新規 `features/tcg-analysis-review/ReviewItemDrawer.tsx`）
- 本番タブの DataTable に onRowClick を足し、Drawer で開く。中身: ItemComparison（readOnly）・ConditionReviewPanel・「商品を訂正」Button（既存の ProductMasterDrawer を開く）・理由の一覧（reviewReasonLabel と出どころ）。
- 件が is_v102 のときだけ、理由ごとに「このままで良い」Button（secondary）。押すと POST /api/v1/tcg/items/{id}/review-ack（source_message_id, codes: [その理由]）。成功で Callout（info）「確認済みにしました。解析をやり直しています」、一覧を読み直す。v6 の件にはボタンを出さない。
- 既存の部品の振る舞いは変えない（props を渡すだけ）。

### 2-4. 文言（ja/en 同じ鍵。既存の名前空間の書き方に合わせる）
タブ名・列名・ボタン名・検査のエラー文・Callout の文。日本語は短い普通の言葉で（例「このままで良い」「件を追加」「保存しました。解析をやり直しています」）。

## 3. テスト
- vitest: 投稿タブの一覧表示と行クリックで Modal が開く／Modal の検査（0・行数超え・重複・整数でない・空）で保存しない／保存で PUT の body（空欄は null）／本番タブの行クリックで Drawer／v102 の件だけ「このままで良い」が出て POST の body が正しい／v6 の件には出ない。
- backend: §1 のテスト。既存の NeedsReviewTabsPanel.test.tsx・関係する vitest・pytest が通る。
- `npm run build`・`npm run lint`（新しいファイルは警告0）・i18n の検査（check:i18n-missing-keys）・UI ガバナンスの検査（scripts にあれば手元で）。

## 4. 触らない
D1・C1 のロジック（§1 の正規化を除く）、既存の訂正部品の中身、配信、migrations、deploy.yml、.github/workflows。

## 5. 完了
commit（Co-Authored-By なし）→ push → `gh pr create --draft --base main`（worktree 内から、PR 本文ファイルを先に作って別コマンドで。テンプレート起点。標準ワークフロー確認：recon docs/handoff/v102-prod-switch/recon.md、設計 design.md、対象ADR ADR-027, ADR-144, ADR-154。触るファイル・削除するファイルは実測からパスのみ・openapi.json も。維持の仕組み欄に守り手）。カードを worktree の docs/handoff/v102-prod-switch/card-CD2.md に写して含める。CI を待たない。最終行 DONE / BLOCKED: / NEEDS_DECISION:。

## 6. 止まる条件
フック・権限に止められた（言い換えず文面を貼る）／金型に無い部品が要る／0 の前提違い／2通り以上に分かれる。

<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。 -->
# Phase 2 recon — review-ack-confirm

**基準**: origin/main e69ed67b7（worktree release-review-ack-confirm）  
**日付**: 2026-10-14  
**担当**: 調査 Sonnet（生出力 /tmp/CC報告ファイル/review-ack-confirm-recon/）、確認と整理 Opus

## 0. 既存 ADR の検索

- `docs/adr/ADR-144-ui-component-governance.md`（金型を先に確認。生の部品禁止）
- `docs/adr/ADR-067-design-token-enforcement.md`（色・余白はトークン）
- `docs/adr/ADR-027-ui-internationalization.md`（文言は t() 経由、ja/en 同一キー）
- 前の設計: `docs/handoff/review-excluded-ack/design.md`（#4273。確認済みの保存を和集合にした。今回の保存先・保存の形は変えない）

## 1. 「1回押しても消えない」の原因（観測事実）

- `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:57-61` の chooseKeep は `setScope("keep")` をするだけで、保存しない。
- そのあと `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:123-134` で、表の下に ReviewFixWizard（scope=keep）が出る。
- `frontend/src/features/tcg-analysis-review/ReviewFixWizard.tsx:155-171` の keep 欄に、理由ごとの2つ目の「このままで良い」ボタンが出る。保存（acknowledge → postReviewAck）はこの2つ目を押したときだけ走る（`frontend/src/features/tcg-analysis-review/ReviewFixWizard.tsx:97-116`）。
- 2つ目のボタンは原文・比較表の下に出るので、画面の外に出ることがある。
- 結論: 1回目の押下では何も保存されない。2回押す作りになっている。

## 2. 倉田さんの件で実際に保存された記録（本番・読み取り）

- item_corrections id=1609、field_name=review_ack、human_value {"v":1,"codes":["excluded"]}、corrected_at 2026-10-14 13:13:26Z（控え /tmp/CC報告ファイル/excluded-ack-followup/recent_corrections.txt）。
- 2つ目のボタンが押され、保存は1回だけ行われた。

## 3. 「要確認」で needs_review が真なのに理由が空の件は無い（候補の否定）

- 本番 is_current の集計: excluded/t/理由あり 290、excluded/f/理由空 215、NULL/f/空 4354、NULL/t/理由あり 8502。needs_review=t かつ理由空は0件（/tmp/CC報告ファイル/excluded-ack-followup/needs_review_shape.txt）。

## 4. 保存のあとの流れ（いまの作り）

- acknowledge: 保存成功 → onAcked → 「確認済みにしました。解析をやり直しています」→ `await onRefresh()`（`frontend/src/features/tcg-analysis-review/ReviewFixWizard.tsx:97-116`）。
- onRefresh は reloadKey を進めるだけ（`frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx:214`）。
- ドロワーは閉じない。一覧から消えると drawerRemoved になり（`frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx:169-173`）、「この商品は要確認から外れました」の Callout が出る（`frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:76`）。
- 理由を使い切ったら scope=null・ackedNotice（`frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:63-71`）。
- 保存 API は codes を配列で受ける（`frontend/src/features/tcg-analysis-review/reviewActions.ts:45-50`）。backend は前の codes と和集合で保存する（#4273）。

## 5. 使える金型と文言

- `frontend/src/components/ConfirmModal.tsx`: props は open / title / message / confirmLabel / cancelLabel / danger / onConfirm / onCancel。size sm 固定。読み込み中の表示は無い。中は Modal（z 400）で、Drawer（z 301、frontend/src/tokens.css:127 の --z-drawer）より上に出る。
- ドロワーの上で ConfirmModal を出す前例: features/supplier-master/SupplierDetailDrawer.tsx:491-501、features/tcg-product-import/TcgProductDetailDrawer.tsx:242-250。
- 文言: common.close=閉じる（ja.json:122）、reviewItem.ack=このままで良い（ja.json:3768）、reviewItem.acked、reviewItem.ackFailed、reviewItem.removedFromList（ja.json:3769-3778）。「このまま」というボタン文言と、確認の見出し・本文のキーは無い。

## 6. 呼び出し元（全走査）

- ReviewFixWizard / FixScope / choicesForScope を使うのは `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx` と `frontend/src/features/tcg-analysis-review/ReviewFixWizard.test.tsx` だけ（grep -rn、frontend/src 全体）。

<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — review-ack-confirm

**対象ADR**: `docs/adr/ADR-144-ui-component-governance.md` / `docs/adr/ADR-067-design-token-enforcement.md` / `docs/adr/ADR-027-ui-internationalization.md`  
**recon**: `docs/handoff/review-ack-confirm/recon.md`  
**前提の設計**: `docs/handoff/review-excluded-ack/design.md`（#4273）  
**日付**: 2026-10-14  
**担当**: Planner（Opus）。設計審査は Fable（architect）、実装は Sonnet

---

## 0. PO の依頼（原文）

「テストしたがボタンを1回押しただけでは消えなかった、ボタンを押した後の想定としては押したら画面中央にポップアップで最終確認としてこのままでいいか、確認する表示を入れたい、このまま、閉じるの選択を出して、このままボタンを押したらこのままでいいの処理を実行する」（2026-10-14、離席一任の範囲で進める）

## 1. 目的（KGI）

| # | 基準（PO が画面で ○× を判定できる形） | 検証方法 |
|---|---|---|
| K1 | スライドの理由の下の「このままで良い」を1回押すと、画面中央にポップアップが出る。中に確認の文と「このまま」「閉じる」の2つのボタンがある | 試験（ReviewItemDrawer.test.tsx）＋本番で PO 目視 |
| K2 | 「閉じる」を押すとポップアップが消え、何も保存されない（保存の通信 0 回） | 試験で postReviewAck が呼ばれないこと |
| K3 | 「このまま」を押すと、保存が1回だけ行われ、「確認済みにしました…」が出て、一覧を読み直す。その件は「要確認」タブから外れ、スライドに「この商品は要確認から外れました」が出る | 試験（呼び出し回数1、codes の中身）＋ NeedsReviewTabsPanel.drawer.test.tsx |
| K4 | 表の下に2つ目の「このままで良い」ボタンは出ない（押すのは1か所だけ） | 試験で「このままで良い」ボタンが1つだけ |
| K5 | 保存中は「このままで良い」が押せない（二重保存しない） | 試験 |

## 2. 変更前 → 変更後

- 変更前（recon §1）: 1回目は表の下に欄を開くだけ。保存は表の下の2つ目のボタン。
- 変更後: 1回目でポップアップ → 「このまま」で保存。表の下の keep 欄は無くす。

## 3. 何をどう変えるか

### 3.1 `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx`
- chooseKeep をやめ、「このままで良い」は `setConfirmOpen(true)` だけにする。
- ConfirmModal（`frontend/src/components/ConfirmModal.tsx`、金型そのまま・拡張しない）を置く:
  - title: `t("reviewItem.ackConfirm.title")`（このままで良いですか？）
  - message: `t("reviewItem.ackConfirm.message")` と、確認済みにする理由の一覧（`reviewReasonLabel(t, code)` を ul で並べる。class は既存の `review-item-reasons` を流用、新しい色・余白は作らない）
  - confirmLabel: `t("reviewItem.ackConfirm.confirm")`（このまま）
  - cancelLabel: `t("common.close")`（閉じる）
  - danger は付けない（消す操作ではない）
- 「このまま」を押したら: まずポップアップを閉じ、pending を立て、`postReviewAck(item, keepCodes)` を1回呼ぶ（keepCodes = `ackableReasonCodes(item, ackedCodes)`、残っている理由をまとめて確認済みにする）。
  - 成功: ackedCodes に足す → ackedNotice（既存 reviewItem.acked）→ `await onRefresh()`（失敗は握りつぶす。いまの acknowledge と同じ）。
  - 失敗: エラー文（ApiError の message、無ければ reviewItem.ackFailed）を warning の Callout で理由欄に出す。ackedCodes は変えない。
  - 保存中は「このままで良い」ボタンを loading・disabled にする（Button 金型の既存 props）。
- 保存処理（acknowledge）は ReviewFixWizard から ReviewItemDrawer へ移す。保存の入口は1か所だけにする。
- ボタンの文言は `t("reviewItem.ack")`（このままで良い、ja.json:3768）に切り替える（いまの `reviewItem.wizard.choice.keep` は消すため）。
- canKeep は `ackableReasonCodes(item, ackedCodes).length > 0` にする。handleAcked は保存成功の処理に統合する（ackedCodes に足し、残りが0なら ackedNotice）。scope の state から "keep" は無くなる。
- 保存失敗の文言は state（ackError）で持ち、行を選んだとき（selectRow）と「このままで良い」を押したときに消す（ackedNotice と同じ所）。
- ConfirmModal は default export。`import ConfirmModal from "../../components/ConfirmModal";` の形で読む（相対パスは実物に合わせる）。
- Esc の扱い: Modal と Drawer はどちらも document の keydown で Esc を拾うため、ポップアップ表示中の Esc でドロワーまで閉じる（審査で判明、Modal.tsx:70-80・Drawer.tsx:73-83）。金型は触らず、ReviewItemDrawer が Drawer に渡す onClose を「ポップアップ表示中は何もしない」に包む（`confirmOpen ? () => {} : onClose` 相当）。

### 3.2 `frontend/src/features/tcg-analysis-review/ReviewFixWizard.tsx`
- FixChoice と FixScope から "keep" を消し、keep 欄（choice==="keep" の ul）、acknowledge、pendingCode、onAcked / ackedCodes の props を消す。
- `ackableReasonCodes` は残して export を続ける（ReviewItemDrawer が使う）。availableFixChoices の keep 追加行は消す。
- availableFixChoices / choicesForScope の `ackedCodes` 引数は使わなくなるので消す。呼んでいる所（ReviewFixWizard.tsx:76、ReviewItemDrawer.tsx、ReviewFixWizard.test.tsx:70,74,94,98,102）も同時に直す。
- 使わなくなる import（ApiError / postReviewAck / reviewReasonLabel、ReviewFixWizard.tsx:12,17,18）と、CSS の `.review-fix-wizard__reasons`（review-fix-wizard.css:18-21）を消す。ほかで使っていないことを grep で確かめてから消す。
- 呼び出し元は ReviewItemDrawer と試験だけ（recon §6）。

### 3.3 文言（ja.json / en.json 同じキー）
- reviewItem.ackConfirm.title: 「このままで良いですか？」/ "Keep as it is?"
- reviewItem.ackConfirm.message: 「次の理由を確認済みにします。要確認の一覧から外れます。書き写しをあとで直すと、また一覧に戻ります。」/ "These reasons will be marked as checked and the item will leave the review list. If the transcription is corrected later, it will come back."
- reviewItem.ackConfirm.confirm: 「このまま」/ "Keep"
- 使わなくなるキー（reviewItem.wizard.choice.keep / keepDesc）は、ほかで使われていなければ消す（grep で確認してから）。

### 3.4 試験
- `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.test.tsx`: K1〜K5（ポップアップが出る、閉じるで POST 0回、このままで POST 1回・codes 一致・onRefresh 1回、ボタンが1つだけ、失敗時の文言と再押下可能、保存中 disabled）。ポップアップ表示中に Esc を押すとポップアップだけ閉じ、ドロワーの onClose は呼ばれないこと。初期フォーカスがどこかは試験しない。
- `frontend/src/features/tcg-analysis-review/ReviewFixWizard.test.tsx`: keep の試験を消し、scope の表を product / condition だけにする。
- `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.drawer.test.tsx`: 「このままで良い」→「このまま」→ 読み直しで件が消え「外れました」が出る、の流れに直す。

## 4. 対象外
- backend・DB・保存の形（#4273 のまま）。一覧の作り、配信。
- ドロワーは保存後も閉じない。理由: 一覧から外れたことを「この商品は要確認から外れました」で見せる既存の作り（recon §4）をそのまま使い、閉じると保存結果の通知が見えなくなるため。
- ConfirmModal 金型の変更。

## 5. 代替案
- A: ポップアップを ReviewFixWizard の2つ目のボタンに付ける → 2回押す問題が残るので不採用。
- B: 理由ごとに1つずつポップアップ → 理由が2つあると2回確認が要り、PO の「押したら…このままを押したら処理を実行」と合わないので不採用。残りの理由をまとめて1回で確認済みにする（backend は配列で受け、和集合で保存）。

## 6. リスクと対処
- 理由が多い件でまとめて確認済みになる → ポップアップに理由を全部並べて見せる。
- 保存失敗 → 何も変えず warning を出し、もう一度押せる。
- 戻し方: この PR を revert（frontend だけ。データの形は変わらない）。

## 7. 外部事例
- 該当なし。理由: 既存の金型（ConfirmModal）と社内の前例（SupplierDetailDrawer.tsx、TcgProductDetailDrawer.tsx）で足り、外部の数値を設計の根拠にしない。

## 8. 維持の仕組み
- 保存の入口が1か所（ReviewItemDrawer）であることと、ポップアップの動きを試験（§3.4）で守る。守り手: `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.test.tsx`
- 文言は ja/en の同一キーを既存 CI が確かめる。

## 9. 審査の記録
- 1回目 Fable（architect）: REVISE（生出力 /tmp/CC報告ファイル/review-ack-confirm-architect/）。指摘: ボタン文言キー、canKeep・handleAcked の置き換え先、ackedCodes 引数、不要 import と CSS、失敗文の消すタイミング、Esc でドロワーまで閉じる件、recon の行番号と z 値。→ §3.1・§3.2・§3.4 と recon §1・§5 に反映。
- 2回目 Fable（architect）: APPROVE。実装への注意: (a) Esc 用の onClose 包みは useCallback 等で固定せず、毎回の描画で `confirmOpen ? () => {} : onClose` を渡す (b) 試験で「閉じる」はポップアップの dialog の中に絞って探す（ドロワーと Modal の × も「閉じる」） (c) Drawer.tsx:12 のコメント（299）は対象外で触らない。
- 実装の承認: PO 依頼原文（§0）と離席一任「PRマージ、デプロイまで完走」（2026-10-14）に基づく。

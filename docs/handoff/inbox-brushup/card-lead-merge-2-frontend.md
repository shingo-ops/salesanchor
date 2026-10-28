# 実装カード 2/2: 受信箱のカルテからリードをまとめる（画面）

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

- 設計: `docs/specs/transaction-flow/lead-merge/design.md` §5-2〜§5-4・§5-5(2)・§8 A2・A3
- 決定: `docs/adr/ADR-1049-lead-merge-all-tables-and-fill-blanks.md`
- 現状: `docs/specs/transaction-flow/lead-merge/recon.md` §4・§5
- 前提: カード 1/2 の PR（下見の入口）が main にマージ済み。手順 1 で確かめる。
- 実装の承認: PO 2026-10-28「決めた内容を記録に残してクローンの大きさを測り、作る」

## 0. カード発行前の照合（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は ready で作る | ○（手順 10） |
| 3 | 完了報告の本文に生出力を全文含める | ○（§報告） |
| 4 | 1便1目的（画面だけ） | ○ |
| 5 | 新しい作業場所 | ○（手順 1） |
| 6 | PR 欄の書式を実例で示す | ○（手順 9） |
| 7 | 合格を出力まで縛る | ○（手順 7・8） |
| 8 | 件数の判定に名前を対で出す | ○（手順 7） |
| 9 | 出力量に上限の無いコマンドを使わない | ○ |
| 10 | 停止時の3点・終端合図・報告冒頭の宣言 | ○ |
| 11 | 期待値は実測から。行番号を停止条件にしない | ○ |
| 12 | 停止は不可逆なものだけ | ○ |
| 13 | 定型の4点 | ○（§守ること） |

## 守ること

- sleep で待たない。CI の終わりを待たない。
- ファイルの作成と編集は Write / Edit ツールで行う。
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる。
- フックや自動判定に止められたら、言い換えて再試行しない。原文を報告して終える。
- 禁止: マージ、`backend/` の変更、`migrations/` の変更、CI 設定の変更、本番への接続、`/review` の実行、GO 記録への書き込み。
- 直書き禁止: 色・大きさ・余白は `var(--…)` と金型だけ。新しいトークンを作らない。足りない値があれば停止して報告する。
- 触る前に `frontend/AGENTS.md` を読む。

## 手順

1. `./scripts/dev/executor-preflight.sh || exit 1`。`git fetch --prune` のあと `git show origin/main:backend/app/routers/leads.py | grep -n "merge/preview"` で下見の入口があることを確かめる。無ければ**停止**。あれば `bash scripts/new-worktree.sh release/lead-merge-inbox` で作業場所を作る。
2. `frontend/src/components/MergeLeadModal.tsx` を design.md §5-2 のとおり直す（確認の段で下見を出す・素の `<button>` 2つを金型 `Button` に・文言から「audit_logs」を消す）。`frontend/src/locales/ja.json` と `en.json` の `mergeLead` を直し、足りないキーを足す（表の日本語名・「元に戻せません」）。
3. `frontend/src/pages/inbox/InboxKartePanel.tsx` の「⋯」メニューの一番下に「ほかのリードとまとめる」を足す（design.md §5-3）。条件は `hasPermission("leads.delete") && status === "lead"`（`usePermissions`）。押すと MergeLeadModal を開き、開いている相手を `source` に渡す。
4. `frontend/src/pages/inbox/useInboxState.ts` に統合の後始末を1つ置く: 一覧から loser を外す → `selectLead(masterId)` → 一覧を取り直す。カルテへは関数として渡す。
5. 幅 390 でメニュー項目の高さを測り（手順 7 の試験）、44px 未満なら `frontend/src/pages/inbox/InboxPage.css` の `.karte-overflow-menu button` に `min-height: var(--size-icon-btn-lg)` を足す。トークンは `frontend/src/tokens.css` に 44px と定義され、金型 `frontend/src/components/ContextMenu.css` も同じ使い方をしている（設計担当が 2026-10-28 に確認）。使う前に `grep -n -e "--size-icon-btn-lg:" frontend/src/tokens.css` で実在を確かめる。無ければ停止。
6. `frontend/tests-e2e/visual-language/inbox-lead-merge.spec.ts` を新しく作る（`inbox-helpers.ts` の `baseMocks`・`openInboxListWithLeadStatus`・`MIN_TOUCH_TARGET_PX` を使う。`/me/permissions` と下見・統合の入口は route で作り物を返す）。中身は design.md §5-5(2):
   - 権限ありで項目が出る／`leads.delete` が無いと出ない
   - 幅 390 でメニュー項目・窓のボタンの高さが `MIN_TOUCH_TARGET_PX` 以上、`document.documentElement.scrollWidth <= clientWidth`
   - 写真3枚を `testInfo.attach`（名前は `step1-menu`・`step2-select`・`step3-confirm`）
7. 確かめ（記録のみで続行）: `cd frontend && npx playwright test visual-language/inbox-lead-merge.spec.ts --project=vl-mobile-390 --project=vl-tablet-768 --project=vl-desktop-1280` の全文、失敗した試験名。`npm run check:all` の全文。`npm run build` の終わり20行。
8. 差分の確かめ（記録のみで続行）: `git diff origin/main --stat`、`git diff origin/main --name-only`。
9. PR 本文を `.github/PULL_REQUEST_TEMPLATE.md` から Write で作る。書き方はカード 1/2 の手順 8 と同じ（良い例 `触るファイル: frontend/src/components/MergeLeadModal.tsx, frontend/src/pages/inbox/InboxKartePanel.tsx`、行頭 `-` と注記は禁止、対象ADR・recon・設計は平打ち）。触るファイルは手順 8 の全部。
10. `scripts/dev/validate-pr-body.sh` exit 0 → `git -C <作業場所の絶対パス> push -u origin release/lead-merge-inbox` を単独で → `gh auth status` で `shingo-cc` → `gh pr create --base main --head release/lead-merge-inbox --title "feat: 受信箱のカルテからリードをまとめる（ADR-1049）" --body-file <絶対パス>`（ready）。

停止するのは: 手順 1 で下見の入口が無いとき、手順 5 でトークンが無いとき、push・PR 作成が拒否されたとき、フックに止められたとき。それ以外は記録して最後まで進む。

## 報告

- 冒頭に「本報告はカード 2/2（リードの統合 受信箱の画面）の実行結果である」。
- 完了報告の本文に、手順 1〜10 で実行した全コマンドの生出力を全文含める。
- 停止したときは「停止した手順番号／最後に実行したコマンド／停止した理由」。
- 最後の行に `END-OF-CARD-2` と書く。

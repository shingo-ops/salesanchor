# 実装カード A — 右下の印と吹き出しの金型（画面の部品だけ）

親: docs/handoff/secretary-chat/design.md §11 段1 ／ ADR-1056 ／ ADR-144・ADR-067・ADR-027
状態: 設計担当（Opus）作成。実装は Sonnet。PO の実装承認: 2026-11-01「GO記録や…必要な権限は全て…PRマージ、デプロイまで完走させてくれ」。

## 1. 作るもの（frontend だけ。backend・DB・deploy は触らない）
- `frontend/src/components/FloatingActionButton.tsx`・`.css`・`.stories.tsx`・`.test.tsx`
- `frontend/src/components/ChatBubble.tsx`・`.css`・`.stories.tsx`・`.test.tsx`
- `frontend/src/tokens.css` に z の段を 1 つ足すだけ（下の 2-3）。
- この PR では、どの画面にも置かない（置くのはカード B）。

## 2. 決め事
### 2-1. FloatingActionButton（画面の右下に浮かぶ丸い印）
- props: `icon: ReactNode`（必須）、`label: string`（必須。aria-label と title に使う。呼ぶ側が t() で渡す）、`onClick`、`badge?: number`（0 や未指定なら出さない）、`className?`。
- 見た目: 丸。大きさは `var(--size-icon-btn-lg)`（44px・タッチの基準）以上。位置は `position: fixed`、右と下の余白は `var(--space-4)`。
- props に `aboveTabbar?: boolean` を足す。true のとき（スマホの殻で呼ぶ側が渡す）は、下のタブの帯に重ならないよう、下の余白を `calc(var(--tabbar-height) + env(safe-area-inset-bottom, 0px) + var(--space-4))` にする（modifier class で切り替える）。`--tabbar-height` は `frontend/src/tokens.css:183` で決まっている（設計担当が確かめた）。
- 色は既存の色トークン（主ボタンの色と同じもの。`frontend/src/components/Button.css` の primary が使う変数）を使う。ダークでも同じ変数で切り替わること（ADR-067）。
  - 設計担当の決め: 「primary は 1 画面に 1 個」（`frontend/src/components/Button.tsx:13`）は、金型 `Button` の `variant="primary"` を本文の主操作に使うときの決まり。この印は `Button` の variant ではなく、全画面に浮かぶ別の金型なので数に入れない。`Button` の variant は使わず、色の変数だけを借りる。
- 中身は自前の `<button type="button">` にする。金型 `Button` の丸い形（`shape="pill"`）はログイン画面だけに決められている（`Button.tsx` の props のコメント・buttonShapeUsage.test.ts）ため使えない。この理由を .tsx の頭のコメントに書く。
- `<button type="button">`。キーボードで押せる。フォーカスの輪は既存の金型と同じ変数。

### 2-2. ChatBubble（チャットの吹き出し）
- props: `side: 'user' | 'assistant'`、`children: ReactNode`、`status?: 'sending' | 'error'`、`className?`。
- 利用者の吹き出しは右寄せ、AI は左寄せ。最大幅は親の 80%。角の丸み・余白・色はトークンだけ。
- 今ある吹き出し（`frontend/src/pages/inbox/InboxMessageThread.tsx` とその CSS）と同じトークンを使い、見た目をそろえる。inbox 側は書き換えない（対象外）。
- `status='sending'` は既存の金型 `Spinner`（`frontend/src/components/loading/Spinner.tsx`。`Button.tsx` と同じく `./loading` から読む）を小さく添える。`error` は文字色を危険の色トークンにし、言葉は呼ぶ側が渡す。

### 2-3. z の段
- `tokens.css` の Z-index（`frontend/src/tokens.css:126-135`）に `--z-fab: 250;` を足す（サイドバーの覆い 210 より上、背景の幕 298・Drawer 301 より下。チャットの Drawer が開いたら印は幕の下に隠れる）。コメントに理由を 1 行。

## 3. 守ること
- CSS は `var()` だけ。色・px の直書き禁止（ui-governance-gate・ADR-067）。
- 画面の言葉を金型の中に書かない（言葉は props で受ける。ADR-027）。stories の中の見本の言葉は、既存の stories と同じ書き方に合わせる。
- 既存の金型・トークンを書き換えない（足すのは `--z-fab` だけ）。

## 4. 想定分岐（迷ったら止まる）
- 主ボタンの色の変数が複数あってどれか決められない → 止めて報告（勝手に選ばない）。
- 自前の `<button>` が ui-governance の検査（生の button の禁止など）に止められる → 止めて報告（例外の書き込みを勝手に足さない）。

## 5. 受入（実装役が自分で流して生の出力を残す）
| 基準 | 検証方法 |
|---|---|
| 金型の作法 | 2 部品とも .tsx・.css・.stories.tsx がある |
| 試験 | `cd frontend && npx vitest run src/components/FloatingActionButton.test.tsx src/components/ChatBubble.test.tsx` が通る（label が aria-label に入る・badge 0 で出ない・aboveTabbar で class が変わる・side で class が変わる） |
| 型 | `cd frontend && npx tsc --noEmit` が通る |
| 金型外の検査 | `node scripts/check-ui-governance.js` が通る |
| ダークの対 | `cd frontend && npm run check:dark-parity`（色トークンを足していないので差分なし） |
| lint | `cd frontend && npx eslint src/components/FloatingActionButton.tsx src/components/ChatBubble.tsx` |

## 6. 進め方
- ブランチ `release/secretary-chat-parts`（origin/main 起点）。コミットの最後に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
- PR 本文の「標準ワークフロー確認」: recon docs/handoff/secretary-chat/recon.md、設計 docs/handoff/secretary-chat/design.md、対象ADR ADR-1056, ADR-144, ADR-067、区分 B-1。
- 本文に `### デザイントークン変更時` の理由（`--z-fab` を足す理由）を書く。

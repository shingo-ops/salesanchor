# 実装カード 便1: 受信箱のページが縦にはみ出す件

- 設計: `docs/handoff/inbox-header-tooltip-overflow/design.md` §3-3（Opus 審査済み: `docs/handoff/inbox-header-tooltip-overflow/review-opus.md`）
- ブランチ: `release/inbox-header-tooltip-overflow`（origin/main bef5a7a8b 起点・書類の commit が既に載っている）
- 区分: 画面の見た目と画面の自動試験だけ（CSS 1か所と spec 1本。backend・migrations・scripts・.tsx の画面部品・.github は触らない）
- PO 承認: 「1」（2026-11-23、縦のはみ出しを直す設計を作り本番まで進める。マージ・反映まで委任）

## 0. 読んだ節と照合（Opus）

- guards/00-common.md: 1手順1コマンド・出力に上限・sleep で待たない・commit と push は git log で確かめる → §4・§5 に反映。
- guards/03-file.md: 既存ファイルは Edit で変える。新しいファイルは Write → §2 (1) は Edit、(2) は新規。
- guards/04-worktree.md: 作業場所は new-worktree.sh で作る → 依頼文【場所】に反映。
- 受領確認: 着手したら最初の返事の1行目に「受領確認: 便1 受信箱の縦のはみ出し」と書く。

## 1. 先に確かめる実物（違えば BLOCKED）

| ファイル | 行 | 今の中身 |
|---|---|---|
| `frontend/src/components.css` | 507 | `.page-header-actions .icon-btn {` |
| `frontend/src/components.css` | 510 | `.page-header-actions .icon-btn:hover {` |
| `frontend/src/components.css` | 512 | `}` |
| `frontend/src/components.css` | 514 | `/* --- Icon Button --- */` |
| `frontend/src/pages/inbox/InboxPage.tsx` | 86 | `    <div className="page-header-actions">` |
| `frontend/tests-e2e/visual-language/inbox-helpers.ts` | 24 | `export const MOBILE_MAX_PX = 767;` |

- `frontend/tests-e2e/visual-language/inbox-page-no-vertical-overflow.spec.ts` がまだ無いこと。

## 2. 触るファイル（これ以外は触らない）

### (1) 新しい試験を先に作る

`frontend/tests-e2e/visual-language/inbox-page-no-vertical-overflow.spec.ts` を、design.md §3-3 (2) のコードのとおりに作る（1文字も変えない）。

### (2) 直す前に試験が落ちることを確かめる（§4 の 3）

### (3) `frontend/src/components.css:512` の `}` の直後（`:513` の空行の前）に4行足す

変更前（`:510-514`）:
```css
.page-header-actions .icon-btn:hover {
  border-color: var(--border-icon);
}

/* --- Icon Button --- */
```
変更後:
```css
.page-header-actions .icon-btn:hover {
  border-color: var(--border-icon);
}
/* 吹き出し（data-tooltip）の位置の基準をボタン自身にする。無いと吹き出しが窓の下に置かれ、ページが縦にはみ出す（docs/handoff/inbox-header-tooltip-overflow/design.md） */
.page-header-actions [data-tooltip] {
  position: relative;
}

/* --- Icon Button --- */
```

### 触らない

- `frontend/src/components.css` の上の4行以外（特に `:437-495` の吹き出しの共通の作り）。
- `frontend/playwright.config.ts`・`.github/`・`frontend/src/pages/`・`frontend/src/components/`・backend・migrations・scripts。

## 3. 想定分岐

| 起きたこと | すること |
|---|---|
| §1 の行が違う（main が進んで行がずれた等） | 中身が同じで行番号だけ違うなら、その中身の行に入れて続ける。中身が違えば BLOCKED: |
| §4 の 3（直す前）で、768px・1280px の試験が落ちない | NEEDS_DECISION:（出力をそのまま書く）。直す前に落ちない試験は見張りにならない |
| §4 の 5（直した後）で、768px の試験だけが `scrollHeight` で落ちる（`positions` は通る） | NEEDS_DECISION:（`scrollHeight` と `innerHeight` の値をそのまま書く）。他の原因がある。試験やコードを変えて通さない |
| §4 の 5 で、390px が skip 以外になる | NEEDS_DECISION: |
| stylelint（`check:all` の中）が新しい指定で落ちる | NEEDS_DECISION:（文面をそのまま書く）。指定を書き換えて通さない |
| 触っていないファイルの理由で検査が落ちる | 落ちた検査名と文面を書いて続ける。直さない |
| `npm ci` や Playwright の取り付けが通らない | BLOCKED: |

## 4. 確かめの命令（frontend で上から1つずつ）

1. `npm ci`
2. `npx playwright install --with-deps chromium`
3. （§2 (1) の後・(3) の前）`npx playwright test visual-language/inbox-page-no-vertical-overflow.spec.ts --project=vl-mobile-390 --project=vl-tablet-768 --project=vl-desktop-1280 --reporter=line` → 768 と 1280 が **落ちる**、390 が skip。出力をそのまま貼る
4. （§2 (3) の後）`npm run check:all`
5. 3 と同じ命令 → 768 と 1280 が **通る**、390 が skip。出力をそのまま貼る
6. `npm run build`
7. `git diff --stat origin/main...HEAD -- frontend` と `git status --short` → `frontend/src/components.css` と新しい spec の2つだけ

## 5. 終わり方

- commit を1つ作り、`git log --oneline -1` で commit があることを確かめてから push する。
- 停止するときは、止まった命令とその文面をそのまま書き、最後の行を `BLOCKED: 理由` か `NEEDS_DECISION: 理由` にする。これが停止時の報告の道。
- うまくいったら最後の行を `DONE: <sha>` にする。

END OF CARD

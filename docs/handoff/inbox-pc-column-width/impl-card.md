# 実装カード 便1: PC受信箱の3列の幅（ADR-1086）

- 設計: `docs/handoff/inbox-pc-column-width/design.md` §3-3（Opus 審査済み: `docs/handoff/inbox-pc-column-width/review-opus.md`）
- ブランチ: `release/inbox-pc-column-width`（origin/main 2b4e2c205 起点・書類の commit が既に載っている）
- 区分: 画面の見た目だけ（CSS とトークン。backend・migrations・scripts・.tsx は触らない）
- PO 承認: 「1」（2026-11-23、実装に進める。マージ・反映まで委任）

## 0. 読んだ節と照合（Opus）

- guards/00-common.md: 1手順1コマンド・出力に上限・sleep で待たない・commit と push は git log で確かめる → §4・§5 に反映。
- guards/03-file.md: 既存ファイルは Edit で変える → §2 は全部既存ファイルの Edit。
- guards/04-worktree.md: 作業場所は new-worktree.sh で作る → 依頼文【場所】に反映。
- 受領確認: 着手したら最初の返事の1行目に「受領確認: 便1 PC受信箱の3列の幅」と書く。

## 1. 先に確かめる実物（違えば BLOCKED）

| ファイル | 行 | 今の中身 |
|---|---|---|
| `frontend/src/tokens.css` | 312 | `  --width-inbox-panel:    443px;   /* 受信箱左パネル幅 */` |
| `frontend/src/tokens.css` | 348 | `  --karte-panel-width: 396px;  /* カルテパネル幅（見本 .panel） */` |
| `frontend/src/pages/inbox/InboxPage.css` | 83 | `  width: var(--width-inbox-panel);` |
| `frontend/src/pages/inbox/InboxPage.css` | 636 | `  width: var(--karte-panel-width); /* カルテ専用幅（見本 396px）— --drawer-width: 300px は topbar ドロワー用で流用不可 */` |

- `git grep -n "width-inbox-panel" -- frontend` の結果が上の2行（tokens.css:312・InboxPage.css:83）だけであること。

## 2. 触るファイル（これ以外は触らない）

### (1) `frontend/src/tokens.css:312` を2行に置き換える

変更前:
```css
  --width-inbox-panel:    443px;   /* 受信箱左パネル幅 */
```
変更後:
```css
  --inbox-pc-list-ratio:  41.6%;   /* PC受信箱 一覧の比率（一覧＋会話欄の幅に対して。3列の幅の27%相当）ADR-1086 */
  --inbox-pc-list-max-w:  330px;   /* PC受信箱 一覧の最大幅 ADR-1086 */
```

### (2) `frontend/src/tokens.css:348` を3行に置き換える

変更前:
```css
  --karte-panel-width: 396px;  /* カルテパネル幅（見本 .panel） */
```
変更後:
```css
  --karte-panel-width: 396px;  /* カルテパネル幅（見本 .panel）。タブレット帯の引き出しで使う。PC帯は下の2つ（ADR-1086） */
  --karte-pc-ratio:      34.6%; /* PC受信箱 カルテの比率（受信箱の中身の幅に対して。3列の幅の35%相当）ADR-1086 */
  --karte-pc-max-w:     480px;  /* PC受信箱 カルテの最大幅 ADR-1086 */
```

### (3) `frontend/src/pages/inbox/InboxPage.css:83`

変更前:
```css
  width: var(--width-inbox-panel);
```
変更後:
```css
  width: min(var(--inbox-pc-list-ratio), var(--inbox-pc-list-max-w)); /* ADR-1086: 比率で広がり最大幅で止まる */
```

### (4) `frontend/src/pages/inbox/InboxPage.css:636`

変更前:
```css
  width: var(--karte-panel-width); /* カルテ専用幅（見本 396px）— --drawer-width: 300px は topbar ドロワー用で流用不可 */
```
変更後:
```css
  width: min(var(--karte-pc-ratio), var(--karte-pc-max-w)); /* ADR-1086: PC帯は比率で広がり最大幅で止まる。タブレット帯は下の @media で --karte-panel-width に戻す */
```

### 触らない

- `frontend/src/pages/inbox/InboxPage.css:902` 以降（タブレット帯・スマホ帯の @media）。特に `:904` の `35%` と `:922` の `var(--karte-panel-width) !important`。
- 上の4か所以外の行。.tsx・backend・migrations・scripts・.github。

## 3. 想定分岐

| 起きたこと | すること |
|---|---|
| §1 の行が違う（main が進んで行がずれた等） | 中身が同じで行番号だけ違うなら、その中身の行に入れて続ける。中身が違えば BLOCKED: |
| `npm run check:all` の `check:css-values` が新しい2行で落ちる | NEEDS_DECISION:（落ちた文面をそのまま書く）。値を書き換えて通さない |
| 新しい4つのトークン以外の理由で検査が落ちる（触っていないファイル） | 落ちた検査名と文面を書いて続ける。直さない |
| `npm ci` が通らない | BLOCKED: |

## 4. 確かめの命令（frontend で上から1つずつ）

1. `npm ci`
2. `npm run check:all`
3. `npm run build`
4. `git grep -n "width-inbox-panel" -- frontend` → 0件であること
5. `git diff --stat` → `frontend/src/tokens.css` と `frontend/src/pages/inbox/InboxPage.css` の2つだけ

## 5. 終わり方

- commit を1つ作り、`git log --oneline -1` で commit があることを確かめてから push する。
- 停止するときは、止まった命令とその文面をそのまま書き、最後の行を `BLOCKED: 理由` か `NEEDS_DECISION: 理由` にする。これが停止時の報告の道。
- うまくいったら最後の行を `DONE: <sha>` にする。

END OF CARD

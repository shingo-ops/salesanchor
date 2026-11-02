---
mode: handoff
title: 受信箱 会話画面 A-2 — スマホの文字の吹き出しと入力欄を WhatsApp 実測へ
status: 実装カード（Opus 作成 2026-11-01・Architect 整合検査は §12・審査役 APPROVE 3bdb03e06）。PO の実装承認済み（2026-11-01）
base: origin/main 85a560cb2（行番号の基準。§9 の対象ファイルは origin/main 8c3333a9b でも同じ中身＝git diff が空）
po_approval: 成功条件 A1〜A4 は PO 承認済み（2026-11-01）。このカードの作成は PO「1」（2026-11-01）。実装の承認は PO「1」（2026-11-01、3回目の審査合格の報告に対して）。
---

# card A-2 — スマホの文字の吹き出しと入力欄を実測値へ

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・03-file.md・04-worktree.md・05-pr.md・10-executor.md。

受領確認: 実行役は作業の前に「card-a2 を受け取りました。対象ファイルが 85a560cb2 と同じことを確かめました」と1行返す。§9 のファイルを並べて `git diff --quiet 85a560cb2 origin/main --` を流し、終了コードが 0 でなければ何もせず停止して報告する。
停止と報告: §10 の分かれ道に当たったら、その場で停止し、当たった番号・ファイル:行・生の出力を Opus に報告する（BLOCKED: で始める）。推測で続けない。

根拠: design.md §3・§5（同じフォルダ）、実測 measure-a2.md（同じフォルダ。端末の実測の写し）。行番号はすべて base。
TSX = `frontend/src/pages/inbox/InboxMessageThread.tsx`、PCSS = `frontend/src/pages/inbox/InboxPage.css`、
BCSS = `frontend/src/components/ChatBubble.css`、CCSS = `frontend/src/components/ChatComposer.css`。
1dp を 1px として使う（端末は 1dp = 3 画素。Chrome の幅360 と同じ尺度）。

## 1. 目的
- スマホ（幅767以下）で、文字の吹き出しと入力欄の大きさ・形・置き方を WhatsApp の実測に揃える。
- PC（幅768以上）は1画素も変えない（A3）。秘書のチャット（layout="panel"）も変えない。

## 2. 変えないもの（触らない範囲）
- 色（全部）。PC の値。秘書のチャットの見た目。
- 画像の吹き出し（`msg.attachment_type === "image"`）の中身と並べ方。次の段で扱う。このカードでは尾・角 10・行の間だけが付く。内側の余白と行の高さ（§5-2 の inline-time の規則）は付かない。
- 送れなかった吹き出し（failed）の見た目。尾も時刻の置き方の変更も付けない。
- 翻訳ボタン・翻訳結果（B で扱う）。既読の印（C で扱う。送信側の時刻の右に印の場所を空けない）。「＋」（D）。
- 送る・受ける・訳す・添付・ハート・長押しの動き。API・型・バックエンド・ja.json / en.json（新しい言葉は無い）。
- 既存のクラス名の付け替え・削除（e2e は `.inbox-send-btn` で送信を探している。ほかの名前も残す）。
- 送れなかったときの帯（TSX:724 `inbox-send-error`）の中身と色。§6-3 で `.inbox-send-area` の余白を 0 にするため、帯の置き場所は §6-3 の規則で今と同じに保ち、K10 で確かめる。

## 3. 実測から決めた目標値（スマホのみ）

| 部位 | 目標 | 実測の出典（measure-a2.md） | トークン |
|---|---|---|---|
| 吹き出しの角 | 10 | U1・U2 | 新規 `--comp-chat-bubble-radius-mobile: 10px` |
| 尾（続きの最初だけ） | 受信は左上・送信は右上。横に 7 張り出し、縦 10 で本体へ戻る三角。尾の側の角は 0 | U1・U2 | 新規 `--comp-chat-bubble-tail-w-mobile: 7px` / `--comp-chat-bubble-tail-h-mobile: 10px` |
| 画面の端から吹き出しまで | 左右 17 | U1・spec 5-2 | 新規 `--comp-chat-row-inset-mobile: 17px` |
| 続きの中の吹き出しの間 | 8画素 = 2.667（行の上下 1.333 ずつ） | U2 | 新規 `--comp-chat-row-gap-inner-mobile: 1.333px` |
| 続きの境目（最初の上・最後の下） | 5 ずつ（境目は 10） | U2 | 新規 `--comp-chat-row-gap-group-mobile: 5px` |
| 吹き出しの幅の上限 | 286（行の幅 326 から 40 引く） | U3 | 新規 `--comp-chat-bubble-max-gap-mobile: 40px` |
| 本文の文字・行 | 16 / 19 | design §3（measure2） | 既存 `--font-md`、新規 `--comp-chat-line-height-mobile: 19px` |
| 1行の吹き出しの高さ | 33（上下の内側 7 ＋ 行 19） | U1 | 新規 `--comp-chat-bubble-pad-y-mobile: 7px` |
| 本文の左右の内側 | 初期値 9（§7 で 1px 刻みに決める） | 墨の位置（受信の墨 左 31画素 = 10.3） | 新規 `--comp-chat-bubble-pad-x-mobile: 9px` |
| 時刻の文字・行 | 12 / 16 | design §3（measure-cal1）・U6（時刻の枠 16.3） | 既存 `--font-xs`、新規 `--comp-chat-time-line-height-mobile: 16px` |
| 時刻の置き方 | 本文の最後の行の右下。入らなければ次の行の右下 | U3（長文で最後の行に入る） | — |
| 時刻の右端 | 吹き出しの右端から 8（受信の実測。送信も同じ値＝印の場所は空けない） | U6 | 新規 `--comp-chat-time-inset-mobile: 8px` |
| 時刻の下端 | 初期値 3（§7 で決める） | 墨の位置（墨の下 16画素 = 5.3） | 新規 `--comp-chat-time-bottom-mobile: 3px` |
| 本文と時刻の間 | 6 | U6（時刻の左の余白 6） | 既存 `--space-6px` |
| 入力欄の帯 | 上下 4・左 8・右 10、ピルと送信の間 8 | spec :99-100・2026-11-01 測り直し | 既存 `--space-1` `--space-2` `--space-10px` |
| ピル | 高さ 48（1行）・角の丸み 24 は伸びても変わらない・中のボタン 48x48 | U4・U4b（伸びた形の角 約 71画素 = 24） | 既存 `--comp-btn-height-lg`、新規 `--comp-chat-input-radius-mobile: 24px`（`--radius-full` は伸びると角が大きくなり文字が面の外に出るので使わない） |
| 入力の文字・行 | 18 / 21（1行増えるごとに 21 伸びる） | design §3（measure3）・U4 | 新規 `--comp-chat-input-font-mobile: 18px` / `--comp-chat-input-line-height-mobile: 21px` |
| 入力欄の上下の内側 | 6 ＋ ピルとの間 7.5（6+21+6+7.5x2 = 48） | U4（入力欄 32.3・ピル 48.3） | 既存 `--space-6px`、新規 `--comp-chat-input-inset-y-mobile: 7.5px` |
| 入力欄の伸び | 上へ伸び、高さ 221 で止まり中で流れる | U4（220.7） | 新規 `--comp-chat-input-max-h-mobile: 221px` |
| 送信の丸 | 直径 48 | design §3 | 既存 `--comp-btn-height-lg` |

- 送信側の幅の上限と送信側の続きは測れていない（PO の端末から送らないため）。U1 で送信と受信の 4 項目（端の 17・高さ 33・角 10・尾 7x10）が左右対称だったので、送信も同じ値にする。これは設計の判断として記録する（§12 の未実測）。
- 入力欄の自動の伸びは CSS `field-sizing: content` を使う。【事実】MDN（Context7 /mdn/content `field-sizing`）: textarea は幅で伸びられないと高さが伸び、高さの上限で中が流れる。`rows` は効かなくなる。【事実】caniuse（2026-11-01 取得）: Chrome 123〜・Android の Chrome 156・iOS Safari 26.2〜・Firefox 152〜。対応しないブラウザでは今と同じ2行の高さのまま（壊れない）。

## 4. トークン（ADR-067 :129-134 の手順）
- `frontend/src/tokens.css` の :root、`--comp-chat-bubble-line-height`（:177）の直後に §3 の新規 18 個を、各行に「何の値か＋出典（card-a2 §3）」のコメント付きで足す。色は足さない。@media の中でトークンを上書きしない。
- `tokens.css:177` のコメント末尾の「A-2 でスマホは実測 19px にする」を「スマホは --comp-chat-line-height-mobile」に直す。
- `docs/adr/ADR-067-design-token-enforcement.md` の表（:69 の行の直後）に同じ 18 個を1行ずつ足す。
- PR 本文の check:new-tokens の表を埋める。

## 5. 金型の変更

### 5-1 `frontend/src/components/ChatBubble.tsx`
props を2つ足す。どちらも thread 用で、既定は false（今の呼び出しは何も変わらない）。
```tsx
 * tail       : 続きの最初の吹き出し。スマホで尾を付ける（PC では何も変わらない）
 * inlineTime : 時刻を本文の最後の行の右下に入れる（スマホのみ。PC は今まで通り下の行）
```
- `tail && !panel && !failed` のとき class に `comp-chat-bubble--tail` を足す。
- `inlineTime && !panel && !failed && time !== undefined` のとき class に `comp-chat-bubble--inline-time` を足し、children の直後・Spinner の前に次を置く:
```tsx
<span className="comp-chat-bubble__time-spacer" aria-hidden="true">{time}</span>
```
  - 時刻と同じ中身を見えない形で置き、その幅だけ最後の行に場所を取る（WhatsApp と同じ作り）。
  - 読み上げには出ない（aria-hidden）。スマホでは visibility:hidden、PC では display:none なので、中に翻訳ボタンが写っても Tab 移動・押す対象にならない。
  - `inert` は付けない（@types/react 18.3.28 に無く、型で必ず落ちるため）。
- 冒頭の説明コメントに2行足す。そのほかは変えない。

### 5-2 BCSS
`@media (max-width: 767px)` の中（:64-76）に足す。全部 `:not(.comp-chat-bubble--panel)` を付ける（秘書を変えないため）。PC の規則（:1-62）は触らない。ただし PC で隙間の札を出さない規則 `.comp-chat-bubble__time-spacer { display: none; }` だけは @media の外、`.comp-chat-bubble--wide` の規則（:58-62）の直後・空行（:63）の前に足す（あとに来る @media の規則の方が詳しいので、stylelint の no-descending-specificity に当たらない）。
```css
  /* 文字も画像も: 角と尾の土台 */
  .comp-chat-bubble--outbound:not(.comp-chat-bubble--panel),
  .comp-chat-bubble--inbound:not(.comp-chat-bubble--panel) {
    position: relative;
    border-radius: var(--comp-chat-bubble-radius-mobile);
  }
  /* 文字の吹き出しだけ: 内側の余白と行の高さ（画像は次の段で決める） */
  .comp-chat-bubble--inline-time:not(.comp-chat-bubble--panel) {
    padding: var(--comp-chat-bubble-pad-y-mobile) var(--comp-chat-bubble-pad-x-mobile);
    line-height: var(--comp-chat-line-height-mobile);
  }
  /* 尾: 尾の側の上の角を 0 にし、外へ三角を出す（受信=左上 / 送信=右上） */
  .comp-chat-bubble--tail.comp-chat-bubble--inbound:not(.comp-chat-bubble--panel) { border-top-left-radius: 0; }
  .comp-chat-bubble--tail.comp-chat-bubble--outbound:not(.comp-chat-bubble--panel) { border-top-right-radius: 0; }
  .comp-chat-bubble--tail:not(.comp-chat-bubble--panel)::before {
    content: "";
    position: absolute;
    top: 0;
    width: var(--comp-chat-bubble-tail-w-mobile);
    height: var(--comp-chat-bubble-tail-h-mobile);
    background: inherit;
  }
  .comp-chat-bubble--tail.comp-chat-bubble--inbound:not(.comp-chat-bubble--panel)::before {
    right: 100%;
    clip-path: polygon(0 0, 100% 0, 100% 100%);
  }
  .comp-chat-bubble--tail.comp-chat-bubble--outbound:not(.comp-chat-bubble--panel)::before {
    left: 100%;
    clip-path: polygon(0 0, 100% 0, 0 100%);
  }
  /* 時刻を本文の最後の行の右下へ */
  .comp-chat-bubble--inline-time:not(.comp-chat-bubble--panel) .comp-chat-bubble__time {
    position: absolute;
    right: var(--comp-chat-time-inset-mobile);
    bottom: var(--comp-chat-time-bottom-mobile);
    margin-top: 0;
    font-size: var(--font-xs);
    line-height: var(--comp-chat-time-line-height-mobile);
  }
  .comp-chat-bubble--inline-time:not(.comp-chat-bubble--panel) .comp-chat-bubble__time-spacer {
    display: inline-block;
    visibility: hidden;
    padding-left: var(--space-6px);
    font-size: var(--font-xs);
    line-height: var(--comp-chat-time-line-height-mobile);
    vertical-align: bottom;
  }
```
- `background: inherit` で尾の色は本体の色（今のスマホの色）と同じになる。色の値は書かない。
- 送れなかった吹き出し（`comp-chat-bubble--failed`）はこの規則のどれにも当たらない（direction の class を持たないため。ChatBubble.tsx:49）。

### 5-3 ChatComposer.tsx
- `{leading}` を `{leading && <span className="comp-chat-composer__leading">{leading}</span>}` にする（スマホで隠すため）。

### 5-4 CCSS
- @media の外に `.comp-chat-composer__leading { display: contents; }`（PC は今と同じ並び）。
- `@media (max-width: 767px)`（:72-77）を次に置き換える。
```css
@media (max-width: 767px) {
  .send-top-row {
    gap: var(--space-2);
    padding: var(--space-1) var(--space-10px) var(--space-1) var(--space-2);
  }
  /* WhatsApp はピルの左に何も置かない（左 8 はピルの端） */
  .comp-chat-composer__leading { display: none; }
  .send-input-wrap {
    min-height: var(--comp-btn-height-lg);
    padding: 0 0 0 var(--space-14px);
    border-radius: var(--comp-chat-input-radius-mobile);
    align-items: flex-end;
    gap: 0;
  }
  .send-attach-btn {
    width: var(--comp-btn-height-lg);
    height: var(--comp-btn-height-lg);
  }
  .inbox-send-btn {
    width: var(--comp-btn-height-lg);
    height: var(--comp-btn-height-lg);
  }
  /* 入力欄の金型の embedded（FormField.css:286・詳しさ 0,2,0）に勝つため 3 つ重ねる */
  .send-input-wrap .comp-field__textarea.comp-textarea--embedded {
    field-sizing: content;
    max-height: var(--comp-chat-input-max-h-mobile);
    overflow-y: auto;
    margin-block: var(--comp-chat-input-inset-y-mobile);
    padding-block: var(--space-6px);
    font-size: var(--comp-chat-input-font-mobile);
    line-height: var(--comp-chat-input-line-height-mobile);
  }
}
```
- stylelint の `no-descending-specificity` が出たら、既存（:45・:65）と同じ形の理由付き disable コメントで対処する。それ以外の disable は足さない。

## 6. ページの変更

### 6-1 TSX（吹き出し）
- :536 `messagesData?.messages.map((msg) => {` を `messagesData?.messages.map((msg, i, list) => {` にし、直後に次を足す。
```tsx
          // 続きの最初と最後（向きが変わったところで切る）。スマホの尾と行の間に使う
          const groupStart = i === 0 || list[i - 1].direction !== msg.direction;
          const groupEnd = i === list.length - 1 || list[i + 1].direction !== msg.direction;
          const textOnly = msg.attachment_type !== "image";
```
- :555 の行の className に `${groupStart ? " group-start" : ""}${groupEnd ? " group-end" : ""}` を足す。
- :559 の `<ChatBubble` に `tail={groupStart}` と `inlineTime={textOnly}` を足す。
- :630 `<div>{msg.message_text || t("inbox.noBody")}</div>` を `<div className="msg-text">{msg.message_text || t("inbox.noBody")}</div>` にする。

### 6-2 TSX（入力欄）
- 変えない（`rows={2}` も残す。field-sizing が効くブラウザでは rows は効かない）。

### 6-3 PCSS（`@media (max-width: 767px)` の中・:1014 からの塊）
- :1075 `.msg-stack     { max-width: 85%; }` を `.msg-stack     { max-width: calc(100% - var(--comp-chat-bubble-max-gap-mobile)); }` にする。
- 同じ塊に足す:
```css
  /* 会話の行の間を WhatsApp の実測へ（card-a2 §3） */
  .inbox-messages {
    gap: 0;
    padding-left: var(--comp-chat-row-inset-mobile);
    padding-right: var(--comp-chat-row-inset-mobile);
  }
  .inbox-msg-row {
    padding-top: var(--comp-chat-row-gap-inner-mobile);
    padding-bottom: var(--comp-chat-row-gap-inner-mobile);
  }
  .inbox-msg-row.group-start { padding-top: var(--comp-chat-row-gap-group-mobile); }
  .inbox-msg-row.group-end { padding-bottom: var(--comp-chat-row-gap-group-mobile); }
  /* 時刻を本文の最後の行に入れるため、本文を行の流れに乗せる */
  .comp-chat-bubble--inline-time .msg-text { display: inline; }
  /* 帯の外枠をなくし、ピルを画面の左 8 に置く */
  .inbox-send-area { padding: 0; }
  .send-card { border: none; border-radius: 0; }
  /* 送れなかったときの帯は、外の余白 0 の前と同じ場所に置く（今の .inbox-send-area :561 の上 4・左右 12） */
  .inbox-send-error {
    margin-top: var(--space-1);
    margin-left: var(--space-3);
    margin-right: var(--space-3);
  }
```
- `.inbox-messages` の上下の余白（--space-4）は変えない。
- この塊にすでに `.inbox-messages` / `.inbox-send-area` / `.send-card` / `.inbox-send-error` の規則がある場合は、新しく足さずそこへ書き足す（実装前に `grep -n` で確かめて報告に書く）。

## 7. 墨の位置合わせ（Opus が端末で行う。実装役はしない）
1. 実装の PR の写しで Storybook を手元で起動し、`adb reverse tcp:6006 tcp:6006` で端末の Chrome に ChatBubble のスマホの見本（英字1行・英字の長文・送信1行）を出す。
2. 端末で撮り、measure-a2.md と同じ道具（PIL の画素読み）で、吹き出しの箱から本文の墨・時刻の墨までの画素を測る。
3. 目標は measure-a2.md「墨の位置」の表の値（受信: 本文の墨 左 31画素・上 29画素、時刻の墨 右 25画素・下 16画素）。±3画素（= ±1px）に入らなければ `--comp-chat-bubble-pad-x-mobile` と `--comp-chat-time-bottom-mobile` だけを 1px 刻みで直す。pad-y（7）は高さ 33 から決まるので動かさない。
4. 直した値と生出力を measure-a2.md に足し、同じ PR に入れる。

## 8. 受入条件（全部 ○ で完了）

| # | 基準 | 検証方法 |
|---|---|---|
| K1 | 幅360（端末の Chrome）で、受信1行の吹き出しの高さ 33・角 10・尾 7x10・左端 17・時刻が本文と同じ行 | §7 と同じ撮り方で画素を測り表にする（±3画素） |
| K2 | 続けて3件届いた会話で、尾は1件目だけ。吹き出しの間 8画素、境目 30画素 | 同上 |
| K3 | Discord 以外の会話（ハートが付かない会話）の長文の受信で幅 858画素（286）・最後の行の右下に時刻 | 同上（ハートは行の幅を取るため InboxPage.css:1829-1843・TSX:651、Discord の会話では測らない） |
| K4 | 入力欄 1行でピルの高さ 145画素（±3）・左端 24画素・送信の丸 144画素。改行ごとに 63画素伸び、入力欄そのもの（ピルではない）の高さ 663画素前後（実測 662）で止まる。伸びた形でもピルの角の丸みは 72画素（±3）で、文字が灰色の面の外に出ない | 端末の Chrome で打ち、送らずに消す。uiautomator ではなく撮った写真で測る |
| K5 | 本文の墨の位置が measure-a2.md「墨の位置」の表と ±3画素 | §7 |
| K6 | 新しい値はすべてトークン経由・直書き 0 件 | `npm run check:all`・ui-governance-gate・差分の grep（`style=`・数字＋px） |
| K7 | PC（幅1280）が前後で全画素一致。秘書のチャットも幅1280と幅360で全画素一致 | A-1 と同じ写真比べ（a1-parity-result.txt の方法） |
| K8 | 既存の試験が全部通る。ChatBubble.test に tail / inlineTime の試験を足す（class が付く・付かない、隙間の札が aria-hidden） | `npm test`・CI |
| K9 | PO が写真（受信の続き・長文・入力欄の1行と伸びた形）を見て合格 | 本番に出す前に PO に見せる |
| K10 | 送れなかったときの帯（`inbox-send-error`）を幅360で出し、帯の左右が画面の端から 12px・上が 4px（前と同じ）。帯の中の見た目は前後で全画素一致 | 前（base）と後を同じ画面で撮り比べる。違えば止めて報告 |

## 9. 変更してよいファイル（これ以外は触らない）
- frontend/src/components/ChatBubble.tsx・ChatBubble.css・ChatBubble.test.tsx・ChatBubble.stories.tsx（スマホの見本を足す）
- frontend/src/components/ChatComposer.tsx・ChatComposer.css・ChatComposer.test.tsx・ChatComposer.stories.tsx
  - ChatComposer.test.tsx:47-57（順番の試験）は §5-3 の span で落ちる。`kids[0]` を「`kids[0].className` が `comp-chat-composer__leading` で、その最初の子の data-testid が `lead`」に直す。kids[1]〜[3] の確かめは変えない。ほかの試験は触らない。
- frontend/src/pages/inbox/InboxMessageThread.tsx・InboxPage.css
- frontend/src/tokens.css・docs/adr/ADR-067-design-token-enforcement.md
- docs/handoff/inbox-deal-ui/thread-a/measure-a2.md（§7 の結果を足す）
- 見た目の基準写真（tests-e2e/visual-language の幅360のもの）が落ちた場合は、撮り直しの前に止めて報告（§10-3）

## 10. 想定される分かれ道（起きたら止めて報告）
1. ChatComposer.test.tsx の順番の試験以外に、§5-3 の span で落ちる試験がある → 落ちた試験名と生の出力を報告して止める。
2. stylelint・check:css-values が新しい規則を止める → 止めた規則名と行を報告。disable を足さない（§5-4 の1件を除く）。
3. 幅360の基準写真の試験が落ちる → 落ちた写真の名前を報告して止める（撮り直しは Opus が判断）。
4. 幅1280 の写真比べで 1画素でも違う → 違う場所を報告して止める。
5. 6-3 の規則が既存の同じ選択子に負けて効かない → 計算値を報告して止める。選択子を強くする変更は Opus が決める。
6. 秘書のチャットの写真に違いが出る → 止めて報告。

## 11. 戻し方
- この PR を戻す（revert）。DB・本番データ・API は触らない。

## 12. Architect 整合検査（同じ AI による自己審査・1回）
- 判定: **APPROVE（実装可能）**。PO の実装承認は別に要る。
- design §12 の未解決（U1〜U6）: U1・U2（受信）・U3（受信）・U4・U6 は実測済み（measure-a2.md）。U5 は §7 で実装後に端末で決める作りにした（値を推測で固定しない。初期値と動かすトークン2つ、合格の幅を決めてある）。
- 未実測で残るもの: 送信側の幅の上限と続き。U1 の左右対称 4 項目を根拠に同じ値を使う判断にした。K2・K3 は受信で判定する。PO が後日送信した長文があれば測り足す。
- 既存との整合: ADR-067（トークン・@media で上書きしない）、ADR-144（金型の中で直す・生の要素を足さない）、ADR-027（新しい言葉なし）、design §2 の対象外（色・B・C・D・画像）を守る。e2e の探し方（クラス名）は変えない。
- 自動の伸びは公式資料で確かめた（§3）。対応しないブラウザは今の2行のまま。
- 弊害: 時刻の見えない写しが DOM に1つ増える（読み上げ・Tab には出ない）。時刻に翻訳ボタン（`.msg-translate-btn`）が入る吹き出しでは、そのボタンも DOM に2つになる。e2e で `.msg-translate-btn` を探す試験は base に無い（審査で確認）。単体試験で `getByText` が時刻を2つ見つける場合があるので K8 で確かめる。
- 送れなかったときの帯は `.inbox-send-area` の余白 0 の影響を受けるので K10 で確かめる。
- 続きの区切り（§6-1）は向きだけで決める。送れなかった吹き出しも続きに数える。送れなかった吹き出しには尾を出さないので、それが続きの最初なら、その続きに尾は出ない。送れなかったことを目立たせる今の作りを優先した判断とする。
- 第3回（2回目の審査の指摘を反映）: ピルの角を伸びても 24 のままに（手元の写真 u4-max で測った）・画像に内側の余白を付けない・送れなかった帯の置き場所を保つ規則と K10 の判定・ADR-067 の行番号・ink.txt の出典を measure-a2.md に・K の並び・送れなかった吹き出しと続き。
- 第2回（審査の指摘を反映）: ChatComposer.test の許可と直し方・`inert` の削除・トークン 17 個・隙間の札の規則の置き場所・e2e の記述・K3 の会話の種類・K4 の測る物・送れなかった帯。

## 13. 追補: スマホで会話を開いている間は下のメニューを隠す（PO 2026-11-02）

### 13-1. 目的と出どころ
- PO の言葉（2026-11-02、K9 の写真を見て）: 「受信箱とか在庫表とかの下のメニューはメッセージ画面では非表示にして」。
- 本物の WhatsApp は会話の画面に下のメニューが無い（手元の並べ写真 /tmp/CC報告ファイル/inbox-deal-ui/a2card/eval/k9-side-2-composer.png。PO の会話を含むためコミットしない）。
- 対象: 幅 767px 以下（MobileShell）で、受信箱の会話を開いている間だけ。会話一覧・ほかの画面・PC は今のまま。

### 13-2. 今の作り（757ddd6b9 で確認）
- 下のメニューは `frontend/src/components/MobileShell.tsx:277` の `<nav className="mobile-tabbar">`。条件なしで描かれる。画面ごとに隠す仕組みは無い（import は `NavLink, Outlet` だけ・:33）。
- 外枠は `frontend/src/components/MobileShell.tsx:209` の `<div className="mobile-shell">`、中身は `:211-213` の `<main className="mobile-content"><Outlet /></main>`。
- 見た目は `frontend/src/mobile-shell.css:96-108`（`position: fixed; bottom: 0; height: var(--tabbar-height, 56px)`）。
- メニューの高さを前提にしている所は2つだけ（`git grep tabbar-height` の結果。FloatingActionButton.css:27 は受信箱で使っていない）:
  - `frontend/src/mobile-shell.css:25` `.mobile-content { padding-bottom: calc(var(--tabbar-height, 56px) + env(safe-area-inset-bottom, 0px)); }`
  - `frontend/src/components/PageLayout.css:78-80`（`@media (max-width: 767px)` の中）`.page-layout.page-layout--slim-header { height: calc(100dvh - var(--tabbar-height)); }`。slimHeaderOnMobile を使うのは受信箱だけ（`InboxPage.tsx:157`）。
- 「会話を開いている」の正は `selectedLeadId`（`useInboxState`）。`InboxPage.tsx:158` の `inbox-wrapper${selectedLeadId != null ? " thread-open" : ""}` と、`InboxPage.css:1052` の `.inbox-wrapper.thread-open .inbox-left-panel { display: none; }` がこれを使う。URL の `lead_id` はスマホで開いたときだけ書かれ、自動選択（PC）では書かれない（`useInboxState.ts:618-624`）ので、正には使わない。

### 13-3. 選んだ方法と理由
- 方法: MobileShell に「下のメニューを隠す」状態を1つ持たせ、子の画面が小さなフックで頼む。受信箱は `selectedLeadId` と同じ条件（スマホで会話を開いている）で頼む。
- 選ばなかった方法:
  - URL（`/lead-chat?lead_id=`）を MobileShell が読む: 正の状態（selectedLeadId）と別の場所を見ることになり、データの置き場が2つになる。数字でない `lead_id` のときに一覧でメニューが消える恐れがある。
  - CSS の `:has(.thread-open)` で MobileShell の外から隠す: 受信箱の CSS が殻の部品の中を直接触ることになり、どの画面が隠しているか読み取れない。単体試験で確かめられない。
- メニューは DOM から消さず、外枠の class で `display: none` にする（未読の数の読み込み・試験の探し方を変えないため）。

### 13-4. 変更（変更前 → 変更後）
1. 新しいファイル `frontend/src/hooks/useMobileTabbarHidden.ts`
   - `MobileTabbarContext`（`React.createContext<((hidden: boolean) => void) | null>(null)`）を export する。
   - `useHideMobileTabbar(hidden: boolean): void` を export する。中身: `const set = useContext(MobileTabbarContext); useEffect(() => { if (!set) return; set(hidden); return () => set(false); }, [set, hidden]);`
   - 冒頭のコメントに、目的（スマホで画面ごとに下のメニューを隠す）・出どころ（card-a2 §13・ADR-140 追記）・Provider が無い所（DesktopShell）では何もしないことを書く。
2. `frontend/src/components/MobileShell.tsx`
   - `const [tabbarHidden, setTabbarHidden] = useState(false);` を足す（:85-86 のシートの状態の並び）。
   - :209 `<div className="mobile-shell">` → `<div className={tabbarHidden ? "mobile-shell mobile-shell--tabbar-hidden" : "mobile-shell"}>`
   - :212 `<Outlet />` → `<MobileTabbarContext.Provider value={setTabbarHidden}><Outlet /></MobileTabbarContext.Provider>`
   - 冒頭の DOM 構造のコメント（:9-21）に `.mobile-shell--tabbar-hidden` で下のメニューを隠せることを1行足す。:277 の nav 自体は変えない。
3. `frontend/src/mobile-shell.css`（:108 の後ろ、`.mobile-tabbar` の規則の直後）に足す:
   ```css
   /* 画面が useHideMobileTabbar で頼んだ間だけ下のメニューを隠す（card-a2 §13・ADR-140 追記）。
      DOM には残す。本文の下の余白はメニューの高さを引き、端末の下端（safe-area）だけ残す。 */
   .mobile-shell--tabbar-hidden .mobile-tabbar {
     display: none;
   }
   .mobile-shell--tabbar-hidden .mobile-content {
     padding-bottom: env(safe-area-inset-bottom, 0px);
   }
   ```
4. `frontend/src/components/PageLayout.css` の `@media (max-width: 767px)` の中、:78-80 の直後に足す:
   ```css
   /* 下のメニューを隠している間（mobile-shell.css の .mobile-shell--tabbar-hidden）は、
      メニューの高さを引かず、端末の下端（safe-area）だけを引く。.mobile-content の
      padding-bottom と同じ値なので、はみ出さない（card-a2 §13）。 */
   .mobile-shell--tabbar-hidden .page-layout.page-layout--slim-header {
     height: calc(100dvh - env(safe-area-inset-bottom, 0px));
   }
   ```
5. `frontend/src/pages/inbox/InboxPage.tsx`
   - import に `import { useHideMobileTabbar } from "../../hooks/useMobileTabbarHidden";` を足す。
   - :69 `const isMobile = useIsMobile();` の直後に、コメント1行（スマホで会話を開いている間は下のメニューを隠す・PO 2026-11-02・card-a2 §13）と `useHideMobileTabbar(isMobile && selectedLeadId != null);` を足す。
6. 新しい色・余白のトークンは足さない（使う値は既存の `env(safe-area-inset-bottom, 0px)` と `100dvh` だけ。どちらも上の2か所で既に使っている形）。言葉（i18n）も足さない。

### 13-5. 試験
1. 新しいファイル `frontend/src/hooks/useMobileTabbarHidden.test.tsx`:
   - Provider の中で `useHideMobileTabbar(true)` → 渡した関数が true で呼ばれる。
   - hidden を true → false に変える → false で呼ばれる。
   - 外す（unmount）→ false で呼ばれる（ほかの画面へ移ったらメニューが戻る）。
   - Provider が無い所で呼んでも例外が出ない。
2. `frontend/src/components/MobileShell.test.tsx` に1件: Outlet の代わりに `useHideMobileTabbar(true)` を呼ぶ子を描くと、`.mobile-shell` に `mobile-shell--tabbar-hidden` が付き、`.mobile-tabbar` は DOM に残る。既存の `Outlet` のモック（:40-47）を使う形で足せない場合は、§13-7 の 1 で止める。
3. `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts` に1件（スマホの幅だけ・:128 の試験と同じ skip の書き方）:
   - 一覧では `.mobile-tabbar` が見える → `openConversation` → `.mobile-tabbar` が `toBeHidden()`、`.inbox-send-area` の下端が画面の高さと ±1px で一致 → 戻るボタン（`backButton`）→ `.mobile-tabbar` がまた見える。
4. 同じファイル :1417-1469 のカルテの試験は、会話を開いた後でメニューが隠れるため「覆う」の確かめ（:1450・:1461-1468）が意味を失う。:1450 と :1461-1468 を「`.mobile-tabbar` が `toBeHidden()`」の1行に置き換え、試験名を「スマホ: カルテが画面全体になる（下部タブバーは会話を開いた時点で隠れている）」に直す。:1449・:1455-1459 は変えない。

### 13-6. 受入条件
| # | 基準 | 検証方法 |
|---|---|---|
| N1 | 幅360の会話一覧で下のメニューが見える（今と同じ） | e2e :128 が通る。端末の写真 |
| N2 | 会話を開くと下のメニューが見えず、入力欄の帯の下端が画面の下端（±1px） | §13-5-3 の e2e。端末の写真で帯の下にメニューが無い |
| N3 | 戻るで一覧に戻るとメニューがまた見える | §13-5-3 の e2e |
| N4 | ほかの画面へ移るとメニューが戻る | §13-5-1 の外す試験 |
| N5 | PC 幅1280 は変わらない | e2e :772-792 が通る（MobileShell が描かれない） |
| N6 | 秘書のチャット・在庫表など受信箱以外のスマホ画面は変わらない | `useHideMobileTabbar` の呼び出しが InboxPage.tsx の1か所だけ（`git grep -n useHideMobileTabbar`） |
| N7 | check:all・stylelint・test:unit がすべて exit=0。CI が通る | 生出力 |
| N8 | PO が端末の写真を本物と並べて見て合格（K9 と一緒） | PO の返事 |

### 13-7. 想定される分かれ道（起きたら止めて報告）
1. MobileShell.test.tsx の Outlet のモックのせいで §13-5-2 の子を描けない → 試験の生の出力を添えて止める。モックの書き換えは Opus が決める。
   - **Opus の決定（2026-11-02、実装役の BLOCKED 報告を受けて）**: モックの書き換えを認める。形は次のとおり。ほかの形にしない。
     - ファイル先頭の `vi.mock` より前に `const outletState = vi.hoisted(() => ({ child: null as React.ReactNode }));` を置く（`React` の型が無ければ `import type { ReactNode } from "react"` を使い `as ReactNode`）。
     - :44 を `Outlet: () => <div data-testid="outlet">{outletState.child}</div>,` に変える。`data-testid="outlet"` は残す（既存の試験が使う）。
     - 試験ごとに戻すため `afterEach(() => { outletState.child = null; })` を足す（同じファイルに afterEach が既にあればその中に1行足す）。
     - 新しい1件は、`useHideMobileTabbar(true)` を呼んで `null` を返す小さな部品をファイル内に定義し、描画の前に `outletState.child = <その部品 />` を入れる。
     - 既存の試験の中身・期待値は変えない。
2. `.mobile-tabbar` が見えることを前提にしたほかの e2e（mobile-shell.spec.ts・inventory-raw-text-mobile.spec.ts）が落ちる → 試験名と生の出力を報告して止める（どちらも受信箱の会話を開かないので落ちない想定）。
3. 会話を開いた後、入力欄の帯の下に隙間が残る、または帯が画面の外に出る → 計算した高さを報告して止める。
4. lint の決まり（hooks の置き場・context の命名・`react-refresh/only-export-components` など）に止められる → 規則名と行を報告して止める。disable を足さない。

### 13-8. 変更してよいファイル（§9 に足す）
- frontend/src/hooks/useMobileTabbarHidden.ts（新規）・useMobileTabbarHidden.test.tsx（新規）
- frontend/src/components/MobileShell.tsx・MobileShell.test.tsx・frontend/src/mobile-shell.css・frontend/src/components/PageLayout.css
- frontend/src/pages/inbox/InboxPage.tsx
- frontend/tests-e2e/visual-language/inbox-single-column.spec.ts
- docs/adr/ADR-140-mobile-nav-bottom-tabs.md（追記は Opus が書く）

### 13-9. 戻し方
- この追補のコミットを戻す（revert）。下のメニューは今のとおり常に出る形に戻る。DB・API は触らない。

### 13-10. Architect 整合検査（同じ AI による自己審査・1回）
- 判定: **APPROVE（実装可能）**。
- ADR-137（殻の分離）: 状態は MobileShell の中だけ。DesktopShell には Provider が無く、フックは何もしない。
- ADR-140: 下のメニューの中身・順番・条件は変えない。会話を開いている間だけ隠す例外を ADR-140 に追記する（PO 2026-11-02 の言葉）。
- データの置き場: 「会話を開いている」の正は selectedLeadId の1つ。InboxPage.tsx:158 の thread-open と同じ式を使い、URL や別の状態を増やさない。
- ADR-067: 新しいトークンなし。値は既存の safe-area と 100dvh の形だけ。
- ADR-144: 新しい部品の見た目なし。生の要素を足さない。
- ADR-027: 新しい言葉なし。
- 弊害: 会話を開いている間は「…」のメニューに直接行けない。戻る1回で一覧とメニューに戻る。WhatsApp と同じ動き。
- 未確認: iPhone の safe-area の実測（手元に端末が無い）。Android の SC-51G で N2 を確かめる。

## 14. 追補: スマホでは入力欄の案内文を出さず、Enter は改行にする（PO 2026-11-02）

### 14-1. 目的と出どころ
- PO（並べた写真 k9-side-v2-1 を見て）: 「メッセージ入力前の入力欄に()でEnterで送信、Shift+Enterで改行と表示されているがこれはPCでの画面のみ有効なのでスマホの入力欄には何も表示させなくて良い、空白」
- PO（改行ボタンの扱いの3択に）: 「2」＝スマホでは改行ボタンで改行し、送信は送信ボタンだけにする。
- PO: 「使い分け方はLINEとWhatsappと同じでいい」＝スマホは Enter で改行・送信はボタン、PC は Enter で送信・Shift+Enter で改行。

### 14-2. 今の作り（bc37ef3bb で確認）
- `frontend/src/pages/inbox/InboxMessageThread.tsx:108` `const isMobile = useIsMobile();`（767px 以下で true。768 のタブレットは false）
- 同 :249-256 `handleKeyDownGuarded`: Enter（Shift なし・変換中でない）で `checkAndSend()`。それ以外は `handleKeyDown(e)`（`useInboxState.ts:867-872` も Enter で `submitSend()`）。スマホでも同じに動く。
- 同 :795-801 案内文: `discordChannelMissing ? t("inbox.discordChannelMissing") : canSend ? t("inbox.messagePlaceholder") : t("inbox.sendDisabled7d")`
- `ja.json:1288` / `en.json:1288` `inbox.messagePlaceholder` に Enter/Shift+Enter の説明が入っている。
- 同 :845-852 送信ボタンの title にも `inbox.messagePlaceholder` を使う（ホバーの説明。スマホでは出ない）→ 今回は触らない。
- Enter の動きを決めた ADR・仕様は無い（`git grep "Shift+Enter\|Enterで送信" docs/adr docs/specs` 0件）。

### 14-3. 変更（変更前 → 変更後）
1. :249-256
   ```tsx
   const handleKeyDownGuarded = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
     // スマホでは Enter は改行。送信は送信ボタンだけ（LINE・WhatsApp と同じ使い分け。PO 2026-11-02）
     if (isMobile) return;
     if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
       e.preventDefault();
       checkAndSend();
       return;
     }
     handleKeyDown(e);
   }, [isMobile, checkAndSend, handleKeyDown]);
   ```
2. :795-801 の `canSend ? t("inbox.messagePlaceholder")` を `canSend ? (isMobile ? undefined : t("inbox.messagePlaceholder"))` に変える。送れない理由の2つ（discordChannelMissing・sendDisabled7d）はスマホでも出したまま。
- 言葉（ja/en.json）・PC の動き・送信ボタン・`useInboxState.ts` は変えない。新しいトークン・部品なし。

### 14-4. 試験（`frontend/tests-e2e/visual-language/inbox-single-column.spec.ts` に足す。既存の試験は変えない）
- 「スマホ: 入力欄に案内文が出ず、Enter で改行され送信されない」（vl-mobile-390 のみ）: 会話を開く → textarea の placeholder 属性が無い（または空）→ `fill("a")`・`press("Enter")`・`type("b")` で値が `"a\nb"` → 送信の API がその間 0 回呼ばれる（呼ばれた回数は既存の送信モックに数えを足して確かめる。モックの場所は inbox-helpers を読んで決める）。
- 「PC・タブレット: 案内文は今のまま出る」（vl-tablet-768・vl-desktop-1280）: placeholder が ja.json の `inbox.messagePlaceholder` と一致。
- `send-guard-phase-a.spec.ts`（既定の幅）の Enter 送信の試験は変えずに通ること。

### 14-5. 受入条件
| # | 基準 | 検証方法 |
|---|------|---------|
| P1 | スマホ幅で入力欄の案内文が空 | 14-4 の e2e（CI の画面検査） |
| P2 | スマホ幅で Enter は改行・送信 0 回 | 14-4 の e2e |
| P3 | PC・タブレットの案内文と Enter 送信が今のまま | 14-4 の e2e ＋ send-guard-phase-a.spec.ts |
| P4 | 実機 SC-51G で、何も打っていない入力欄が空白・改行ボタンで改行され送信されない | 評価係が実機で測る（送信の API はモック。本物の送信はしない） |
| P5 | check:all・lint・tsc・unit が今のまま通る | 実装役の生の出力 |

### 14-6. 想定される分かれ道（起きたら止めて報告）
1. `TextareaControl` の型が placeholder に undefined を受けない → 型の生の出力を報告して止める（空文字や型の書き換えを勝手にしない）。
2. 既存の e2e が「スマホで Enter 送信」を前提にして落ちる → 試験名と生の出力を報告して止める。
3. 送信の API の呼ばれた回数を数える場所が inbox-helpers に無い → 今ある route を読んで数えを足す形を報告し、helpers の既存の動きを変えずに足せるならそのまま進める。変えずに足せないなら止める。

### 14-7. 変更してよいファイル（§9・§13-8 に足す）
- frontend/src/pages/inbox/InboxMessageThread.tsx
- frontend/tests-e2e/visual-language/inbox-single-column.spec.ts（と、14-6-3 で必要なら同じフォルダの inbox-helpers）

### 14-8. 戻し方
- この追補のコミットを戻す（revert）。スマホも Enter で送信・案内文ありの今の形に戻る。DB・API は触らない。

### 14-9. Architect 整合検査（同じ AI による自己審査・1回）
- 判定: **APPROVE（実装可能）**。
- 判定の正: スマホかどうかは既存の `useIsMobile()`（:108）の1つだけを使い、新しい判定を増やさない（ADR-137 の幅の境と同じ）。
- ADR-027: 言葉の追加・変更なし。スマホで案内文を出さないだけ。
- ADR-067 / ADR-144: 見た目・部品の追加なし。
- 弊害: スマホで送るには送信ボタンを押す必要がある（PO の指示どおり）。外付けキーボードをつないだスマホでも Enter は改行になる。
- 未確認: iPhone の改行ボタンの動き（手元に端末が無い）。

END OF CARD

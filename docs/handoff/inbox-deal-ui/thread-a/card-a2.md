---
mode: handoff
title: 受信箱 会話画面 A-2 — スマホの文字の吹き出しと入力欄を WhatsApp 実測へ
status: 実装カード（Opus 作成 2026-11-01・Architect 整合検査は §12）。PO の実装承認待ち
base: origin/main 85a560cb2
po_approval: 成功条件 A1〜A4 は PO 承認済み（2026-11-01）。このカードの作成は PO「1」（2026-11-01）。実装の承認はまだ。
---

# card A-2 — スマホの文字の吹き出しと入力欄を実測値へ

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・03-file.md・04-worktree.md・05-pr.md・10-executor.md。

受領確認: 実行役は作業の前に「card-a2 を受け取りました。base 85a560cb2 を確かめました」と1行返す。base が違えば何もせず停止して報告する。
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
- 画像の吹き出し（`msg.attachment_type === "image"`）の中身と並べ方。次の段で扱う。このカードでは尾と行の間だけが付く。
- 送れなかった吹き出し（failed）の見た目。尾も時刻の置き方の変更も付けない。
- 翻訳ボタン・翻訳結果（B で扱う）。既読の印（C で扱う。送信側の時刻の右に印の場所を空けない）。「＋」（D）。
- 送る・受ける・訳す・添付・ハート・長押しの動き。API・型・バックエンド・ja.json / en.json（新しい言葉は無い）。
- クラス名の付け替え（e2e が `send-top-row` 等で要素を探している）。

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
| 本文の左右の内側 | 初期値 9（§7 で 1px 刻みに決める） | ink.txt（受信の墨 左 10.3） | 新規 `--comp-chat-bubble-pad-x-mobile: 9px` |
| 時刻の文字・行 | 12 / 16 | design §3（measure-cal1）・U6（時刻の枠 16.3） | 既存 `--font-xs`、新規 `--comp-chat-time-line-height-mobile: 16px` |
| 時刻の置き方 | 本文の最後の行の右下。入らなければ次の行の右下 | U3（長文で最後の行に入る） | — |
| 時刻の右端 | 吹き出しの右端から 8（受信の実測。送信も同じ値＝印の場所は空けない） | U6 | 新規 `--comp-chat-time-inset-mobile: 8px` |
| 時刻の下端 | 初期値 3（§7 で決める） | ink.txt（墨の下 5.3） | 新規 `--comp-chat-time-bottom-mobile: 3px` |
| 本文と時刻の間 | 6 | U6（時刻の左の余白 6） | 既存 `--space-6px` |
| 入力欄の帯 | 上下 4・左 8・右 10、ピルと送信の間 8 | spec :99-100・2026-11-01 測り直し | 既存 `--space-1` `--space-2` `--space-10px` |
| ピル | 高さ 48（1行）・角は完全に丸・中のボタン 48x48 | U4 | 既存 `--comp-btn-height-lg` `--radius-full` |
| 入力の文字・行 | 18 / 21（1行増えるごとに 21 伸びる） | design §3（measure3）・U4 | 新規 `--comp-chat-input-font-mobile: 18px` / `--comp-chat-input-line-height-mobile: 21px` |
| 入力欄の上下の内側 | 6 ＋ ピルとの間 7.5（6+21+6+7.5x2 = 48） | U4（入力欄 32.3・ピル 48.3） | 既存 `--space-6px`、新規 `--comp-chat-input-inset-y-mobile: 7.5px` |
| 入力欄の伸び | 上へ伸び、高さ 221 で止まり中で流れる | U4（220.7） | 新規 `--comp-chat-input-max-h-mobile: 221px` |
| 送信の丸 | 直径 48 | design §3 | 既存 `--comp-btn-height-lg` |

- 送信側の幅の上限と送信側の続きは測れていない（PO の端末から送らないため）。U1 で送信と受信の 4 項目（端の 17・高さ 33・角 10・尾 7x10）が左右対称だったので、送信も同じ値にする。これは設計の判断として記録する（§12 の未実測）。
- 入力欄の自動の伸びは CSS `field-sizing: content` を使う。【事実】MDN（Context7 /mdn/content `field-sizing`）: textarea は幅で伸びられないと高さが伸び、高さの上限で中が流れる。`rows` は効かなくなる。【事実】caniuse（2026-11-01 取得）: Chrome 123〜・Android の Chrome 156・iOS Safari 26.2〜・Firefox 152〜。対応しないブラウザでは今と同じ2行の高さのまま（壊れない）。

## 4. トークン（ADR-067 :125-133 の手順）
- `frontend/src/tokens.css` の :root、`--comp-chat-bubble-line-height`（:177）の直後に §3 の新規 15 個を、各行に「何の値か＋出典（card-a2 §3）」のコメント付きで足す。色は足さない。@media の中でトークンを上書きしない。
- `tokens.css:177` のコメント末尾の「A-2 でスマホは実測 19px にする」を「スマホは --comp-chat-line-height-mobile」に直す。
- `docs/adr/ADR-067-design-token-enforcement.md` の表（:69 の行の直後）に同じ 15 個を1行ずつ足す。
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
<span className="comp-chat-bubble__time-spacer" aria-hidden="true" inert>{time}</span>
```
  - 時刻と同じ中身を見えない形で置き、その幅だけ最後の行に場所を取る（WhatsApp と同じ作り）。読み上げ・Tab 移動・押す対象にならない（aria-hidden・inert）。
  - React 18 の型で `inert` が通らない場合は分かれ道 §10-1。
- 冒頭の説明コメントに2行足す。そのほかは変えない。

### 5-2 BCSS
`@media (max-width: 767px)` の中（:64-76）に足す。全部 `:not(.comp-chat-bubble--panel)` を付ける（秘書を変えないため）。PC の規則（:1-62）は触らない。ただし PC で隙間の札を出さない規則 `.comp-chat-bubble__time-spacer { display: none; }` だけは @media の外に足す。
```css
  .comp-chat-bubble--outbound:not(.comp-chat-bubble--panel),
  .comp-chat-bubble--inbound:not(.comp-chat-bubble--panel) {
    position: relative;
    padding: var(--comp-chat-bubble-pad-y-mobile) var(--comp-chat-bubble-pad-x-mobile);
    line-height: var(--comp-chat-line-height-mobile);
    border-radius: var(--comp-chat-bubble-radius-mobile);
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
    border-radius: var(--radius-full);
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
```
- `.inbox-messages` の上下の余白（--space-4）は変えない。
- この塊にすでに `.inbox-messages` / `.inbox-send-area` / `.send-card` の規則がある場合は、新しく足さずそこへ書き足す（実装前に `grep -n` で確かめて報告に書く）。

## 7. 墨の位置合わせ（Opus が端末で行う。実装役はしない）
1. 実装の PR の写しで Storybook を手元で起動し、`adb reverse tcp:6006 tcp:6006` で端末の Chrome に ChatBubble のスマホの見本（英字1行・英字の長文・送信1行）を出す。
2. 端末で撮り、ink.txt と同じ道具で、吹き出しの箱から本文の墨・時刻の墨までの画素を測る。
3. 目標は ink.txt の値（受信: 本文の墨 左 31画素・上 29画素、時刻の墨 右 25画素・下 16画素）。±3画素（= ±1px）に入らなければ `--comp-chat-bubble-pad-x-mobile` と `--comp-chat-time-bottom-mobile` だけを 1px 刻みで直す。pad-y（7）は高さ 33 から決まるので動かさない。
4. 直した値と生出力を measure-a2.md に足し、同じ PR に入れる。

## 8. 受入条件（全部 ○ で完了）

| # | 基準 | 検証方法 |
|---|---|---|
| K1 | 幅360（端末の Chrome）で、受信1行の吹き出しの高さ 33・角 10・尾 7x10・左端 17・時刻が本文と同じ行 | §7 と同じ撮り方で画素を測り表にする（±3画素） |
| K2 | 続けて3件届いた会話で、尾は1件目だけ。吹き出しの間 8画素、境目 30画素 | 同上 |
| K3 | 長文の受信で幅 858画素（286）・最後の行の右下に時刻 | 同上 |
| K4 | 入力欄 1行でピルの高さ 145画素（±3）・左端 24画素・送信の丸 144画素。改行ごとに 63画素伸び、上限 663画素前後で止まる | 端末の Chrome で打ち、送らずに消す。uiautomator ではなく撮った写真で測る |
| K5 | 本文の墨の位置が ink.txt と ±3画素 | §7 |
| K6 | 新しい値はすべてトークン経由・直書き 0 件 | `npm run check:all`・ui-governance-gate・差分の grep（`style=`・数字＋px） |
| K7 | PC（幅1280）が前後で全画素一致。秘書のチャットも幅1280と幅360で全画素一致 | A-1 と同じ写真比べ（a1-parity-result.txt の方法） |
| K8 | 既存の試験が全部通る。ChatBubble.test に tail / inlineTime の試験を足す（class が付く・付かない、隙間の札が aria-hidden） | `npm test`・CI |
| K9 | PO が写真（受信の続き・長文・入力欄の1行と伸びた形）を見て合格 | 本番に出す前に PO に見せる |

## 9. 変更してよいファイル（これ以外は触らない）
- frontend/src/components/ChatBubble.tsx・ChatBubble.css・ChatBubble.test.tsx・ChatBubble.stories.tsx（スマホの見本を足す）
- frontend/src/components/ChatComposer.tsx・ChatComposer.css・ChatComposer.stories.tsx
- frontend/src/pages/inbox/InboxMessageThread.tsx・InboxPage.css
- frontend/src/tokens.css・docs/adr/ADR-067-design-token-enforcement.md
- docs/handoff/inbox-deal-ui/thread-a/measure-a2.md（§7 の結果を足す）
- 見た目の基準写真（tests-e2e/visual-language の幅360のもの）が落ちた場合は、撮り直しの前に止めて報告（§10-3）

## 10. 想定される分かれ道（起きたら止めて報告）
1. `inert` が型で通らない → `{...({ inert: "" } as Record<string, string>)}` などで回避せず、止めて報告。
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
- 弊害: 時刻の見えない写しが DOM に1つ増える（読み上げ・Tab には出ない）。単体試験で `getByText` が時刻を2つ見つける場合があるので K8 で確かめる。

END OF CARD

---
mode: handoff
title: 受信箱 会話画面 A-1 追補 — 吹き出しの金型 ChatBubble を1つにまとめる（受信箱と秘書のチャットの見た目は変えない）
status: 実装カード（Opus 作成 2026-11-01・Architect 整合検査は §11）
base: release/inbox-chat-molds-a1 ad4eef6673794cfca149341958a1190c9759540b ＋ origin/main fbee46fce
po_approval: 2026-11-01 PO「1」（2つの吹き出し金型を1つにする。受信箱の金型を土台に広げ、秘書のチャットの見た目は変えない）＋同日「PRマージ、デプロイまで完走させてくれ」（実装承認）
---

# card A-1 追補 — ChatBubble を1つにまとめる

根拠: card-a1.md（同じフォルダ）・design.md §4-1。行番号は、ad4eef667 の側は「A1:」、origin/main fbee46fce の側は「M:」を付ける。

## 1. 何が起きたか（事実）
- A-1（PR #4974・ad4eef667）が `frontend/src/components/ChatBubble.{tsx,css,stories.tsx,test.tsx}` を新しく作った。
- その間に秘書のチャット（ADR-1056・PR #4976）が**同じ名前の別の金型**を main に入れた（M: `frontend/src/components/ChatBubble.tsx:12-34`）。
- そのため #4974 は main と衝突してマージできない（2026-11-01 PO の `!` 実行で "Pull Request has merge conflicts"）。
- 同じ役目の金型が2つあると SSOT に反する。PO は「1つにまとめる」を選んだ。

## 2. 2つの金型の違い（M と A1 を1行ずつ比べた結果）

| 項目 | 受信箱（A1: ChatBubble.css） | 秘書（M: ChatBubble.css） | まとめた後 |
|---|---|---|---|
| クラス名 | `msg-bubble` `msg-time` | `comp-chat-bubble` | `comp-chat-bubble`（components/*.css 38個中 32個が `comp-` で始まる慣習に合わせる） |
| 色・角（送信） | `--bubble-outbound-bg` `--on-accent` `--radius-bubble-out`（A1:16-20） | 同じ（M:19-24） | 共通の1規則 |
| 色・角（受信） | `--bubble-inbound-bg` `--text-primary` `--radius-bubble-in`（A1:22-26） | 同じ（M:26-31） | 共通の1規則 |
| 余白・字の大きさ・折り返し | `--space-2` `--space-3` `--font-md` `break-word` `pre-wrap`（A1:7-14） | 同じ（M:2-13） | 共通 |
| 行の間隔 | `var(--comp-chat-bubble-line-height)`（=1.45） | `1.45` の直書き（M:10） | トークンに統一（値は同じ 1.45） |
| 幅の上限 | 70%（A1:8。受信箱のページは `.msg-stack` 側で 70%、吹き出しは 100% に上書き） | 80%（M:7） | 受信箱 70%／秘書 80% のまま |
| 並べ方 | なし（ページの行が並べる） | flex・中央そろえ・間 `--space-2`・`border-box`・左右の自動の余白（M:3-6・20・27） | 秘書の形だけに付ける |
| 時刻の行 | あり（A1:33-39） | なし | 渡したときだけ出す |
| 送れなかった | 赤の地＋赤の枠 2px＋角 `--radius-xl`（A1:27-32） | 文字だけ赤（M:33-35） | それぞれ今のまま |
| 考え中の印 | なし | 回る印（M:31 `Spinner size="sm" tone="inherit" decorative`） | 渡したときだけ出す |
| スマホの色 | 幅 767px 以下で送信 `--accent`・受信 `--neutral-bg`（A1:41-52） | なし | 受信箱の形だけに付ける |
| 中身の入れ物 | なし（children を直に置く） | `comp-chat-bubble__body`（`min-width: 0`） | 秘書の形だけに付ける |
| 広い吹き出し（下書きの票） | なし | 呼ぶ側の `.secretary-chat__draft-bubble`（M: SecretaryChat.css:15-19: 幅 100%・`white-space: normal`）。`.comp-chat-bubble`（M: ChatBubble.css:2-13）と詳しさが同じ 0,1,0 で、今は後から読まれる下書きの票の側が勝つ（SecretaryChat.tsx:14 で金型を先に、:30 で自分の CSS を後に読むため） | 金型の `wide` に移す（同じファイルの `--panel` より後ろに置くので、読む順に関係なく勝つ） |

## 3. まとめた金型（このとおりに書く）

### 3-1 `frontend/src/components/ChatBubble.tsx`（全文を置き換え）
```tsx
/**
 * ChatBubble — 会話の吹き出し金型（ADR-144・ADR-067）
 *
 * layout    : thread（受信箱の会話。並べ方はページの行が持つ）/ panel（秘書のチャット。左右に自分で寄る）
 * direction : inbound（相手・AI から）/ outbound（自分から）。時刻の寄せ方もこれで決まる
 * failed    : 送れなかった吹き出し。thread は赤の地と枠、panel は文字だけ赤
 * pending   : 返事を待っている間の回る印を出す
 * wide      : 吹き出しを横いっぱいにする（下書きの票などを入れるとき）
 * time      : 吹き出しの下端に出す時刻の行の中身。渡さなければ行を出さない
 * children  : 本文・画像・訳など吹き出しの中身
 * そのほかの div の属性（role・title・長押しの手当て）はそのまま外側の div に付ける。
 *
 * 言葉は持たない。文言は呼ぶ側が children / time で渡す（ADR-027）。
 * 業務の意味（どの経路のメッセージか等）はこの金型に埋め込まない。
 */
import type { HTMLAttributes, ReactNode } from 'react';
import { Spinner } from './loading';
import './ChatBubble.css';

export type ChatBubbleDirection = 'inbound' | 'outbound';
export type ChatBubbleLayout = 'thread' | 'panel';

export interface ChatBubbleProps extends Omit<HTMLAttributes<HTMLDivElement>, 'className' | 'children'> {
  direction: ChatBubbleDirection;
  layout?: ChatBubbleLayout;
  failed?: boolean;
  pending?: boolean;
  wide?: boolean;
  time?: ReactNode;
  children: ReactNode;
}

export function ChatBubble({
  direction,
  layout = 'thread',
  failed = false,
  pending = false,
  wide = false,
  time,
  children,
  ...rest
}: ChatBubbleProps) {
  const outbound = direction === 'outbound';
  const panel = layout === 'panel';
  const classes = [
    'comp-chat-bubble',
    panel ? 'comp-chat-bubble--panel' : '',
    // thread の failed は色を丸ごと置き換える（送信・受信の色を付けない）。panel の failed は色を残して文字だけ赤くする
    panel || !failed ? `comp-chat-bubble--${direction}` : 'comp-chat-bubble--failed',
    panel && failed ? 'comp-chat-bubble--error' : '',
    wide ? 'comp-chat-bubble--wide' : '',
  ]
    .filter(Boolean)
    .join(' ');
  return (
    <div {...rest} className={classes}>
      {panel ? <div className="comp-chat-bubble__body">{children}</div> : children}
      {pending && <Spinner size="sm" tone="inherit" decorative />}
      {time !== undefined && (
        <div className={`comp-chat-bubble__time${outbound ? '' : ' comp-chat-bubble__time--inbound'}`}>{time}</div>
      )}
    </div>
  );
}
```

### 3-2 `frontend/src/components/ChatBubble.css`（全文を置き換え）
規則の中身は A1:6-52 と M:1-35 から**値を1つも変えずに**写す。並び順も下のとおりにする（後ろの規則が勝つ前提で並べている）。
```css
/**
 * ChatBubble — 会話の吹き出し（受信箱の会話・秘書のチャットで共通）
 * ADR-067: 全カラー・寸法は CSS 変数参照のみ
 */

/* Meta実測: バブル 16px / padding=8px 12px */
.comp-chat-bubble {
  max-width: 70%;
  padding: var(--space-2) var(--space-3);
  font-size: var(--font-md);
  line-height: var(--comp-chat-bubble-line-height);
  word-break: break-word;
  white-space: pre-wrap;
}
/* outbound バブル */
.comp-chat-bubble--outbound {
  background: var(--bubble-outbound-bg);
  color: var(--on-accent);
  border-radius: var(--radius-bubble-out);
}
/* inbound バブル */
.comp-chat-bubble--inbound {
  background: var(--bubble-inbound-bg);
  color: var(--text-primary);
  border-radius: var(--radius-bubble-in);
}
.comp-chat-bubble--failed {
  background: var(--danger-bg);
  color: var(--danger-text);
  border: 2px solid var(--danger);
  border-radius: var(--radius-xl);
}
.comp-chat-bubble__time {
  font-size: var(--font-2xs);
  opacity: var(--opacity-muted);
  margin-top: var(--space-1);
  text-align: right;
}
.comp-chat-bubble__time--inbound { text-align: left; }

/* panel: 秘書のチャット。吹き出しが自分で左右に寄り、中身と回る印を横に並べる */
.comp-chat-bubble--panel {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  box-sizing: border-box;
  max-width: 80%;
}
.comp-chat-bubble--panel.comp-chat-bubble--outbound { margin-left: auto; }
.comp-chat-bubble--panel.comp-chat-bubble--inbound { margin-right: auto; }
.comp-chat-bubble__body {
  min-width: 0;
}
.comp-chat-bubble--error {
  color: var(--danger-text);
}
/* wide: 下書きの票など、横いっぱいに使う中身 */
.comp-chat-bubble--wide {
  max-width: 100%;
  width: 100%;
  white-space: normal;
}

@media (max-width: 767px) {
  /* A1:42-49 のコメントをそのまま写す（「4. 吹き出しを「地・面・強調色」の3役に…」から「PC は ADR-064 … 触らない。」まで） */
  /* 秘書のチャット（panel）はこの上書きを受けない（まとめる前と同じ） */
  .comp-chat-bubble--outbound:not(.comp-chat-bubble--panel) { background: var(--accent); }
  .comp-chat-bubble--inbound:not(.comp-chat-bubble--panel)  { background: var(--neutral-bg); }
}
```
- 上の `/* A1:42-49 … */` の1行は、A1:42-49 のコメント本文に置き換える（中身を一字も変えない）。
- 詳しさ（どの規則が勝つか）の確認: thread の failed は送信・受信のクラスを持たないので、スマホの上書き（詳しさ 0,2,0）に当たらない（A1 と同じ）。panel の `--error`（0,1,0）は `--inbound`（0,1,0）より後ろにあるので勝つ（M と同じ）。`--wide`（0,1,0）は `--panel`（0,1,0）より後ろなので幅で勝つ。

### 3-3 ストーリー `frontend/src/components/ChatBubble.stories.tsx`（全文を置き換え）
- A1 の5つ（Inbound / Outbound / Failed / LongText / TimeWithButton）をそのまま残す（args は今のまま。layout を書かない＝thread）。
- M の4つを panel として足す: `PanelAssistant`（`layout: 'panel', direction: 'inbound', time: undefined, children: 'ここに返事が入ります。'`）・`PanelUser`（`layout: 'panel', direction: 'outbound', time: undefined, children: 'ここに質問が入ります。'`）・`PanelSending`（`layout: 'panel', direction: 'outbound', pending: true, time: undefined`）・`PanelError`（`layout: 'panel', direction: 'inbound', failed: true, time: undefined, children: '失敗しました。'`）。panel の5つはすべて `layout: 'panel'` と `time: undefined` を書く（全体の初期値 `time: '5 min ago'` を引き継がないため）。
- 1つ足す: `PanelWide`（`layout: 'panel', direction: 'inbound', wide: true, time: undefined, children: 'A wide bubble for a draft form.'`）。
- 先頭のコメントの「状態:」の行に panel の5つを書き足す。

### 3-4 単体試験 `frontend/src/components/ChatBubble.test.tsx`（全文を置き換え）
A1 の4つをクラス名だけ置き換えて残し、M の4つを panel 版にして足す。
- (1) inbound: 外側 `comp-chat-bubble comp-chat-bubble--inbound`・時刻 `comp-chat-bubble__time comp-chat-bubble__time--inbound`
- (2) outbound: 外側 `comp-chat-bubble comp-chat-bubble--outbound`・時刻 `comp-chat-bubble__time`
- (3) failed は direction に関係なく外側 `comp-chat-bubble comp-chat-bubble--failed`
- (4) role・title・onPointerDown が外側の div に付く
- (5) time を渡さなければ `.comp-chat-bubble__time` が無い
- (6) panel: 子が `.comp-chat-bubble__body` の中に出る・外側が `comp-chat-bubble comp-chat-bubble--panel comp-chat-bubble--outbound`（inbound も同様）
- (7) pending のときだけ `.sa-spinner` が出る（M: ChatBubble.test.tsx:22-27 と同じ確かめ方）
- (8) panel の failed は `comp-chat-bubble--inbound` と `comp-chat-bubble--error` を両方持ち、`comp-chat-bubble--failed` を持たない
- (9) wide で `comp-chat-bubble--wide` が付く

## 4. 呼ぶ側の書き換え

### 4-1 受信箱 `frontend/src/pages/inbox/InboxMessageThread.tsx`
- 変えない（A1:559-650 の `<ChatBubble direction=… failed=… role=… title=… time=…>` のまま。layout は既定の thread）。

### 4-2 受信箱 `frontend/src/pages/inbox/InboxPage.css`
- A1:1826 `.msg-stack .msg-bubble { max-width: 100%; min-width: 0; }` → `.msg-stack .comp-chat-bubble { max-width: 100%; min-width: 0; }`（クラス名だけ）。ほかは触らない。

### 4-3 秘書 `frontend/src/features/secretary/SecretaryChat.tsx`（M:109-149 の5か所）

| M の行 | 変更前 | 変更後 |
|---|---|---|
| 109 | `<ChatBubble key={m.id} side="user">` | `<ChatBubble key={m.id} layout="panel" direction="outbound">` |
| 117 | `<ChatBubble key={m.id} side="assistant" status={m.status}>` | `<ChatBubble key={m.id} layout="panel" direction="inbound" pending={m.status === "sending"} failed={m.status === "error"}>` |
| 123 | `<ChatBubble key={m.id} side="assistant" className="secretary-chat__draft-bubble">` | `<ChatBubble key={m.id} layout="panel" direction="inbound" wide>` |
| 134 | 同上 | 同上 |
| 144 | `<ChatBubble key={m.id} side="assistant">` | `<ChatBubble key={m.id} layout="panel" direction="inbound">` |

- M:7 のコメント「エラー表示（status="error"）は AI 側の吹き出しにだけ使う。…」は「エラー表示（failed）は AI 側の吹き出しにだけ使う。利用者側の吹き出しには付けない。」に直す。
- `ChatMessage` 型（M:32-37）の `status?: "sending" | "error"` は会話の状態なので変えない。

### 4-4 秘書 `frontend/src/features/secretary/SecretaryChat.css`
- M: SecretaryChat.css:15-19 の `.secretary-chat__draft-bubble { … }` を消す（金型の `--wide` に移った）。前後の空行を1つにそろえる。ほかは触らない。

### 4-5 秘書の試験 `frontend/src/features/secretary/SecretaryChat.test.tsx`
- M:170 `.comp-chat-bubble--user.comp-chat-bubble--error` → `.comp-chat-bubble--outbound.comp-chat-bubble--error`
- M:171 `.comp-chat-bubble--assistant.comp-chat-bubble--error` → `.comp-chat-bubble--inbound.comp-chat-bubble--error`
- M:145 `.comp-chat-bubble b` は変えない。

## 5. 作業の順番
1. `release/inbox-chat-molds-a1` の先頭から始める。先頭は ad4eef667 の上に、このカードと design.md だけを足した docs の commit が乗った状態であること（`git log --oneline ad4eef667..HEAD` と `git diff --name-only ad4eef667 HEAD` で確かめる。docs/handoff/inbox-deal-ui/thread-a/ の外のファイルが出たら止まる）。
2. 比べる前の写真と値を取る（§7 の before）。**origin/main fbee46fce の写し**で取る（受信箱も秘書も、今の本番と同じコード）。
3. `git merge origin/main`（merge commit。rebase・force push はしない）。衝突は §3 の全文で解く。`docs/adr/README.md` の衝突は `node scripts/generate-adr-index.js` で作り直して解く。en.json・ja.json・tokens.css は自動で混ざることを `git diff` で確かめる（`--comp-chat-bubble-line-height` が1行だけあること・`humanAgentLabel` が無いこと）。
4. §4 の書き換え。
5. §6 の受入条件を全部回す。

## 6. 受入条件（全部 ○ で完了）

| 基準 | 検証方法 |
|---|---|
| U1 受信箱の見た目が変わらない | card-a1.md §7 の写真比べ（判定の決まり第3版: a1-parity-result.txt 冒頭）を before=fbee46fce・after=作業後 HEAD でやり直し、6場面すべて ○。比べの一時 spec は吹き出しの四角を `.comp-chat-bubble`（after）・`.msg-bubble`（before）で取る。結果を `docs/handoff/inbox-deal-ui/thread-a/a1-parity-result.txt` に上書きする |
| U2 秘書のチャットの見た目が変わらない | §7 の写真比べで4枚すべて違う画素 0、かつ値比べで違う値 0。結果を `docs/handoff/inbox-deal-ui/thread-a/a1-secretary-parity-result.txt` に書く |
| U3 金型は1つ | `git grep -n "msg-bubble\|msg-time" -- frontend/src` の行が `frontend/src/pages/inbox/InboxMessageThread.tsx` の `msg-bubble-line` と `frontend/src/pages/inbox/InboxPage.css` の `msg-bubble-line`・コメントだけ。`git grep -n "side=\"user\"\|side=\"assistant\"\|secretary-chat__draft-bubble" -- frontend/src` が 0件。`frontend/src/components/` に吹き出しの金型は ChatBubble だけ |
| U4 直書きが無い | check:css-colors・check:css-values が通る。かつ `git grep -n "1.45" -- frontend/src/components/ChatBubble.css` が 0件（枠の `2px` と `@media` の `767px` は A1 から写す値なので対象外） |
| U5 点検が全部通る | card-a1.md §6 K5 と同じ（`npm run check:all`・型検査・`npm run test:unit`・`node scripts/check-ui-governance.js`） |
| U6 既存の試験が通る | card-a1.md §6 K6 に加えて `src/features/secretary/SecretaryChat.test.tsx`・`src/components/ChatBubble.test.tsx` が通る |
| U7 触らない範囲を守った | 次の2つとも ○。(a) 本線を取り込んだ後に直したファイル: `git diff --name-only <取り込みの commit> HEAD` が §8 の一覧に収まる。(b) 取り込みで衝突を解いたファイル: 取り込みの時に `git diff --name-only --diff-filter=U` で出た一覧（生のまま報告に貼る）が §3・§8 の一覧に収まる。PR 本文には `git diff --name-only fbee46fce...HEAD` も参考として載せる |

## 7. 写真比べと値比べのやり方（U2・秘書のチャット）
1. 一時的な見本ページを作る（**コミットしない**）: `frontend/parity-secretary.html`（`<div id="root"></div>` と `<script type="module" src="/src/parity-secretary.tsx"></script>`）と `frontend/src/parity-secretary.tsx`。
2. `parity-secretary.tsx` は `frontend/src/main.tsx` と同じ順で全体の CSS を読む（M: main.tsx:4-5 `./index.css`・`./loading-animations.css`）。そのあと SecretaryChat.tsx と同じ順で読む: 先に `ChatBubble`（M: SecretaryChat.tsx:14。金型の CSS がここで読まれる）、後に `./features/secretary/SecretaryChat.css`（M: SecretaryChat.tsx:30）。この順を逆にしない（下書きの票の幅がどちらの規則で決まるかが変わるため）。読んだあと、幅 400px の箱の中に `<div className="secretary-chat__messages">` を置き、次の6つを並べる:
   - (a) 利用者の文 `Please make an invoice for Tanaka.`
   - (b) AI 考え中 `Thinking…`（回る印つき）
   - (c) AI エラー `Something went wrong.`
   - (d) AI 長い文（`LongText` ストーリーと同じ文）
   - (e) AI 広い吹き出し: 中に `<div className="secretary-draft"><p className="secretary-draft__title">Draft</p><p className="secretary-draft__text">Item A × 2</p></div>`
   - (f) AI 作った知らせ `Created. ` ＋ `<a href="#x">Open</a>`
   - before（fbee46fce）は M の書き方（`side`・`status`・`className="secretary-chat__draft-bubble"`）、after は §4-3 の書き方。中身の文と並びは同じにする。
3. `cd frontend && npx vite --port 5199 --strictPort` で開き、Playwright で `/parity-secretary.html` を撮る: 幅 1280 と幅 390 × 明るい色・暗い色（`colorScheme: 'light' | 'dark'`）= 4枚。回る印は撮る前に `animation: none` を一時ページ側の `<style>` で止める（before と after で同じ）。
4. 値比べ: 6つの吹き出しそれぞれについて、外側・中身の入れ物・回る印の要素の `getComputedStyle` の全項目を JSON にして、before と after で項目ごとに比べる。違う項目の数を数える。
4b. 本番用に組み立てた CSS でも順を確かめる: before（fbee46fce）と after でそれぞれ `cd frontend && npm run build` し、`dist/assets/*.css` の中で `.comp-chat-bubble{`・`.secretary-chat__draft-bubble{`・`.comp-chat-bubble--panel{`・`.comp-chat-bubble--wide{` が出てくる位置（文字の位置）を `grep -bo` で記録する。before は `.comp-chat-bubble{` が `.secretary-chat__draft-bubble{` より前、after は `.secretary-chat__draft-bubble{` が無く `.comp-chat-bubble--panel{` が `.comp-chat-bubble--wide{` より前なら ○。比べる語は同じ CSS ファイルの中で見つかること（before は `.comp-chat-bubble{` と `.secretary-chat__draft-bubble{`、after は `.comp-chat-bubble--panel{` と `.comp-chat-bubble--wide{`）。ファイルが分かれていたら止まる。違えば止まる。
5. 画素はしきい値 0・許容なしで比べる（A-1 と同じ pngjs）。4枚の違う画素の数と値比べの違う項目の数を生のまま結果ファイルに書く。写真はコミットしない。
6. 0 でないものが1つでもあれば**止めて報告する**（自分で規則を書き換えて合わせない）。

## 8. 変更してよいファイル（これ以外は触らない）
- 置き換え: `frontend/src/components/ChatBubble.tsx` `ChatBubble.css` `ChatBubble.stories.tsx` `ChatBubble.test.tsx`
- 変更: `frontend/src/pages/inbox/InboxPage.css`（§4-2 の1行）・`frontend/src/features/secretary/SecretaryChat.tsx` `SecretaryChat.css` `SecretaryChat.test.tsx`・`docs/adr/README.md`（作り直し）
- 書き直し・新規: `docs/handoff/inbox-deal-ui/thread-a/a1-parity-result.txt`・`docs/handoff/inbox-deal-ui/thread-a/a1-secretary-parity-result.txt`
- それ以外の A-1 のファイル（ChatComposer・InboxMessageThread.tsx・tokens.css・locales・ADR-067・scene7 spec）は merge の結果のまま触らない。

## 9. 想定される分かれ道（起きたら止めて報告）
- §5-1 の確かめが合わない（ブランチの先が違う）→ 止まる。
- merge で §3 以外のファイルが衝突した → 生の出力を付けて止まる。
- U1 か U2 で1画素・1項目でも違う → 原因の候補を生の出力つきで報告して止まる。規則の並びや値を変えて合わせ込まない。
- `Spinner` の読み込み先（`./loading`）が M と違う → 止まる。
- `bindLongPress` の返り値に `className` がある、または SecretaryChat が ChatBubble に `key` 以外の属性を渡している → 型が合わないので止まる。
- 見本ページの CSS の読み込み順を main.tsx と同じにできない → 止まる。
- 取り込みのあと、訳文のファイル（ja.json・en.json）や tokens.css に `<<<<<<<` などの衝突の印が残っている、または `npm run check:i18n-missing-keys` が赤 → 生の出力を付けて止まる。
- 取り込みの記録を `git show --cc <取り込みの commit> --name-only` で見て、出たファイルが次の2つのどちらにも当たらない → 生の出力を付けて止まる（§4 の書き換えは取り込みの記録に混ぜず、別の commit にする）。(i) (b) の衝突の一覧にあるファイル。(ii) 両側が変えたので自動で混ざったファイルで、`git diff <取り込みの commit>^2 <取り込みの commit> -- <file>` が §5-3 の確かめどおり（en.json・ja.json は `humanAgentLabel` の行の削除だけ、tokens.css は `--comp-chat-bubble-line-height` の1行の追加だけ）。(ii) の差分は生のまま報告に貼る。
- e2e が CI で元から赤 → card-a1.md §9 と同じ（base でも同じ赤かを両方の生の出力で示す）。

## 10. 戻し方・測り方
- 戻し方: この PR を revert する（受信箱と秘書のチャットの両方が main の今の形に戻る）。DB・本番データ・バックエンドは触らない。
- 測り方（本番に出た後）: 本番の受信箱を幅1280と幅390で開き、card-a1.md §11 と同じに見る。秘書のチャットは、出せる人（ADR-1056 の4条件）で開いて1回やりとりし、吹き出しの色・寄せ・幅が変わっていないことを写真で見る（Evaluator）。

## 11. Architect 整合検査（同じ AI による自己審査・1回）
- 判定: **APPROVE（実装可）**
- 確かめたこと:
  - SSOT: 吹き出しの色・角・余白・字・行の間隔の規則は1か所（ChatBubble.css）になる。2画面の違い（幅・並べ方・赤の出し方・スマホの色）は金型の props（layout / failed / pending / wide）で選ぶ。呼ぶ側の CSS が金型の中身を上書きするのは受信箱の `.msg-stack .comp-chat-bubble`（A-1 で審査済みの1行・名前だけ変更）だけになり、秘書の `className` 上書きは無くなる。○
  - ADR-144 §4: 金型は .tsx＋.css＋.stories.tsx（＋試験）。新しい金型は作らず既存の1つを広げる。○
  - ADR-067: 新しいトークンは無い。秘書の `1.45` の直書きを既存トークン `--comp-chat-bubble-line-height`（値 1.45・A-1 で登録）に置き換える＝値は同じ。○
  - ADR-027: 金型は言葉を持たない。新しい画面の文字は無い。○
  - クラス名を `comp-chat-bubble` に変えても、e2e は `msg-bubble` / `msg-time` を探していない（`git grep "msg-bubble\|msg-time" origin/main -- frontend/tests-e2e` 0件）。秘書の試験は §4-5 の2行を直す。○
  - 見た目が変わらないことは写真（画素 0）と値（項目 0）の両方で確かめる。CSS の読み込み順は見本ページを main.tsx と SecretaryChat.tsx（:14 金型 → :30 自分の CSS）と同じにして確かめる。今の下書きの票は後から読まれる `.secretary-chat__draft-bubble` が勝っている。まとめた後は `--wide` が同じファイルの後ろにあるので順に関係なく勝つ。○
  - 第1回審査（審査役 Opus・2026-11-01）: REVISE（見本ページの CSS の順・U4 の基準・panel のストーリーの time）。3点を直した。
  - 第2回審査: REVISE（U7 を取り込み後の一覧で判定する形に・§7-4b に同じ CSS ファイルの条件）。2点を直した。
  - 第3回審査: APPROVE。止めるほどではない補足2つ（取り込みの記録の確かめ・訳文などの自動の混ざりが崩れた時の止まり方）を §9 に足した。
  - 1回目の実行（2026-11-01 18:45 JST）: §9 の取り込みの記録の確かめで止まった。`--cc` には両側が変えて自動で混ざったファイル（en.json・ja.json・tokens.css）も出るのに、条件が衝突の一覧だけを許していた＝条件の書き漏れ。実行役の報告では各ファイルの差分は §5-3 の確かめどおり（humanAgentLabel の削除各1行・line-height の追加1行）。条件に (ii) を足した。
  - 危険な場所（migrations/・deploy.yml・本番 scripts/）を含まない → ADR-136 の GO 手順は不要。ADR-1015 の区分は A のまま（feat・金型）。○
- 未解決: なし。A-2 で行の間隔をスマホだけ 19px にするときは、トークンの値を変えず thread の @media に足す（秘書を変えないため）。これは A-2 のカードに書く。

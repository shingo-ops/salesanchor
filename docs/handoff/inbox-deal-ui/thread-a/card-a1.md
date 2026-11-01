---
mode: handoff
title: 受信箱 会話画面 A-1 — 吹き出しと入力欄を金型（ChatBubble / ChatComposer）へ移す（見た目は変えない）
status: 実装カード（Opus 作成 2026-11-01・Architect 整合検査は §12）
base: origin/main 508e86036b5b1ab519d49cd3edde888986ba6e22
po_approval: 2026-11-01 PO「1」（金型を新しく登録してから作る。ADR-144 §4 の許可）＋同日「PRマージ、デプロイまで完走させてくれ」（実装承認）
---

# card A-1 — 吹き出しと入力欄を金型へ移す

根拠: recon.md・design.md（同じフォルダ）。行番号はすべて base の origin/main。
TSX = `frontend/src/pages/inbox/InboxMessageThread.tsx`、CSS = `frontend/src/pages/inbox/InboxPage.css`。

## 1. 目的
- 吹き出しと入力欄の行を `components/` の金型にする。次の段（A-2 のスマホの値、B の訳の表示、C の既読の印、D の「＋」）は、この金型だけを直せば済むようにする。
- **見た目は変えない**（例外は §5 の1つだけ）。値（px・色・角）は1つも変えない。

## 2. 変えないもの（触らない範囲）
- 吹き出し・入力欄の大きさ・色・角・余白・文字の値。トークンの値。
- 送る・受ける・訳す・添付・ハート・長押しの動き。API・型（`frontend/src/lib/messages.ts`）・バックエンド。
- クラス名（`msg-bubble` `msg-time` `send-top-row` `send-input-wrap` `send-attach-btn` `inbox-send-btn` `inbox-textarea`）。e2e 6本がこの名前で要素を探している（recon 調べ: inbox-header-ui-screenshots / send-guard-phase-a / send-guard-screenshots / inbox-baseline / inbox-helpers / inbox-single-column）。名前の付け替えはこのカードでしない。
- 吹き出しの外側（`.inbox-messages` `.inbox-msg-row` `.msg-stack` `.msg-bubble-line` `.msg-heart-hover` `MessageReactionBadges`）、入力欄の外側（`.inbox-send-area` `.send-card` 画像プレビュー `.inbox-textarea` 英訳ボタン `.inbox-translate-outbound-btn`）。これらはページに残す。
- 吹き出しの中の翻訳ボタン（TSX:637-649）・翻訳結果（TSX:617-633）。B で扱う。このカードでは中身をそのまま渡すだけ。

## 3. 新しく作るファイル

### 3-1 `frontend/src/components/ChatBubble.tsx`
```tsx
/**
 * ChatBubble — 会話の吹き出し金型（本文と時刻の入れ物）
 *
 * direction : inbound（相手から）/ outbound（自分から）。時刻の寄せ方もこれで決まる
 * failed    : 送れなかった吹き出し（赤の枠）。direction より優先して色を決める
 * time      : 吹き出しの下端に出す時刻の行の中身
 * children  : 本文・画像・訳など吹き出しの中身
 * そのほかの div の属性（role・title・長押しの手当て）はそのまま外側の div に付ける。
 *
 * 業務の意味（どの経路のメッセージか等）はこの金型に埋め込まない。
 */
import type { HTMLAttributes, ReactNode } from 'react';
import './ChatBubble.css';

export type ChatBubbleDirection = 'inbound' | 'outbound';

export interface ChatBubbleProps extends Omit<HTMLAttributes<HTMLDivElement>, 'className' | 'children'> {
  direction: ChatBubbleDirection;
  failed?: boolean;
  time: ReactNode;
  children: ReactNode;
}

export function ChatBubble({ direction, failed = false, time, children, ...rest }: ChatBubbleProps) {
  const outbound = direction === 'outbound';
  return (
    <div {...rest} className={`msg-bubble${failed ? ' failed' : outbound ? ' outbound' : ' inbound'}`}>
      {children}
      <div className={`msg-time${outbound ? '' : ' inbound'}`}>{time}</div>
    </div>
  );
}
```

### 3-2 `frontend/src/components/ChatBubble.css`
CSS の次の規則を**一字も変えずに**移す（移した元は消す）。ただし `line-height: 1.45;` だけは `line-height: var(--comp-chat-bubble-line-height);` に置き換える（§3-7 のトークン）。
- CSS:503-536（コメント「Meta実測: バブル 16px …」から `.msg-time.inbound { text-align: left; }` まで）: `.msg-bubble` / `.msg-bubble.outbound` / `.msg-bubble.inbound` / `.msg-bubble.failed` / `.msg-time` / `.msg-time.inbound`
- CSS:1304-1313 の `@media (max-width: 767px)` 内の「4. 吹き出しを…」コメントと `.msg-bubble.outbound` `.msg-bubble.inbound` の2行 → ChatBubble.css の末尾に `@media (max-width: 767px) { … }` として置く。コメントも一緒に移す。
- 先頭に IconToggleButton.css と同じ形のコメント（`ChatBubble — 会話の吹き出し / ADR-067: 全カラー・寸法は CSS 変数参照のみ`）を付ける。
- CSS:1937 `.msg-stack .msg-bubble { … }` はページの並べ方の規則なので**ページに残す**。

### 3-3 `frontend/src/components/ChatComposer.tsx`
```tsx
/**
 * ChatComposer — 会話の入力欄の行の金型（ピル＋送信の丸）
 *
 * leading  : ピルの左に置く物（送信者のアバター等）。任意
 * input    : ピルの中の入力欄（TextareaControl 等）と、隠しのファイル入力など
 * attach   : ピルの中の右端のアイコンボタン。任意
 * trailing : ピルと送信の丸の間に置く物（英訳ボタン等）。任意
 * send     : 送信の丸。label は画面には出さず読み上げ用（sr-only）に入る
 *
 * 業務の意味（どこへ送るか等）はこの金型に埋め込まない。
 */
import type { ReactNode } from 'react';
import type { Icon } from '../constants/icons';
import { ICON } from '../constants/iconSizes';
import './ChatComposer.css';

export interface ChatComposerAttach {
  icon: Icon;
  /** aria-label と title の両方に使う */
  label: string;
  onClick: () => void;
  disabled?: boolean;
}

export interface ChatComposerSend {
  icon: Icon;
  /** 読み上げ用の名前（sr-only） */
  label: string;
  title: string;
  onClick: () => void;
  disabled?: boolean;
}

export interface ChatComposerProps {
  leading?: ReactNode;
  input: ReactNode;
  attach?: ChatComposerAttach;
  trailing?: ReactNode;
  send: ChatComposerSend;
}

export function ChatComposer({ leading, input, attach, trailing, send }: ChatComposerProps) {
  const AttachIcon = attach?.icon;
  const SendIcon = send.icon;
  return (
    <div className="send-top-row">
      {leading}
      <div className="send-input-wrap">
        {input}
        {attach && AttachIcon && (
          <button
            type="button"
            className="send-attach-btn"
            onClick={attach.onClick}
            disabled={attach.disabled}
            aria-label={attach.label}
            title={attach.label}
          >
            <AttachIcon size={ICON.md} aria-hidden="true" />
          </button>
        )}
      </div>
      {trailing}
      <button
        type="button"
        className="inbox-send-btn"
        onClick={send.onClick}
        disabled={send.disabled}
        title={send.title}
      >
        <SendIcon size={ICON.base} aria-hidden="true" />
        <span className="sr-only">{send.label}</span>
      </button>
    </div>
  );
}
```
- `Icon` 型と `ICON` の import 元は IconToggleButton.tsx:13-14 と同じ。名前が違えば IconToggleButton.tsx と同じ書き方に合わせる（逸脱ではない）。

### 3-4 `frontend/src/components/ChatComposer.css`
CSS の次の規則を**一字も変えずに**移す（元は消す）。
- CSS:606-624 `.send-top-row`（直前のコメント「上段: …」を含む）と `.send-input-wrap`（直前のコメント「入力ラップ …」を含む）
- CSS:629-650 `.send-attach-btn` / `:hover:not(:disabled)` / `:disabled`（直前のコメントと `stylelint-disable-next-line` の行を含む）
- CSS:708-730 `.inbox-send-btn` / `:hover:not(:disabled)` / `:disabled`（直前のコメントと `stylelint-disable-next-line` の行を含む）
- CSS:1190-1193 の `@media (max-width: 767px)` 内の `.inbox-send-btn { width: var(--size-icon-btn-lg); height: var(--size-icon-btn-lg); }` → ChatComposer.css の末尾に `@media (max-width: 767px) { … }` として置く。CSS:1174-1189 の長いコメントはページに残し、その最後に1行「`.inbox-send-btn` の規則は components/ChatComposer.css へ移した（2026-11-01 A-1）」を足す。
- **ページに残す**: CSS:625-628 `.inbox-textarea`、`.send-attachment-preview` `.send-preview-*`（CSS:651-691）。
- 先頭に ChatBubble.css と同じ形のコメントを付ける。

### 3-5 ストーリー（ADR-144 §4・check:stories）
- `frontend/src/components/ChatBubble.stories.tsx`: 受信 / 送信 / 送れなかった / 長い本文（折り返し）/ 時刻の行にボタンが入る形。文言は `t()` を使わずストーリー内の固定の英字でよい（既存 stories と同じ扱い。IconToggleButton.stories.tsx を手本にする）。
- `frontend/src/components/ChatComposer.stories.tsx`: 空 / 文字あり / 添付なし / trailing あり / 送信が押せない。

### 3-6 単体試験（IconToggleButton.test.tsx を手本）
- `frontend/src/components/ChatBubble.test.tsx`: (1) inbound は `msg-bubble inbound`・時刻は `msg-time inbound` (2) outbound は `msg-bubble outbound`・時刻は `msg-time` (3) failed は direction に関係なく `msg-bubble failed` (4) role・title・onPointerDown 等の属性が外側の div に付く。
- `frontend/src/components/ChatComposer.test.tsx`: (1) 送信は `inbox-send-btn`・読み上げ名が label (2) disabled が効く (3) attach 無しならボタンが出ない (4) attach の aria-label と title が label (5) leading・input・trailing が DOM の順（leading → ピル → trailing → 送信）に並ぶ。

### 3-7 トークン（ADR-067 :125-133 の手順）
- `frontend/src/tokens.css` の `--comp-multiselect-check-col-w`（:175）の次の行に1つ足す:
  `  --comp-chat-bubble-line-height: 1.45; /* 会話の吹き出しの行の間隔（CSS:508 の直書きを移した値。A-2 でスマホは実測 19px にする） */`
- 色ではないので index.css は触らない。`check:dark-parity` は通ることだけ確かめる。
- `docs/adr/ADR-067-design-token-enforcement.md` のコンポーネントトークン表（:47-66）の末尾に1行足す: `| \`--comp-chat-bubble-line-height\` | \`1.45\` | 会話の吹き出しの行の間隔（ChatBubble 金型） |`
- PR 本文の「デザイントークン変更時」チェック表を埋める（check:new-tokens）。

## 4. ページの書き換え（TSX）

### 4-1 吹き出し（TSX:557-651 → ChatBubble）
- import に `import { ChatBubble } from "../../components/ChatBubble";` を足す（同じファイルの他の components import と同じ並び）。
- 変更前 TSX:557-566 の開きタグと TSX:635-651 の時刻の行・閉じタグを、次に置き換える。中身（TSX:572-633）はそのまま children にする:
```tsx
              <ChatBubble
                direction={outbound ? "outbound" : "inbound"}
                failed={failed}
                role={failed ? "alert" : undefined}
                {...(canReact ? bindLongPress(msg.id) : {})}
                title={
                  failed
                    ? `${t("inbox.sendError.generic")}${t("inbox.sendError.codeSuffix", { code: msg.error_code })}${msg.error_message ? ` — ${msg.error_message}` : ""}`
                    : formatAbsolute(msg.created_at, i18n.language)
                }
                time={
                  <>
                    {relativeTime(msg.created_at, t, i18n.language)}
                    {/* Translate button */}
                    {msg.message_id && msg.message_text && !failed && (
                      /* TSX:639-648 の <button className="msg-translate-btn"> … </button> をそのまま */
                    )}
                  </>
                }
              >
                {/* TSX:572-633 をそのまま（§5 で 567-571 は消す） */}
              </ChatBubble>
```
- 属性の順（role → 長押し → title）は元と同じにする。

### 4-2 入力欄の行（TSX:775-852 → ChatComposer）
- import に `import { ChatComposer } from "../../components/ChatComposer";` を足す。
- TSX:775-852 の `<div className="send-top-row"> … </div>` を次に置き換える:
```tsx
          <ChatComposer
            leading={
              /* TSX:776-778 の <div className="conv-avatar" …>…</div> をそのまま */
            }
            input={
              <>
                {/* TSX:780-796 の <TextareaControl …/> をそのまま */}
                {/* TSX:797-807 の 隠し file input をそのまま */}
              </>
            }
            attach={{
              icon: INBOX_ACTION_ICONS.attach,
              label: t("inbox.attachImage"),
              onClick: handleAttachClick,
              disabled: !canSend || sending,
            }}
            trailing={
              /* TSX:820-833 の 英訳ボタンの条件式をそのまま（コメント含む） */
            }
            send={{
              icon: INBOX_ACTION_ICONS.send,
              label: sending ? t("inbox.sending") : t("inbox.send"),
              title: /* TSX:840-846 の式をそのまま */,
              onClick: checkAndSend,
              disabled: sendDisabled && !attachedFile,
            }}
          />
```
- TSX:808 のコメント「クリップボタン（Meta と同配置: ピル内右端）」は ChatComposer.tsx の attach の場所へ移す。

## 5. 1つだけ見た目が変わるところ（PO 決定 2026-11-01）
- TSX:567-571（吹き出しの上の「ヒューマンエージェント」の行）を消す。PC もスマホも。
  - 根拠: 送るときに付く札は `HUMAN_AGENT` か無しの2つだけ（`backend/app/services/messaging_window.py:134-149`）。この行は札を見せるだけで、送る決まりは変えない（バックエンドは触らない）。
- 使われなくなる文言を消す: `frontend/src/locales/ja.json:1242` と `frontend/src/locales/en.json:1242` の `"humanAgentLabel"`（ほかの参照は無い。`git grep humanAgentLabel` で TSX:569 の1件だけ）。前後のカンマを壊さない。
- `frontend/tests-e2e/scene7-human-agent-tag.spec.ts:108-109` を「出ないこと」に変える:
```ts
    // 吹き出しの上の "Human Agent" 表示は出さない（PO 決定 2026-11-01）。送るときの札は下の検証で見る
    await expect(page.getByText("Human Agent", { exact: true })).toHaveCount(0);
```

## 6. 受入条件（全部 ○ で完了）

| 基準 | 検証方法 |
|---|---|
| K1 見た目が変わらない（PC・タブレット・スマホ） | §7 の写真比べで、vl-desktop-1280 / vl-tablet-768 / vl-mobile-390 の3つ × 2場面（会話を開いた直後・入力欄に `hello` を入れた後）= 6枚すべて**違う画素 0**。比べる場面では、モックの全メッセージの `message_tag` を null にしてから撮る（§5 の行を比べから外すため） |
| K2 「ヒューマンエージェント」の行が出ない | scene7-human-agent-tag.spec.ts が通る（§5 の書き換え後）。加えて `message_tag: "HUMAN_AGENT"` のままのモックで vl-mobile-390 を撮り、行が無い写真を残す |
| K3 金型の作法 | ChatBubble / ChatComposer それぞれ .tsx・.css・.stories.tsx・.test.tsx がある。2つの .css に色の直値・px の余白/大きさ/角の直値が 0（check:css-colors・check:css-values が通る） |
| K4 移した元が残っていない | `git grep -nE '^\.msg-bubble|^\.msg-time|^\.send-top-row|^\.send-input-wrap|^\.send-attach-btn|^\.inbox-send-btn' -- frontend/src/pages` が 0件。スマホの上書き（`.msg-bubble.outbound` `.msg-bubble.inbound` `.inbox-send-btn`）も InboxPage.css に 0件 |
| K5 点検が全部通る | `cd frontend && npm run check:all`・`npx tsc --noEmit`（または既存の型検査コマンド）・`npm run test:unit`・`node scripts/check-ui-governance.js`（BASE_SHA=base, HEAD_SHA=HEAD）が全部 0 で終わる |
| K6 既存の試験が通る | `InboxMessageThread.discordSendError.test.tsx`・`useInboxState.autoSelectBadge.test.tsx`、e2e の `inbox-header-menu` `send-guard-phase-a` `scene7-human-agent-tag` と `test:e2e:vl` の inbox 3本（baseline / single-column / lead-merge）が通る |
| K7 触らない範囲を守った | 変更ファイルが §8 の一覧だけ |

## 7. 写真比べのやり方（K1）
1. base（508e86036 か、作業開始時の origin/main）で、比べ用の一時的な spec（**コミットしない**。例 `tests-e2e/visual-language/tmp-a1-parity.spec.ts`）を使い、inbox-helpers.ts の会話を開く手順で6枚撮る。モックの `message_tag` は全部 null にする。写真は `/tmp/a1-parity/before/` に置く。
2. 作業後の HEAD で同じ spec を同じ手順で回し `/tmp/a1-parity/after/` に置く。
3. 画素を比べる（pixelmatch か Python の画像比較。しきい値 0、アンチエイリアスの許容もしない）。6枚それぞれの「違う画素の数」を生のまま `docs/handoff/inbox-deal-ui/thread-a/a1-parity-result.txt` に書いてコミットする（写真そのものはコミットしない）。
4. 0 でない写真が1枚でもあれば**止めて報告する**（直し方を自分で決めない）。

## 8. 変更してよいファイル（これ以外は触らない）
- 新規: `frontend/src/components/ChatBubble.tsx` `ChatBubble.css` `ChatBubble.stories.tsx` `ChatBubble.test.tsx` `ChatComposer.tsx` `ChatComposer.css` `ChatComposer.stories.tsx` `ChatComposer.test.tsx`、`docs/handoff/inbox-deal-ui/thread-a/a1-parity-result.txt`
- 変更: `frontend/src/pages/inbox/InboxMessageThread.tsx` `frontend/src/pages/inbox/InboxPage.css` `frontend/src/tokens.css` `frontend/src/locales/ja.json` `frontend/src/locales/en.json` `frontend/tests-e2e/scene7-human-agent-tag.spec.ts` `docs/adr/ADR-067-design-token-enforcement.md`
- ADR を変えたら `node scripts/generate-adr-index.js` を回し `docs/adr/README.md` の差分もコミットする（CI「ADR index is up to date」）。

## 9. 想定される分かれ道（起きたら止めて報告）
- 移した後で写真が1画素でも違う → 原因（CSS の読み込み順など）を生の出力つきで報告して止まる。規則の書き換えで合わせ込まない。
- `Icon` 型・`ICON` の場所が §3-3 と違う → IconToggleButton.tsx と同じ書き方に合わせてよい（報告に書く）。
- check:stories や ui-governance が新しい金型で赤 → 生の出力を付けて止まる。
- `bindLongPress` の返り値に `className` が含まれていた → ChatBubble の props 型と合わないので止まる。
- e2e が CI で元から赤（この変更と関係なく）→ base でも同じ赤かを確かめ、両方の生の出力を付けて報告する。

## 10. 戻し方
- この PR を revert する。DB・本番データ・バックエンドは触らない。

## 11. 測り方（本番に出た後）
- 本番の受信箱を幅1280と幅390で開き、会話の吹き出しと入力欄の写真を撮る。§7 の after と並べて、違いが「ヒューマンエージェントの行が無い」ことだけかを見る（Evaluator）。

## 12. Architect 整合検査（同じ AI による自己審査・1回）
- 判定: **APPROVE（実装可）**
- 確かめたこと:
  - ADR-144 §4: 金型が無い → PO 許可（2026-11-01「1」）→ Xxx.tsx＋Xxx.css＋Xxx.stories.tsx。○
  - ADR-067: 新トークン1つは :125-133 の手順（tokens.css・表の更新・check:new-tokens）。色ではないので index.css は不要。○
  - check:css-values の規則（frontend/scripts/check-css-hardcoded-values.js）: 移す規則の `50%`・`1px`/`2px` の枠・単位なしの数は検出対象外。px の余白・大きさ・角は全部 var()。○
  - CSS の読み込み順: 移した規則とスマホの上書きは同じファイルの中で元と同じ順に並ぶ。ページに残る同じ要素への規則は `.msg-stack .msg-bubble`（詳しさ 0,2,0 で、移した `.msg-bubble` の 0,1,0 より強い）と `.inbox-textarea`（別の要素）だけ。どちらの順で読まれても結果は同じ。○（写真比べ K1 で最終確認）
  - クラス名を変えないので e2e 6本と FormField.css:285 のコメントは影響なし。○
  - 「ヒューマンエージェント」の行を消しても送る決まり（messaging_window.py）は変えない。scene7 の検証を「出ない」に変える。○
  - i18n: 新しい画面の文字は無い（金型は文言を受け取るだけ）。消す鍵は ja/en の両方。○
  - 危険な場所（migrations/・deploy.yml・本番 scripts/）を含まない → ADR-136 の GO 手順は不要。○
- 未解決: なし（A-2 の測り足し U1〜U6 はこのカードの範囲外）。

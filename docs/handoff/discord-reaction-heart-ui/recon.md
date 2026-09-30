# Discord リアクション ハート方式 UI — recon（現在地）

> 実測時の origin/main: 4c056c5f9c80b481643e0150f29fd3c95ea86e1e（#3869 マージ済みを含む）
> 承認済みKGI: docs/specs/discord-reaction/kgi.md（⑥ 受信箱に出る情報がDiscordと同じか）。前便: docs/handoff/discord-reaction-wiring-fix/design.md

## 事実

1. 現状の UI は絵文字ピッカー方式。frontend/src/pages/inbox/InboxMessageThread.tsx:12 が EmojiPickerWrapper を import し、:185 に picker 状態（openPickerForMsgId）、:190-198 に外側クリックで閉じる effect がある。EmojiPickerWrapper.tsx の importer は InboxMessageThread.tsx のみ（`grep -rn EmojiPickerWrapper frontend/src`）。
2. アイコンは frontend/src/constants/icons.tsx に集約。INBOX_ACTION_ICONS は :369 から。Heart は未登録（`git grep -in heart origin/main -- frontend/src/constants/icons.tsx` ヒット 0）。
3. 押下色トークンは既存: frontend/src/index.css:196（`--icon-action-danger: var(--danger)`）、ダーク側 :400。`--icon-action` / `--icon-action-hover` は :194-195、:398-399。
4. トグル用の金型は無い（`ls frontend/src/components | grep -i toggle` に該当なし。Button は className/style を受けない）。Tooltip 金型は frontend/src/components/Tooltip.tsx（children をラップ・content は文字列・マウス hover 表示）。
5. 金型作法（docs/CC_UI_GOVERNANCE.md）: 無ければ止めて PO 許可を得てから components/ に Xxx の tsx + css（var() のみ）+ stories を登録。frontend/scripts/check-stories-count.js は components/ 直下の tsx に stories が無いと赤にする。金型の索引ファイルは無く、更新が必要な一覧・許可リストは無い（`git grep -l Tooltip` の docs/scripts ヒットは過去の handoff のみ）。
6. リアクション表示 CSS は frontend/src/pages/inbox/InboxPage.css の「Discord リアクション」節（.msg-reaction-bar / -pill / -add-btn / -picker-popover / .emoji-preset-*）。`--size-6` / `--size-8` は tokens.css / index.css のどこにも定義が無い（`grep -rn "^\s*--size-[0-9]*:" frontend/src` ヒット 0）。
7. API は前便で整備済み: リアクションは内部ID（msg.id）で送信/取消し、一覧は `is_mine` と `reactors[{user_id,display_name}]` を返す（docs/handoff/discord-reaction-wiring-fix/design.md）。
8. i18n: inbox.addReaction / removeReaction / reactedBy / reactionSendFailed / reactionDeleteFailed は使用継続。inbox.emojiPicker と inbox.customEmojis は EmojiPickerWrapper 削除後に参照ゼロ（`grep -rn "emojiPicker\|customEmojis" frontend/src --include='*.tsx' --include='*.ts'`）。
9. 前便で未実施だった項目: ledger-auto-done-main（run 36668141216）は「not found (skip): .claude-pipeline/active-work.d/release-discord-reaction-wiring-fix.md」で終了し、#3869 の DONE 化 PR は作られていない（台帳ファイルが本店の未追跡ファイルで origin/main に無かったため）。

## PO 決定（2026-09-30・原文の選択肢）

- ハート以外の顧客リアクション =「表示だけ残す (推奨)」
- 新金型「アイコンの切替ボタン」=「登録してよい (推奨)」
- ハート表示 =「マウスを乗せた時だけ (推奨)」
- 位置 =「設計者が決める (推奨)」

## ADR 検索（着手前）

- `git grep -il reaction origin/main -- docs/adr/` は ADR-024 と ADR-091 のみ（前便 recon と同じ）。UI 金型・デザイントークンの拘束は ADR-144（docs/adr/ADR-144-ui-component-governance.md）と ADR-067（docs/adr/ADR-067-design-token-enforcement.md）。
- 対象 ADR: ADR-144, ADR-067, ADR-091。

## 引用（file:line・origin/main 4c056c5f9）

- frontend/src/pages/inbox/InboxMessageThread.tsx:12 — EmojiPickerWrapper の import
- frontend/src/pages/inbox/InboxMessageThread.tsx:185 — picker 状態（openPickerForMsgId）
- frontend/src/pages/inbox/InboxMessageThread.tsx:190-198 — 外側クリックで閉じる effect
- frontend/src/constants/icons.tsx:369 — INBOX_ACTION_ICONS の定義開始
- frontend/src/index.css:196 — `--icon-action-danger`（ダーク側は :400）
- frontend/src/index.css:194-195 — `--icon-action` / `--icon-action-hover`

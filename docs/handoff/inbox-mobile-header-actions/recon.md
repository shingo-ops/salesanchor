# recon: 受信箱のヘッダー操作行をスマホの一覧で出さない（現状把握）

調査日 2026-10-13 / ブランチ `release/inbox-mobile-header-actions`（`origin/main` 起点）

PO 指定: 「ヘッダーアクションもスレッドでしか必要ないのでスマホ版では非表示にして。受信箱の顧客一覧表示では表示しなくていい」＋選択「4つ消して絞り込みは検索欄の横へ移す」（2026-10-13）

## A. 現状の操作行（4つ）

| # | 事実 | 根拠 |
|---|---|---|
| A1 | 操作行は `PageLayout` の `headerAction` に渡す1つの `div.page-header-actions` で、中身は テンプレート / FAQ / 絞り込み / 受信箱の設定 の4つ | `frontend/src/pages/inbox/InboxPage.tsx:61-101` |
| A2 | `PageLayout` は `headerAction` が渡されたときだけ `div.page-layout-header-right` を描く＝渡さなければ行ごと出ない | `frontend/src/components/PageLayout.tsx:47-49`（`{headerAction && (...)}`） |
| A3 | ページ見出し `h2.text-page-title` は `headerAction` の有無に関係なく常に描かれる＝読み上げでの現在地は失われない | `frontend/src/components/PageLayout.tsx:45` |
| A4 | スマホでは見出しと説明文を視覚的に隠している（受信箱のみ `slimHeaderOnMobile`） | `frontend/src/components/PageLayout.css:21-35` ／ `frontend/src/pages/inbox/InboxPage.tsx:104` |
| A5 | 操作行は**一覧でも会話でも同じ位置に出ている**（実機実測・1080x2340 @480dpi） | 一覧: テンプレート `(48,141)-(420,273)`・FAQ `(453,141)-(660,273)`・絞り込み `(693,153)-(804,261)`・設定 `(837,153)-(948,261)` ／ 会話を開いた状態も**同一座標** |
| A6 | 行の高さは 132 device px（＝44dp）、行全体では約 162 device px（＝54dp） | 同実測（`y=141-273` と、その下の一覧開始 `y=423` の差） |

## B. 絞り込みボタンの性質（一覧専用）

| # | 事実 | 根拠 |
|---|---|---|
| B1 | 絞り込みは `mobileFiltersOpen` を切り替えるだけのボタン | `frontend/src/pages/inbox/InboxPage.tsx:83-93`（削除前） |
| B2 | 開くのは**一覧の**ステータスタブと詳細条件（`.inbox-full-tab-bar` / `.inbox-sub-filter-bar`）＝会話側では使い道がない | `frontend/src/pages/inbox/InboxPage.css:1184-1188`（`.inbox-wrapper.filters-open` のときだけ `display: flex`） |
| B3 | PC・タブレットではボタン自体を出さない（タブが常時見えているため） | `frontend/src/pages/inbox/InboxPage.css:996`（既定 `display: none`）／`:1181-1182`（`@media (max-width: 767px)` で `inline-flex`） |
| B4 | 当たり判定は 111x108 device px（＝37x36dp）で **44px 未満**。第2便（押す場所の拡大）の対象として既知 | 実機実測 `(693,153)-(804,261)` ／ `docs/handoff/app-visual-language/card-stage4b-inbox-mobile.md` §6 の第2便 |

## C. 移設先（検索欄）

| # | 事実 | 根拠 |
|---|---|---|
| C1 | 検索欄は `div.inbox-search-row` で、中身は 検索（`.inbox-search-wrap`）と 管理（`.inbox-manage-wrap`） | `frontend/src/pages/inbox/InboxConversationList.tsx:60-72` |
| C2 | 検索欄は横並び（flex）で要素間の間隔がトークン指定済み＝要素を1つ足せる | `frontend/src/pages/inbox/InboxPage.css:94-100`（`display:flex; align-items:center; gap: var(--space-2)`） |
| C3 | 検索欄は**左パネル（一覧）の中**にある＝会話を全画面にすると一緒に隠れる | `frontend/src/pages/inbox/InboxConversationList.tsx:58`（`<aside className="inbox-left-panel">` の内側）／`frontend/src/pages/inbox/InboxPage.css` の `@media (max-width: 767px)` 内 `.inbox-wrapper.thread-open .inbox-left-panel { display: none; }` |
| C4 | 管理ボタンの実測は 213x102 device px（＝71x34dp） | 実機実測 `(843,303)-(1056,405)` |

## D. スマホ判定の手段（既存）

| # | 事実 | 根拠 |
|---|---|---|
| D1 | `useIsMobile()` が `matchMedia` と `BREAKPOINTS.MOBILE_MAX` で判定する既存 hook（ADR-137） | `frontend/src/hooks/useIsMobile.ts:15-28` |
| D2 | 受信箱の状態側でも既に使っている（スマホでは先頭会話を自動選択しない） | `frontend/src/pages/inbox/useInboxState.ts` の自動選択の効果（PR #4171） |
| D3 | CSS 側の切替点と同じ 767px | `frontend/src/tokens.css:113-117` の `--breakpoint-mobile-max: 767px` |

## E. 影響範囲

- `div.page-header-actions` を参照しているのは CSS の見た目指定のみ。E2E の spec では `frontend/tests-e2e/visual-language/inbox-single-column.spec.ts` に追加する検査が初出（既存 spec に参照なし）。
- `InboxConversationList` の Props はフラットな一覧で、呼び出し側（`frontend/src/pages/inbox/InboxPage.tsx:132-...`）が1つずつ明示的に渡している＝3つ足す形に無理がない。
- 単体テストに受信箱のヘッダー操作行を見るものは無い（`grep -rn "page-header-actions" frontend/src --include=*.test.tsx` の結果0件）。

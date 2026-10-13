# recon: 絞り込みを下から出るシートにする（現状把握）

調査日 2026-10-13 / ブランチ `release/inbox-filter-sheet`（`origin/main` 起点）

PO 指示: 「全てのメッセージやリードなどで絞り込むアイコンも押したらタブを開くんじゃなくてポップアップで画面に表示してその時に選択して閉じるポップアップにしたい」
PO 選択: **下から出るシート**（2026-10-13）／金型の新設も**明示の許可を受領**（同日「進める」）

## A. 現状の絞り込みの動き

| # | 事実 | 根拠 |
|---|---|---|
| A1 | 絞り込みボタンは `mobileFiltersOpen` を切り替えるだけ | `frontend/src/pages/inbox/InboxConversationList.tsx` の該当ボタン |
| A2 | `mobileFiltersOpen` が真のとき wrapper に `filters-open` が付き、**画面内の帯**（`.inbox-full-tab-bar` と `.inbox-sub-filter-bar`）が現れる | `frontend/src/pages/inbox/InboxPage.tsx` の wrapper の className ／ `frontend/src/pages/inbox/InboxPage.css` の `@media` 内の指定 |
| A3 | 帯の中身は ステータス6つ（すべて/リード/商談中/既存顧客/未返信/アーカイブ）＋ プラットフォーム選択、サブ帯は 未読・未返信の2つ | `frontend/src/pages/inbox/inbox.types.ts` の `STATUS_TABS` ／ `frontend/src/pages/inbox/InboxPage.tsx` ／ `frontend/src/pages/inbox/InboxConversationList.tsx` |
| A4 | 選んでも帯は開いたまま（閉じる操作が別に必要） | A1・A2 から（`setStatusTab` は `mobileFiltersOpen` を変えない） |
| A5 | 絞り込みボタンは**スマホでしか出ない** | `frontend/src/pages/inbox/InboxPage.css` の `.icon-btn.inbox-mobile-filter-toggle { display: none; }` と `@media` 内の表示指定 |

## B. 使える金型（ADR-144 の「金型を先確認」）

| 金型 | 性質 | 判定 |
|---|---|---|
| `frontend/src/components/Modal.tsx` | 画面中央のダイアログ。Esc・背景クリック・フォーカストラップ・ポータル | 「下から出る」ではない |
| `frontend/src/components/Drawer.tsx` | **右から**出るサイドパネル。同じ a11y を持つ | 向きが違う。**かつ 22 ページで使用中**（`grep -rln '<Drawer' src/ --include=*.tsx` の結果）＝改造の波及が大きい |
| `frontend/src/components/Popover.tsx` | トリガー基準の小さなパネル | 360px では位置が端に寄って切れる恐れ（会話ヘッダで実際に起きている） |

**結論**: 下から出る金型は**無い**。ADR-144 §4（「実装を止め PO に報告 → PO 許可を得てから `components/` に金型を新設（Xxx.tsx ＋ Xxx.css（var() のみ）＋ Xxx.stories.tsx）」）に従い、**PO 許可を得て新設**した。

## C. 新設する金型が満たすべきこと（Drawer から写す）

| # | 事実 | 根拠 |
|---|---|---|
| C1 | Esc で閉じる／背景クリックで閉じる／フォーカストラップ／閉じたら元の要素へフォーカス復帰／`role="dialog"`・`aria-modal`・`aria-labelledby`／`ReactDOM.createPortal` で `document.body` へ | `frontend/src/components/Drawer.tsx` の実装（そのまま踏襲） |
| C2 | 閉じるラベルは `t("common.close")`（ADR-027） | 同ファイル |
| C3 | 重ね順のトークンは既存のものを使う（`--z-backdrop: 298` / `--z-drawer: 301` / `--z-modal: 400`） | `frontend/src/tokens.css` |
| C4 | 使うトークンはすべて既存（`--overlay-bg` / `--shadow-modal` / `--transition-slow` / `--radius-xl` / `--bg-surface` / `--border-subtle` / `--space-*` / `--font-md` / `--font-weight-semi` / `--size-icon-btn-lg`） | 同ファイルと `frontend/src/index.css` で実値を確認済み |
| C5 | 下端は `env(safe-area-inset-bottom)` を足す作法が既にある | `frontend/src/mobile-shell.css` の `.mobile-content` |

## D. 検査への影響

既存の画面検査に「絞り込みを押すと `.inbox-full-tab-bar` が見える」という基準がある（`frontend/tests-e2e/visual-language/inbox-single-column.spec.ts`）。**シート方式ではこの帯はスマホで常に出さない**ため、この基準は書き換えが必要。

## E. ADR との関係

| # | 事実 | 根拠 |
|---|---|---|
| E1 | ADR-144 §4 が新規金型の手順を定めている（止める→PO 許可→Xxx.tsx ＋ Xxx.css ＋ Xxx.stories.tsx） | `docs/adr/ADR-144-ui-component-governance.md` |
| E2 | `check:stories` が全部品に stories を要求する | `frontend/package.json` の `check:stories` ／ `frontend/scripts/check-stories-count.js` |
| E3 | ADR-064（PC の Meta 再現）は PC 対象。スマホのみの変更は抵触しない | `docs/adr/ADR-064-inbox-meta-exact-replica.md` |

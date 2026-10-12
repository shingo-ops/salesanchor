# recon: スマホ上部のページ名バーを消す（現状把握）

調査日 2026-10-13 / 対象ブランチ `release/mobile-remove-topbar`（`origin/main` 起点）

PO 指定: 「スマホには受信箱というヘッダーを消して欲しい」→ 適用範囲は**スマホの全ページ**（2026-10-13 選択）。

## A. 消す対象の正体

| # | 事実 | 根拠 |
|---|---|---|
| A1 | 帯は `.mobile-topbar` で、中身は**ページ名のテキスト1つだけ** | `frontend/src/components/MobileShell.tsx:190-193` — `<div className="mobile-topbar"><span className="mobile-topbar-title">{pageTitle}</span></div>` |
| A2 | 帯に押せる要素は無い（メニュー・アバター・戻るのいずれも持たない） | 同上。`frontend/src/components/MobileShell.tsx:9-26` の DOM 構造コメントにも子は PageTitle のみと記載 |
| A3 | 高さは 56px（トークン参照） | `frontend/src/mobile-shell.css:23` の `height: var(--topbar-height)` ／ `frontend/src/tokens.css:171` の `--topbar-height: 56px` |
| A4 | 帯のスタイルは2ブロック・25行 | `frontend/src/mobile-shell.css:15-37`（`.mobile-topbar` と `.mobile-topbar-title`） |
| A5 | ページ名の出どころ | `frontend/src/hooks/usePageTitle.ts:16-21` → `frontend/src/config/routeTitles.ts:17`（`"/lead-chat": "nav.leadChat"`）→ `frontend/src/locales/ja.json:206`（`"leadChat": "受信箱"`） |
| A6 | `pageTitle` は帯の中だけで使われている | `frontend/src/components/MobileShell.tsx:36`（import）・`:75`（呼び出し）・`:192`（使用）の3箇所のみ |
| A7 | `usePageTitle` は副作用を持たない純粋な hook（文書タイトル等を変えない） | `frontend/src/hooks/usePageTitle.ts:16-21` は `t(key)` を返すだけ |

## B. 消しても操作が失われないことの確認

| # | 事実 | 根拠 |
|---|---|---|
| B1 | メニュー（「もっと」シート）を開く手段は**下部タブバーにある** | `frontend/src/components/MobileShell.tsx:311-318` の `button.mobile-tab`（`onClick={() => setMoreSheetOpen(true)}`・`aria-label={t("nav.menu")}`） |
| B2 | 実機でも下部タブバーが4つ出ている | 実機ダンプ（1080x2340 @480dpi）: `y=2130-2295` に 受信箱 / 在庫表 / 受注管理 / メニュー、各 `270x165` device px（＝90x55dp） |
| B3 | 実機の帯は押せる要素を含まない | 同ダンプ: `(0,111)-(1080,279)` は `TextView`（文字のみ）。内側に clickable な節点なし |
| B4 | 本文エリアの余白は**タブバー**の高さだけを見ている（帯の高さは参照していない） | `frontend/src/mobile-shell.css:41-44` の `.mobile-content { padding-bottom: calc(var(--tabbar-height, 56px) + env(safe-area-inset-bottom, 0px)); }` |
| B5 | `.mobile-shell` は縦並びの flex で、帯は通常の要素（絶対配置ではない）＝削除しても空白は残らない | `frontend/src/mobile-shell.css:9-13`（`display:flex; flex-direction:column`）／`:16-27` の `.mobile-topbar` に `position: sticky` はあるが in-flow |

## C. 削除してはいけないもの

| # | 事実 | 根拠 |
|---|---|---|
| C1 | トークン `--topbar-height` は **PC** でも使う＝残す | `frontend/src/topbar.css:13`（`height: var(--topbar-height)`）／`frontend/src/loading-animations.css:383`（`.sa-drawer__header` の `min-height`） |
| C2 | `--z-topbar` は下部タブバーが使う＝残す | `frontend/src/mobile-shell.css` のタブバー側で参照（帯と共用） |
| C3 | ページ内の見出しは各ページで**見えたまま**。視覚的に隠しているのは受信箱だけ | `slimHeaderOnMobile` を渡しているのは `frontend/src/pages/inbox/InboxPage.tsx:104` のみ（`grep -rn slimHeaderOnMobile frontend/src` の結果は PageLayout 本体・stories・InboxPage の3箇所） |
| C4 | 受信箱でも読み上げ用の見出しは残る（消さない） | `frontend/src/components/PageLayout.css:21-30` は `position:absolute; width:1px; height:1px; clip-path: inset(50%)` で視覚的に隠すだけ。実機ダンプでも `(45,372)-(48,378)`＝3x6px の「受信箱」として存在 |

## D. 影響範囲（コード参照の網羅）

`grep -rn "mobile-topbar" --include=*.ts --include=*.tsx --include=*.css` の結果、**現行コードの参照は `frontend/src/components/MobileShell.tsx` と `frontend/src/mobile-shell.css` の2ファイルのみ**。他の一致はすべて過去の作業記録（`docs/handoff/mobile-responsive/`、`docs/handoff/mobile-shell-pr-r2b/`、`docs/handoff/mobile-shell-pr-r2d/`、`docs/handoff/fix-z-drawer-close/`）で、現行仕様ではない。E2E の spec に `.mobile-topbar` への参照は**0件**。

## E. ADR との関係

| # | 事実 | 根拠 |
|---|---|---|
| E1 | ADR-140 の決定は「ハンバーガー+Drawer → 下部タブバー」。**上部帯の存在は決めていない** | `docs/adr/ADR-140-mobile-nav-bottom-tabs.md:14-29` |
| E2 | ADR-137 は「MobileShell は DesktopShell と独立した DOM」。本変更は MobileShell 側のみ＝PC に波及しない | `frontend/src/components/MobileShell.tsx:3-4` のコメントが ADR-137 を引用 |
| E3 | ADR-067（トークン強制）に抵触しない。本変更は削除のみで新しい値を書かない | 追加する CSS は無し。トークンは残す（C1） |

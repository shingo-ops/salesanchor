# recon: PC受信箱でページが縦に約30pxはみ出す件

> この文書は何か: PC の受信箱で、ページ全体に縦のスクロールバーが出る原因を、本番の画面とコードで確かめた記録。

親（設計仕様書）: [docs/specs/inbox/README.md](../../specs/inbox/README.md) ／ 設計: [design.md](./design.md)

- 調査: 2026-11-23 Claude Opus（設計担当）。コードの基準は origin/main bef5a7a8b。
- 前の件（PC受信箱の3列の幅・ADR-1086）の調査 `docs/handoff/inbox-pc-column-width/recon.md` §3-1 で「縦に 31px はみ出す」と記録し、対象外にしていた件。

## 1. 既存 ADR の検索

- `git grep -l -i -E "tooltip|HeaderButton|page-header-actions" -- docs/adr` → `docs/adr/ADR-067-design-token-enforcement.md` の1件だけ（`:141` opacity 0/1 の直書き許可の説明で tooltip に触れるだけ）。吹き出し（tooltip）の位置の決めごとを定めた ADR は無い。
- 関係する決めごと: ADR-067（デザイントークン）、ADR-144（UI ガバナンス。部品は `components/` と共通 CSS を先に使う）。
- 注: `frontend/src/components.css:496` の見出しコメントは「ADR-069: 標準コンポーネントクラス」と書くが、`docs/adr/ADR-069-uptime-kuma-activation.md` は監視ダッシュボードの件で、標準部品の ADR ファイルは `docs/adr/` に見つからない（`git grep -l -i "page-header-actions" -- docs/adr` は 0 件）。本件ではこのコメントを直さない（範囲外）。

## 2. コードの事実

### 2-1. 吹き出しの共通の作り（SSOT）

`frontend/src/components.css:437-457`:
- `:437-441` のコメントに「要素は position: relative/fixed/absolute/sticky が必要」「インラインフローの要素は各コンポーネントのCSSに position: relative を追加すること」と書かれている。
- `:443-446` `[data-tooltip]::after` は `position: absolute; top: calc(100% + 8px);`。
- `:463-466` `[data-tooltip]::before` は `position: absolute; top: calc(100% + 4px);`。
- `:458-459` 普段は `opacity: 0; visibility: hidden;`（見えないが、場所は取る＝ページの高さに数えられる）。

### 2-2. 受信箱のヘッダー右端のボタン

`frontend/src/pages/inbox/InboxPage.tsx:86-114`:
- `:86` `<div className="page-header-actions">`
- `:87-95` テンプレート（`Button variant="ghost"`・`:92` `data-tooltip={t("nav.templates")}`）
- `:96-104` FAQ（`Button variant="ghost"`・`:101` `data-tooltip={t("faq.title")}`）
- `:105-113` 設定（`<button className="icon-btn">`・`:110` `data-tooltip={t("inbox.settings.tooltip")}`）
- `:83` `const showHeaderActions = !isMobile;`（PC とタブレットで出す。スマホでは出さない）

`frontend/src/components.css:501-512` `.page-header-actions` と `.page-header-actions .icon-btn` には `position` が無い。`:516-` `.icon-btn` にも無い。

→ 3つのボタンはどれも `position: static`。吹き出しの `position: absolute` は、位置の基準になる親が無いため、ページ全体（最初の箱）を基準にし、`top: 100% + 8px` ＝ 窓の下端より下に置かれる。

### 2-3. 他に data-tooltip を使う場所（`git grep -n "data-tooltip" -- frontend/src`）

| 場所 | 位置の基準 | PC でのはみ出し |
|---|---|---|
| `frontend/src/components/DesktopShell.tsx:416`・`:444` | 親に position あり | なし（下の §3 の実測） |
| `frontend/src/pages/inbox/InboxMessageThread.tsx:471` | relative | なし |
| `frontend/src/pages/inbox/InboxConversationList.tsx:82`・`frontend/src/pages/inbox/InboxConversationListMobile.tsx:89`（絞り込みの開閉） | static | PC ではなし（§3） |
| `frontend/src/pages/inbox/InboxKartePanel.tsx:174`（カルテを閉じる） | static | PC ではなし（§3） |
| `frontend/src/pages/inbox/InboxPage.tsx:92`・`:101`・`:110`（本件） | static | **あり** |

`.page-header-actions` を使う画面は他に5つある（`frontend/src/pages/companies/CompaniesPage.tsx:174`・`frontend/src/pages/company-detail/CompanyDetailPage.tsx:99`・`frontend/src/pages/contacts/ContactsPage.tsx:241`・`frontend/src/pages/dashboard/DashboardPage.tsx:384`・`frontend/src/pages/design-system/DesignSystemPage.tsx:412-452`）。この中で `data-tooltip` を渡すのは受信箱だけ（上の grep）。

## 3. 本番での実測（2026-11-23・https://app.salesanchor.jp/lead-chat・窓 1626×1392・Chrome）

| 測ったもの | 値 |
|---|---|
| ページの高さ `document.documentElement.scrollHeight` | 1426 |
| 窓の高さ `innerHeight` | 1392 |
| はみ出し | **34px** |
| 吹き出しの見えない部分をすべて消した（`[data-tooltip]::after,::before{display:none}` を手元だけで差し込み） | 1392（はみ出し 0） |
| ヘッダーの3つのボタンの `::after` の位置 `top` | 1400px（窓の下端 1392 + 8） |
| ヘッダーの3つのボタンの `position` | static |
| ダッシュボード・リード一覧 | はみ出しなし（ヘッダーに吹き出し付きのボタンが無い） |

- はみ出し 34px の内訳: 吹き出しの上端 1400px ＋ 吹き出しの高さ（文字の小さい1行＋上下の余白）で 1426px。
- 前の調査の「31px」は、窓の高さが違う日の値（同じ原因）。

### 3-1. 直し方の試し（手元のブラウザだけ。本番のファイルは変えていない）

`.page-header-actions [data-tooltip]{position:relative}` を手元で差し込んだ結果:

| 測ったもの | 値 |
|---|---|
| ページの高さ | 1392（はみ出し 0） |
| 設定ボタンの `::after` の位置 `top` | 42px（高さ 36px のボタンのすぐ下） |
| 横のはみ出し（`scrollWidth` と `innerWidth`） | 同じ（はみ出しなし） |
| 設定ボタンにマウスを乗せたとき | 「設定」の吹き出しがボタンのすぐ下に見えた（画面写真で確認）。直す前は窓の外に出ていて見えなかった |

## 4. 観測事実・仮説・未確認

- 観測事実: §2・§3 のとおり。
- 仮説: なし。
- 未確認: タブレット帯（768〜1279px）での実測（本番で窓の大きさを変えられない。前の件の K7 と同じ事情）。ただし同じ3つのボタンが同じ CSS で出るので、原因と直し方は同じ。確かめは GitHub 上の画面の自動試験で行う（design.md §6）。

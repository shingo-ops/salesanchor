# recon: PC受信箱の3列の幅（一覧・会話・カルテ）

> この文書は何か: PC の受信箱で、会話一覧・会話欄・顧客カルテの3列が今それぞれ何pxで、どこで決まっているかを、コードと本番の実測で調べた記録。

親（設計仕様書）: [docs/specs/inbox/README.md](../../specs/inbox/README.md) ／ 設計: [design.md](./design.md) ／ 決定: [ADR-1086](../../adr/ADR-1086-inbox-pc-column-width.md)

- 調査日: 2026-11-23（基準: origin/main 2b4e2c205）
- 調査者: Claude Opus（設計担当）

## 1. 既存 ADR の検索結果

- 検索: `git grep -l -i -E "受信箱.*(幅|カラム|列)|inbox.*(width|column)|karte-panel|3カラム|3列" origin/main -- docs/adr` → ADR-063・ADR-064・ADR-1001（無関係）・README。
- `docs/adr/FEATURE-INDEX.md:42`（受信箱行）→ ADR-108 ／ ADR-110 ／ ADR-022 ／ ADR-061 ／ ADR-063 ／ ADR-064 ／ ADR-143。
- `docs/adr/ADR-064-inbox-meta-exact-replica.md:104-105` は左 280px・右 360px と書くが、同 ADR `:117` が「パネル幅の記述は現在の実装と異なるため、本ADRを根拠に実装を判断してはならない」と明記している。
- `docs/specs/design-system/visual-language/design.md:119` は「PC帯の寸法は ADR-064 の担当範囲」とする。つまり今、PC 3列の幅を正しく決めている有効な決定記録は無い → 本件で ADR-1086 を起こす。
- カルテ 396px の出どころ: `frontend/src/tokens.css:347-348`（「カルテパネル専用値（見本 karte_reference.html 準拠）」・ADR-108 の見本）。

## 2. 幅を決めているコード

| 何 | 場所 | 値 |
|---|---|---|
| 受信箱の外枠（左余白） | `frontend/src/pages/inbox/InboxPage.css:4-12` | `padding-left: var(--space-3)`（12px） |
| 左：会話一覧 | `frontend/src/pages/inbox/InboxPage.css:82-85` | `width: var(--width-inbox-panel)`・伸び縮みしない |
| 一覧の幅の値 | `frontend/src/tokens.css:312` | `--width-inbox-panel: 443px` |
| 真ん中：会話欄 | `frontend/src/pages/inbox/InboxPage.css:392`（`.inbox-center`） | 実測 `flex: 1 1 0%`（残り全部） |
| 右：カルテ | `frontend/src/pages/inbox/InboxPage.css:635-641` | `width: var(--karte-panel-width)`・`margin-left: var(--space-14px)`（14px） |
| カルテの幅の値 | `frontend/src/tokens.css:348` | `--karte-panel-width: 396px` |
| タブレット帯（≤1279px）の一覧 | `frontend/src/pages/inbox/InboxPage.css:904` | `width: 35%; min-width: var(--inbox-left-panel-min-w)`（220px・`tokens.css:343`） |
| タブレット帯のカルテ（右から出る引き出し） | `frontend/src/pages/inbox/InboxPage.css:922` | `width: var(--karte-panel-width) !important; max-width: 92vw` |
| スマホ帯（≤767px）の一覧・カルテ | `frontend/src/pages/inbox/InboxPage.css:1041-1048`・`:1244-1251` | 一覧 `width: 100%`・カルテ `width: 100% !important` |
| 画面左のメニュー | `frontend/src/sidebar.css:19`・`:281` | 閉じた状態 54px。本文は `margin-left: 54px` |
| 全要素の箱の数え方 | `frontend/src/index.css:444-448` | `box-sizing: border-box`（線の太さも幅に含む） |
| 帯の境目 | `frontend/src/constants/breakpoints.ts`・`frontend/src/tokens.css:122` | PC は 1280px 以上 |

- 箱の入れ子（`frontend/src/pages/inbox/InboxPage.tsx:161-273`）: `.inbox-wrapper`（横並び）の中に `.inbox-main-area`（`:163`・縦並び・`flex: 1`。CSS `InboxPage.css:15-21`）とカルテ（`:245` `InboxKartePanel`）。`.inbox-main-area` の中に上のタブ列（`:168`）と `.inbox-columns`（`:190`）。`.inbox-columns` の中に一覧（`InboxConversationList.tsx:60`）と会話欄。
  - よって `%` の基準は、カルテ＝`.inbox-wrapper` の中身の幅、一覧＝`.inbox-columns` の幅（＝`.inbox-main-area` の幅）。どちらにも左右の余白・線は無い（`InboxPage.css:4-12`・`:15-21`・`:75-79`）。
- カルテは設定で隠せる: `frontend/src/pages/inbox/InboxKartePanel.tsx:130-133` `style={{ display: inboxSettings.showRightPanel ? undefined : "none" }}`。
- `--width-inbox-panel` と `--karte-panel-width` を使う場所は `InboxPage.css:83`・`:636`・`:922` の3か所だけ（`git grep` で frontend/src 全体を走査。.tsx からの参照なし）。

## 3. 本番の実測（2026-11-23・https://app.salesanchor.jp/lead-chat・PO の Chrome・読み取りのみ）

### 3-1. 実ウィンドウ 1440px

- `innerWidth=1440`・`documentElement.clientWidth=1425` → 縦スクロールバーが 15px を使っている。
- `scrollHeight=779` > `clientHeight=748` → ページが縦に 31px はみ出している（スクロールバーが出る原因。本件の対象外・別件）。
- 左から: メニュー 54 ／ 外枠の左余白 12 ／ 一覧 443 ／ 会話欄 506 ／ すき間 14 ／ カルテ 396 → 合計 1425（`clientWidth` と一致）。

### 3-2. 画面幅ごと（body の幅を一時的に変えて測定。PC帯の CSS のまま。測定後は元に戻した）

| 窓の幅 | body | 一覧 | 会話欄 | カルテ |
|---|---|---|---|---|
| 1280 | 1265 | 443 | 346 | 396 |
| 1366 | 1351 | 443 | 432 | 396 |
| 1440 | 1425 | 443 | 506 | 396 |
| 1536 | 1521 | 443 | 602 | 396 |
| 1920 | 1905 | 443 | 986 | 396 |

- 式: 会話欄 = body幅 − 54 − 12 − 443 − 14 − 396。5幅すべてで一致。
- 測れなかったこと: ウィンドウの大きさ変更は効かなかった（`innerWidth` 1440 のまま）。iframe での測定は `contentDocument` が null で不可。

## 4. 規則・検査の実物

- `frontend/scripts/check-css-hardcoded-values.js:63-68`（sizing-px）: width 等に生の px（4px以上）を書くと CI で止まる。`var()`/`calc()` を含む値は検査しない。`%` は検査しない（`InboxPage.css:904` の `35%` は直書きのまま残っている）。
- `%` のトークンの前例: `frontend/src/tokens.css:499` `--drawer-panel-w-mobile-inset: 83%`。
- 新しいトークンを足すと `frontend/scripts/check-new-tokens.js` が PR 本文の「デザイントークン変更時」チェック欄を確かめる。
- 使われなくなったトークンは `frontend/scripts/check-unused-tokens.js`（`.github/workflows/design-token-audit.yml:26`。止めない監査）が数える。
- CSS の書き出し先: `frontend/vite.config.ts:18` `cssTarget: ['chrome87', 'safari14', 'firefox78', 'edge88']`。
  - `min()` は対応範囲内（MDN `/mdn/content` web/css/reference/values/min を Context7 で確認。`width: min(40%, 400px)` の例が公式にある）。
  - コンテナ単位（`cqw`）は Safari 14 が対象に入るため使わない。
- 同じファイルを触る開いた PR: #2919・#2914・#2911・#2895・#2889・#2884・#2879（色トークン・2026-06 の古い PR。幅のトークンは触らない）。受信箱のスマホ幅は Android 側の担当（本件はスマホ帯を触らない）。

## 5. 観測事実・仮説・未確認

- 観測事実: §2・§3・§4。
- 仮説: なし。
- 未確認: 一覧 320〜330px での中身の見え方（名前・最後のメッセージの省略位置）。タブレット帯（1024px 付近）では今も一覧が約 335px（`35%`）で表示されているので、同程度の幅は既に本番で使われている。最終確認は実装後の画面確認（design.md §6）で行う。

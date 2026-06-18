# ADR-140: モバイルナビ刷新 — 下部タブバー方式への移行

| 項目 | 内容 |
|------|------|
| ステータス | Accepted |
| 決定日 | 2026-06-17 |
| 起案者 | Planner（Web Claude） |
| 承認 | Shingo 2026-06-17 |
| 関連ADR | ADR-137（Adaptive Shell Architecture: DesktopShell/MobileShell 分離） |
| 関連doc | `docs/handoff/mobile-responsive/design.md`・`recon.md` |

---

## What（何をするか）

1. **MobileShell のナビ方式変更**: 現行のハンバーガーボタン＋Drawerを、下部タブバー（主役4タブ＋「もっと」シート）に置き換える。
2. **Drawer/Modal ブレークポイント是正**: `Drawer.css` と `Modal.css` で生値 `640px` を使用している `@media` クエリを公式値 `767px` に統一する。

PC/タブレット（≥768px）は DesktopShell が担当し、本ADRの変更は一切加えない。

### 下部タブバーの構成

| タブ | ルート | 表示条件 |
|------|--------|---------|
| ホーム | `/` | 常時（dashboard.view権限） |
| 受信箱 | `/lead-chat` | prefs.show_chat_menu |
| 受注管理 | `/orders` | orders.view権限 |
| 在庫 | `/inventory` | products.view権限 |
| もっと | — | 常時（残ナビ項目をシートで表示） |

「もっと」シート内容: スケジュール・リード/CRM・発注管理・見積請求管理・売上管理・報酬管理・管理センター

---

## Why（なぜこうするか）

### 現状の問題

1. **ハンバーガー方式のUX問題**: 目的画面への遷移に2タップ（ハンバーガー→目的地）が必要。営業現場での頻繁な画面切り替えに摩擦が大きい。
2. **Drawer/Modal の境界帯バグ**: `640px` の生値使用により、タブレット寄りの幅帯（641〜767px）でフルスクリーン化すべき箇所が固定幅のままになる。公式トークン `--breakpoint-mobile-max: 767px` と乖離。

### 採用する方式の根拠

- **Apple HIG「Tab Bars」/ Google Material「Bottom navigation」**: 主要な行き先が3〜5個のとき下部ナビを推奨。5個超は「もっと（More）」へ集約。我々の4タブ＋もっとはこの推奨範囲に収まる。
- **業務アプリの定石**: PC＝サイドバー、モバイル＝下部タブが標準的パターン（Slack・Notion・各種ECバックオフィス）。
- **ADR-137との整合**: DesktopShell/MobileShellの分離（ADR-137）によりPC側への影響なしでモバイル専用改善が可能。

### スコープ外（意図的に除外）

- 各ページ内部のレイアウト崩れ（テーブルはみ出し・フォーム幅）→ 第二弾
- 非公式ブレークポイント全掃（640px以外）→ 第三弾
- CIガード（breakpoint allowlist）整備 → 第三弾

---

## 受け入れ基準（KGI）

| # | 基準 | 検証方法 |
|---|------|---------|
| G1 | 375px で横スクロール無し | Playwright `document.scrollWidth <= window.innerWidth` |
| G2 | 375px でサイドバー余白なし・コンテンツ全幅 | Playwright `getBoundingClientRect().width ≈ viewport.width` |
| G3 | 下部タブ4つで遷移・「もっと」でシート開閉 | Playwright click → URL変化 / シート表示確認 |
| G4 | タップ領域 高さ≥44px | Playwright `getBoundingClientRect().height >= 44` |
| G5 | 641〜767px で Drawer/Modal が全画面 | Playwright 700px: Drawer/Modal 幅 = viewport 幅 |
| 構造1 | 1280px でPC表示が変化しない | Playwright 視覚差分ゼロ |
| 構造2 | 640px の生値消滅 | `grep "640px" Drawer.css Modal.css` → 0件 |
| 構造3 | 375px で sidebar-panel が DOM に存在しない | Playwright `.sidebar-panel` 不在（MobileShell使用時） |

---

## 実装PR

| PR | 内容 |
|----|------|
| PR-A (`feature/morimoto/mobile-bp-token`) | Drawer/Modal 640→767 是正 ＋ 本design.md/recon.md保存 |
| PR-B (`feature/morimoto/mobile-nav-tabs`) | MobileShell ハンバーガー→下部タブ刷新 ＋ Playwright G1〜G5 |

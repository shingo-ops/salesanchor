# Phase 3 設計 — スマホレスポンシブ第一弾（土台：モバイルナビ刷新）

| 項目 | 内容 |
|------|------|
| 対象ADR | ADR-140（新規起案・本doc §A に What/Why 骨子内包） |
| recon | `docs/handoff/mobile-responsive/recon.md`（追補recon 2026-06-17）＋初回recon 2026-06-17 |
| 日付 | 2026-06-17 |
| 担当 | Planner（Web Claude） |
| 関連 | `docs/specs/component-standard.md`（3バンド・44pxタップ標準）、ADR-112（設計起点フローv2）、ADR-137（Adaptive Shell Architecture） |

---

## 決定ログ（PO承認済み・このセッションで確定）

| 決定 | 内容 | 承認 |
|------|------|------|
| 第一弾スコープ | 土台＝「スマホでの画面とメニューを成立させる」（各ページ内部の崩れは第二弾） | Shingo 2026-06-17 |
| KGI | G1〜G5（§受け入れ基準） | Shingo 2026-06-17 |
| ナビ方式 | モバイルは**下部タブ**（主役4＋もっと）。PC/タブレットは現状サイドバー維持 | Shingo 2026-06-17 |
| 主役4タブ | ホーム／受信箱／受注管理／在庫。「もっと」に残り（リード・見積請求・管理・スケジュール等） | Shingo 2026-06-17 |

---

## §A 新規ADR What/Why 骨子（ADR-140に転記済み）

- **What**: モバイル幅（≤767px）でのナビゲーションを、現行のハンバーガー＋Drawerから下部タブバー（4タブ＋もっと）へ切り替える。PC/タブレット（≥768px）は現状の左サイドバーを維持する。あわせて、Drawer/Modalのブレークポイント不整合（640px生値）を公式トークン値（767px）に是正する。
- **Why**: 主用途がスマホでの顧客対応・現場オペレーションであり、下部タブは片手操作・1タップ遷移で常用に最も適する（外部事例参照）。現状のハンバーガー方式は2タップ必要（ハンバーガー→目的地）で、日常操作の摩擦が大きい。Drawer/ModalのブレークポイントはADR公式値と14px（640〜767px帯）で乖離しており、タブレット境界付近の挙動が意図と異なる。
- **Scope外**: 各ページ内部のレイアウト（はみ出すテーブル・広いフォーム＝入力欄展開）。非公式ブレークポイント全掃（640px以外）。CIガード全体整備。`/design-preview` 本番露出の是非。

---

## 外部・過去事例の参照と我々への応用

- 事例1: Apple HIG「Tab Bars」/ Google Material「Bottom navigation」— 主要な行き先が3〜5個のときに下部ナビを推奨、5個超は「もっと（More）」へ集約する。→ 我々への応用: 主役4タブ＋「もっと」で残りを格納する構成は、両ガイドラインの推奨範囲そのまま。
- 事例2: 一般的な業務/コミュニケーションアプリ（メッセージ系・ECバックオフィス系）— PC＝サイドバー、モバイル＝下部タブ＋ハンバーガー、と画面幅でナビを分けるのが定石。→ 我々への応用: DesktopShell/MobileShellの分離（ADR-137）の上に、MobileShell内部をハンバーガー→下部タブに切り替え。
- 社内過去事例: ADR-022（サイドバー化）で「モバイルでハンバーガー化」は Phase 2 として明示的に先送りされていた（2026-05-12）。ADR-137でMobileShellが実装された。→ 我々への応用: 本第一弾がさらにその先（下部タブ化）にあたる。

---

## 受け入れ基準（KGI G1〜G5＋構造）— process-artifacts gate 用

検証幅: モバイル＝375px、境界帯＝641〜767px（700px代表）、PC＝1280px。自動はPlaywright、最終はShingo実機。

| # | 基準 | 検証方法 |
|---|------|---------|
| G1 | 375px で共通の枠・トップバー・下部タブが横にはみ出さない（横スクロール無し） | Playwright 375px: `document.scrollWidth <= window.innerWidth` を全主要ルートで確認（`mobile-nav.spec.ts`） |
| G2 | 375px で本文が画面の横幅いっぱい（サイドバー分の余白が無い） | Playwright 375px: メインコンテンツ要素の幅が viewport 幅とほぼ一致（差 ≤ パディング分） |
| G3 | 下部タブ4つで各画面へ遷移でき、「もっと」でシートが開閉する | Playwright: 各タブ click → URL 変化／「もっと」click → シート表示 → 閉じる |
| G4 | 下部タブ各項目・「もっと」・主要ボタンのタップ領域が高さ≥44px | Playwright: 対象要素の `getBoundingClientRect().height >= 44` |
| G5 | 641〜767px帯で Drawer/Modal が全画面で開く（中途半端な幅にならない） | Playwright 700px: Drawer/Modal 展開時の幅が viewport 幅と一致 |
| 構造1 | PC（1280px）でサイドバー等の既存ナビが変化していない | Playwright 1280px 視覚差分（変更前後で diff 無し）＋ `git diff` でPC専用CSSの無改変確認 |
| 構造2 | 640px の生値が Drawer/Modal から消え、公式トークンを参照している | `grep -rn "640px" frontend/src/components/Drawer.css frontend/src/components/Modal.css` → 0件 |
| 構造3 | モバイルでサイドバー（`sidebar-panel`）が非表示になる（DesktopShell非表示） | Playwright 375px: DesktopShell が DOM に存在しない（`#sidebar-panel` 不在） |

---

## §B 技術 How（develop 環境での実態を踏まえた修正版）

### 前提: develop 時点の実装状況

ADR-137（PR-R2-A〜D, #2313）により develop では以下が実装済み:
- `DesktopShell.tsx`: PC/タブレット向けサイドバーシェル
- `MobileShell.tsx`: モバイル向けシェル（現状: ハンバーガー＋Drawer方式）
- `NavItemList.tsx`: ナビ項目リストコンポーネント
- `useIsMobile()`: 767px以下でtrueを返すフック
- App.tsx: useIsMobile()でDesktopShell/MobileShellを切り替え
- 構造3（sidebar-panel非表示）は **MobileShell使用時にDesktopShellがレンダリングされないことで達成済み**

### B-1. Drawer/Modal の 640→767 統一＋トークン化（PR-A）

- 対象: `Drawer.css:104` / `Modal.css:96` の `640px` を `767px` に変更
- 注意: CSS @media で `var()` は使用不可。`767px` の生値＋`/* = --breakpoint-mobile-max */` コメントで参照先を明示
- 影響幅帯: 641〜767px で Drawer/Modal がフルスクリーン表示になる（これが意図された挙動）

### B-2. MobileShell をハンバーガー→下部タブに刷新（PR-B）

現状の MobileShell DOM構造:
```
MobileShell (.mobile-shell)
├── MobileTopBar (.mobile-topbar — hamburger + title + avatar)
├── MobileDrawerBackdrop
├── MobileDrawer (.mobile-drawer)
│   └── NavItemList variant="mobile"（全ナビ項目）
└── .mobile-content → <Outlet />
```

変更後の DOM構造:
```
MobileShell (.mobile-shell)
├── .mobile-content → <Outlet />（上部・全幅）
├── MobileTabBar (.mobile-tabbar — position:fixed, bottom:0)
│   ├── TabItem(ホーム: /)
│   ├── TabItem(受信箱: /lead-chat)
│   ├── TabItem(受注管理: /orders)
│   ├── TabItem(在庫: /inventory)
│   └── MoreButton(「もっと」)
└── MoreSheet (.mobile-more-sheet — position:fixed, bottom:0, slide-up)
    └── NavItemList variant="more"（脇役全項目）
    ※ backdrop クリック/外クリックで閉じる
```

実routes（recon §E 確認済み）:
- ホーム: `to="/"` (DesktopShell:内 NavLink)
- 受信箱: `to="/lead-chat"` (prefs.show_chat_menu 条件付き)
- 受注管理: `to="/orders"` (permission: orders.view)
- 在庫: `to="/inventory"` (permission: products.view)

「もっと」シートの項目（permissions不問で全表示・各自権限で非表示は実装しない v1）:
- スケジュール: `/schedule`
- リード/CRM: `/crm`
- 発注管理: `/purchase-orders`
- 見積・請求管理: `/quotes`（または showSalesLink 条件）
- 売上管理: `/sales`
- 報酬管理: `/commissions`
- 管理センター: `/management-center`

AvatarButton（ユーザーメニュー）:
- 現MobileShell の `.mobile-topbar-avatar` を下部タブバーのトレイまたは「もっと」シートに移動
- 位置: タブバーの右端に小さいアバターボタン（inline）

### KPI

- 主KPI: G1〜G5＋構造1〜3 がすべてPASS

---

## §C 弊害・トレードオフ

| リスク | 対策 |
|--------|------|
| 既存 mobile-shell.spec.ts がハンバーガー前提のテスト | PR-B でハンバーガー検証をタブ検証に置換（既存テストを削除して新規に書き直し） |
| 「もっと」シートの作り込み過剰 | v1は単純なシート表示に限定。リッチ化は継続課題 |
| タブバーでコンテンツ下部が隠れる | .mobile-content に `padding-bottom: 60px`（タブバー高さ）を設定 |

---

## §D 計画票（PR分割・1リリース1変更原則）

| PR | 内容 | 危険度 | ゲート |
|----|------|--------|------|
| PR-A | Drawer/Modal 640→767 統一（B-1）＋design.md + ADR-140 保存 | 通常 | CI＋構造2・G5。CI緑で自動デプロイ可 |
| PR-B | MobileShell ハンバーガー→下部タブ刷新（B-2）＋Playwright G1〜G4・構造1/3 | 通常（モバイル幅限定） | CI＋G1〜G4・構造1/3。**本番反映前にShingo実機確認を挟む** |

---

## §E architect 実装前 recon 結果（2026-06-17 確定）

| # | 確認項目 | 結果 |
|---|---------|------|
| E1 | ホーム/受信箱/受注管理/在庫の実route名 | `/`（DesktopShell内 NavLink:end）/ `/lead-chat`（prefs.show_chat_menu条件）/ `/orders`（orders.view権限）/ `/inventory`（products.view権限） |
| E2 | --breakpoint-mobile-max 等の実トークン名・実値 | `--breakpoint-mobile-max: 767px`（tokens.css:113）/ `--breakpoint-tablet-min: 768px`（tokens.css:114） |
| E3 | 640px の該当全箇所 | `Drawer.css:104`・`Modal.css:96` の2か所のみ（@mediaとして） |
| E4 | 既存サイドバー全項目（「もっと」に入る脇役） | スケジュール(`/schedule`)・リード/CRM(`/crm`)・発注管理(`/purchase-orders`)・見積請求(`/quotes`系)・売上管理(`/sales`)・報酬管理(`/commissions`)・管理センター(`/management-center`) |
| E5 | モバイルでサイドバー非表示時の検索・ユーザーメニュー到達手段 | avatar-btn は `position:fixed`（sidebar.css:109）でサイドバー非表示でも常時表示。MobileShellではTopBar内に inline AvatarButton を配置（既実装）。グローバル検索バーはLayout層に存在しない（各ページ内実装）→ 影響なし |

---

## §F 継続（完了後）

- 第二弾: 各ページ内部のスマホ化（入力欄展開582件・テーブルのモバイル化）。Task 1E/2E/3E/4Eの実画面展開と統合。
- 第三弾候補: 非公式ブレークポイント全掃（560/720/800/1023）＋CIガード整備。
- 監視: PR-B本番反映後、Shingo実機（手持ちスマホ）でG1〜G5を目視確認し、進捗台帳を更新。

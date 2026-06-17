# recon — スマホレスポンシブ 現在地確定

**仕事名**: スマホレスポンシブ 現在地確定（KGI着手前）
**日付**: 2026-06-17（追補: 2026-06-17）
**対象ADR**: なし（デザインシステム一元管理の一環。関連: ADR-027, ADR-067, ADR-137）
**担当**: architect（読み取り専用・推測禁止）
**ブランチ**: develop（チェックアウト済み）

---

## クラスタA — レスポンシブの基礎

| # | 確認事項 | マーク | file:line | 詳細 |
|---|---------|--------|-----------|------|
| A1 | viewport meta | ✅ | `frontend/index.html:7` | `width=device-width, initial-scale=1.0` 存在 |
| A2 | 公式3バンドトークン | ✅ | `frontend/src/tokens.css:113-116` | `--breakpoint-mobile-max:767px` / `--breakpoint-tablet-min:768px` / `--breakpoint-tablet-max:1279px` / `--breakpoint-desktop-min:1280px` 定義済み |
| A3 | responsive.css の @media | ✅ | `frontend/src/responsive.css` | ファイル存在。`@media (max-width: 768px)` に8クラス定義（詳細は追補クラスタ①-3参照） |
| A4 | responsive.css import | ✅ | `frontend/src/App.tsx:87` 付近 | App.tsx で import 済み |

---

## クラスタB — 標準部品の実在とモバイル分岐

| # | 確認事項 | マーク | file:line | 詳細 |
|---|---------|--------|-----------|------|
| B1 | 部品7点の実在 | ✅ | `frontend/src/components/{Button,Card,TextField,Select,Textarea,Badge,DataTable}.tsx` | 全7部品存在確認 |
| B2 | タップ領域 44px | ✅ | `frontend/src/components/Button.css:30-38` | `@media (max-width: 767px)` で `min-height: var(--btn-min-height-mobile, 44px)` 自動適用（WCAG 2.5.5） |
| B3 | Card余白の自動圧縮 | ✅ | `frontend/src/components/Card.css:34-37` | `@media (max-width: 767px)` で `var(--comp-card-padding-compact)` に縮小 |
| B4 | DataTable 横スクロール | ✅ | `frontend/src/components/DataTable.css:12-18` | `.comp-table { overflow-x: auto; min-width: var(--comp-table-min-width); }` |
| B5 | Card.tsx 「Preview専用」コメント | ⚠️ | `frontend/src/components/Card.tsx:1-11` | **「Preview専用」コメント残存**（技術的依存なし・コメントのみ） |
| B6 | main に Card.tsx 存在 | ✅ | `main:frontend/src/components/Card.tsx` | main にも同一内容で存在 |

---

## クラスタC — 実画面への展開度（残作業量）

| # | 確認事項 | マーク | 置換済 / 残 / 合計 | 詳細 |
|---|---------|--------|--------------------|------|
| C1 | 入力欄の金型展開 | ❌ | **17 / 582 / 599 件**（展開率 2.8%） | `<input>`: 439件 / `<select>`: 115件 / `<textarea>`: 45件 / 新TextField等: 17件 |
| C2 | Badge の展開 | ⚠️ | **33 / 97 / 130 件**（展開率 25%） | CSS `.badge-\|.status-badge`: 130件 / React `<Badge`: 33件 |
| C3 | DataTable の適用 | ⚠️ | 主要3ページ✅ / raw `<table>` 残 34件 | LeadsPage/CompaniesPage/OrdersPage は DataTable 採用済み |
| C4 | Button・Card 利用数（参考） | ⚠️ | **48件**（pages/） | 部品展開は初期段階 |

---

## クラスタD — スマホ特有レイアウト/ナビ

| # | 確認事項 | マーク | file:line | 詳細 |
|---|---------|--------|-----------|------|
| D1 | Sidebar・Layout モバイル対応 | ✅ | `frontend/src/components/MobileShell.tsx`（develop） | ADR-137 (PR-R2-A〜D) により DesktopShell/MobileShell 分離済み。モバイルでは MobileShell が表示され sidebar-panel は DOM に存在しない |
| D2 | TopBar モバイル対応 | ✅ | `frontend/src/mobile-shell.css:29` | MobileShell の `.mobile-topbar` がトップバーを担当 |
| D3 | Drawer 実装 | ✅ | `frontend/src/components/Drawer.tsx` / `frontend/src/components/Drawer.css:104` | 存在。`@media (max-width: 640px)` で全画面（640px = 非公式値・PR-A で修正対象） |
| D4 | Modal の非公式 bp 640px | ⚠️ | `frontend/src/components/Modal.css:96,104` | `@media (max-width: 640px)` でボトムシート。公式 767px とズレ（PR-A で修正対象） |
| D5 | 一覧テーブルのモバイルはみ出し | ✅ | `frontend/src/components/DataTable.css:12-18` | DataTable 化済みは overflow-x:auto で横スクロール |

---

## クラスタE — 非公式ブレークポイントの残存棚卸し

| # | 確認事項 | マーク | 件数 / 値 | 詳細 |
|---|---------|--------|----------|------|
| E1 | 非公式 @media breakpoint（確定） | ⚠️ | **6値・8か所** | 480px(1): `company-forms.css:206` / 560px(1): `InboxPage.css:1453` / 640px(2): `Drawer.css:104`, `Modal.css:96` / 720px(1): `GoalSettingPage.css:32` / 960px(1): `DashboardPage.css:66` / 1023px(1): `ParseReviewPage.css:92` |
| E2 | CI allowlist / baseline | ❌ | 0件 | `.github/` / `scripts/` から検出されず |
| E3 | JS側の非公式値 | ⚠️ | 6件 | `frontend/src/constants/breakpoints.ts:31` に定義あり |

---

## クラスタF — プレビュー画面の生存確認

| # | 確認事項 | マーク | file:line | 詳細 |
|---|---------|--------|-----------|------|
| F1 | design-preview ルート | ✅ | `frontend/src/App.tsx:289` | DEV限定ではない。ログイン後URL直打ちで本番でも到達可能 |

---

---

# 追補 recon — 不明点4件の解消（2026-06-17）

---

## クラスタ①: Layout.tsx のモバイルナビ・ロジック

| # | 確認項目 | マーク | file:line | 事実 |
|---|---------|--------|-----------|------|
| 1-1 | ハンバーガー実装の有無 | ✅ | `frontend/src/components/MobileShell.tsx:29` （develop） | ADR-137 PR-R2-B で MobileShell のハンバーガー+Drawer 実装済み |
| 1-2 | サイドバーのモバイル表示 | ✅ | `frontend/src/components/MobileShell.tsx` + App.tsx | App.tsx の `useIsMobile()` で 767px 以下は MobileShell をレンダリング。DesktopShell（sidebar-panel）は DOM に存在しない |
| 1-3 | responsive.css 8クラスの正体（main時点の事実） | ⚠️ | `frontend/src/responsive.css:7-65` | main時点では `.layout`（実: `app-shell`）/ `.sidebar`（実: `sidebar-panel`）/ `.sidebar-nav`（実: `sidebar-nav-items`）が死にCSS。develop では MobileShell 分離により解消 |
| 1-4 | サイドバー幅の決定 | ✅ | `frontend/src/sidebar.css:19,35` | DesktopShell で `--sidebar-width-collapsed: 54px` |
| 1-5 | モバイルでの崩れ | ✅ | MobileShell使用で解消 | App.tsx で MobileShell に切り替え済みのため崩れなし（develop） |

**この結果から言える事実**:
1. main では Layout.tsx ＋ responsive.css の死にCSS 構造が残存（構造3未達成）。
2. develop では MobileShell 分離により構造3達成済み。
3. PR-B は MobileShell の**ハンバーガー → 下部タブ**切り替えが主作業。

---

## クラスタ②: Drawer/Modal の 640px 採用

| # | 確認項目 | マーク | file:line | 事実 |
|---|---------|--------|-----------|------|
| 2-1 | 640px 使用箇所全列挙（@media） | ✅ | `Drawer.css:104` / `Modal.css:96` | @media として 2か所のみ |
| 2-2 | 640px のトークン化 | ❌ | — | 生値。公式トークン `--breakpoint-mobile-max: 767px` と別物 |
| 2-3 | 640px 採用の理由 | ❓ | コミット 46a3fa77（Drawer）/ 78896434（Modal） | 意図コメントなし |
| 2-4 | 640→767 影響幅帯 | ✅ | 641〜767px 幅帯 | Drawer/Modal がこの幅帯でフルスクリーン化するようになる（これが正しい挙動） |
| 2-5 | 連鎖の有無 | ✅ | 2か所のみ | 連鎖なし |

---

## クラスタ③: Task 1E 完了条件

| # | 確認項目 | マーク | file:line | 事実 |
|---|---------|--------|-----------|------|
| 3-1 | Task 1E の受け入れ基準 | ❌ | `docs/specs/component-standard.md` | **定義なし**（「Task 1E で行う」参照のみ） |
| 3-2 | 入力欄残582件の内訳 | ✅ | pages/ grep | `<input>` 439件 / `<select>` 115件 / `<textarea>` 45件 |
| 3-3 | Badge残97件・DataTable残34件 | ✅ | grep結果 | Badge CSS残: 定義ファイル込み130件。DataTable raw: 34件 |
| 3-4 | Card.tsx 「Preview専用」コメント | ✅ | `Card.tsx:1-11` | コメントのみ。技術的依存なし |
| 3-5 | baseline/allowlist | ❌ | — | 存在しない |
| 3-6 | 非公式bp全箇所 | ✅ | 各 file:line | 6値8か所。CI ガードなし |

---

## クラスタ④: 本番反映状態

| # | 確認項目 | マーク | file:line | 事実 |
|---|---------|--------|-----------|------|
| 4-1 | 7部品 main 存在 | ✅ | 各コンポーネント | 全7部品 main に存在 |
| 4-2 | responsive.css・Drawer/Modal が main 存在 | ✅ | main確認済み | 640px @media も main に存在 |
| 4-3 | develop-main 差分 | ✅ | `git diff main...develop` | **develop は main より大幅に先行**（ADR-137 MobileShell 等が develop のみに存在） |
| 4-4 | Card.tsx コメント両ブランチ | ✅ | develop・main両方確認 | 両ブランチに「Preview専用」コメント残存 |
| 4-5 | /design-preview 本番到達可否 | ✅ | `App.tsx:289` | DEV限定でない。本番で到達可能 |

---

## §E architect 実装前 recon 結果（2026-06-17 確定・設計doc §E より転記）

| # | 確認項目 | 結果（file:line） |
|---|---------|-----------------|
| E1 | ホーム/受信箱/受注管理/在庫の実route名 | `"/"` NavLink end / `"/lead-chat"` prefs.show_chat_menu条件 / `"/orders"` orders.view権限 / `"/inventory"` products.view権限 |
| E2 | `--breakpoint-mobile-max` 実トークン名・実値 | `--breakpoint-mobile-max: 767px`（`frontend/src/tokens.css:113`） |
| E3 | 640px の全箇所 | `frontend/src/components/Drawer.css:104` / `frontend/src/components/Modal.css:96`（2件のみ） |
| E4 | 既存サイドバー全項目 | 主役4: `/`・`/lead-chat`・`/orders`・`/inventory` / 脇役: `/schedule`・`/crm`・`/purchase-orders`・`/quotes`系・`/sales`・`/commissions`・`/management-center` |
| E5 | サイドバー非表示時の検索・ユーザーメニュー到達手段 | avatar-btn は `position:fixed`（`sidebar.css:109`）で常時表示。グローバル検索バーはLayout層に存在しない。影響なし |

---

## file:line 引用表（主要参照点）

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/index.html:7` | viewport meta 存在 |
| `frontend/src/tokens.css:113-116` | 公式3バンドトークン定義 |
| `frontend/src/components/MobileShell.tsx` | モバイルシェル実装（ADR-137・develop） |
| `frontend/src/components/Drawer.css:104` | `@media (max-width: 640px)` — **PR-A修正対象** |
| `frontend/src/components/Modal.css:96` | `@media (max-width: 640px)` — **PR-A修正対象** |
| `frontend/src/App.tsx:289` | `/design-preview` は本番アクセス可 |
| `frontend/src/sidebar.css:109` | `avatar-btn { position: fixed }` — ユーザーメニュー常時表示 |

---

## 現在地サマリー（3行・develop基準）

1. **土台**: ADR-137（PR-R2-A〜D）により DesktopShell/MobileShell 分離済み。モバイルで sidebar-panel が非表示になる構造3は達成済み（develop）。
2. **残作業**: MobileShell のハンバーガー → 下部タブ刷新（PR-B）。Drawer/Modal 640px → 767px 是正（PR-A）。部品実画面展開（入力欄582件/Badge97件）は第二弾以降。
3. **640px**: Drawer.css:104 と Modal.css:96 の2か所のみ。CI ガードなし。是正は PR-A で対応。

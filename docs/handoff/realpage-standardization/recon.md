# Phase 2 Recon: 実ページの標準部品化

> **作成日**: 2026-06-09  
> **担当**: architect（読み取り専用。アプリコード変更0件）  
> **ステータス**: 完了

---

## 冒頭サマリ

### 1. 対象ページ数
- **38 実ページ** (App.tsx のルーティングから列挙、dev/preview/coming-soon 除外)  
  参照: `frontend/src/App.tsx:104–298`

### 2. ハードコード総量の概観（多い順 上位）

| 順位 | ページ | inline style 件数 | うち生値（rem/px/hex直書き） | modal-overlay |
|------|--------|:-----------------:|:---------------------------:|:-------------:|
| 1 | ChannelsPage (640行) | **38** | 0（全 var()使用） | 0 |
| 2 | ParseReviewPage (927行) | **31** | **10**（rem直書き多数） | 0 |
| 3 | InvoiceCreatePage (480行) | **28** | 0（全 var()使用） | 0 |
| 4 | InventoryPage (728行) | **27** | 2（rem直書き） | 0 |
| 5 | ProductsPage (745行) | **26** | 2（rem直書き） | 1 |
| 6 | DiscordInboundPage (468行) | **26** | 2（px直書き） | 1 |
| 7 | QuoteCreatePage (332行) | **24** | 0 | 0 |
| 8 | InvoiceDetailPage (257行) | **24** | 0 | 0 |
| 9 | InventoryOffersPage (605行) | **23** | 3（rem直書き） | 1 |
| 10 | RolesPage (578行) | **9** | **13（hex直書き12+fallback1）** | 2 |

**全体**: 実ページ全体で inline style 約 363 件。  
うち **CSS トークン正規使用（`var(--xxx)`）** ≈ 330 件（形式問題のみ、色・寸法値は適切）。  
うち **生値ハードコード（rem/px/hex直書き）** ≈ 33 件（主に super-admin 系とRolesPage）。

### 3. 推奨パイロット: **TeamsPage**

`frontend/src/pages/teams/TeamsPage.tsx`（256行）

**理由**:
- 規模が小さく検証が速い（256行 ≒ 最小クラスの CRUD ページ）
- `modal-overlay` が2件（lines 160, 183）→ Modal コンポーネントへの置換を2パターン実証できる
- inline style が1件のみ（`var()` 使用、単純）
- hex/raw値ハードコードなし
- カスタムタブなし
- ビジネスリスクが低い（チーム管理、コア売上フローではない）
- 成功すれば他24ページの `modal-overlay` 置換の**テンプレート**になる

---

## 1. 実ページ一覧（ルーティング全列挙）

出典: `frontend/src/App.tsx:104–298`。dev 専用（`/design-system`, `/design-preview`）と
placeholder（`/faq`, `/templates`）は除外。

### 1-1. 認証フロー（公開）

| # | パス | コンポーネント | 行数 |
|---|------|--------------|------|
| A1 | `/login` | LoginPage | 74 |
| A2 | `/register` | RegisterPage | 384 |
| A3 | `/register/address` | RegisterAddressPage | 300 |

### 1-2. CRM

| # | パス | コンポーネント | 行数 |
|---|------|--------------|------|
| B1 | `/crm/leads` | LeadsPage | 433 |
| B2 | `/crm/companies` | CompaniesPage | 594 |
| B3 | `/crm/companies/:id` | CompanyDetailPage | 292 |
| B4 | `/crm/contacts` | ContactsPage | 537 |
| B5 | `/crm/archive` | ArchivesPage | 53 |

### 1-3. 在庫・商品

| # | パス | コンポーネント | 行数 |
|---|------|--------------|------|
| C1 | `/inventory` | InventoryPage | 728 |
| C2 | `/own-inventory` | OwnInventoryPage | 260 |
| C3 | `/admin/products` | ProductsPage | 745 |

### 1-4. 見積・請求

| # | パス | コンポーネント | 行数 |
|---|------|--------------|------|
| D1 | `/quotes` | QuotesPage | 204 |
| D2 | `/quotes/new` | QuoteCreatePage | 332 |
| D3 | `/quotes/:id` | QuoteDetailPage | 217 |
| D4 | `/invoices` | InvoicesPage | 128 |
| D5 | `/invoices/new` | InvoiceCreatePage | 480 |
| D6 | `/invoices/:id` | InvoiceDetailPage | 257 |

### 1-5. 営業・取引

| # | パス | コンポーネント | 行数 |
|---|------|--------------|------|
| E1 | `/` | DashboardPage | 748 |
| E2 | `/goals/settings` | GoalSettingPage | 447 |
| E3 | `/deals` | DealsPage | 390 |
| E4 | `/orders` | OrdersPage | 177 |
| E5 | `/sales` | SalesPage | 176 |
| E6 | `/commissions` | CommissionsPage | 271 |
| E7 | `/commission-settings` | CommissionSettingsPage | 331 |

### 1-6. スタッフ・スケジュール

| # | パス | コンポーネント | 行数 |
|---|------|--------------|------|
| F1 | `/staff` | StaffPage | 333 |
| F2 | `/teams` | TeamsPage | 256 |
| F3 | `/roles` | RolesPage | 578 |
| F4 | `/shifts` | ShiftsPage | 89 |
| F5 | `/schedule` | SchedulePage | 794 |
| F6 | `/reports` | StaffReportsPage | 104 |

### 1-7. チャンネル・仕入

| # | パス | コンポーネント | 行数 |
|---|------|--------------|------|
| G1 | `/channels` | ChannelsPage | 640 |
| G2 | `/bots` | BotsPage | 305 |
| G3 | `/suppliers` | SuppliersPage | 181 |
| G4 | `/purchase-orders` | PurchaseOrdersPage | 294 |
| G5 | `/data` | ERPPage | 78 |

### 1-8. 受信箱・受注

| # | パス | コンポーネント | 行数 |
|---|------|--------------|------|
| H1 | `/lead-chat` | InboxPage | 229 |

### 1-9. 設定・管理

| # | パス | コンポーネント | 行数 |
|---|------|--------------|------|
| I1 | `/settings` | NotificationsPage | 89 |
| I2 | `/account/settings` | AccountSettingsPage | 17 (wrapper) |
| I3 | `/admin/tenant-profile` | TenantProfilePage | 271 |
| I4 | `/admin/tenant-policy` | TenantPolicyPage | 332 |
| I5 | `/admin/discord-config` | DiscordConfigPage | 425 |
| I6 | `/admin/discord-announce` | DiscordAnnouncePage | 126 |
| I7 | `/admin/inventory-visibility` | InventoryVisibilityPage | 183 |
| I8 | `/super-admin/inbound` | DiscordInboundPage | 468 |
| I9 | `/super-admin/inbound/:id/review` | ParseReviewPage | 927 |
| I10 | `/super-admin/phase-switch` | PhaseSwitchPage | 226 |
| I11 | `/super-admin/inventory-offers` | InventoryOffersPage | 605 |

### 1-10. 統合・インテグレーション

| # | パス | コンポーネント | 行数 |
|---|------|--------------|------|
| J1 | `/management-center/integrations/google-drive` | GoogleDriveIntegrationPage | 197 |
| J2 | `/management-center/integrations/fedex` 他 | CarrierIntegrationPage | 220 |

---

## 2. 各ページの現状

### 2-1. 標準部品の採用状況

**現在 使われている標準コンポーネント**（`frontend/src/components/` 配下）:
- `PageLayout` — 全実ページで使用（ほぼ網羅）
- `ConfirmModal` — 18ページ以上で使用（削除確認ダイアログ）
- `CompanyContactSelector` — 3ページ（LeadsPage, DealsPage, ContactsPage）
- `MergeLeadModal` / `MergeCompanyModal` — それぞれ1ページ
- `PriorityScoreBadge` / `PriorityScoreOverride` — LeadsPage のみ
- `SubMenu` — NavBar/Layout レベルで使用（ページ直接使用なし）

**存在するが実ページで未使用の標準コンポーネント**:

| コンポーネント | 実ページ使用数 | 代わりに使われているもの |
|--------------|:--------:|------------------------|
| `Modal` | **0** | `<div className="modal-overlay">` (31件) |
| `DataTable` | **0** | `<table className="data-table">` (50件) |
| `EmptyState` | **0** | ページ独自の空表示 or なし |
| `Tabs` | **0** | `<nav className="tab-nav">` (4+ ページ) |
| `Button` | **0** | `<button className="btn-primary">` 直書き |
| `TextField` / `Select` / `Textarea` | **0** | `<input>` / `<select>` / `<textarea>` 直書き |

出典:
- Modal 未使用: `grep -r "from.*components/Modal" frontend/src/pages --include="*.tsx"` → 0件
- DataTable 未使用: `grep -r "DataTable" frontend/src/pages --include="*.tsx"` → 0件
- modal-overlay 件数: `grep -r "modal-overlay" frontend/src/pages --include="*.tsx"` → 31件

### 2-2. inline style 詳細（主要ページ）

#### TeamsPage（推奨パイロット）
`frontend/src/pages/teams/TeamsPage.tsx`
- inline style 1件: `frontend/src/pages/teams/TeamsPage.tsx:187` — `style={{ marginBottom: "var(--space-4)" }}`（var()使用、色なし）
- modal-overlay 2件: `frontend/src/pages/teams/TeamsPage.tsx:160`、`:183`
- data-table: なし（テーブルなし）
- ConfirmModal 使用: `:245`

#### LeadsPage
`frontend/src/pages/leads/LeadsPage.tsx`
- inline style **0件**
- modal-overlay 2件: `:251`（新規フォーム）、`:329`（コンバート）
- data-table 1件: （table.data-table）
- 使用コンポーネント: ConfirmModal, CompanyContactSelector, MergeLeadModal, PriorityScoreBadge, PageLayout

#### DealsPage
`frontend/src/pages/deals/DealsPage.tsx`
- inline style **0件**
- modal-overlay 1件: `frontend/src/pages/deals/DealsPage.tsx:244`
- data-table 1件: `:337`
- 使用コンポーネント: ConfirmModal, CompanyContactSelector, PageLayout

#### ChannelsPage（inline style 最多）
`frontend/src/pages/channels/ChannelsPage.tsx`
- inline style **38件**（全て `var()` 使用 — 色・寸法トークンは正しく使用されているが形式はクラスに移行すべき）
- modal-overlay 0件
- 例: `frontend/src/pages/channels/ChannelsPage.tsx:337` — `style={{ marginRight: "var(--space-2)" }}`

#### InvoiceCreatePage（inline style 第3位）
`frontend/src/pages/invoice-create/InvoiceCreatePage.tsx`
- inline style **28件**（大半は `var()` 使用。テーブル内カラム幅など）
- modal-overlay 0件（フォームはページ埋め込み型）
- 例: `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:242` — `style={{ display: "flex", gap: "var(--space-2)" }}`
- 例: `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:344` — `<table className="data-table" style={{ minWidth: "var(--table-min-width-base)" }}`

#### RolesPage（hex ハードコード最多）
`frontend/src/pages/roles/RolesPage.tsx`
- inline style **9件**
- **hex 直書き 13件**:
  - `frontend/src/pages/roles/RolesPage.tsx:74`–`:85` — カラーピッカー配列 12色（`"#ef4444"` 〜 `"#64748b"`）
  - `frontend/src/pages/roles/RolesPage.tsx:249` — フォールバック `"#6c757d"`
- modal-overlay 2件: `:（確認済み）`
- 備考: カラーピッカーはロール色の任意設定機能。ユーザーが選ぶ色なので「自由値」として (c) 相当。ただし `"#6c757d"` フォールバックはトークン化可能

#### ParseReviewPage（inline style 第2位・rem直書き最多）
`frontend/src/pages/super-admin/ParseReviewPage.tsx`
- inline style **31件**
- **rem 直書き 10件**:
  - `frontend/src/pages/super-admin/ParseReviewPage.tsx:560` — `style={{ minWidth: "10rem", maxWidth: "16rem" }}`
  - `:593` — `style={{ width: "6rem" }}`
  - `:614` — `style={{ width: "5.5rem" }}`（以下同様）
- modal-overlay 0件
- super-admin 専用ページ。標準化優先度は低い

#### DiscordInboundPage
`frontend/src/pages/super-admin/DiscordInboundPage.tsx`
- inline style **26件**
- px 直書き 2件: `frontend/src/pages/super-admin/DiscordInboundPage.tsx:285` — `style={{ width: "72px" }}`、`:286` — `style={{ width: "104px" }}`
- modal-overlay 1件: `frontend/src/pages/super-admin/DiscordInboundPage.tsx:（確認済み）`

#### InvoicesPage / QuotesPage（カスタムタブ）
- `frontend/src/pages/invoices/InvoicesPage.tsx:73` — `<nav className="tab-nav">`
- `frontend/src/pages/quotes/QuotesPage.tsx:112` — `<nav className="tab-nav">`
- Tabs コンポーネント（`frontend/src/components/Tabs.tsx`）は未使用
- inline style: InvoicesPage 0件、QuotesPage 5件

#### CompaniesPage / CompanyDetailPage（カスタムタブ）
- `frontend/src/pages/companies/CompaniesPage.tsx:448`–`:450` — `<button className=\`tab ${...}\`>`（3タブ）
- `frontend/src/pages/company-detail/CompanyDetailPage.tsx:141`–`:153` — `<button className=\`tab ${...}\`>`（5タブ）
- Tabs コンポーネント未使用

#### DashboardPage
`frontend/src/pages/dashboard/DashboardPage.tsx`
- inline style **2件**
  - `frontend/src/pages/dashboard/DashboardPage.tsx:226` — `style={{ width: \`\${clamped}%\`, background: color }}` （動的計算値 + 変数 → (c)）
- hex 直書き 1件: `:180` — `|| "#1877F2"` (CSS変数取得失敗時のフォールバック。`var(--accent)` が取れない場合のガード)
- Recharts 使用。チャート固有処理は (c)

---

## 3. 分類（置換方針の土台）

### (a) 標準部品で置換すべき独自実装

**最大の機会: modal-overlay → Modal コンポーネント**

| 対象 | 規模 | 代表ファイル:行 |
|------|------|----------------|
| `<div className="modal-overlay">` 全インスタンス | **31件 × 26ファイル** | `frontend/src/pages/teams/TeamsPage.tsx:160` |
| `<nav className="tab-nav">` カスタムタブ | **4 ページ** | `frontend/src/pages/invoices/InvoicesPage.tsx:73` |
| `<button className=\`tab ${...}\`>` タブボタン群 | **2 ページ** | `frontend/src/pages/companies/CompaniesPage.tsx:448` |

`Modal` コンポーネントの API（`frontend/src/components/Modal.tsx:37–49`）:
```tsx
<Modal open={bool} onClose={fn} title={t("...")} size="md" footer={...}>
  {children}
</Modal>
```
フォーカストラップ・Esc 閉鎖・a11y・Portal 実装済み。現在の raw div モーダルにはこれらが一切ない。

**DataTable コンポーネントへの移行**（優先度は Modal より低い）

| 対象 | 規模 | 代表ファイル:行 |
|------|------|----------------|
| `<table className="data-table">` | **50件** | `frontend/src/pages/bots/BotsPage.tsx:246` |

DataTable の column-definition API は既存の `<th>/<td>` 直書きより verbose になるため、
段階的移行が適切（まず Modal を完了させてから検討）。

### (b) トークン化すべき直書き

| 分類 | 件数 | 代表ファイル:行 | 処置案 |
|------|------|----------------|--------|
| rem/px 直書き inline style | **~33件** | `frontend/src/pages/super-admin/ParseReviewPage.tsx:560` | CSS クラス化またはトークン変数化 |
| hex 直書き（RolesPage カラーピッカー配列） | **12件** | `frontend/src/pages/roles/RolesPage.tsx:74–85` | ユーザー選択値なので (c) 扱いも可能（後述） |
| hex フォールバック（#1877F2, #6c757d） | **2件** | `frontend/src/pages/dashboard/DashboardPage.tsx:180`、`roles/RolesPage.tsx:249` | `var(--accent)` / `var(--text-muted)` に統一 |
| `var()` 使用の inline style（形式問題のみ） | **~330件** | `frontend/src/pages/channels/ChannelsPage.tsx:337` | CSS クラスに移行（優先度低・視覚変更なし） |

### (c) ページ固有で残してよいレイアウト

| ページ | 残す理由 |
|--------|---------|
| DashboardPage チャート/KPI グリッド | Recharts 固有・動的サイズ計算 (`frontend/src/pages/dashboard/DashboardPage.tsx:226`) |
| RolesPage カラーピッカー配列 | ユーザーが選択する自由値（デザイントークン外） |
| SchedulePage イベントポップアップ位置 (`left: safeX, top: safeY`) | 計算位置（`frontend/src/pages/schedule/SchedulePage.tsx:358`） |
| InvoiceCreatePage / QuoteCreatePage テーブル内 input 幅 | 業務要件の幅制約（`minWidth`, `width` 指定） |
| ParseReviewPage テーブル列幅 | super-admin 専用・業務要件 |
| hub-shell パターン (CustomerHubPage, ManagementCenterPage) | ページ間ナビ構造。SubMenu と組み合わせて現状維持 |

---

## 4. パイロット候補

### 推奨: TeamsPage
`frontend/src/pages/teams/TeamsPage.tsx`

| 評価軸 | 内容 |
|--------|------|
| **規模** | 256行（最小クラスの CRUD ページ） |
| **代表性** | 標準的な管理 CRUD（リスト＋作成モーダル＋メンバー管理パネル） |
| **依存** | `ConfirmModal`, `PageLayout` のみ。複雑な業務ロジックなし |
| **効果の明確さ** | `modal-overlay` × 2 → `Modal` コンポーネントへの置換が明確（lines 160, 183） |
| **リスク** | チーム管理機能（請求・在庫・SSEなどコアフローではない） |
| **汎用性** | 成功すれば他 24ファイルの `modal-overlay` 置換の**テンプレート**になる |

**置換スコープ（想定）**:
1. `frontend/src/pages/teams/TeamsPage.tsx:160` — 作成フォームモーダル → `<Modal open={showForm} onClose={...} title={t("teams.newTeam")}>`
2. `frontend/src/pages/teams/TeamsPage.tsx:183` — メンバー管理パネル → `<Modal open={...} onClose={...} title={...}>`
3. `frontend/src/pages/teams/TeamsPage.tsx:187` — `style={{ marginBottom: "var(--space-4)" }}` → CSS クラス化（小）
4. `ConfirmModal` は既に標準部品 → 変更不要

**期待 LOC 変化**: +5〜−15行（Modal の props 記述が増えるが div+div が1タグに置き換わる）

### 次点: DealsPage
`frontend/src/pages/deals/DealsPage.tsx`（390行）
- modal-overlay 1件（`frontend/src/pages/deals/DealsPage.tsx:244`）
- inline style 0件（最クリーン）
- data-table 1件（DataTable コンポーネントへの移行も同時試験可能）
- 業務重要度がやや高い（成約管理）ため TeamsPage の後にする

---

## 5. 注意点・依存

1. **Modal コンポーネントのフォーカストラップ**  
   `frontend/src/components/Modal.tsx` は Tab/Shift+Tab のフォーカス循環を実装済み。  
   移行後、フォーム内の `<input>` が意図通りにフォーカスを受け取るか動作確認が必要。

2. **CompanyDetailPage のタブ**  
   `frontend/src/pages/company-detail/CompanyDetailPage.tsx:94` — `switchTab` 関数が「変更があれば離脱防止」ロジックを持つ。  
   Tabs コンポーネントへの移行時はこの `dirty` チェックロジックを保持する必要がある。

3. **modal-overlay の onClick ハンドラ（バブリング）**  
   現行: `<div className="modal-overlay" onClick={close}>` + `<div className="modal" onClick={e => e.stopPropagation()}>` のパターン。  
   Modal コンポーネントは `dismissOnOverlay` prop で同等動作（default: true）。ただし `stopPropagation` の位置が変わるため動作確認必須。

4. **SchedulePage のモーダル**  
   `frontend/src/pages/schedule/SchedulePage.tsx:168` — モーダルに `onClose` prop を渡すパターン（外部コンポーネント渡し）。Modal 移行時は props 設計が他ページと異なる。

5. **OrdersFormModal / PurchaseOrdersFormModal（ファイル分離済みモーダル）**  
   `frontend/src/pages/orders/OrdersFormModal.tsx` 等は既にファイル分離済み。  
   これらは Modal コンポーネントを使うよう直接修正する（親ページ経由不要）。

---

## 6. 不明点

1. **Button / TextField / Select / Textarea の採用方針**  
   現行ページはすべて `<button>`, `<input>`, `<select>` 直書き。  
   これら form element 系の標準部品移行は CSS クラスが変わらないか確認が必要（デザインの差異が生じる場合がある）。**調査未完了**。

2. **EmptyState コンポーネントの既存使用状況**  
   実ページでの使用が 0件だが、InboxPage や DiscordInboundPage では空状態の独自表示が存在する。  
   EmptyState のデザインが現行の空状態表示と一致するか比較未実施。

3. **Chromatic / Storybook での視覚差分ベースライン**  
   Modal コンポーネントへの移行後、既存のモーダルスタイルとの視覚差分（border, padding, shadow）が生じる可能性がある。  
   CSS (`frontend/src/components/Modal.css`) と各ページの `.modal` スタイルが一致するか確認が必要。

---

*アプリのコード変更: 0件*

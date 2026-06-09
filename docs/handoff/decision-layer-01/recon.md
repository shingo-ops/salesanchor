# 決定レイヤー① — ステータス見た目の対応表 recon

> **実施日**: 2026-06-08  
> **ブランチ**: feature/morimoto/decision-layer-01-recon  
> **種別**: Read-only recon（コード変更なし）

---

## 冒頭サマリ

### 1. before 件数

| 種別 | 件数 |
|------|------|
| 集約関数（ステータス→見た目ロジックがまとまっている） | **5** |
| 散在インライン（JSXの中でステータスを直接バッジクラスに変換） | **24** |
| **合計サイト数** | **29** |
| うち個別分岐数（branches） | **約 44+** |

### 2. ステータス種別数と一覧

**10 ドメイン**

| # | ドメイン | 型定義場所 | 値の例 |
|---|----------|-----------|--------|
| 1 | LeadStatus | `frontend/src/constants/leadStatus.ts:9` | `lead`, `negotiating`, `existing_customer`, `follow_up_short`, `follow_up_long`, `lost`, `out_of_scope` |
| 2 | QuoteStatus | インライン (`quotesSort.ts`) | `approved`, `rejected`, `expired`, `sent`, `draft` |
| 3 | InvoiceStatus | インライン (`InvoicesPage.tsx`) | `paid`, `voided`, `overdue`, `issued`, `draft`, `sent` |
| 4 | DealStatus | インライン (`DealsPage.tsx`) | CSS直注入（`badge-${d.status}`） |
| 5 | OrderStatus | インライン (`OrdersTable.tsx`) | `awaiting_payment`, `sourcing`, `awaiting_shipping`, `completed`, `trouble`, `cancelled` |
| 6 | PurchaseOrderStatus | インライン (`PurchaseOrdersPage.tsx`) | `draft`, `ordered`, `received`, `cancelled`, `error` |
| 7 | ParseStatus (Discord) | `frontend/src/pages/super-admin/DiscordInboundPage.tsx:65` | `approved`, `parsed`, `parsed_rule_only`, `parsed_llm`, `rejected`, `unparsed`, `budget_exhausted`, `ignored_routing`, `pending`, `parsing` |
| 8 | StaffStatus | インライン (`StaffPage.tsx`) | `active`, その他 |
| 9 | BotStatus | インライン (`BotsPage.tsx`) | `active`, その他 |
| 10 | ProspectRank | インライン (`LeadsPage.tsx`) | `A`, `B+`, `B`, `B-`, `仮C`, `確定C` |

### 3. 既存の部分集約

**5 関数が存在する**が、スコープは各ページ/ファイルに閉じている。

| 関数名 | ファイル | 行 | 対象ドメイン | スコープ |
|--------|---------|-----|------------|---------|
| `badgeVariant()` | `frontend/src/pages/quotes/quotesSort.ts` | 20 | Quote | QuotesPage・QuoteDetailPage で使用 |
| `statusBadgeClass()` | `frontend/src/pages/purchase-orders/PurchaseOrdersPage.tsx` | 173 | PurchaseOrder | 同ページ内のみ |
| `statusBadgeClass()` | `frontend/src/pages/super-admin/DiscordInboundPage.tsx` | 66 | ParseStatus | 同ページ内のみ |
| `getStageBadge()` | `frontend/src/pages/inbox/InboxKartePanel.tsx` | 68 | LeadStatus | カルテパネルのみ |
| `rankBadge()` | `frontend/src/pages/leads/LeadsPage.tsx` | 224 | ProspectRank | LeadsPageのみ |

### 4. 最も目立つ不整合 上位3つ

#### 不整合①: LeadStatus "negotiating" が3色に分裂

同じ `"negotiating"` ステータスが文脈によって異なる色になる。

| 表示場所 | CSSクラス | 色 |
|---------|----------|-----|
| LeadsPage テーブル | `lead-badge-negotiating` | `var(--lead-contact-bg)` （オレンジ系） |
| InboxKartePanel ステージバッジ | `karte-stage-badge--deal` | `var(--warning-bg)` （黄系） |
| Quote/汎用 badge | `badge-negotiating` | `var(--info-bg)` （青系） |

→ 同一概念「商談中」が3種類の色に見える。ユーザーは文脈ごとに色の意味を学習し直す必要がある。

#### 不整合②: InvoicesPage と InvoiceDetailPage でロジックが複製

| ファイル | 行 | 内容 |
|---------|-----|------|
| `frontend/src/pages/invoices/InvoicesPage.tsx` | 110 | `paid→won / voided→lost / overdue→cancelled / issued→negotiating / default→pending` |
| `frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx` | 191 | 同一の inline ternary チェーンが重複 |

→ 集約関数なしで copy-paste。片方だけ変更されるドリフトリスクがある。

#### 不整合③: DealStatus はバッジクラスを CSS 直注入

`frontend/src/pages/deals/DealsPage.tsx:358`
```tsx
<span className={`badge badge-${d.status}`}>
```
→ Deal のステータス値（例: `"negotiating"`, `"won"`）が CSS クラス名と 1:1 で紐付いている。  
ステータス値を変えると CSS も壊れる。中間マッピング層がない。

---

## 全決定ポイント一覧

### A. 集約関数（5件）

#### A-1: `badgeVariant()` — Quote ステータス → バッジバリアント

**ファイル**: `frontend/src/pages/quotes/quotesSort.ts:20–25`

```ts
export const badgeVariant = (status: string): string =>
  status === "approved"  ? "won"
  : status === "rejected" ? "lost"
  : status === "expired"  ? "cancelled"
  : status === "sent"     ? "negotiating"
  : "pending";
```

| 入力値 | 出力クラス（`badge-{variant}`） | 最終色 |
|-------|-------------------------------|--------|
| `"approved"` | `badge-won` | `--success-bg` |
| `"rejected"` | `badge-lost` | `--danger-bg` |
| `"expired"` | `badge-cancelled` | `--danger-bg` |
| `"sent"` | `badge-negotiating` | `--info-bg` |
| default | `badge-pending` | `--warning-bg` |

**使用箇所**: `frontend/src/pages/quotes/QuotesPage.tsx:150`, `frontend/src/pages/quotes/QuotesPage.tsx:188`

---

#### A-2: `getStageBadge()` — LeadStatus → カルテバッジバリアント

**ファイル**: `frontend/src/pages/inbox/InboxKartePanel.tsx:68–79`

```ts
function getStageBadge(status: string): { labelKey: string; variant: string } {
  switch (status) {
    case "lead":              return { variant: "lead",     labelKey: "leads.statusCode.lead" };
    case "negotiating":       return { variant: "deal",     labelKey: "leads.statusCode.negotiating" };
    case "existing_customer": return { variant: "existing", labelKey: "leads.statusCode.existing_customer" };
    case "follow_up_short":   return { variant: "followup", labelKey: "leads.statusCode.follow_up_short" };
    case "follow_up_long":    return { variant: "followup", labelKey: "leads.statusCode.follow_up_long" };
    case "lost":              return { variant: "default",  labelKey: "leads.statusCode.lost" };
    case "out_of_scope":      return { variant: "default",  labelKey: "leads.statusCode.out_of_scope" };
    default:                  return { variant: "default",  labelKey: `leads.statusCode.${status}` };
  }
}
```

| 入力値 | variant | CSSクラス | 最終色 |
|-------|---------|----------|--------|
| `"lead"` | `lead` | `karte-stage-badge--lead` | `--link-active-bg` |
| `"negotiating"` | `deal` | `karte-stage-badge--deal` | `--warning-bg` |
| `"existing_customer"` | `existing` | `karte-stage-badge--existing` | `--success-bg` |
| `"follow_up_short"` / `"follow_up_long"` | `followup` | `karte-stage-badge--followup` | `--bg-subtle` |
| `"lost"` / `"out_of_scope"` | `default` | `karte-stage-badge--default` | `--bg-subtle` |

**CSS定義**: `frontend/src/pages/inbox/InboxPage.css:1301`  
**使用箇所**: `frontend/src/pages/inbox/InboxKartePanel.tsx:152`

---

#### A-3: `statusBadgeClass()` — PurchaseOrderStatus → バッジクラス

**ファイル**: `frontend/src/pages/purchase-orders/PurchaseOrdersPage.tsx:173–186`

```ts
const statusBadgeClass = (status: string): string => {
  switch (status) {
    case "received":  return "badge-won";
    case "cancelled": return "badge-lost";
    case "ordered":   return "badge-negotiating";
    case "error":     return "badge-lost";
    default:          return "badge-pending";
  }
};
```

| 入力値 | 出力クラス | 最終色 |
|-------|----------|--------|
| `"received"` | `badge-won` | `--success-bg` |
| `"cancelled"` | `badge-lost` | `--danger-bg` |
| `"ordered"` | `badge-negotiating` | `--info-bg` |
| `"error"` | `badge-lost` | `--danger-bg` |
| default | `badge-pending` | `--warning-bg` |

**使用箇所**: `frontend/src/pages/purchase-orders/PurchaseOrdersPage.tsx:220`

---

#### A-4: `statusBadgeClass()` — ParseStatus (Discord) → バッジクラス

**ファイル**: `frontend/src/pages/super-admin/DiscordInboundPage.tsx:66–84`

```ts
function statusBadgeClass(status: string): string {
  switch (status) {
    case "approved": case "parsed": case "parsed_rule_only": case "parsed_llm":
      return "badge badge-success";
    case "rejected": case "unparsed":
      return "badge badge-danger";
    case "budget_exhausted": case "ignored_routing":
      return "badge badge-warning";
    case "pending": case "parsing":
    default:
      return "badge badge-secondary";
  }
}
```

| 入力値 | 出力クラス |
|-------|----------|
| `"approved"` / `"parsed"` / `"parsed_rule_only"` / `"parsed_llm"` | `badge badge-success` |
| `"rejected"` / `"unparsed"` | `badge badge-danger` |
| `"budget_exhausted"` / `"ignored_routing"` | `badge badge-warning` |
| `"pending"` / `"parsing"` / default | `badge badge-secondary` |

**使用箇所**: `frontend/src/pages/super-admin/DiscordInboundPage.tsx:430`

---

#### A-5: `rankBadge()` — ProspectRank → バッジ

**ファイル**: `frontend/src/pages/leads/LeadsPage.tsx:224–237`

```ts
const rankBadge = (rank: string | null) => {
  const colorMap: Record<string, string> = {
    "A":    "badge-won",
    "B+":   "badge-confirmed",
    "B":    "badge-negotiating",
    "B-":   "badge-on_hold",
    "仮C":  "badge-pending",
    "確定C": "badge-lost",
  };
  return <span className={`badge ${colorMap[rank] || ""}`}>{rank}</span>;
};
```

| ランク | CSSクラス | 最終色 |
|-------|----------|--------|
| `A` | `badge-won` | `--success-bg` |
| `B+` | `badge-confirmed` | `--success-bg` |
| `B` | `badge-negotiating` | `--info-bg` |
| `B-` | `badge-on_hold` | `--purple-bg` |
| `仮C` | `badge-pending` | `--warning-bg` |
| `確定C` | `badge-lost` | `--danger-bg` |

**使用箇所**: `frontend/src/pages/leads/LeadsPage.tsx:381`

---

### B. インラインマッピング（24サイト）

#### B-1: LeadStatus テーブルバッジ（直注入）

**ファイル**: `frontend/src/pages/leads/LeadsPage.tsx:389`

```tsx
<span className={`badge lead-badge-${l.status}`}>{translateLeadStatus(l.status)}</span>
```

**CSS定義**: `frontend/src/pages-layout.css:383–389`

| CSSクラス | 背景色 |
|----------|--------|
| `.lead-badge-lead` | `--info-bg` |
| `.lead-badge-negotiating` | `--lead-contact-bg` ← **不整合①** |
| `.lead-badge-existing_customer` | `--success-bg` |
| `.lead-badge-follow_up_short` | `--purple-bg` |
| `.lead-badge-follow_up_long` | `--purple-bg` |
| `.lead-badge-lost` | `--danger-bg` |
| `.lead-badge-out_of_scope` | `--bg-hover` |

---

#### B-2: QuotesPage — フィルターボタン

**ファイル**: `frontend/src/pages/quotes/QuotesPage.tsx:150`

```tsx
<span className={`badge badge-${badgeVariant(s)}`}>
```
→ `badgeVariant()` (A-1) を経由

---

#### B-3: QuotesPage — テーブル行

**ファイル**: `frontend/src/pages/quotes/QuotesPage.tsx:188`

```tsx
<span className={`badge badge-${badgeVariant(q.status)}`}>
```
→ `badgeVariant()` (A-1) を経由

---

#### B-4: QuoteDetailPage — inline ternary

**ファイル**: `frontend/src/pages/quote-detail/QuoteDetailPage.tsx:161`

```tsx
badge-${q.status === "approved" ? "won" : q.status === "rejected" ? "lost" : "pending"}
```

| 入力値 | バリアント |
|-------|----------|
| `"approved"` | `won` |
| `"rejected"` | `lost` |
| default | `pending` |

---

#### B-5: InvoicesPage — inline ternary（複製元）

**ファイル**: `frontend/src/pages/invoices/InvoicesPage.tsx:110`

```tsx
badge-${inv.status === "paid" ? "won"
       : inv.status === "voided"   ? "lost"
       : inv.status === "overdue"  ? "cancelled"
       : inv.status === "issued"   ? "negotiating"
       : "pending"}
```

| 入力値 | バリアント |
|-------|----------|
| `"paid"` | `won` |
| `"voided"` | `lost` |
| `"overdue"` | `cancelled` |
| `"issued"` | `negotiating` |
| default | `pending` |

---

#### B-6: InvoiceDetailPage — inline ternary（複製先・不整合②）

**ファイル**: `frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:191`

B-5 と同一ロジックが copy-paste されている。

---

#### B-7: DealsPage — CSS直注入（不整合③）

**ファイル**: `frontend/src/pages/deals/DealsPage.tsx:358`

```tsx
<span className={`badge badge-${d.status}`}>{t(`deals.status_${d.status}`) || d.status}</span>
```
→ DB値 = CSSクラスサフィックスが 1:1 前提。中間マッピング層なし。

---

#### B-8: PurchaseOrdersPage — statusBadgeClass 呼び出し

**ファイル**: `frontend/src/pages/purchase-orders/PurchaseOrdersPage.tsx:220`

```tsx
<span className={`badge ${statusBadgeClass(p.status)}`}>
```
→ A-3 を経由

---

#### B-9: DiscordInboundPage — statusBadgeClass 呼び出し

**ファイル**: `frontend/src/pages/super-admin/DiscordInboundPage.tsx:430`

```tsx
className={statusBadgeClass(m.parse_status)}
```
→ A-4 を経由

---

#### B-10: OrdersTable — フェーズバッジ

**ファイル**: `frontend/src/pages/orders/OrdersTable.tsx:102`

```tsx
<span className={`badge badge-${phase}`}>{PHASE_LABELS[phase] ?? phase}</span>
```
→ phase 値がそのままCSSクラスに（DealsPage と同パターン）

---

#### B-11: OrdersTable — ステータスバッジ

**ファイル**: `frontend/src/pages/orders/OrdersTable.tsx:105`

```tsx
<span className={`badge badge-${o.status}`}>
```
→ 同上

---

#### B-12: StaffPage — active/inactive

**ファイル**: `frontend/src/pages/staff/StaffPage.tsx:309`

```tsx
badge badge-${s.status === "active" ? "won" : "lost"}
```

---

#### B-13: BotsPage — active/inactive

**ファイル**: `frontend/src/pages/bots/BotsPage.tsx:262`

```tsx
badge badge-${b.status === "active" ? "won" : "lost"}
```

---

#### B-14: ERPPage — inline ternary

**ファイル**: `frontend/src/pages/erp/ERPPage.tsx:65`

```tsx
badge-${status === "completed" ? "won" : status === "failed" ? "lost" : "pending"}
```

---

#### B-15: InventoryPage — ハードコード

**ファイル**: `frontend/src/pages/inventory/InventoryPage.tsx:675`

```tsx
<span className="badge badge-negotiating">
```

---

#### B-16: ArchivesPage — ハードコード

**ファイル**: `frontend/src/pages/archives/ArchivesPage.tsx:43`

```tsx
<span className="badge badge-won">
```

---

#### B-17: BuddyPage — is_active

**ファイル**: `frontend/src/pages/buddy/BuddyPage.tsx:79`

```tsx
badge-${p.is_active ? "won" : "lost"}
```

---

#### B-18: BuddyPage — feedback_type

**ファイル**: `frontend/src/pages/buddy/BuddyPage.tsx:94`

```tsx
badge-${f.feedback_type === "Good" ? "won" : "lost"}
```

---

#### B-19: NotificationsPage — is_active

**ファイル**: `frontend/src/pages/notifications/NotificationsPage.tsx:76`

```tsx
badge-${ch.is_active ? "won" : "lost"}
```

---

#### B-20: ProductsPage — ハードコード

**ファイル**: `frontend/src/pages/products/ProductsPage.tsx:644`

```tsx
<span className="badge badge-lost">
```

---

#### B-21: StaffReportsPage — ハードコード

**ファイル**: `frontend/src/pages/staff-reports/StaffReportsPage.tsx:92`

```tsx
<span className="badge badge-negotiating">
```

---

#### B-22: StaffReportsPage — reviewed_at

**ファイル**: `frontend/src/pages/staff-reports/StaffReportsPage.tsx:95`

```tsx
badge-${r.reviewed_at ? "won" : "pending"}
```

---

#### B-23: ShiftsPage — ハードコード

**ファイル**: `frontend/src/pages/shifts/ShiftsPage.tsx:79`

```tsx
<span className="badge badge-negotiating">
```

---

#### B-24: InventoryOffersPage — ハードコード

**ファイル**: `frontend/src/pages/super-admin/InventoryOffersPage.tsx:441`

```tsx
<span className="badge badge-negotiating">
```

---

## CSS 定義場所（視覚出力の SSoT）

### 汎用バッジ色

**ファイル**: `frontend/src/components.css:388–392`

```css
.badge-open, .badge-pending      { background: var(--warning-bg); color: var(--warning-text); }
.badge-negotiating               { background: var(--info-bg);    color: var(--info-text); }
.badge-won, .badge-confirmed, .badge-delivered
                                  { background: var(--success-bg); color: var(--success-text); }
.badge-lost, .badge-cancelled    { background: var(--danger-bg);  color: var(--danger-text); }
.badge-on_hold, .badge-shipped   { background: var(--purple-bg);  color: var(--purple-text); }
```

### リード専用バッジ色

**ファイル**: `frontend/src/pages-layout.css:383–389`

```css
.lead-badge-lead              { background: var(--info-bg); }
.lead-badge-negotiating       { background: var(--lead-contact-bg); }   /* ← 不整合① */
.lead-badge-existing_customer { background: var(--success-bg); }
.lead-badge-follow_up_short   { background: var(--purple-bg); }
.lead-badge-follow_up_long    { background: var(--purple-bg); }
.lead-badge-lost              { background: var(--danger-bg); }
.lead-badge-out_of_scope      { background: var(--bg-hover); }
```

### カルテステージバッジ色

**ファイル**: `frontend/src/pages/inbox/InboxPage.css:1301–1305`

```css
.karte-stage-badge--lead     { background: var(--link-active-bg); color: var(--accent); }
.karte-stage-badge--deal     { background: var(--warning-bg);     color: var(--warning-text); }  /* ← negotiating = --warning-bg */
.karte-stage-badge--existing { background: var(--success-bg);     color: var(--success-text); }
.karte-stage-badge--followup { background: var(--bg-subtle);      color: var(--text-secondary); }
.karte-stage-badge--default  { background: var(--bg-subtle);      color: var(--text-muted); }
```

---

## ドメイン × 集約度マトリクス

| ドメイン | 型定義 | 集約関数 | 散在インライン | スコア |
|---------|--------|---------|------------|-------|
| LeadStatus | ✅ `leadStatus.ts` | △ 2関数（スコープが別） | B-1, B-2系 | △ |
| QuoteStatus | ❌ インライン | ✅ `badgeVariant()` | B-2, B-3, B-4 | △ |
| InvoiceStatus | ❌ インライン | ❌ なし | B-5, B-6（複製） | ❌ |
| DealStatus | ❌ インライン | ❌ なし | B-7（直注入） | ❌ |
| OrderStatus | ❌ インライン | ❌ なし | B-10, B-11 | ❌ |
| PurchaseOrderStatus | ❌ インライン | ✅ `statusBadgeClass()` | B-8 | △ |
| ParseStatus | △ `DiscordInboundPage` | ✅ `statusBadgeClass()` | B-9 | △ |
| StaffStatus | ❌ インライン | ❌ なし | B-12 | ❌ |
| BotStatus | ❌ インライン | ❌ なし | B-13 | ❌ |
| ProspectRank | ❌ インライン | ✅ `rankBadge()` | B-17系 | △ |

---

## 次フェーズへの申し送り

このファイルは **現状（as-is）の事実記録**。提案・実装は別 ADR で行う。

- 集約関数の統合先候補: `frontend/src/utils/statusBadge.ts`（新規作成想定）
- CSS 分裂解消: `--lead-contact-bg` vs `--info-bg` の意味整理が先決
- 型定義 SSoT: 各ドメインの型を `frontend/src/types/` に集約検討

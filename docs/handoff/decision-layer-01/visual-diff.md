# 移行前 視覚差分レポート（現状 vs SSoT）

> **作成日**: 2026-06-09  
> **目的**: ステップ2b（実画面置換）の PO 確認用。全 56 ステータスの「現状 → 新」を網羅。  
> **参照**: `design.md` / `recon.md` / ADR-120

---

## 冒頭サマリ

| カテゴリ | 件数 |
|---------|------|
| **色が変わる status** | **14** |
| **CSS バグが修正される（現行 unstyled）** | **10（ParseStatus 全件）** |
| **変わらない status** | **32** |
| **合計** | **56** |

### 色が変わる 14件（要 PO 確認）

| ドメイン | status | 現状 | 新 | 変化 |
|---------|--------|------|-----|------|
| lead | `lead` | 青（`--info-bg`） | 灰（`--bg-subtle`） | 青 → 灰 |
| lead | `negotiating` | 橙（`--lead-contact-bg`）| 青（`--info-bg`） | 橙 → 青 |
| lead | `follow_up_short` | 紫（`--purple-bg`） | 黄（`--warning-bg`） | 紫 → 黄 |
| lead | `follow_up_long` | 紫（`--purple-bg`） | 黄（`--warning-bg`） | 紫 → 黄 |
| lead | `out_of_scope` | 薄灰（`--bg-hover`） | 灰（`--bg-subtle`） | 薄灰 → 灰 |
| quote | `draft` | 黄（`--warning-bg`） | 灰（`--bg-subtle`） | 黄 → 灰 |
| invoice | `draft` | 黄（`--warning-bg`）| 灰（`--bg-subtle`） | 黄 → 灰 |
| invoice | `sent` | 黄（`--warning-bg`）| 青（`--info-bg`） | 黄 → 青 |
| deal | `open` | 黄（`--warning-bg`）| 灰（`--bg-subtle`） | 黄 → 灰 |
| purchaseOrder | `draft` | 黄（`--warning-bg`）| 灰（`--bg-subtle`） | 黄 → 灰 |
| karte | `lead` | 青（`--link-active-bg`）| 灰（`--bg-subtle`）※ | 青 → 灰 |
| karte | `negotiating` | 黄（`--warning-bg`）| 青（`--info-bg`）※ | 黄 → 青 |
| karte | `follow_up_short/long` | 灰（`--bg-subtle`）| 黄（`--warning-bg`）※ | 灰 → 黄 |
| quoteDetail | `sent` / `expired` | 黄（`--warning-bg`）| 青 / 赤 ※ | 変化あり |

> ※ karte = InboxKartePanel の `getStageBadge()` — 専用 CSS クラスを使用。SSoT 置換時に別途検討が必要。

### ParseStatus — CSS バグ修正（10件）

Discord 解析ステータスの `statusBadgeClass()` は `badge-success`、`badge-danger`、`badge-warning`、`badge-secondary` を返しているが、これらのクラスはプロジェクト CSS に**定義されていない**。現行バッジは**無色（透明背景）**で表示されている。

SSoT 置換後は標準プロジェクトカラーに変わる（バグ修正）。

---

## 全 56 ステータス 詳細差分

### 凡例

| 記号 | 意味 |
|------|------|
| ✅ | 変更なし（同色・同トークン） |
| ⚠️ | 色が変わる（要確認） |
| 🔧 | CSS バグ修正（現行 unstyled） |
| ❓ | 別途確認が必要（karte 専用 CSS） |

---

### LeadStatus（7件）

**現在のコード**: `LeadsPage.tsx:389` — `badge lead-badge-${l.status}`  
**CSS**: `pages-layout.css:383–389`

| status | 現状 CSS クラス | 現状色（Light） | SSoT badge | SSoT色 | 判定 |
|--------|---------------|--------------|-----------|--------|------|
| `lead` | `lead-badge-lead` | 青 `--info-bg` (#bee3f8) | `badge-neutral` | 灰 `--bg-subtle` (#f7fafc) | ⚠️ 青 → 灰 |
| `negotiating` | `lead-badge-negotiating` | 橙 `--lead-contact-bg` (#fbd38d) | `badge-negotiating` | 青 `--info-bg` (#bee3f8) | ⚠️ 橙 → 青 |
| `existing_customer` | `lead-badge-existing_customer` | 緑 `--success-bg` (#c6f6d5) | `badge-won` | 緑 `--success-bg` | ✅ |
| `follow_up_short` | `lead-badge-follow_up_short` | 紫 `--purple-bg` (#e9d8fd) | `badge-pending` | 黄 `--warning-bg` (#fefcbf) | ⚠️ 紫 → 黄 |
| `follow_up_long` | `lead-badge-follow_up_long` | 紫 `--purple-bg` (#e9d8fd) | `badge-pending` | 黄 `--warning-bg` (#fefcbf) | ⚠️ 紫 → 黄 |
| `lost` | `lead-badge-lost` | 赤 `--danger-bg` (#fed7d7) | `badge-lost` | 赤 `--danger-bg` | ✅ |
| `out_of_scope` | `lead-badge-out_of_scope` | 薄灰 `--bg-hover` (#e2e8f0) | `badge-neutral` | 灰 `--bg-subtle` (#f7fafc) | ⚠️ 薄灰 → 灰（近似） |

**変更件数: 5件**（lead, negotiating, follow_up_short, follow_up_long, out_of_scope）

---

### LeadStatus — InboxKartePanel 専用バッジ（5件・別途検討）

**現在のコード**: `InboxKartePanel.tsx:68–79` — `getStageBadge()` → `karte-stage-badge--{variant}`  
**CSS**: `InboxPage.css:1301–1305`

カルテパネルはリード一覧と別のビジュアルシステム（`karte-stage-badge--*`）を持つ。SSoT 置換では `badge badge-${variant}` 形式に変わる。

| status | 現状 CSS クラス | 現状色 | SSoT badge | SSoT 色 | 判定 |
|--------|--------------|--------|-----------|---------|------|
| `lead` | `karte-stage-badge--lead` | 青（`--link-active-bg` #E7F3FF） | `badge-neutral` | 灰（`--bg-subtle`） | ❓ 専用CSS廃止 |
| `negotiating` | `karte-stage-badge--deal` | 黄（`--warning-bg`） | `badge-negotiating` | 青（`--info-bg`） | ❓ |
| `existing_customer` | `karte-stage-badge--existing` | 緑（`--success-bg`） | `badge-won` | 緑（`--success-bg`） | ❓ 同色 |
| `follow_up_short/long` | `karte-stage-badge--followup` | 灰（`--bg-subtle`） | `badge-pending` | 黄（`--warning-bg`） | ❓ |
| `lost` / `out_of_scope` | `karte-stage-badge--default` | 灰（`--bg-subtle`） | `badge-neutral` | 灰（`--bg-subtle`） | ❓ 同色 |

> **Note**: karte バッジは SSoT 置換時に専用CSS（`karte-stage-badge--*`）を廃止してよいか、別途 PO 判断が必要。リードタブの見た目と揃えるか、カルテ独自のビジュアルを維持するかの選択。

---

### QuoteStatus（5件）

**現在のコード**:  
- `QuotesPage.tsx:149, 187` — `badge badge-${badgeVariant(s)}`（`quotesSort.ts:20` 経由）  
- `QuoteDetailPage.tsx:161` — inline ternary（`approved/rejected` のみ、残は `pending`）  

| status | 現状 variant | 現状色 | SSoT variant | SSoT 色 | 判定 |
|--------|------------|--------|-------------|---------|------|
| `draft` | `pending` | 黄（`--warning-bg`） | `neutral` | 灰（`--bg-subtle`） | ⚠️ 黄 → 灰 |
| `sent` | `negotiating` | 青（`--info-bg`） | `negotiating` | 青（`--info-bg`） | ✅ |
| `approved` | `won` | 緑（`--success-bg`） | `won` | 緑（`--success-bg`） | ✅ |
| `rejected` | `lost` | 赤（`--danger-bg`） | `lost` | 赤（`--danger-bg`） | ✅ |
| `expired` | `cancelled` | 赤（`--danger-bg`） | `cancelled` | 赤（`--danger-bg`） | ✅ |

**QuoteDetailPage 追加注意**: `draft`/`sent`/`expired` はすべて `"pending"`（黄）になっている。SSoT 後は 3 色に分かれる。

**変更件数: 1件**（draft: 黄 → 灰）

---

### InvoiceStatus（6件）

**現在のコード**:  
- `InvoicesPage.tsx:110` — inline ternary（paid/voided/overdue/issued の4値のみ処理、残 → pending）  
- `InvoiceDetailPage.tsx:191` — 短い ternary（paid/voided のみ、残はすべて → pending）

| status | 現状（InvoicesPage） | 現状（InvoiceDetailPage） | SSoT variant | SSoT 色 | 判定 |
|--------|-------------------|----------------------|-------------|---------|------|
| `draft` | `pending` → 黄 | `pending` → 黄 | `neutral` → 灰 | ⚠️ 黄 → 灰 |
| `sent` | `pending` → 黄 | `pending` → 黄 | `negotiating` → 青 | ⚠️ 黄 → 青 |
| `issued` | `negotiating` → 青 | `pending` → 黄 ⚠️ | `negotiating` → 青 | InvoicesPage: ✅ / DetailPage: ⚠️ |
| `paid` | `won` → 緑 | `won` → 緑 | `won` → 緑 | ✅ |
| `overdue` | `cancelled` → 赤 | `pending` → 黄 ⚠️ | `cancelled` → 赤 | InvoicesPage: ✅ / DetailPage: ⚠️ |
| `voided` | `lost` → 赤 | `lost` → 赤 | `lost` → 赤 | ✅ |

**⚠️ InvoiceDetailPage の既存バグ**: `issued` と `overdue` が `"pending"`（黄）になっている（InvoicesPage と不一致）。SSoT 置換で正しい色に修正される。

**変更件数: 2件**（draft: 黄 → 灰、sent: 黄 → 青）+ InvoiceDetailPage のバグ修正

---

### DealStatus（5件）

**現在のコード**: `DealsPage.tsx:358` — `badge-${d.status}`（直注入）

| status | 現状 CSS クラス | 現状色 | SSoT variant | SSoT 色 | 判定 |
|--------|--------------|--------|-------------|---------|------|
| `open` | `badge-open` | 黄（`--warning-bg`） | `neutral` | 灰（`--bg-subtle`） | ⚠️ 黄 → 灰 |
| `negotiating` | `badge-negotiating` | 青（`--info-bg`） | `negotiating` | 青（`--info-bg`） | ✅ |
| `won` | `badge-won` | 緑（`--success-bg`） | `won` | 緑（`--success-bg`） | ✅ |
| `lost` | `badge-lost` | 赤（`--danger-bg`） | `lost` | 赤（`--danger-bg`） | ✅ |
| `on_hold` | `badge-on_hold` | 紫（`--purple-bg`） | `on_hold` | 紫（`--purple-bg`） | ✅ |

**変更件数: 1件**（open: 黄 → 灰）

---

### OrderStatus（6件）

**現在のコード**: `OrdersTable.tsx:102, 105` — `badge-${phase}` / `badge-${o.status}`（直注入）

| status | 現状 CSS クラス | 現状色 | SSoT variant | SSoT 色 | 判定 |
|--------|--------------|--------|-------------|---------|------|
| `awaiting_payment` | `badge-awaiting_payment` | 黄（`--warning-bg`） | `awaiting_payment` | 黄（`--warning-bg`） | ✅ |
| `sourcing` | `badge-sourcing` | 青（`--info-bg`） | `sourcing` | 青（`--info-bg`） | ✅ |
| `awaiting_shipping` | `badge-awaiting_shipping` | 紫（`--purple-bg`） | `awaiting_shipping` | 紫（`--purple-bg`） | ✅ |
| `completed` | `badge-completed` | 緑（`--success-bg`） | `completed` | 緑（`--success-bg`） | ✅ |
| `trouble` | `badge-trouble` | 赤（`--danger-bg`） | `trouble` | 赤（`--danger-bg`） | ✅ |
| `cancelled` | `badge-cancelled` | 赤（`--danger-bg`） | `cancelled` | 赤（`--danger-bg`） | ✅ |

**変更件数: 0件** ← 直注入なのでバリアント名が一致

---

### PurchaseOrderStatus（5件）

**現在のコード**: `PurchaseOrdersPage.tsx:173–186` — `statusBadgeClass()`

| status | 現状 variant | 現状色 | SSoT variant | SSoT 色 | 判定 |
|--------|------------|--------|-------------|---------|------|
| `draft` | `pending` | 黄（`--warning-bg`） | `neutral` | 灰（`--bg-subtle`） | ⚠️ 黄 → 灰 |
| `ordered` | `negotiating` | 青（`--info-bg`） | `negotiating` | 青（`--info-bg`） | ✅ |
| `received` | `won` | 緑（`--success-bg`） | `won` | 緑（`--success-bg`） | ✅ |
| `cancelled` | `lost` | 赤（`--danger-bg`） | `lost` | 赤（`--danger-bg`） | ✅ |
| `error` | `lost` | 赤（`--danger-bg`） | `lost` | 赤（`--danger-bg`） | ✅ |

**変更件数: 1件**（draft: 黄 → 灰）

---

### ParseStatus（10件）

**現在のコード**: `DiscordInboundPage.tsx:66–84` — `statusBadgeClass()`  
**現行問題**: `badge-success`, `badge-danger`, `badge-warning`, `badge-secondary` はプロジェクト CSS に定義されていない → **全件バッジが無色（透明）**

| status | 現状クラス | 現状色（実際） | SSoT variant | SSoT 色 | 判定 |
|--------|----------|------------|-------------|---------|------|
| `pending` | `badge badge-secondary` | 無色 | `neutral` | 灰 | 🔧 無色 → 灰 |
| `parsing` | `badge badge-secondary` | 無色 | `negotiating` | 青 | 🔧 無色 → 青 |
| `parsed` | `badge badge-success` | 無色 | `won` | 緑 | 🔧 無色 → 緑 |
| `parsed_rule_only` | `badge badge-success` | 無色 | `won` | 緑 | 🔧 無色 → 緑 |
| `parsed_llm` | `badge badge-success` | 無色 | `won` | 緑 | 🔧 無色 → 緑 |
| `approved` | `badge badge-success` | 無色 | `won` | 緑 | 🔧 無色 → 緑 |
| `rejected` | `badge badge-danger` | 無色 | `lost` | 赤 | 🔧 無色 → 赤 |
| `unparsed` | `badge badge-danger` | 無色 | `lost` | 赤 | 🔧 無色 → 赤 |
| `budget_exhausted` | `badge badge-warning` | 無色 | `pending` | 黄 | 🔧 無色 → 黄 |
| `ignored_routing` | `badge badge-warning` | 無色 | `pending` | 黄 | 🔧 無色 → 黄 |

**変更件数: 10件（すべてバグ修正・視覚改善）**

---

### StaffStatus（3件）

**現在のコード**: `StaffPage.tsx:309` — `s.status === "active" ? "won" : "lost"`

| status | 現状 variant | 現状色 | SSoT variant | SSoT 色 | 判定 |
|--------|------------|--------|-------------|---------|------|
| `active` | `won` | 緑（`--success-bg`） | `won` | 緑（`--success-bg`） | ✅ |
| `inactive` | `lost` | 赤（`--danger-bg`） | `neutral` | 灰（`--bg-subtle`） | ⚠️ 赤 → 灰 |
| `pending` | `lost`（else 節） | 赤（`--danger-bg`） | `lost` | 赤（`--danger-bg`） | ✅（現状維持） |

**変更件数: 1件**（inactive: 赤 → 灰）  
**Note**: `inactive` は「解雇・退職」で赤にしていたが、SSoT では「無効・休止」として灰。

---

### BotStatus（3件）

**現在のコード**: `BotsPage.tsx:262` — `b.status === "active" ? "won" : "lost"`

| status | 現状 variant | 現状色 | SSoT variant | SSoT 色 | 判定 |
|--------|------------|--------|-------------|---------|------|
| `active` | `won` | 緑（`--success-bg`） | `won` | 緑（`--success-bg`） | ✅ |
| `inactive` | `lost` | 赤（`--danger-bg`） | `neutral` | 灰（`--bg-subtle`） | ⚠️ 赤 → 灰 |
| `maintenance` | `lost`（else 節） | 赤（`--danger-bg`） | `lost` | 赤（`--danger-bg`） | ✅（現状維持） |

**変更件数: 1件**（inactive: 赤 → 灰）

---

### ProspectRank（6件）

**現在のコード**: `LeadsPage.tsx:224–237` — `rankBadge()` → colorMap

| ランク | 現状 variant | 現状色 | SSoT variant | SSoT 色 | 判定 |
|-------|------------|--------|-------------|---------|------|
| `A` | `won` | 緑（`--success-bg`） | `won` | 緑（`--success-bg`） | ✅ |
| `B+` | `confirmed` | 緑（`--success-bg`） | `confirmed` | 緑（`--success-bg`） | ✅ |
| `B` | `negotiating` | 青（`--info-bg`） | `negotiating` | 青（`--info-bg`） | ✅ |
| `B-` | `on_hold` | 紫（`--purple-bg`） | `on_hold` | 紫（`--purple-bg`） | ✅ |
| `仮C` | `pending` | 黄（`--warning-bg`） | `pending` | 黄（`--warning-bg`） | ✅ |
| `確定C` | `lost` | 赤（`--danger-bg`） | `lost` | 赤（`--danger-bg`） | ✅ |

**変更件数: 0件** ← 既存 colorMap が SSoT と一致

---

## 変更まとめ（PO 確認リスト）

### A. 意味的に納得できる変化（確認推奨）

| # | ドメイン | status | 変化 | 理由 |
|---|---------|--------|------|------|
| 1 | lead | `lead`（新規リード） | 青 → 灰 | 「新規・未着手」は neutral（灰）が設計意図 |
| 2 | lead | `negotiating`（商談中）| 橙 → 青 | 不整合①解消: 全ドメインで negotiating = info（青）に統一 |
| 3 | lead | `follow_up_short/long` | 紫 → 黄 | 「要フォロー」= warning（黄）が設計意図 |
| 4 | quote | `draft` | 黄 → 灰 | 「下書き」= neutral（灰）が設計意図 |
| 5 | invoice | `draft` | 黄 → 灰 | 同上 |
| 6 | invoice | `sent` | 黄 → 青 | 「送信済み」= info（青）が設計意図 |
| 7 | deal | `open` | 黄 → 灰 | 「新規商談」= neutral（灰）が設計意図 |
| 8 | purchaseOrder | `draft` | 黄 → 灰 | 同上 |
| 9 | staff | `inactive` | 赤 → 灰 | 「休職/無効」は danger ではなく neutral が妥当 |
| 10 | bot | `inactive` | 赤 → 灰 | 同上 |

### B. 現行バグ修正（変更というより修正）

| # | ドメイン | 問題 | 修正内容 |
|---|---------|------|---------|
| 11–20 | parseStatus（Discord）| CSS クラス `badge-success` 等が未定義 → 無色 | SSoT で標準クラスに変更 → 正常表示 |
| 21 | invoice | InvoiceDetailPage で `issued`/`overdue` が `pending`（黄） | SSoT で正しい色（青/赤）に修正 |

### C. 別途検討（karte 専用 CSS）

| # | 内容 |
|---|------|
| 22 | InboxKartePanel の `getStageBadge()` 置換時、`karte-stage-badge--*` CSS を廃止するか存続させるかを決める |

---

## PO へのアクション確認

> ステップ2b 実施前に、以下の各項目について「OK（変更してよい）」または「現状維持（変更しない）」をご確認ください。

| No. | 確認項目 | PO 判断 |
|----|---------|---------|
| 1 | lead.`lead`: 青 → 灰 | |
| 2 | lead.`negotiating`: 橙 → 青（全ドメイン統一） | |
| 3 | lead.`follow_up_short/long`: 紫 → 黄 | |
| 4 | lead.`out_of_scope`: 薄灰 → 灰（近似・微差） | |
| 5 | quote/invoice/deal/purchaseOrder の `draft`/`open`: 黄 → 灰 | |
| 6 | invoice.`sent`: 黄 → 青 | |
| 7 | staff/bot.`inactive`: 赤 → 灰 | |
| 8 | ParseStatus（Discord）バグ修正: 無色 → 標準カラー | |
| 9 | InvoiceDetailPage の `issued`/`overdue` バグ修正 | |
| 10 | karte バッジ: 専用CSS 廃止か存続か | |

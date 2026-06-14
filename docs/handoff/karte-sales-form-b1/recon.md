# recon — ADR-108 Phase B-1: カルテ販売形態 複数選択

**仕事名**: カルテ販売形態 複数選択 + その他自由記述  
**日付**: 2026-06-14  
**対象ADR**: ADR-108 / ADR-027 / ADR-067 / ADR-072 / ADR-135  
**担当**: Hikky-dev

---

## ADR 検索結果

| ADR | 関連 |
|-----|------|
| ADR-108 | カルテ再設計 Phase B — 販売形態複数選択の起点 |
| ADR-027 | i18n 強制（全 UI 文字列 t() 必須） |
| ADR-067 | デザイントークン / 標準コンポーネント強制 |
| ADR-072 | write endpoint の db.commit() 直後に reset_tenant_context() 必須 |
| ADR-135 | develop にマージ = 本番投入可の宣言。migration 含む本PRはPO GO待ち |

---

## file:line 引用表

### Backend — スキーマ

| 引用先 | 確認内容 |
|--------|---------|
| `backend/app/schemas/lead.py:72` | SalesFormSelectionCreate 定義 |
| `backend/app/schemas/lead.py:86` | SalesFormOptionResponse 定義 |
| `backend/app/schemas/lead.py:153` | LeadUpdate に sales_form_selections 追加 |
| `backend/app/schemas/lead.py:226` | LeadResponse に sales_form_selections 追加 |
| `backend/app/schemas/lead.py:228` | LeadResponse に sales_form_options 追加 |

### Backend — Router

| 引用先 | 確認内容 |
|--------|---------|
| `backend/app/routers/leads.py:241` | GET /leads/sales-form-options エンドポイント |
| `backend/app/routers/leads.py:259` | _fetch_lead_selections ヘルパー |
| `backend/app/routers/leads.py:324` | GET /leads/{id} に sales_form_selections 付加 |
| `backend/app/routers/leads.py:439` | PATCH /leads/{id} sales_form_selections 個別処理 |

### Frontend — InboxKartePanel.tsx

| 引用先 | 確認内容 |
|--------|---------|
| `frontend/src/pages/inbox/InboxKartePanel.tsx:464` | SalesFormMultiSelect 配置（company タブ） |
| `frontend/src/pages/inbox/InboxKartePanel.tsx:465` | `options={leadDetail.sales_form_options ?? []}` 直参照（state 介さず） |

### Frontend — SalesFormMultiSelect.tsx

| 引用先 | 確認内容 |
|--------|---------|
| `frontend/src/pages/inbox/SalesFormMultiSelect.tsx:1` | 新規コンポーネント（チェックボックスドロップダウン） |

### Migration

| 引用先 | 確認内容 |
|--------|---------|
| `migrations/20260614_100000_create_sales_form_tables.sql:1` | D案 2テーブル新設（additive-only） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | Phase B-1で新規テーブルを作る必要があるか | ADR-108本体は「DB構造変えず表示再編」だが、複数選択は VARCHAR(100)単一列では実現不可 → 新規テーブル必須（design.md §設計方針 参照） | ✅ 解消済み |
| 2 | options fallback（別フェッチ vs leadDetail埋め込み） | 推奨A採用: GET /leads/{id} が常に sales_form_options を返す（leads.py:324） | ✅ 解消済み |
| 3 | 重複 option_id が来た場合の挙動 | API で 400 返却（DB UNIQUE制約の前段） | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

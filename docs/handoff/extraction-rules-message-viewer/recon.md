# recon: extraction-rules-message-viewer

## 調査対象 ADR
- ADR-027: UI i18n 強制
- ADR-144: UIガバナンス（金型コンポーネント強制）

## バックエンド確認

### SupplierExtractionRulesResponse スキーマ
- `backend/app/schemas/central_masters.py:409`
- フィールド: `supplier_id, extraction_price_format, extraction_qty_format, extraction_order_pattern, extraction_default_unit, extraction_notes, extraction_state_format, latest_raw_text`
- `rules` ネストなし・フラット構造

### 既存エンドポイント
- `backend/app/routers/super_admin_suppliers.py:815` — GET extraction-rules
- `backend/app/routers/super_admin_suppliers.py:867` — PATCH extraction-rules

### フロントエンド型の不一致（修正前）
- `frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx:44-49`
  - 旧: `source_text: string | null` + `rules: ExtractionRules`（ネスト）
  - 実際のAPIレスポンス: `latest_raw_text` + フラット `extraction_*` フィールド
- `detailToForm(data.rules)` — `data.rules` は存在しないため undefined

### source_messages テーブル
- `public.source_messages` — `id, raw_text, created_at, supplier_channel_id, is_active`
- `public.supplier_channels` — `id, supplier_id`
- 既存の GET extraction-rules エンドポイントは最新1件のみ取得

### アイコン確認
- `frontend/src/constants/icons.tsx:274` — `DashboardIcons.arrowRight` (ArrowRightIcon)
- `frontend/src/constants/icons.tsx:387` — `SCHEDULE_SETTINGS_ICONS.back` (ArrowLeftIcon)

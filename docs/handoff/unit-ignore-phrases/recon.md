# Recon: unit-ignore-phrases（単位にしない言い回しマスタ・便1）

実測時の origin/main: 5bc79ef9710133af21bef437423ab0d02ecfda60

## 目的
「ONE PIECE」のように単位の別名（PIECE）を含むが単位ではない言い回しを、人が画面から登録できる表を作る。値の登録は別便（PO が画面で行う）。

## 既存 ADR 検索
- docs/adr/ADR-155-product-master-ssot-csv-app.md（マスタ値はコードに直書きせず画面から登録する方針）
- docs/adr/ADR-027-ui-internationalization.md（t() 経由・ja/en 同一キー）
- docs/adr/ADR-144-ui-component-governance.md（金型のみ使用）
- docs/adr/ADR-072-tenant-schema-prefix-enforcement.md（reset_tenant_context。本 API は get_current_tenant 不使用のため対象外）

## 手本（実物）
- migration: migrations/20260919_020000_master_ssot_public_tables.sql:62（public.units の CREATE TABLE。のち line_units に改名: migrations/20260922_080000_rename_line_analysis_tables.sql）。RLS・GRANT の記述なし。
- COMMENT ON COLUMN: migrations/20261002_160000_create_payment_fee_settings.sql と migrations/20261002_180000_comment_payment_fee_settings_columns.sql
- API: backend/app/routers/super_admin_units.py（生 SQL・require_super_admin・IntegrityError は 409）
- reset_tenant_context 不使用の根拠: backend/app/routers/super_admin_tenants.py:11,86
- 画面: frontend/src/pages/super-admin/components/UnitMasterPanel.tsx、表示場所 frontend/src/pages/super-admin/AnalysisRulesPage.tsx の unit-master セクション
- テスト: backend/tests/test_super_admin_phase_switch.py（TEST_PG_URL 無しは skip）、frontend/src/pages/super-admin/components/ExtractionErrorLogPanel.test.tsx
- migration 登録: scripts/run_all_migrations.sh 末尾（backend/CLAUDE.md 必須事項）

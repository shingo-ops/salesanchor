# Recon — payment_fee_settings §D01

**対象ADR**: ADR-072  
**日付**: 2026-10-02  
**担当**: Sonnet

---

## 調査結果

### 既存のNULLパターン実装例

- `backend/app/routers/units.py`: テナントCRUD、権限キー `suppliers.view`
- `backend/app/routers/super_admin_units.py`: 中央admin CRUD
- `migrations/20240901_000006_add_units.sql`: NULLパターン（`tenant_id IS NULL` = 共用デフォルト）

### 設計方針の根拠

- NULLパターン（共用デフォルト＋テナント独自）はunits/conditionsで確立済み
- 権限キー `suppliers.view` はunits.pyと整合
- ADR-072: write endpoint後に `reset_tenant_context()` 必須 → 実装済み
- マイグレーションはテーブル定義のみ（値はアプリ画面から管理・PO方針）

### 触るファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `migrations/20261002_160000_create_payment_fee_settings.sql` | NEW |
| `backend/app/schemas/payment_fee_setting.py` | NEW |
| `backend/app/routers/super_admin_payment_fee_settings.py` | NEW |
| `backend/app/routers/payment_fee_settings.py` | NEW |
| `backend/app/main.py` | MOD |
| `scripts/run_all_migrations.sh` | MOD |

### 削除するファイル

なし

### 既存ADR確認

- ADR-072: reset_tenant_context 必須 → 対応済み
- ADR-135/136: migrations/ 含むPRはPO GO必須 → PR本文に明記

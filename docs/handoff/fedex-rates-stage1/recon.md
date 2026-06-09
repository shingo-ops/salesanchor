# Phase 2 Recon — FedEx Rates連携 第1段

**実施日**: 2026-06-09  
**対象ADR**: ADR-124  
**担当**: architect recon

---

## A. テナント別外部クレデンシャル保管

### A1 — Meta OAuthクレデンシャル保管方式（流用可能）

| 項目 | file:line | 内容 |
|------|-----------|------|
| テーブル定義（テナントスキーマ） | `migrations/040_create_tenant_meta_config.sql:23-82` | `{schema}.tenant_meta_config`。`page_access_token_encrypted BYTEA`（Fernet暗号化）、`page_token_expires_at TIMESTAMPTZ` |
| 暗号化サービス | `backend/app/services/encryption.py:1-144` | Fernet対称暗号（AES-128-CBC + HMAC-SHA256）。`METADATA_FERNET_KEY` 環境変数。Meta・Google・キャリア全社共用 |
| **FedEx用テーブル（既存）** | `migrations/20260608_080000_add_carrier_credentials.sql:14-25` | `public.tenant_carrier_credentials`。`client_id_encrypted`, `client_secret_encrypted` TEXT（Fernet）。`carrier IN ('fedex','dhl','ups')`、`environment` (sandbox/production)。UNIQUE(tenant_id, carrier) |
| サービス層 | `backend/app/services/carrier_credentials.py:67-141` | `get_status()` / `get_credentials()` / `save_credentials()` / `delete_credentials()` |

**判断**: `tenant_carrier_credentials` テーブルおよび `encryption.py` はそのまま流用可能。FedEx用の新規テーブル作成は不要。`account_number_encrypted` カラム追加のみ必要（ADR-123 D3）。

### A2 — RLSポリシー（新規実装要）

| テーブル | RLS有無 | file:line |
|---------|---------|-----------|
| `tenant_meta_config`（テナントスキーマ） | **有り** | `migrations/040_create_tenant_meta_config.sql:54-67` |
| `tenant_carrier_credentials`（publicスキーマ） | **無し** | `migrations/20260608_080000_add_carrier_credentials.sql` — RLSポリシー定義なし |
| `tenant_google_drive_config`（publicスキーマ） | **無し** | `migrations/20260606_010000_add_google_drive_config.sql` — 同上 |

**判断**: `tenant_carrier_credentials` はRLS未設定。アプリ層フィルタのみで保護されている。PR-A でRLSポリシーを追加する。

### A3 — FedExの新方式OAuth（流用可能）

既存の接続テスト実装:
- `backend/app/services/carrier_credentials.py:163-197` — `_test_oauth_token()` で FedEx OAuth2 (client_credentials) の疎通確認済み
- `backend/app/routers/integrations.py:292-400` — PUT/DELETE/POST test-connection エンドポイント実装済み

**判断**: FedExのserver-to-server OAuth（client_id + client_secret → Bearer token）は既存パターンで実装可能。リダイレクト型OAuthは不要。

### A4 — トークンリフレッシュパターン（流用可能）

| パターン | file:line | 内容 |
|---------|-----------|------|
| オンデマンドリフレッシュ | `backend/app/services/google_drive_oauth.py:277-316` | `_refresh_if_needed()` — API呼び出し直前に5分バッファで確認 |
| バッチリフレッシュ | `backend/app/tasks/refresh_meta_tokens.py:1-493` | Celery Beat毎日03:00 JST |

**判断**: FedEx OAuth token（有効期限3600秒）にはオンデマンドリフレッシュが適合。`google_drive_oauth.py:277-316` を参考に `carrier_credentials.py` に `get_or_refresh_token()` を追加する。

---

## B. 既存の見積もり／送料ロジック

### B1 — 実装済み

| 項目 | file:line |
|------|-----------|
| `shipping_zones` テーブル | `migrations/005_add_phase2_tenant_tables.sql:44-53` |
| `shipping_rates` テーブル | `migrations/005_add_phase2_tenant_tables.sql:56-68` |
| Pydanticスキーマ一式 | `backend/app/schemas/shipping.py:1-72` |
| `calculate_shipping_fee()` | `backend/app/routers/shipping.py:249-285` |
| `POST /shipping/calculate` | `backend/app/routers/shipping.py:288-302` |
| フロントエンドDTO | `frontend/src/components/ShippingDetailPanel.tsx:27-75` |

### B2 — 現状：静的レート表

`backend/app/routers/shipping.py:249-285` は `shipping_zones` + `shipping_rates` テーブルのみ参照。外部API呼び出しなし。

### B3 — 拡張方針：併用（静的 + FedExライブ）

自然な拡張点: `backend/app/routers/shipping.py:249-285` — `carrier` パラメータが既にある。`carrier='fedex'` かつクレデンシャル存在時のみFedEx APIにフォールバックする条件分岐が最小変更。

---

## C. 見積もり／連携設定UI

### C1 — テナント外部連携設定UI（流用可能）

| 項目 | file:line |
|------|-----------|
| `CarrierIntegrationPage` | `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:1-200+` |
| バックエンドAPI一式 | `backend/app/routers/integrations.py:292-400` |

**判断**: FedEx/DHL/UPS向け設定ページ実装済み。`account_number` フィールド追加のみ必要。

### C2 — 見積もり表示UI（新規実装要）

`frontend/src/components/ShippingDetailPanel.tsx` に `est_shipping_fee` 入力欄あり（手動）。ライブ見積もり比較モーダルは未実装 → 新規。

### C3 — デザインシステム（流用可能）

`TextField` / `Select` / `Button` / `DataTable` / `PageLayout` — 全て存在確認済み。

---

## D. Google Drive連携（第2段前提確認）

| 項目 | file:line |
|------|-----------|
| `google_drive_oauth.py` | `backend/app/services/google_drive_oauth.py:1-316` |
| `upload_pdf()` | 実装済み、スコープ: `drive.file` |
| DBテーブル | `migrations/20260606_010000_add_google_drive_config.sql:16-27` |

**留意**: 共有ドライブ書き込みには `drive.file` スコープ拡張またはサービスアカウント方式の検討が必要（第2段着手前に確認）。

---

## E. テスト・CI

### E1 — 既存テスト

| ファイル | file:line | 関連 |
|---------|-----------|------|
| `test_rls_tenant_meta_config.py` | `backend/tests/test_rls_tenant_meta_config.py:1-241` | RLSパターン参考（現在skip） |
| `test_rls_invariants.py` | `backend/tests/test_rls_invariants.py:1-188` | **最重要参考** — cross-tenant blocking |
| `test_carrier_integrations.py` | `backend/tests/test_carrier_integrations.py` | キャリア統合テスト |
| `test_meta_oauth_endpoints.py` | `backend/tests/test_meta_oauth_endpoints.py:1-818` | OAuthフローパターン参考 |

`tenant_carrier_credentials` 専用RLSテストは未実装。

### E2 — CI設定

| 項目 | file:line |
|------|-----------|
| PostgreSQL 16 | `.github/workflows/test.yml:123` |
| `salesanchor_app`（NOBYPASSRLS） | `.github/workflows/test.yml:186-188` |
| `RLS_TEST_DATABASE_URL` | `.github/workflows/test.yml:222` |
| `RLS_ADMIN_DATABASE_URL` | `.github/workflows/test.yml:224` |

**担保範囲**: RLSテストはCI上でPostgreSQL接続時に実行される。`tenant_carrier_credentials` のRLSテストは未作成のため追加必要。

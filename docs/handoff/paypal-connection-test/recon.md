# recon — PayPal 決済連携 接続テストページ（Model A）

**仕事名**: paypal-connection-test
**日付**: 2026-06-10
**対象ADR**: ADR-123
**担当**: architect（Hikky-dev）

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/services/carrier_credentials.py:1` | 既存の per-tenant 暗号化認証情報サービス（PayPal の雛形）。Fernet 暗号化 CRUD + httpx 接続テストの構造を確認 |
| `backend/app/routers/integrations.py:40` | API連携ルーターの import 構造（`carrier_credentials as carriers`）。同所に PayPal サービスを足す方針を確認 |
| `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:1` | 既存の接続テストページ（PaypalIntegrationPage の雛形）。Client/Secret 入力＋環境＋保存＋接続テスト＋削除の UI 構造を確認 |
| `frontend/src/pages/management-center/ManagementCenterPage.tsx:55` | API連携メニュー（`apiIntegration` セクション）。ここに PayPal 項目を追加する箇所を確認 |
| `frontend/src/App.tsx:49` | 統合ページの import/ルート登録箇所。PayPal ルート追加箇所を確認 |
| `migrations/20260609_100000_add_carrier_account_number.sql:1` | 直近の migration 命名・additive パターン（PayPal migration の雛形）を確認 |
| `scripts/run_all_migrations.sh:47` | `TOTAL=` 宣言行。実ステップ数との整合（既存 develop は drift あり）を確認 |

*（引用先は実在するファイルと行番号。process-artifacts gate が自動照合する）*

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `paypal` モジュール名が既存と衝突しないか（cf 過去の shipping_carriers 衝突） | `git ls-tree -r origin/develop \| grep -i paypal` で確認＝衝突なし → `paypal_payments.py` を採用 | ✅ 解消済み |
| 2 | PayPal の接続確認に使う最小エンドポイント | OAuth2 client_credentials トークン取得（`/v1/oauth2/token`）で認証可否を判定（公式 REST 仕様） | ✅ 解消済み |
| 3 | Model A/B どちらで実装するか | Model A（各テナントが自分の認証情報を入力）で確定。Model B はしんごさん相談中・将来拡張（[[project_pending_backlog]]） | ✅ 解消済み（PO 方針: A→B） |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- 本ページは「接続テスト」止まり。決済作成（Orders API）・Model B（Connect with PayPal / Multiparty）は別途（Phase B 以降）。
- 認証情報はテナント別に `public.tenant_paypal_config` へ Fernet 暗号化保存（`tenant_carrier_credentials` と同方針）。

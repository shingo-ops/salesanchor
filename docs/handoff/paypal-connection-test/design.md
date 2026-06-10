# Phase 3 設計 — PayPal 決済連携 接続テストページ（Model A）

**対象ADR**: ADR-123（外部販売を見据えた per-tenant 連携アーキ。PayPal Model A はその一インスタンス）
**recon**: docs/handoff/paypal-connection-test/recon.md
**日付**: 2026-06-10
**担当**: Planner（Hikky-dev）

---

## 外部・過去事例の参照と我々への応用

- **事例1: Ship&co / AnyLogi / 主要 EC カート（Shopify / BASE / STORES / カラーミー / EC-CUBE）の PayPal 連携** → いずれも「各店舗が自分の PayPal アカウントを接続して、自店の顧客から受け取る」モデル。**我々への応用**: salesanchor も同型の per-tenant モデル（Model A）を採用＝各テナントが自社の PayPal 認証情報を入力。
- **事例2: 自社の既存 per-tenant 連携（配送キャリア接続テスト `carrier_credentials.py` / `CarrierIntegrationPage`）** → テナント別に Fernet 暗号化保存＋接続テスト（OAuth トークン取得）する構造が実証済み。**我々への応用**: 同じパターンを PayPal に流用し、実装リスクと工数を最小化。
- **将来事例（Model B）: PayPal Multiparty / Partner Referrals（Connect with PayPal）** → 接続ボタンのみで onboarding＋手数料可。**我々への応用**: 同テーブル/サービスを基点に後から拡張（本 PR の対象外・しんごさん相談中）。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| テナントが PayPal Client ID/Secret を暗号化保存できる | CI pytest `tests/test_paypal_integration.py::test_save_credentials` |
| 保存済み認証情報で接続(認証)テストが成功/失敗を返す | CI pytest `test_token_success` / `test_token_unauthorized` / `test_test_connection_endpoint` |
| status エンドポイントがシークレットを返さない | CI pytest `test_status_endpoint` ＋ Reviewer コードレビュー APPROVE |
| 認可: 保存/削除=admin、status/test=erp.view | Reviewer コードレビュー（integrations.py の `require_permission` / `_require_admin`） |
| 書込後に reset_tenant_context を呼ぶ（ADR-072） | pre-commit ADR-072 lint ＋ Reviewer レビュー |
| migration が additive・冪等で適用される | CI migration-test（`run_all_migrations.sh`） |
| UI で入力→保存→接続テスト→削除ができる | 本番反映後の手動確認（管理センター > API連携 > PayPal） |
| i18n ja/en キー数一致 | CI `check:all`（i18n parity） |

*（各行の「検証方法」は空欄なし。process-artifacts gate が照合する）*

---

## 技術 How・KPI

- KPI: 接続テストで「接続成功（トークン取得）」が返ること（各テナントの認証情報投入後）。
- 技術選択:
  - 認証情報＝テナント別 `public.tenant_paypal_config` に Fernet 暗号化保存（理由: `tenant_carrier_credentials` で実証済みの安全パターン流用）。
  - 接続テスト＝PayPal OAuth2 `client_credentials`（`POST /v1/oauth2/token`・Basic base64(id:secret)）。sandbox=`api-m.sandbox.paypal.com` / live=`api-m.paypal.com`（理由: 最小の読み取りで認証可否を判定でき副作用なし）。
  - httpx 同期呼び出しを router 側で `run_in_threadpool` でラップ（理由: 既存 carrier と統一・event loop を塞がない）。

---

## 弊害・トレードオフ

- Model A は各テナントが自分で PayPal 認証情報を発行・入力する手間がある → 対策: 将来 Model B（Connect with PayPal）で吸収（別 PR）。
- 接続テストは未認証情報時「未設定」表示でグレースフル（副作用なし）。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | migration `tenant_paypal_config` ＋ run_all_migrations 登録 | Generator |
| 2 | service `paypal_payments.py`（暗号化 CRUD＋接続テスト） | Generator |
| 3 | router endpoints（status/credentials/test-connection） | Generator |
| 4 | frontend `PaypalIntegrationPage` ＋ メニュー/ルート/i18n | Generator |
| 5 | tests（httpx/DB モック） | Generator |
| 6 | 検証ゲート（Reviewer APPROVE＋CI） | Reviewer/Evaluator |

---

## 継続

- 完了後の監視: 各テナントの認証情報投入後に接続テスト成功を確認。
- 次フェーズへの引き継ぎ: Phase B（決済作成 Orders API）／Model B（Connect with PayPal・しんごさん方針確定後）。RLS ポリシー追加（`tenant_carrier_credentials` に倣い本番前に）。

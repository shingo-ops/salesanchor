# ADR-125: FedEx Rates連携 第1段 — テナント別ライブ見積もり取得

- **Status**: Proposed
- **Date**: 2026-06-09
- **Deciders**: shingo-ops（PO）, Hikky-dev（Dev）

## Context

ADR-123（キャリア連携アーキテクチャ）の Phase B として、テナントが自社FedExアカウントを連携しアプリ上でリアルタイム見積もり（料金・配達日数）を取得・表示できる機能を実装する。

FedEx Rates and Transit Times API は認証不要（公開ドキュメントより: rate quotesにOAuth tokenは必要だが、Developer登録で即取得可能・FedEx審査不要）のため、ラベル発行（審査必要）とは分離して先行実装できる。

現状:
- `public.tenant_carrier_credentials`（2026-06-08追加）: FedEx/DHL/UPS の client_id/client_secret を Fernet 暗号化で保存済み
- `CarrierIntegrationPage.tsx`: 接続テスト UI 実装済み（Account Number フィールドは未追加）
- `shipping_zones` / `shipping_rates`: 静的テーブルで配送料計算済み
- `calculate_shipping_fee()`（`backend/app/routers/shipping.py:249-285`）: 静的計算のみ

課題:
- `tenant_carrier_credentials` に RLS ポリシーが未設定（アプリ層フィルタのみ）
- FedEx Rates API 呼び出しロジックが未実装
- `account_number`（Rates/Ship APIに必須）が未保存

## Decision

### D1. RLS ポリシー追加（PR-A・人承認ゲート）

`public.tenant_carrier_credentials` に FORCE ROW LEVEL SECURITY + ポリシーを追加:
```sql
USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER)
```
`NULLIF` は空文字列 → INTEGER キャストエラーを防ぐため（`test_rls_invariants.py` パターン準拠）。

### D2. account_number_encrypted カラム追加（PR-B）

`tenant_carrier_credentials` に `account_number_encrypted TEXT NULL` を additive migration で追加。FedEx Rates/Ship API の `accountNumber` フィールドに使用。既存レコードは NULL 許容（接続テスト機能は維持）。

### D3. FedEx OAuth トークン管理（PR-B）

FedEx OAuth（client_credentials フロー）トークンをインメモリキャッシュで管理。`{(tenant_id, env): (token, expires_at)}` の dict。有効期限5分前にリフレッシュ（`google_drive_oauth.py:277-316` パターン転用）。

### D4. Rates API 呼び出し（PR-B）

新規 `backend/app/services/fedex_rates.py` に実装:
- エンドポイント: `POST /rate/v1/rates/quotes`
- 必須: `accountNumber`, `origin_country_code`, `recipient.countryCode`, `weight_kg`
- `rateRequestType: ["LIST"]`（アカウント料金取得）
- timeout: 10秒（connect=3s + read=7s）

### D5. 暗黙フォールバック禁止（D2）

FedEx クレデンシャルが未設定またはAPIエラーの場合、静的値を「ライブ」と偽らない:
- credentials なし → `source='static'` で通常計算
- credentials あり + APIエラー → `live_error` フィールドに明示エラー、`source` なし

`ShippingCalcResponse` に `source: 'static' | 'fedex_live'` と `live_error: str | None` を追加。

### D6. 見積もり比較UIモーダル（PR-C）

`DataTable` + `Modal` の既存コンポーネントで構成。出所バッジ（ライブ/静的）を必須表示。未連携・失敗時の導線を提供。全文字列は `t("key")` 経由（ADR-027準拠）。

## Consequences

### 良い点
- FedEx審査不要で即実装・テスト開始可能（Rates APIはFedEx Developer登録のみ）
- 既存 `tenant_carrier_credentials` + `encryption.py` を流用し、新規インフラ不要
- RLS追加でDBレイヤのテナント分離を強化（Google Drive等の公開スキーマテーブルと同型に揃える）
- 暗黙フォールバック禁止により、UIが「偽ライブ料金」を表示するリスクを排除

### 留意・リスク
- `origin_country_code` がリクエスト必須パラメータとなるため、既存クライアントの呼び出しコード更新が必要
- FedEx APIタイムアウト（p95 3秒以内目標）でUI応答悪化の可能性 → ローディング表示で対処
- インメモリキャッシュはプロセス再起動でリセット（許容コスト）
- `account_number` の追加に伴い `CarrierIntegrationPage.tsx` の更新が必要（PR-C）

## スコープ外（第2段）

- ラベル発行（Ship API / Open Ship API）
- ラベル PDF の Google Drive 保存
- FedEx Integrator Provider Validation 提出
- エンドカスタマー登録 + MFA
- DHL / UPS ライブ見積もり

## References

- 設計: `docs/handoff/fedex-rates-stage1/design.md`
- recon: `docs/handoff/fedex-rates-stage1/recon.md`
- 先行ADR: ADR-123（キャリア連携アーキテクチャ）
- 既存実装: `backend/app/services/carrier_credentials.py`, `backend/app/routers/integrations.py:292-400`
- RLSパターン参考: `migrations/040_create_tenant_meta_config.sql:54-67`, `backend/tests/test_rls_invariants.py`
- FedEx Rates API: https://developer.fedex.com/api/en-us/catalog/rate/v1/docs.html

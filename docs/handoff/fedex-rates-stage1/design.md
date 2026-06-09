# Phase 3 設計 — FedEx Rates連携 第1段

**対象ADR**: ADR-124  
**recon**: docs/handoff/fedex-rates-stage1/recon.md  
**日付**: 2026-06-09  
**担当**: architect → Generator

---

## 外部・過去事例の参照と我々への応用

- **Ship&co（APAC初 FedEx Compatible）**: テナントが自社FedExアカウントを連携する per-tenant bring-your-own-account モデル。Rates APIを使った見積もりをSaaSとして提供。→ 我々への応用: 既存 `tenant_carrier_credentials` + Rates API呼び出しで同型実装可能。アカウント番号をテナント別に暗号化保存するADR-123の方向性を裏付ける。
- **AnyLogi**: 複数キャリア対応のマルチキャリア見積もり。→ 我々への応用: 今回は FedEx のみ。将来のDHL/UPS拡張を見越し `source` フィールドにキャリア名を含める設計とする（`'fedex_live'`）。
- **Google Drive OAuth（既存実装）**: オンデマンドトークンリフレッシュ（5分バッファ）＋インメモリキャッシュ。→ `google_drive_oauth.py:277-316` のパターンをFedEx OAuthトークン管理に転用。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| PR-A: `tenant_carrier_credentials` でRLSが有効、別テナントの行がSELECTで見えない | `pytest backend/tests/test_rls_carrier_credentials.py -v`（PostgreSQL専用・RLS_TEST_DATABASE_URL要） |
| PR-B: FedEx credentialが設定済みテナントで `POST /shipping/calculate?carrier=fedex` がライブ料金を返す（source='fedex_live'） | `pytest backend/tests/test_fedex_rates.py -v`（モック使用） |
| PR-B: credentialが未設定のテナントで同エンドポイントが `source='static'` または `live_error` を返し、静的値をライブと偽らない | `pytest backend/tests/test_fedex_rates.py::test_no_credentials_returns_static -v` |
| PR-B: FedEx APIタイムアウト/エラー時にフォールバックせず `live_error` フィールドに明示的エラーを返す（D2: 暗黙フォールバック禁止） | `pytest backend/tests/test_fedex_rates.py::test_api_error_explicit` |
| PR-C: 見積もりモーダルに出所バッジ（ライブ/静的）が表示される | Playwright: `frontend/tests-e2e/fedex-rate-modal.spec.ts` |
| PR-C: FedEx未連携テナントでモーダルを開くと「連携が必要です」導線が表示される | Playwright: 同上 |
| PR-D: サンドボックスcredentialでAPIが200を返す疎通テストが通る | `pytest backend/tests/test_fedex_sandbox.py -v`（要: FEDEX_SANDBOX_CLIENT_ID/SECRET） |

---

## 技術 How・KPI

### KPI
- FedExライブ見積もり取得の成功率 ≥ 98%（sandbox環境）
- レスポンスタイム ≤ 3秒（FedEx API p95）
- 出所未明示ゼロ（`source` フィールド必須、未連携時は `live_error` を返す）

### 技術選択

**A. RLSポリシー設計（PR-A）**  
`public.tenant_carrier_credentials` に対し `test_rls_invariants.py` と同型のポリシーを適用:
```sql
USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER)
```
`NULLIF` を使うのは `test_rls_tenant_meta_config.py:236-240` で指摘された空文字 → INTEGER キャストエラーを防ぐため。`FORCE ROW LEVEL SECURITY` で所有者にも適用。

**B. account_number_encrypted カラム追加（PR-B 前半）**  
FedEx Rates API は `accountNumber` 必須。ADR-123 D3 に明記済み。additive-only migration で `TEXT NULLABLE` として追加（既存データの後方互換を保持）。後で `save_credentials()` と frontend UI に account_number フィールドを追加。

**C. FedEx OAuth トークンキャッシュ（PR-B）**  
FedEx OAuth の有効期限は3600秒。毎リクエストでトークン取得するのは非効率。`google_drive_oauth.py:277-316` と同型のオンデマンドリフレッシュを実装:
- インメモリキャッシュ: `{(tenant_id, env): (token, expires_at)}` の dict
- 有効期限5分前にリフレッシュ
- キャッシュが複数プロセス間で共有されない問題: 許容（FedEx API は1時間ごと1リクエスト程度で済む）
- **リトライポリシー（2026-06-09確定）**: Rates API 401 はキャッシュをクリアして `FedExAuthError` を raise するのみ。同一リクエスト内での自動再試行は行わない。次回リクエストで新トークンが自動取得される設計で許容（PO判断）。

**D. Rates API 呼び出し設計（PR-B）**  
エンドポイント: `POST /rate/v1/rates/quotes`  
最小必須パラメータ:
- `accountNumber.value`: テナントのFedExアカウント番号
- `requestedShipment.shipper.address.countryCode`: リクエストの `origin_country_code`（デフォルト: リクエストパラメータで明示必須、デフォルト値なし）
- `requestedShipment.recipient.address.countryCode`: `country_code`
- `requestedShipment.requestedPackageLineItems[0].weight`: `weight_kg`
- `rateRequestType`: `["LIST"]`（アカウント料金を取得）

`origin_country_code` をリクエストの必須パラメータとし、ハードコードしない。

**E. shipping.py 分岐設計（PR-B）**  
`calculate_shipping_fee()` 内:
```python
if carrier == "fedex":
    creds = await get_credentials(db, tenant_id, "fedex")
    if creds and creds.get("account_number"):
        live_results = await _try_fedex_live(creds, country_code, weight_kg, origin_country_code)
        if live_results is not None:
            return live_results  # source='fedex_live'
        # None = API エラー → live_error を返す（静的フォールバック禁止）
        return ShippingCalcLiveError(carrier="fedex", live_error="FedEx API error")
    # creds なし → source='static' で通常の DB クエリ
```
`tenant_id` を `calculate_shipping_fee()` の引数に追加する。

**F. スキーマ拡張（PR-B）**  
`ShippingCalcResult` に `source: Literal['static', 'fedex_live']` を追加（デフォルト: `'static'`）。  
`ShippingCalcResponse` に `live_error: str | None` を追加。  
`ShippingCalcRequest` に `origin_country_code: str | None` を追加（FedExライブ使用時に必須）。

**G. フロントエンドモーダル設計（PR-C）**  
`DataTable` + `Modal` + `Button` の既存コンポーネントで構成。  
行: `{service_type, estimated_delivery, fee, currency, source_badge}`  
出所バッジ: `'fedex_live'` → 青バッジ「ライブ」、`'static'` → グレーバッジ「静的」。  
未連携 / `live_error` 時: インライン警告 + 連携設定ページへの導線。  
全文字列は `t("key")` 経由（ADR-027）。

---

## 弊害・トレードオフ

| リスク | 対策 |
|-------|------|
| 暗黙フォールバック（ライブ失敗→静的を「ライブ」と偽る） | D2 強制: `live_error` を明示返却、UIで出所バッジ必須 |
| FedEx API タイムアウトでUI応答悪化 | `httpx` timeout=10秒（接続3秒+読み取り7秒）、UIにローディング表示 |
| アカウント番号の平文露出 | Fernet暗号化して保存。APIレスポンスにアカウント番号を返さない |
| RLS未設定で他テナントのクレデンシャルが漏洩 | PR-A を人承認ゲート付きで先行マージ（migration-guard.yml でブロック） |
| インメモリキャッシュが複数プロセス間で非共有 | 許容（1時間に1回程度のOAuthリクエストは無視できるコスト） |
| `origin_country_code` 未指定でFedEx APIが失敗 | リクエストバリデーションで `origin_country_code` が `None` かつ FedEx の場合は `422` を返す |

---

## 計画票

| PR | ステップ | 内容 | 担当 |
|----|---------|------|------|
| A | 1 | `migrations/20260609_090000_add_carrier_credentials_rls.sql` 作成 | Generator |
| A | 2 | `run_all_migrations.sh` に追記 | Generator |
| A | 3 | `backend/tests/test_rls_carrier_credentials.py` 作成 | Generator |
| A | 4 | PR作成（人承認ゲート） | Generator |
| B | 5 | `migrations/20260609_100000_add_carrier_account_number.sql` 作成 | Generator |
| B | 6 | `run_all_migrations.sh` に追記 | Generator |
| B | 7 | `backend/app/services/fedex_rates.py` 作成 | Generator |
| B | 8 | `backend/app/services/carrier_credentials.py` に `get_or_refresh_token()` 追加 | Generator |
| B | 9 | `backend/app/schemas/shipping.py` スキーマ拡張 | Generator |
| B | 10 | `backend/app/routers/shipping.py` FedEx分岐追加 | Generator |
| B | 11 | `backend/tests/test_fedex_rates.py` 作成 | Generator |
| B | 12 | PR作成 | Generator |
| C | 13 | `frontend/src/components/FedExRateModal.tsx` 作成 | Generator |
| C | 14 | `frontend/src/pages/integrations/CarrierIntegrationPage.tsx` account_number追加 | Generator |
| C | 15 | `frontend/src/locales/ja.json` / `en.json` i18nキー追加 | Generator |
| C | 16 | PR作成 | Generator |
| D | 17 | `backend/tests/test_fedex_sandbox.py` 作成 | Generator |
| D | 18 | PR作成 | Generator |

---

## 継続

- **完了後の監視**: FedEx API エラー率・レスポンスタイムをアプリログで計測。`live_error` が多発する場合はアラート追加を検討。
- **第2段への引き継ぎ**: ラベル発行（Ship API）は FedEx Integrator Provider Validation の承認後。ADR-123 Phase B 参照。
- **Google Drive 共有ドライブスコープ**: 第2段着手前に `drive.file` → `drive` へのスコープ拡張要否を確認。

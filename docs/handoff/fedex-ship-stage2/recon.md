# Recon — FedEx Ship/Pickup Stage 2（自社出荷 Shipper 組織）

**実施日**: 2026-06-11
**対象**: ADR 起案前 recon（KGI: SalesAnchor アプリ内で HIGH LIFE JPN の FedEx ラベル発行＋集荷予約）
**担当**: architect recon

---

## 凡例

| マーク | 意味 |
|--------|------|
| ✅ 確認済 | file:line または web 実機で事実確認 |
| ⚠️ 要確認 | しんごさん Portal 操作が必要 |
| 🔴 Shingo 判断 | 設計分岐・POのみが決定可 |

---

## B. Stage 1 既存コードの拡張点（file:line 突合）

### B1 — `get_credentials()` の Ship/Pickup 流用可否 ✅

| 確認事項 | file:line | 結果 |
|----------|-----------|------|
| 返却フィールド | `backend/app/services/carrier_credentials.py:110-140` | `client_id`, `client_secret`, `environment`, `account_number`（4フィールド）を返す |
| account_number カラム | `migrations/20260609_100000_add_carrier_account_number.sql:15-16` | `account_number_encrypted TEXT NULL` 追加済み |
| Ship API 必須フィールド | `migrations/20260609_100000_add_carrier_account_number.sql:7` | "FedEx Rates / Ship API は accountNumber が必須" とコメント明記 |

**判断**: `get_credentials()` はそのまま Ship/Pickup で流用可能。Ship も Pickup も `accountNumber` として同じカラム値を使う。追加カラムは不要。

---

### B2 — `get_or_refresh_token()` のスコープ・キャッシュキー流用可否 ✅

| 確認事項 | file:line | 結果 |
|----------|-----------|------|
| OAuth エンドポイント | `backend/app/services/fedex_rates.py:180-223` | `POST {base_url}/oauth/token` で `grant_type=client_credentials` |
| キャッシュキー | `backend/app/services/fedex_rates.py:152` | `(tenant_id, environment)` のタプル |
| トークン有効期限 | `backend/app/services/fedex_rates.py:218-219` | `expires_in`（通常 3600 秒）を使ってキャッシュ |
| スコープ区別 | web 調査（FedEx 公式・trafficparrot.com 統合ガイド） | FedEx OAuth は単一エンドポイント・スコープ指定なし。同一トークンで Rate/Ship/Pickup すべて叩ける |

**判断**: `get_or_refresh_token()` は Ship/Pickup でそのまま流用可。別関数・別キャッシュ不要。`fedex_rates.py` 内の関数を `import` して使う形になる。

---

### B3 — `_try_fedex_ship()` / `_try_fedex_pickup()` の新設方針 ✅

| 確認事項 | file:line | 結果 |
|----------|-----------|------|
| `_try_fedex_live()` の構造 | `backend/app/routers/shipping.py:303-365` | `asyncio.to_thread` で同期 httpx 呼び出しをラップ。creds dict を受け取り `(results, live_error, precision)` を返す |
| エラー分岐 | `backend/app/routers/shipping.py:344-349` | `FedExAuthError` / `FedExAPIError` を try-except で捕捉し `live_error` 文字列を返す（ADR-125 D5） |
| account_number チェック | `backend/app/routers/shipping.py:323-325` | `creds.get("account_number")` が None なら即 `live_error` を返す |

**判断**: 同パターンで `_try_fedex_ship()` / `_try_fedex_pickup()` を新設する形が妥当。`account_number` 未設定チェックも同様に冒頭で行う。

---

### B4 — 新規モジュール vs 既存 `fedex_rates.py` への同居 ✅

| 確認事項 | file:line | 結果 |
|----------|-----------|------|
| `fedex_rates.py` の責務 | `backend/app/services/fedex_rates.py:1-24` | "FedEx Rates and Transit Times API クライアント" と明記。Rates 固有定数（`TARGET_INTERNATIONAL_SERVICE_TYPES`、`_REPRESENTATIVE_POSTAL_CODES`）が 60 行超を占める |
| `fedex_rates.py` の行数 | `backend/app/services/fedex_rates.py:1-456` | 456 行（800 行上限の 57%。Ship を同居させると 800 行超えリスク） |
| 例外クラス | `backend/app/services/fedex_rates.py:108-122` | `FedExNotConfiguredError`, `FedExAuthError`, `FedExAPIError` は Ship/Pickup でも共用できる |

**判断**: **新規 `backend/app/services/fedex_ship.py` を作成**して Ship + Pickup API クライアントを実装する方が自然（ファイル責務の明確化・サイズ管理）。`get_or_refresh_token()` と例外クラスは `fedex_rates.py` から `import`。

---

### B5 — ラベルの保存・返却方法 ✅（保存先は 🔴 D2）

| 確認事項 | file:line / 調査 | 結果 |
|----------|-----------------|------|
| Ship API レスポンスのラベル形式 | web 調査（developer.fedex.com, doc.oneentry.cloud） | `encodedLabel` フィールドに **Base64 エンコード**で返却。フォーマットは `labelSpecification.imageType` で指定（PDF / PNG / ZPLII / EPL2 / DPL） |
| `labelResponseOptions` | web 調査 | `"LABEL"`（Base64 直返し）または `"URL_ONLY"`（署名付き URL 返し）の2択 |
| Google Drive upload_pdf | `backend/app/services/google_drive_oauth.py`（存在確認） | `upload_pdf()` 実装済み。スコープ `drive.file` |
| ラベル保存テーブル | `migrations/` 全体を確認 | **現時点で `tenant_shipments` テーブルは未作成**（ADR-123 D3 で「新規追加」と言及のみ） |
| Google Drive 注記 | `docs/handoff/fedex-rates-stage1/recon.md:97-103` | 共有ドライブ書き込みには `drive.file` スコープ拡張またはサービスアカウント方式の検討が必要と記録済み |

**確認済み事実**: ラベルは Base64 で受け取れる。保存インフラ（DB テーブル / GDrive）は未実装。
**🔴 D2 でShingo判断が必要**: 保存先（DB `tenant_shipments` / Google Drive / 都度発行・非保存）。

---

### B6 — 集荷予約の確認番号保存先 ✅（保存先は 🔴 D2 に内包）

| 確認事項 | file:line / 調査 | 結果 |
|----------|-----------------|------|
| Pickup API レスポンス | web 調査（developer.fedex.com） | `pickupConfirmationCode`（確認番号）＋ Express の場合は `locationCode`（ロケーションコード）が返る |
| 保存先テーブル | `migrations/` 全体 | **未存在**。`tenant_shipments` に一緒に保存するか、別テーブルにするかは未定 |

**判断**: `tenant_shipments` テーブル設計時に `shipment_type` カラム（label / pickup / both 等）か、`tenant_pickups` 別テーブルか、ADR 起案時に決定する。

---

## C. FedEx API 仕様（web 調査）

### C1 — Ship API エンドポイント・リクエスト・レスポンス ✅

| 項目 | 内容 |
|------|------|
| **エンドポイント** | `POST /ship/v1/shipments` |
| base URL | sandbox: `https://apis-sandbox.fedex.com` / production: `https://apis.fedex.com` |
| 認証 | `Authorization: Bearer {token}` （Stage 1 と同一） |
| **リクエスト構造（最上位キー）** | `accountNumber.value`, `labelResponseOptions`, `requestedShipment` |
| `requestedShipment` 必須フィールド | `shipper`（contact + address）, `recipients[]`（contact + address）, `serviceType`, `packagingType`, `pickupType`, `shippingChargesPayment`, `labelSpecification`, `requestedPackageLineItems[]`（weight per pkg） |
| `labelSpecification` | `imageType`（PDF / PNG / ZPLII / EPL2 / DPL）, `labelFormatType`（COMMON2D 等）, `labelStockType` |
| `labelResponseOptions` | `"LABEL"`（Base64 直返し）または `"URL_ONLY"` |
| **レスポンス** | `output.transactionShipments[].masterTrackingNumber`（追跡番号）, `output.transactionShipments[].pieceResponses[].packageDocuments[].encodedLabel`（Base64） |
| 追加レスポンス | `deliveryDatestamp`（配達予定日）, `shipDatestamp` |

出典: developer.fedex.com/api/en-us/catalog/ship/v1/docs.html, doc.oneentry.cloud/docs/integrations/fedex-example/

---

### C2 — Pickup API エンドポイント・リクエスト・レスポンス ✅

| 項目 | 内容 |
|------|------|
| **Create Pickup エンドポイント** | `POST /pickup/v1/pickups` |
| Check Availability | `GET /pickup/v1/pickupoptions`（集荷可否・締切時刻事前確認） |
| Cancel Pickup | `PUT /pickup/v1/pickups/cancel` |
| base URL | sandbox/production: Ship と同じ |
| 認証 | `Authorization: Bearer {token}` （Stage 1 と同一） |
| **リクエスト主要フィールド** | `associatedAccountNumber.value`（FedEx アカウント番号）, `pickupAddress`（集荷場所 contact + address）, `pickupRequestType`（`SAME_DAY` / `FUTURE_DAY`）, `readyDateTimestamp`（集荷可能時刻）, `customerCloseTime`（受付締切時刻）, `carrierCode`（`FDXE`=Express / `FDXG`=Ground）, `packageCount`, `totalWeight` |
| **レスポンス** | `output.pickupConfirmationCode`（集荷確認番号）, Express のみ `output.location`（ロケーションコード）, `output.pickupMessage` |

出典: developer.fedex.com/api/en-us/catalog/pickup/v1/docs.html

---

### C3 — Ship/Pickup が client_credentials で叩けるか ✅（重要）

| 項目 | 内容 |
|------|------|
| OAuth 認証 | Ship/Pickup ともに `grant_type=client_credentials`（Stage 1 と同一）で叩ける。追加スコープ不要 |
| Sandbox | Validation 不要で即テスト可能 |
| **本番 Ship API** | **Label Validation が必要**。流れ: ①テスト環境でラベル生成 → ②ラベルカバーシートと共に `label@fedex.com` に提出 → ③Bar Code Analysis チームが **3営業日**でレビュー → ④承認で本番クレデンシャル有効化 |
| **本番 Pickup API** | **Validation 不要**（certification ページに Pickup の記載なし。Ship/Open Ship/Consolidation のみ対象） |
| 提出先 | `label@fedex.com`（Shipper 向け。Integrator Provider 向け `validationmtp@fedex.com` とは別） |

出典: developer.fedex.com/api/en-us/certification/shipper.html（3 business day turnaround 記載確認）

---

### C4 — Service Availability API との関係 ✅

| 項目 | 内容 |
|------|------|
| 既存利用 | Stage 1（`fedex_rates.py`）内での `transitTime` 取得（Rates API レスポンス内） |
| 集荷可否事前確認 | Pickup API の `GET /pickup/v1/pickupoptions` で対応可能（Check Pickup Availability） |
| 利用場面 | UI で「本日集荷可能か」「締切時刻は何時か」を表示する際に使える |
| 必須性 | 初版は省略可（Create Pickup 単体でも動く）。エラーレスポンスが "cutoff time を超えた" 旨を返すため、事前チェックは UI 品質向上用途 |

---

## A. FedEx Portal 実機（要確認事項）

以下は **しんごさんの Portal ログインが必要**。推測で設計を進めない。

| 項目 | 確認方法 | 確認すること |
|------|----------|-------------|
| **A1** | developer.fedex.com → 組織 10568591 → プロジェクト「マイ・プロジェクト96」→ API一覧 | Ship API が既に追加されているか（種類に Rate, Ship, Other と表示されているはず → Ship があれば追加不要） |
| **A2** | 同プロジェクト → 「API を追加」→ Pickup Request API を検索 | Pickup API をこのプロジェクトに追加できるか（APIカタログで選択→ Test/Prod スイッチ） |
| **A5** | プロジェクト設定 → Credentials（Test/Prod） | 現在 Sandbox のみか Prod も有効か。Ship の Prod は Label Validation 後に有効化されるはず → Production ステータスが locked か active か |

**A3・A4 は web 調査で確認済み**:
- A3: Label Validation = `label@fedex.com` 提出 → 3営業日（web 確認）
- A4: Pickup の validation = **不要**（web 確認）

---

## D. Shingo 判断が必要な設計分岐

| ID | 質問 | 判断が必要な理由 |
|----|------|-----------------|
| **D1** | 通関書類（Trade Documents Upload / Commercial Invoice）は自社分に含めるか、スコープ外か | 国際出荷では通関書類が必要。ただし初版から含めるかは事業要件 |
| **D2** | ラベルの保存先 | DB（`tenant_shipments.label_encoded TEXT`）/ Google Drive（`upload_pdf()` 流用）/ 都度発行・非保存の3択。コスト・再発行要件・監査要件が判断軸 |
| **D3** | UI 導線 | 見積もりモーダルの延長（見積もり選択→ラベル発行ボタン）/ 別画面「出荷管理」のいずれか |
| **D4** | Label Validation の申請タイミング | 実装完了後に即申請（Sandbox テストと並行）／集荷機能を先行リリースしてから申請の2択 |

---

## まとめ（確認済み vs 判断待ち）

### 確認済み（設計に使える事実）

1. `carrier_credentials.py:110-140` の `get_credentials()` は Ship/Pickup でそのまま流用可
2. `fedex_rates.py:226-246` の `get_or_refresh_token()` トークンは Ship/Pickup でも有効。キャッシュキー `(tenant_id, environment)` 流用可
3. `shipping.py:303-365` の `_try_fedex_live()` と同パターンで `_try_fedex_ship()` / `_try_fedex_pickup()` を新設する方針が妥当
4. 新規 `backend/app/services/fedex_ship.py` を作成（`fedex_rates.py` に同居させない）
5. Ship API: `POST /ship/v1/shipments`。ラベルは `encodedLabel` に Base64 で返る（PDF/PNG/ZPLII 選択可）
6. Pickup API: `POST /pickup/v1/pickups`。Validation 不要。集荷確認番号が返る
7. 認証は Stage 1 と同一（`client_credentials`）。追加スコープ不要
8. **Ship API 本番利用には Label Validation 必須**（`label@fedex.com` 提出 → 3営業日）。Pickup は不要
9. ラベル・集荷確認番号の保存テーブル（`tenant_shipments`）は現時点で**未作成**（migration 追加が必要）

### しんごさん Portal 確認待ち（A項目）

- A1: Ship API が「マイ・プロジェクト96」に既に含まれているか
- A2: Pickup API をプロジェクトに追加できるか
- A5: Prod クレデンシャルのステータス（locked / active）

### Shingo 判断待ち（D項目）

- D1: 通関書類のスコープ
- D2: ラベル保存先
- D3: UI 導線
- D4: Label Validation 申請タイミング

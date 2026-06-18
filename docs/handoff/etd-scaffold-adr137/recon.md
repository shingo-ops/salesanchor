# Recon: ETD骨格コード実装（CTS非依存分）— ADR-137

**仕事名**: etd-scaffold-adr137  
**日付**: 2026-06-18  
**担当**: Hikky-dev  
**目的**: ADR-137のうちCTS非依存で実装できる骨格の現在地把握

---

## ADR 検索結果

`git grep -i "fedex\|etd\|etdDetail\|letterhead\|trade.*doc" docs/adr/`

| キーワード | 該当ADR |
|---|---|
| FedEx ETD / Paperless Trade | **ADR-137**（本PR対象・Proposed） |
| FedEx Rates / OAuth | **ADR-125** `docs/adr/ADR-125-fedex-rates-stage1.md` |
| FedEx Label Validation ウィザード | **ADR-129** `docs/adr/ADR-129-fedex-label-validation-wizard.md` |
| FedEx Integrator Provider | **ADR-123** |

---

## 現在地

### BE: 既存FedEx実装

- `backend/app/services/fedex_rates.py:43` — `_BASE_URLS` 定義（sandbox/production）。`get_or_refresh_token()` を Ship/ETDサービスで共用
- `backend/app/services/fedex_ship.py:57` — `create_shipment()` 関数。`requested_shipment:dict` を `backend/app/services/fedex_ship.py:112-133` で構築
- `backend/app/services/fedex_ship.py:112-133` — `requested_shipment` 構築。`customsClearanceDetail` あり。`etdDetail` / `shippingDocumentSpecification` なし
- `backend/app/routers/shipping.py:415` — `carrier_credentials.get_credentials(db, tenant_id, "fedex")` パターン（BE認証情報取得の標準）
- `backend/app/routers/shipping.py:629` — `await reset_tenant_context(db, tenant_id)` ADR-072 必須パターン（db.commit() 直後）

### BE: テーブル設計参照

- `migrations/20260608_080000_add_carrier_credentials.sql:14` — `public.tenant_carrier_credentials` 定義（同スキーマ設計のモデル）。publicスキーマ + tenant_id列 + UNIQUE制約の構成
- `migrations/20260609_090000_add_carrier_credentials_rls.sql` — RLS 設定パターン: `NULLIF(current_setting('app.tenant_id', true), '')::INTEGER`

### FE: Label Validation タブ

- `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:1` — LVウィザード（Step 1-9）。ETD セクションは未存在
- `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:49` — `FedexLabelValidationTab()` 関数。新 Step 10 として ETD 書類登録を追加予定
- i18nキーは `ja.json` / `en.json` の `carrierIntegration.*` ネームスペース

### FedEx ETD API（外部調査・要公式確認）

既存 stamp recon（`docs/handoff/fedex-etd-stamp-recon/recon.md`）の外部調査によると:

- アップロードエンドポイント候補: `POST /ship/v1/shipments/images`（未公式確認）
- imageType候補: LETTER_HEAD / SIGNATURE（未公式確認）
- Ship リクエストの ETD 組み込み構造（外部調査・C-Q6未確定）:

```json
"shippingDocumentSpecification": {
  "stampType": "INCLUSIVE",
  "etdDetail": {
    "requestedDocumentCopies": ["COMMERCIAL_INVOICE"],
    "uploadedDocuments": [
      {"id": "docId", "documentType": "LETTER_HEAD", "referenceIndex": "LETTER_HEAD"},
      {"id": "docId", "documentType": "SIGNATURE", "referenceIndex": "SIGNATURE"}
    ]
  }
}
```

**⚠️ 注意**: 上記は外部調査由来。stampType(INCLUSIVE/EXCLUSIVE)・requestedDocumentCopies の正確な値は C-Q6（CTS）確認待ち（J3 dormant の理由）。

### 確定事実（Eva Q1-Q4）

| 項目 | 確定内容 |
|---|---|
| LETTERHEAD/SIGNATURE docId | **無期限** → リフレッシュ機構不要 |
| 再利用可否 | **再利用OK** → DB保存して繰り返し参照 |
| 出荷書類 docId | **使い捨て** → DB永続化しない |
| 対象テーブル | `fedex_etd_images`（LETTERHEAD/SIGNATURE専用。出荷書類は保存しない） |

---

## 未確定（Clarifyブロック）

| # | 不明点 | 影響スコープ |
|---|---|---|
| C-Q1 | FedEx Trade Documents Upload API の正確なエンドポイント・リクエスト形式 | S2 APIコントラクト |
| C-Q2 | G3完了状態（Developer Portal でAPIキーに Trade Documents Upload API 追加済みか） | S2 Sandbox疎通可否 |

---

## 触っていない領域

- deploy.yml の migration wiring（G2）: Shingo GO 後の別PR
- 本番FedEx設定（G3）: Shingo直接操作
- SA-02 / QA Smoke / mobile shell: 未参照
- 実装変更: 本reconでは行っていない

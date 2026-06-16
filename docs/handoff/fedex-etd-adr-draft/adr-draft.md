# ADR-XXX: FedEx ETD（Electronic Trade Documents）実装 — たたき台

> **ステータス**: DRAFT（起案前・Shingo GO待ち）  
> **番号**: 未確定  
> **日付**: 2026-06-16  
> **依存 ADR**: ADR-123（キャリア連携基盤）/ ADR-125（FedEx Rates OAuth）/ ADR-129（Label Validation ウィザード）  
> **前提条件**: APAC FedEx API チームへの回答受領後に正式起案する。

---

## Shingo GO 必須の変更一覧

| # | 変更内容 | 理由 | GO 条件 |
|---|---------|------|---------|
| G1 | `migrations/YYYYMMDD_HHMMSS_add_fedex_etd_images.sql` | 本番 DB への schema 変更 | APAC 確認済み + Shingo GO |
| G2 | `deploy.yml` への migration 実行反映 | deploy workflow 変更 | G1 GO 後 |
| G3 | FedEx 側アカウント設定（Paperless Trade 有効化） | FedEx外部GUI操作 | APAC回答後にShingo直接操作 |
| G4 | Sandbox ETD 動作確認後の本番切替 | 本番FedExアカウント設定 | Sandbox PASS + Shingo確認 |

コード変更（`fedex_ship.py` への `etdDetail` 追加）は通常PR。ただし上記のDB / deploy / 外部設定は別途GO必須。

---

## 背景

FedEx ETD（Paperless Trade）は、国際出荷時にラベルと共に税関向け書類（インボイス等）を電子的にFedExへ提出する仕組み。

現状の問題:
- `backend/app/services/fedex_ship.py` の `create_shipment()` に `etdDetail` フィールドが存在しない
- レターヘッド・署名画像のアップロード処理が存在しない
- DBにレターヘッド/署名の `docId` を保存する構造が存在しない
- ETDがLabel Validation必須要件か未確認

---

## 暫定設計

### J1: `fedex_etd_images` テーブル追加

レターヘッド・署名の `docId` をテナント・環境・画像種別ごとに保存する。

```sql
CREATE TABLE IF NOT EXISTS fedex_etd_images (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    image_type VARCHAR(20) NOT NULL CHECK (image_type IN ('LETTER_HEAD', 'SIGNATURE')),
    doc_id TEXT NOT NULL,
    environment VARCHAR(20) NOT NULL CHECK (environment IN ('production', 'sandbox')),
    uploaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    uploaded_by INTEGER REFERENCES users(id),
    UNIQUE (tenant_id, image_type, environment)
);
```

### J2: 画像アップロードAPI

```text
POST /integrations/fedex/etd-images
body: { image_type, image_base64, environment }
```

処理:
1. FedEx `POST /ship/v1/shipments/images` を呼び出す
2. 返却された `docId` をDBへ保存する
3. 保存済み情報を返却する

APAC回答次第で、毎回アップロード方式または事前登録方式を選択する。

### J3: Shipリクエストへの `etdDetail` 組み込み

`fedex_ship.py` の `requestedShipment` に `shippingDocumentSpecification.etdDetail` を追加する。

```python
if etd_doc_ids:
    requested_shipment["shippingDocumentSpecification"] = {
        "stampType": "INCLUSIVE",
        "etdDetail": {
            "requestedDocumentCopies": ["COMMERCIAL_INVOICE"],
            "uploadedDocuments": [
                {
                    "id": etd_doc_ids["LETTER_HEAD"],
                    "documentType": "LETTER_HEAD",
                    "referenceIndex": "LETTER_HEAD",
                },
                {
                    "id": etd_doc_ids["SIGNATURE"],
                    "documentType": "SIGNATURE",
                    "referenceIndex": "SIGNATURE",
                },
            ],
        },
    }
```

### J4: UI

FedEx Label Validation / 連携ガイド画面に、ETD書類登録セクションを追加する。

- レターヘッド画像アップロード
- 署名画像アップロード
- 登録済み画像の状態表示
- Sandbox / Production 環境分離

---

## スコープ

| フェーズ | 内容 | 危険変更 |
|---------|------|---------|
| E1 | APAC回答受領・設計確定 | なし |
| E2 | `fedex_etd_images` migration作成 | あり |
| E3 | バックエンドAPI・Ship payload拡張 | 通常PR |
| E4 | フロントエンドUI追加 | 通常PR |
| E5 | Sandbox動作確認 | なし |
| E6 | FedEx Paperless Trade有効化 | あり |
| E7 | 本番切替・Label Validation申請 | あり |

---

## 未解決事項

| # | 問い | 判断が必要な理由 |
|---|-----|----------------|
| U1 | ETDをLabel Validation申請前に実装するか | APAC回答次第 |
| U2 | ADR正式起案タイミング | APAC回答後に確定 |
| U3 | ADR番号 | 正式起案時に確定 |
| U4 | `docId` の有効期限 | APAC回答次第 |
| U5 | Paperless Tradeの有効化方法 | FedEx側確認が必要 |

---

## 関連ファイル

| ファイル | 関係 |
|---------|------|
| `backend/app/services/fedex_ship.py` | `etdDetail` 追加対象 |
| `backend/tests/test_fedex_ship.py` | ETDテスト追加対象 |
| `docs/adr/ADR-123-carrier-integrator-provider.md` | キャリア連携基盤 |
| `docs/adr/ADR-125-fedex-rates-stage1.md` | FedEx OAuth / Rates |
| `docs/adr/ADR-129-fedex-label-validation-wizard.md` | Label Validationウィザード |
| `docs/handoff/fedex-etd-stamp-recon/recon.md` | ETD現状recon |
| `docs/handoff/fedex-etd-adr-draft/fedex-apac-questions.md` | APAC確認質問 |

---

## 却下した代替案

| 案 | 却下理由 |
|---|---------|
| carrier_credentials への列追加 | LETTER_HEAD / SIGNATURE の複数種別に弱い |
| 毎回オンデマンドアップロード固定 | APAC回答次第ではAPI負荷が過剰 |
| ETDを無条件に後回し | Label Validation必須なら申請不可になる |

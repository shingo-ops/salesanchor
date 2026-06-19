# Design: ETD骨格コード実装（CTS非依存分）— ADR-137

**参照**:
- recon: docs/handoff/etd-scaffold-adr137/recon.md
- ADR-137: docs/adr/ADR-137-fedex-etd-paperless-trade.md

---

## C-Q1 確定事項（2026-06-18 Shingo確認）

Trade Documents Upload API は Ship API とは**別カタログ**（upload-documents）。

| 操作 | 対象 | 戻り値 | Ship API での参照先 |
|---|---|---|---|
| Upload Image | レターヘッド/署名（再利用） | imageIndex | `shippingDocumentSpecification.customerImageUsages` |
| Upload Document | 出荷ごとの自前書類（使い捨て） | docId | `etdDetail.attachedDocuments.documentId` + `specialServiceTypes=ELECTRONIC_TRADE_DOCUMENTS` |

**画像制約**:
- 署名: 240×25px, GIF/PNG, 5MB以下
- レターヘッド: 700×50px, GIF/PNG, 5MB以下
- 書類: 出荷10日前まで

**docタイプ（出荷書類）**: COMMERCIAL_INVOICE / CERTIFICATE_OF_ORIGIN / PRO_FORMA_INVOICE / USMCA_* / ETD_LABEL / OTHER

**エンドポイント**: 正確なRESTパスはPortal APIリファレンスより取得。コード内 `_UPLOAD_IMAGE_PATH` / `_UPLOAD_DOCUMENT_PATH` をTODOで明記。

**ワークフロー**: ETDPreShipment（標準）/ ETDPostShipment(PSDU)。最終構成はCTS確認。

---

## S1. migration ファイル（fedex_etd_images テーブル）

**ファイル**: `migrations/20260618_120000_add_fedex_etd_images.sql`  
**スキーマ**: public（tenant_carrier_credentials と同じ方針）  
**適用**: ファイル作成のみ。deploy.yml wiring（G2）・実適用は Shingo GO 後の別PR

```sql
CREATE TABLE IF NOT EXISTS public.fedex_etd_images (
    id                 SERIAL PRIMARY KEY,
    tenant_id          INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    image_type         TEXT NOT NULL CHECK (image_type IN ('LETTERHEAD', 'SIGNATURE')),
    environment        TEXT NOT NULL CHECK (environment IN ('sandbox', 'production')),
    fedex_image_index  TEXT NOT NULL,  -- Upload Image API 戻り値（imageIndex）
    created_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (tenant_id, image_type, environment)
);
-- 有効期限カラムなし（Eva Q4: imageIndex は無期限）
-- 出荷ごとの自前書類 docId は本テーブルに保存しない（Eva Q3: 使い捨て・poka-yoke対象）
```

RLS パターン: `migrations/20260609_090000_add_carrier_credentials_rls.sql` と同一。

---

## S2. BE: レターヘッド/署名アップロード

### 新規: `backend/app/services/fedex_etd.py`

```
PERSISTENT_IMAGE_TYPES = frozenset({"LETTERHEAD", "SIGNATURE"})

upload_image(tenant_id, environment, image_type, image_bytes, client_id, client_secret) -> str
  # Trade Documents Upload API: Upload Image エンドポイント
  # TODO(C-Q1): _UPLOAD_IMAGE_PATH をPortal APIリファレンスから埋める
  # Returns: imageIndex（文字列）

upsert_etd_image(db, tenant_id, image_type, environment, image_index) -> None
  # fedex_etd_images に upsert

get_etd_images(db, tenant_id, environment) -> dict[str, str]
  # {image_type: image_index} を返す（Ship時のcustomerImageUsages組み立て用）
```

### 追記: `backend/app/routers/shipping.py`

```
POST /shipping/etd/images
  multipart: image_type, environment, file（画像バイナリ）
  → upload_image() → upsert_etd_image()
  → db.commit() → reset_tenant_context() （ADR-072必須）

GET /shipping/etd/images
  → get_etd_images() → 登録済み画像一覧（FE表示用）
```

### poka-yoke: 出荷書類 docId の誤永続化防止（S5）

```python
PERSISTENT_IMAGE_TYPES = frozenset({"LETTERHEAD", "SIGNATURE"})

def _guard_persistent_only(image_type: str) -> None:
    if image_type not in PERSISTENT_IMAGE_TYPES:
        raise ValueError(f"{image_type} は使い捨て書類です。DB保存禁止（Eva Q3）")
```

---

## S3. FE: ETD書類登録UI（VITE_FEDEX_ETD_ENABLED でデフォルト非表示）

**ファイル**: `frontend/src/pages/integrations/FedexLabelValidationTab.tsx`

Step 9 の後に ETD セクション追加（`VITE_FEDEX_ETD_ENABLED === "true"` のみレンダリング）:
- レターヘッド画像アップロード（GIF/PNG 700×50px 5MB以下）
- 署名画像アップロード（GIF/PNG 240×25px 5MB以下）
- 環境セレクタ（sandbox / production）
- 送信ボタン → `POST /shipping/etd/images`

i18n: `carrierIntegration.etd*` キー（ja.json / en.json）

---

## S4. etdDetail dormant フック（J3・CTS待ち）

**ファイル**: `backend/app/services/fedex_ship.py`（`create_shipment()` 内）

```python
# J3 dormant: CTS確認後に customerImageUsages を組み立て
# TODO(C-Q6/CTS): stampType / requestedDocumentCopies / workflow(Pre/PostShipment) 確定後に実装
# _ETD_ENABLED = False（本番フロー無影響・フラグOFFで完全除外）
_ETD_ENABLED: bool = False

if _ETD_ENABLED and etd_image_indices:
    requested_shipment["shippingDocumentSpecification"] = {
        "customerImageUsages": etd_image_indices,  # TODO(C-Q6): 正確な構造はCTS確認後
    }
```

パラメータ `etd_image_indices: dict | None = None` をオプショナルで追加。未登録テナントは従来通り動作。

---

## 検証基準

| 基準 | 検証方法 |
|---|---|
| migration schema: UNIQUE(tenant_id, image_type, environment) | migration-test で確認 |
| LETTERHEAD/SIGNATUREのみDB保存 | poka-yoke ユニットテスト |
| 出荷書類typeがguardで例外になる | ユニットテスト |
| etdDetailが本番経路に出ない | `_ETD_ENABLED=False` + テスト |
| imageIndex の再利用（upsert上書き） | ユニットテスト |
| imageIndex ≠ docId の混同なし | 型名・変数名で明示 |

---

## 外部・過去事例

- Eva Q3/Q4（APAC 2026-06-16）: LETTERHEAD/SIGNATURE imageIndex は無期限・再利用OK / 出荷書類は使い捨て
- Shingo C-Q1確認（2026-06-18）: Trade Documents Upload API は Ship APIと別カタログ
- `migrations/20260609_090000_add_carrier_credentials_rls.sql` — RLS パターン踏襲

## 弊害・リスク

| リスク | 対策 |
|---|---|
| G3未完了でSandbox疎通不通 | コードは完成。G3未済として切り分け報告 |
| エンドポイントパスTODO（C-Q1未完） | `_UPLOAD_IMAGE_PATH` TODO + Portal確認後1行修正 |
| J3 dormant が誤ってON | `_ETD_ENABLED=False` ハードコード + テスト |

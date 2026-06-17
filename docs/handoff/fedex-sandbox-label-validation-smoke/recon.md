# recon: FedEx Sandbox Label Validation 実機確認（PDF / A4 一本化）

**仕事名**: fedex-sandbox-label-validation-smoke  
**更新日**: 2026-06-17（PDF/A4 一本化方針反映）  
**対象ADR**: ADR-123 / ADR-129  
**目的**: A4通常プリンターによる PDF ラベルのみで FedEx Label Validation 申請フローを完結させる  
**スコープ**: PNG / ZPL は通常フロー対象外（低レイヤー互換は維持）

---

## 運用前提（2026-06-17 Shingo 確定）

- **プリンター形式**: A4 通常プリンター（熱転写ラベルプリンターは使用しない）
- **発行形式**: PDF のみ（PNG / ZPL は通常フロー確認対象外）
- **背景**: FedEx Label Validation 申請は PDF / A4 だけで完結する。ZPL（熱転写）は不使用のため通常フローから除去。

---

## 既存 ADR 検索結果

| ADR | 関連内容 |
|---|---|
| `docs/adr/FEATURE-INDEX.md:17` | "発送/出荷/FedEx/DHL" → ADR-103 / ADR-123 / ADR-128 |
| `docs/adr/ADR-123-carrier-integrator-provider.md:1` | FedEx Integrator 認定フロー全般 |
| `docs/adr/ADR-129-fedex-label-validation-wizard.md:1` | Label Validation Wizard 設計。§3.2 にサンプルラベル一括発行 UI を定義 |

---

## A. バックエンド実装（PDF 専用化後）

### A1. create_shipment() — label_image_type / label_stock_type

| 確認事項 | file:line | 内容 |
|---|---|---|
| 関数定義 | `backend/app/services/fedex_ship.py:57` | `def create_shipment(...)` — 同期関数 |
| label_image_type 引数 | `backend/app/services/fedex_ship.py:69` | `label_image_type: str = "PDF"` — デフォルト PDF |
| label_stock_type 引数 | `backend/app/services/fedex_ship.py:70` | `label_stock_type: str = "PAPER_85X11_TOP_HALF_LABEL"` — デフォルト A4 |
| リクエスト組み立て imageType | `backend/app/services/fedex_ship.py:122` | `"imageType": label_image_type` |
| リクエスト組み立て labelStockType | `backend/app/services/fedex_ship.py:124` | `"labelStockType": label_stock_type` |

※ 低レイヤー（`fedex_ship.create_shipment`）は PNG/ZPL パラメータを保持しているが、LV 通常フローでは使用しない。

### A2. LVSampleResult レスポンスモデル（PDF専用）

| 確認事項 | file:line | 内容 |
|---|---|---|
| クラス定義 | `backend/app/routers/shipping.py:673` | `class LVSampleResult(_BaseModel)` |
| pdf_base64 フィールド | `backend/app/routers/shipping.py:679` | PDF ラベル Base64 |
| png_base64 / zpl_base64 | 除去済み | 通常フロー対象外のため削除 |

### A3. lv_issue_sample_labels() — エンドポイント（PDF専用）

| 確認事項 | file:line | 内容 |
|---|---|---|
| エンドポイント定義 | `backend/app/routers/shipping.py:688` | POST /shipping/label-validation/samples |
| 対象サービス定義 | `backend/app/routers/shipping.py:665` | `_LV_SERVICES` — IP / IE / IPE / FICP の 4 サービス |
| PDF 発行（4サービス × 1回） | `backend/app/routers/shipping.py:755` | `fedex_ship.create_shipment(...)` — label_image_type デフォルト(PDF) |
| PNG / ZPL 発行 | 除去済み | `_lv_issue_zpl_with_fallback` 含め削除 |

---

## B. フロントエンド実装（PNG/ZPL除去後）

### B1. LVSampleLabel インターフェース

| 確認事項 | file:line | 内容 |
|---|---|---|
| インターフェース定義 | `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:26` | `interface LVSampleLabel` |
| pdf_base64 | `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:30` | PDF フィールドのみ |
| png_base64 / zpl_base64 / zpl_label_stock_type | 除去済み | 通常フロー対象外のため削除 |

### B2. ダウンロードハンドラー

| 確認事項 | file:line | 内容 |
|---|---|---|
| PDF ダウンロード | `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:96` | `const handleDownloadPdf` — PDF Blob, `application/pdf` |
| handleDownloadPng / handleDownloadZpl | 除去済み | 通常フロー対象外のため削除 |

### B3. ラベル一覧 UI

| 確認事項 | file:line | 内容 |
|---|---|---|
| ラベル一覧コンテナ | `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:261` | `lv-label-list` — 4 サービス分の lv-label-item |
| PDF ダウンロードボタン（のみ） | `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:267` | `lvStep2DownloadPdf` キー（PNG/ZPLボタン除去済み） |

---

## C. PNG / ZPL の取り扱い

| 形式 | 通常フロー | 低レイヤー対応（開発検証用） |
|------|-----------|--------------------------|
| PDF  | ✅ 発行対象 | `create_shipment(label_image_type="PDF")` |
| PNG  | ❌ 対象外  | `create_shipment(label_image_type="PNG")` で発行可能 |
| ZPL  | ❌ 対象外  | `create_shipment(label_image_type="ZPLII", label_stock_type=...)` で発行可能 |

---

## 参照元

- `docs/STANDARD-WORKFLOW.md`
- `docs/adr/FEATURE-INDEX.md:17`
- `docs/adr/ADR-123-carrier-integrator-provider.md:1`
- `docs/adr/ADR-129-fedex-label-validation-wizard.md:1`

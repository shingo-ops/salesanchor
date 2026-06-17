# recon: FedEx Sandbox ラベル発行 実機確認

**仕事名**: fedex-sandbox-label-validation-smoke  
**調査日**: 2026-06-17  
**対象ADR**: ADR-123 / ADR-129  
**目的**: PR #2300 でマージした PNG/ZPL ラベル発行実装が、実際の FedEx Sandbox 認証情報で正常動作するかを確認するための調査・手順書作成  
**スコープ**: 実装変更なし・docs-only（手順書・確認チェックリスト）

---

## PR #2300 マージ・CI 確認

- PR #2300 (`feature/morimoto/fedex-png-zpl-labels`) は develop にマージ済み
- Backend Tests: success / Frontend Check: success / Frontend E2E: success / Chromatic: success / Secret Scan: success / Migration Guard: success / Process Artifacts Gate: success（最終 head `3f39093e` で全 CI グリーン確認）
- ADR-129 §3.2「テストラベル一括発行 UI」Sprint 3.2 の実装完了分

---

## 既存 ADR 検索結果

| ADR | 関連内容 |
|---|---|
| `docs/adr/FEATURE-INDEX.md:17` | "発送/出荷/FedEx/DHL" → ADR-103 / ADR-123 / ADR-128 |
| `docs/adr/ADR-123-carrier-integrator-provider.md:1` | FedEx Integrator 認定フロー全般 |
| `docs/adr/ADR-129-fedex-label-validation-wizard.md:1` | Label Validation Wizard 設計。§3.2 にサンプルラベル一括発行 UI を定義 |

---

## A. バックエンド実装（#2300 マージ済み）

### A1. create_shipment() — label_image_type / label_stock_type

| 確認事項 | file:line | 内容 |
|---|---|---|
| 関数定義 | `backend/app/services/fedex_ship.py:57` | `def create_shipment(...)` — 同期関数 |
| label_image_type 引数 | `backend/app/services/fedex_ship.py:69` | `label_image_type: str = "PDF"` — デフォルト PDF |
| label_stock_type 引数 | `backend/app/services/fedex_ship.py:70` | `label_stock_type: str = "PAPER_85X11_TOP_HALF_LABEL"` — デフォルト A4 |
| リクエスト組み立て imageType | `backend/app/services/fedex_ship.py:122` | `"imageType": label_image_type` |
| リクエスト組み立て labelStockType | `backend/app/services/fedex_ship.py:124` | `"labelStockType": label_stock_type` |

### A2. ZPLII フォールバック実装

| 確認事項 | file:line | 内容 |
|---|---|---|
| フォールバック関数 | `backend/app/routers/shipping.py:673` | `async def _lv_issue_zpl_with_fallback(...)` — STOCK_4X6 優先、失敗時 PAPER_85X11_TOP_HALF_LABEL |
| primary stock type | `backend/app/routers/shipping.py:692` | `_primary = "STOCK_4X6"` |
| fallback stock type | `backend/app/routers/shipping.py:693` | `_fallback = "PAPER_85X11_TOP_HALF_LABEL"` |
| fallback ログ | `backend/app/routers/shipping.py:717` | `"[shipping] ZPLII STOCK_4X6 失敗 … → PAPER_85X11_TOP_HALF_LABEL にフォールバック"` |
| 両方失敗時 422 | `backend/app/routers/shipping.py:732-733` | `"STOCK_4X6: {primary_err}; PAPER_85X11_TOP_HALF_LABEL: {fallback_err}"` |

### A3. LVSampleResult レスポンスモデル

| 確認事項 | file:line | 内容 |
|---|---|---|
| クラス定義 | `backend/app/routers/shipping.py:738` | `class LVSampleResult(_BaseModel)` |
| png_base64 フィールド | `backend/app/routers/shipping.py:744` | PNG ラベル Base64 |
| zpl_base64 フィールド | `backend/app/routers/shipping.py:745` | ZPLII ラベル Base64 |
| zpl_label_stock_type フィールド | `backend/app/routers/shipping.py:746` | 実際に使用した labelStockType（デバッグ用） |

### A4. lv_issue_sample_labels() — エンドポイント

| 確認事項 | file:line | 内容 |
|---|---|---|
| エンドポイント定義 | `backend/app/routers/shipping.py:759` | `async def lv_issue_sample_labels(...)` POST /shipping/label-validation/samples |
| 内部ヘルパー _issue_one | `backend/app/routers/shipping.py:781` | `async def _issue_one(service_type, service_name, abbr, fmt, stock_type)` |
| 対象サービス定義 | `backend/app/routers/shipping.py:665` | `_LV_SERVICES` — IP / IE / IPE / FICP の 4 サービス |
| PDF 発行呼び出し | `backend/app/routers/shipping.py:808` | `_issue_one(..., "PDF", "PAPER_85X11_TOP_HALF_LABEL")` |
| PNG 発行呼び出し | `backend/app/routers/shipping.py:809` | `_issue_one(..., "PNG", "PAPER_85X11_TOP_HALF_LABEL")` |
| ZPL フォールバック呼び出し | `backend/app/routers/shipping.py:811` | `_lv_issue_zpl_with_fallback(...)` |
| zpl_label_stock_type 格納 | `backend/app/routers/shipping.py:827` | `zpl_label_stock_type=zpl_stock_used` |

---

## B. フロントエンド実装（#2300 マージ済み）

### B1. LVSampleLabel インターフェース

| 確認事項 | file:line | 内容 |
|---|---|---|
| インターフェース定義 | `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:26` | `interface LVSampleLabel` |
| zpl_label_stock_type | `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:34` | `zpl_label_stock_type: string` — デバッグ用フィールド |

### B2. ダウンロードハンドラー

| 確認事項 | file:line | 内容 |
|---|---|---|
| PDF ダウンロード | `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:105` | `const handleDownloadPdf` — PDF Blob, `application/pdf` |
| PNG ダウンロード | `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:111` | `const handleDownloadPng` — PNG Blob, `image/png` |
| ZPL ダウンロード | `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:117` | `const handleDownloadZpl` — ZPL テキスト, `application/octet-stream` |

### B3. ラベル一覧 UI

| 確認事項 | file:line | 内容 |
|---|---|---|
| ラベル一覧コンテナ | `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:269` | `lv-label-list` — 4 サービス分の lv-label-item |
| PNG ダウンロードボタン | `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:287` | `lvStep2DownloadPng` キー |
| ZPL ダウンロードボタン | `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:293` | `lvStep2DownloadZpl` キー |

---

## C. 不明点・実機確認が必要な事項

| # | 不明点 | 解消手段 | ブロッカー |
|---|---|---|---|
| U1 | ZPLII の labelStockType — Sandbox で STOCK_4X6 が成功するか | 実機テストで zpl_label_stock_type レスポンスフィールドを確認 | Sandbox アカウント番号が必要 |
| U2 | ZPLII の返却値形式 — Base64 バイナリか ZPL コマンド文字列か | `docs/handoff/fedex-ship-stage2/recon.md:74` では Base64 返却と記録。実機で ZPL ファイルを開いて確認 | Sandbox 実機 |
| U3 | PNG が PAPER_85X11_TOP_HALF_LABEL で正常生成されるか | 実機でダウンロードして画像として開けるか確認 | Sandbox 実機 |

---

## 参照元

- `docs/STANDARD-WORKFLOW.md`
- `docs/adr/FEATURE-INDEX.md:17`
- `docs/adr/ADR-123-carrier-integrator-provider.md:1`
- `docs/adr/ADR-129-fedex-label-validation-wizard.md:1`
- `docs/handoff/fedex-png-zpl-labels/recon.md` — #2300 実装 recon
- `docs/handoff/fedex-png-zpl-labels/design.md` — #2300 設計
- `docs/handoff/fedex-ship-stage2/recon.md:74` — ZPL 返却形式記録

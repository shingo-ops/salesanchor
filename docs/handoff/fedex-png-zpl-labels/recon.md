# recon: FedEx PNG/ZPL ラベル発行ワイヤリング

**仕事名**: fedex-png-zpl-labels  
**調査日**: 2026-06-16  
**対象ADR**: ADR-123 / ADR-125 / ADR-129  
**目的**: lv_issue_sample_labels にPNG/ZPLIIを追加するために必要な現状確認  
**スコープ**: 実装変更なし・docs-only recon

---

## 既存 ADR 検索結果

```bash
git grep -i "fedex" docs/adr/         # → ADR-123 / ADR-125 / ADR-129
git grep -i "label" docs/adr/FEATURE-INDEX.md  # → ADR-103/ADR-123/ADR-128
```

| ADR | 関連内容 |
|---|---|
| FEATURE-INDEX.md:17 | "発送/出荷/FedEx/DHL" → ADR-103 / ADR-123 / ADR-128（Integrator 認定）|
| ADR-123 §D4 | "ラベル/インボイス: 既存PDF基盤（reportlab）を活用。ZPLはFedEx応答をそのまま保存" |
| ADR-125 スコープ外 | "ラベル発行（Ship API / Open Ship API）" は第2段と明記 |
| ADR-129 §3.2 | "テストラベル一括発行UI（Sandbox 4サービス）" — Sprint 3.2 実装済み |
| ADR-129 §技術的制約 | "IPE のサービスタイプコードは FEDEX_INTERNATIONAL_PRIORITY_EXPRESS（FEDEX_ プレフィックス必須）" |

---

## A. Ship API — label_image_type パラメータ

### A1. create_shipment() の label_image_type

| 確認事項 | file:line | 内容 |
|---|---|---|
| 関数シグネチャ | `backend/app/services/fedex_ship.py:57` | `create_shipment(tenant_id, environment, client_id, client_secret, account_number, shipper, recipient, service_type, weight_kg, ...)` |
| label_image_type パラメータ | `backend/app/services/fedex_ship.py:69` | `label_image_type: str = "PDF"` — デフォルト PDF。任意の形式文字列を渡せる |
| リクエスト組み立て | `backend/app/services/fedex_ship.py:120` | `"imageType": label_image_type` — labelSpecification に動的セット済み |
| labelStockType | `backend/app/services/fedex_ship.py:122` | `"labelStockType": "PAPER_85X11_TOP_HALF_LABEL"` — 現状 PDF 固定値 |
| 返却値 | `backend/app/services/fedex_ship.py:196-204` | ShipmentResult(tracking_number, label_bytes, ...) — label_bytes は Base64 デコード済みバイト列 |
| customs_clearance | `backend/app/services/fedex_ship.py:126-127` | 国際便用通関情報。現在 lv では _LV_CUSTOMS を渡している |

**確認事項**: label_image_type の引数を変えるだけで PNG / ZPLII に切り替わる。ただし labelStockType が "PAPER_85X11_TOP_HALF_LABEL" に固定されているため、ZPLII 用に STOCK_4X6 を渡すには create_shipment() への label_stock_type 引数追加が必要（実装時に追加済み）。

**既存調査**: `docs/handoff/fedex-ship-stage2/recon.md:107` — "imageType（PDF / PNG / ZPLII / EPL2 / DPL）"

### A2. ZPL の labelStockType について

FedEx Ship API の仕様（`docs/handoff/fedex-ship-stage2/recon.md:107`）で確認済み:
- PDF: labelStockType = PAPER_85X11_TOP_HALF_LABEL（現在の固定値）
- PNG: labelStockType = PAPER_85X11_TOP_HALF_LABEL でも動作する見込み（ピクセル画像）
- ZPLII: labelStockType = STOCK_4X6（熱転写プリンター用 4x6インチ）推奨

⚠️ **Sandbox 実機確認が必要**: ZPLII の labelStockType はサンドボックス実機テストで確認する（STOCK_4X6 / PAPER_85X11_TOP_HALF_LABEL どちらが返るか）。

---

## B. バックエンドエンドポイント — 現状

### B1. LVSampleResult の現状

```python
# backend/app/routers/shipping.py:673-679
class LVSampleResult(_BaseModel):
    service_abbr: str      # IP / IE / IPE / FICP
    service_name: str
    service_type: str
    tracking_number: str
    pdf_base64: str        # ← PDF のみ
```

**不足**: png_base64 / zpl_base64 フィールドが存在しない。

### B2. lv_issue_sample_labels() の現状

| 確認事項 | file:line | 内容 |
|---|---|---|
| エンドポイント定義 | `backend/app/routers/shipping.py:686` | POST /shipping/label-validation/samples |
| 関数本体 | `backend/app/routers/shipping.py:691-745` | |
| label_image_type 引数 | `backend/app/routers/shipping.py:720-733` | create_shipment() に渡していない → デフォルト PDF のみ |
| ループ対象サービス | `backend/app/routers/shipping.py:714` | for abbr, service_type, service_name in _LV_SERVICES: |
| 返却 | `backend/app/routers/shipping.py:737-742` | pdf_base64=_b64.b64encode(result.label_bytes).decode() のみ |
| エラーメッセージ | `backend/app/routers/shipping.py:734-736` | f"{service_name}({abbr}) ラベル発行失敗: {e}" — サービス名のみ（形式が分からない） |

### B3. 固定データ（4サービス）

| 確認事項 | file:line | 内容 |
|---|---|---|
| _LV_SERVICES | `backend/app/routers/shipping.py:665-669` | IP / IE / IPE / FICP の 4 サービス |
| IP | `backend/app/routers/shipping.py:666` | `("IP", "INTERNATIONAL_PRIORITY", "FedEx International Priority")` |
| IE | `backend/app/routers/shipping.py:667` | `("IE", "INTERNATIONAL_ECONOMY", "FedEx International Economy")` |
| IPE | `backend/app/routers/shipping.py:668` | `("IPE", "FEDEX_INTERNATIONAL_PRIORITY_EXPRESS", "FedEx International Priority Express")` |
| FICP | `backend/app/routers/shipping.py:669` | `("FICP", "FEDEX_INTERNATIONAL_CONNECT_PLUS", "FedEx International Connect Plus")` |
| _LV_SHIPPER | `backend/app/routers/shipping.py:643` | 固定テスト発送者情報（日本・東京） |
| _LV_RECIPIENT | `backend/app/routers/shipping.py:647` | 固定テスト受取人情報（米国・Memphis） |
| _LV_CUSTOMS | `backend/app/routers/shipping.py:651` | 固定通関情報（commodity / unitPrice / customsValue） |

---

## C. フロントエンド — 現状

### C1. LVSampleLabel インターフェース

```typescript
// frontend/src/pages/integrations/FedexLabelValidationTab.tsx:25-30
interface LVSampleLabel {
  service_abbr: string;
  service_name: string;
  service_type: string;
  tracking_number: string;
  pdf_base64: string;   // ← PDF のみ
}
```

**不足**: png_base64 / zpl_base64 フィールドが存在しない。

### C2. handleDownloadLabel() の現状

```typescript
// frontend/src/pages/integrations/FedexLabelValidationTab.tsx:92-100
const handleDownloadLabel = (label: LVSampleLabel) => {
  const bytes = Uint8Array.from(atob(label.pdf_base64), (c) => c.charCodeAt(0));
  const blob = new Blob([bytes], { type: "application/pdf" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "fedex_lv_" + label.service_abbr + "_" + label.tracking_number + ".pdf";
  a.click();
  URL.revokeObjectURL(url);
};
```

**問題**: PDF のみ対応。PNG/ZPL ダウンロード関数が存在しない。

### C3. Step 2 UI の現状

| 確認事項 | file:line | 内容 |
|---|---|---|
| Step 2 セクション開始 | `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:163` | `<section className="lv-step card">` |
| 発行ボタン | `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:166-173` | 「テストラベルを発行（4サービス）」ボタン 1 つ |
| ラベル一覧 | `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:177-194` | lv-label-list 内に lv-label-item ×4 |
| ダウンロードボタン | `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:185-190` | `btn-secondary btn-sm` ボタン **1 つだけ**（"PDFをダウンロード"） |

**不足**: PNG / ZPL 用ダウンロードボタンが存在しない。ダウンロードボタンが 1 サービスにつき 1 つだけ（3 形式分のボタンが必要）。

---

## D. i18n キー — 現状

### D1. ja.json 既存キー

```json
// frontend/src/locales/ja.json:235-240
"lvStep2Title": "Step 2: テストラベルを発行",
"lvStep2Desc":  "4サービス分のテストラベルをSandboxで発行します。各サービス3ページ（AWBコピー含む）のPDFが生成されます。",
"lvStep2Button": "テストラベルを発行（4サービス）",
"lvStep2Issuing": "発行中...",
"lvStep2Success": "ラベル発行完了",
"lvStep2Download": "PDFをダウンロード",
```

**不足**: PNG/ZPL ダウンロードボタン用キー（lvStep2DownloadPng / lvStep2DownloadZpl）と説明文更新が必要。

### D2. en.json 既存キー（ADR-027 準拠・ja.json と同一キー必須）

```json
// frontend/src/locales/en.json:235-240
"lvStep2Title": "Step 2: Issue test labels",
"lvStep2Desc":  "Issue test labels for 4 services in Sandbox. Each service generates a 3-page PDF including AWB copies.",
"lvStep2Button": "Issue test labels (4 services)",
"lvStep2Issuing": "Issuing...",
"lvStep2Success": "Labels issued successfully",
"lvStep2Download": "Download PDF",
```

---

## E. テスト — 現状

### E1. test_fedex_ship.py

| 確認事項 | file:line | 内容 |
|---|---|---|
| ファイル存在 | `backend/tests/test_fedex_ship.py:1` | 461 行 |
| create_shipment テスト | `backend/tests/test_fedex_ship.py:145-327` | 正常系 / 認証エラー / APIエラー / dimensions あり・なし / surcharges |
| label_image_type テスト | `backend/tests/test_fedex_ship.py:1-461` | **存在しない** — label_image_type を引数に渡すケースのテストなし |
| _mock_ship_resp | `backend/tests/test_fedex_ship.py:59-101` | Base64 ダミーラベル返却モックあり。形式に関わらず同じ構造 |

### E2. lv_issue_sample_labels テスト

`backend/tests/` 全体を確認:
- `backend/tests/test_carrier_integrations.py` — lv エンドポイントのテストなし
- `backend/tests/test_fedex_ship.py` — lv_issue_sample_labels のテストなし

**不足**: lv_issue_sample_labels の単体テストが存在しない（PNG/ZPL 追加時に合わせて追加が必要）。

---

## F. 不明点

| # | 不明点 | 解消手段 | ブロッカー |
|---|---|---|---|
| U1 | ZPLII の labelStockType — Sandbox で STOCK_4X6 が成功するか未確定 | **コード上はフォールバック実装済み**（STOCK_4X6 失敗時に PAPER_85X11_TOP_HALF_LABEL で自動再試行）。実際にどちらが使われたかは zpl_label_stock_type レスポンスフィールドで確認可能。Sandbox 実機テストでの確認推奨 | 解消済み（フォールバック実装 — Sandbox アカウント番号登録後に実機確認） |
| U2 | ZPLII の FedEx Sandbox 返却値はテキスト（ZPL コマンド文字列）か Base64 か | 既存 recon（`docs/handoff/fedex-ship-stage2/recon.md:74`）では "Base64 で返却" と記録 — ただし ZPL は印刷コマンド文字列のためバイナリではない可能性あり | Sandbox 実機確認 |

---

## 参照元

- `docs/STANDARD-WORKFLOW.md`
- `docs/adr/FEATURE-INDEX.md:17`
- `docs/adr/ADR-123-carrier-integrator-provider.md`
- `docs/adr/ADR-125-fedex-rates-stage1.md`
- `docs/adr/ADR-129-fedex-label-validation-wizard.md`
- `docs/handoff/fedex-ship-stage2/recon.md` — Ship API imageType 仕様
- `docs/handoff/fedex-label-validation-readiness/checklist.md` — 棚卸しと A1+A2 の優先度

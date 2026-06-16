# handoff: FedEx PNG/ZPL ラベル発行ワイヤリング

**仕事名**: fedex-png-zpl-labels  
**作成日**: 2026-06-16  
**対象ADR**: ADR-123 / ADR-129  
**設計**: docs/handoff/fedex-png-zpl-labels/design.md  
**recon**: docs/handoff/fedex-png-zpl-labels/recon.md  
**実装役**: Generator (Claude Code)  
**Shingo GO 要否**: 不要（migration なし・危険変更なし）

---

## Claude Code への実装指示

### 前提確認（着手前に必ず読む）

1. `docs/handoff/fedex-png-zpl-labels/recon.md` — 現状把握
2. `docs/handoff/fedex-png-zpl-labels/design.md` — 実装方針・KGI・受け入れ基準
3. `docs/STANDARD-WORKFLOW.md` — 標準フロー

---

## 変更対象ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `backend/app/routers/shipping.py` | 修正（LVSampleResult 拡張 + lv_issue_sample_labels 拡張） |
| `frontend/src/pages/integrations/FedexLabelValidationTab.tsx` | 修正（LVSampleLabel 拡張 + ダウンロード関数分割 + Step 2 UI 3ボタン化） |
| `frontend/src/locales/ja.json` | 修正（PNG/ZPL ダウンロードキー追加 + lvStep2Desc 更新） |
| `frontend/src/locales/en.json` | 修正（同上・ADR-027） |
| `backend/tests/test_fedex_ship.py` | 修正（label_image_type テストケース追加） |

---

## ファイルごとの実装方針

### 1. `backend/app/routers/shipping.py`

#### 1-1. LVSampleResult にフィールド追加

```python
# 変更箇所: shipping.py:673-679
# 現状:
class LVSampleResult(_BaseModel):
    service_abbr: str
    service_name: str
    service_type: str
    tracking_number: str
    pdf_base64: str

# 変更後（2フィールド追加・既存フィールドはそのまま）:
class LVSampleResult(_BaseModel):
    service_abbr: str
    service_name: str
    service_type: str
    tracking_number: str
    pdf_base64: str    # 既存（削除しない）
    png_base64: str    # 追加
    zpl_base64: str    # 追加
```

#### 1-2. lv_issue_sample_labels() の拡張

- `create_shipment()` を 3 回呼ぶヘルパー `_issue_one(creds, service_type, service_name, abbr, fmt, account_number)` を作る（または インライン記述でも可）
- 各呼び出しに `label_image_type=fmt` を渡す（PDF / PNG / ZPLII）
- ZPLII の `labelStockType` は **`STOCK_4X6`** を試す。Sandbox でエラーになる場合は `PAPER_85X11_TOP_HALF_LABEL` にフォールバック（実機確認して確定させる）
- エラーメッセージ形式: `f"{service_name}({abbr}) {fmt} ラベル発行失敗: {e}"`
- 全形式を 1 つの `LVSampleResult` にまとめて返す（一部失敗なら HTTPException を raise）

#### 1-3. create_shipment() への labelStockType 引数追加（必要な場合のみ）

ZPLII が `PAPER_85X11_TOP_HALF_LABEL` では動作しない場合、`create_shipment()` に `label_stock_type: str = "PAPER_85X11_TOP_HALF_LABEL"` 引数を追加し、呼び出し側で形式別に渡す。**まず既存の labelStockType で試してから判断する。**

---

### 2. `frontend/src/pages/integrations/FedexLabelValidationTab.tsx`

#### 2-1. LVSampleLabel インターフェース拡張

```typescript
// shipping.py:25-30 の対応箇所（変更後）
interface LVSampleLabel {
  service_abbr: string;
  service_name: string;
  service_type: string;
  tracking_number: string;
  pdf_base64: string;    // 既存（削除しない）
  png_base64: string;    // 追加
  zpl_base64: string;    // 追加
}
```

#### 2-2. ダウンロード関数の分割

既存の `handleDownloadLabel` は削除して以下に分割する:

```typescript
const _triggerDownload = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
};

const handleDownloadPdf = (label: LVSampleLabel) => {
  const bytes = Uint8Array.from(atob(label.pdf_base64), c => c.charCodeAt(0));
  _triggerDownload(new Blob([bytes], { type: "application/pdf" }),
    `fedex_lv_${label.service_abbr}_${label.tracking_number}.pdf`);
};

const handleDownloadPng = (label: LVSampleLabel) => {
  const bytes = Uint8Array.from(atob(label.png_base64), c => c.charCodeAt(0));
  _triggerDownload(new Blob([bytes], { type: "image/png" }),
    `fedex_lv_${label.service_abbr}_${label.tracking_number}.png`);
};

const handleDownloadZpl = (label: LVSampleLabel) => {
  const bytes = Uint8Array.from(atob(label.zpl_base64), c => c.charCodeAt(0));
  _triggerDownload(new Blob([bytes], { type: "application/octet-stream" }),
    `fedex_lv_${label.service_abbr}_${label.tracking_number}.zpl`);
};
```

#### 2-3. Step 2 UI — 3ボタン化

`shipping.py:185-190` の PDF ボタン 1 つを、PDF / PNG / ZPL の 3 ボタンに変更:

```tsx
<div className="lv-label-download-buttons">
  <button className="btn-secondary btn-sm" onClick={() => handleDownloadPdf(label)}>
    {t("carrierIntegration.lvStep2DownloadPdf")}
  </button>
  <button className="btn-secondary btn-sm" onClick={() => handleDownloadPng(label)}>
    {t("carrierIntegration.lvStep2DownloadPng")}
  </button>
  <button className="btn-secondary btn-sm" onClick={() => handleDownloadZpl(label)}>
    {t("carrierIntegration.lvStep2DownloadZpl")}
  </button>
</div>
```

`lv-label-download-buttons` は CSS の flex layout 推奨（横並び）。

---

### 3. `frontend/src/locales/ja.json`

`carrierIntegration` オブジェクト内で、**既存キーの直後に**追加する:

```json
// lvStep2Download の直後に追加（lvStep2Download は削除する）
"lvStep2DownloadPdf": "PDF をダウンロード",
"lvStep2DownloadPng": "PNG をダウンロード",
"lvStep2DownloadZpl": "ZPL をダウンロード",
```

既存 `lvStep2Desc` の値を更新:
```json
"lvStep2Desc": "4サービス分のテストラベルをSandboxで発行します。各サービス PDF / PNG / ZPL の3形式が生成されます。"
```

既存 `lvStep2Download` は削除する（`FedexLabelValidationTab.tsx` で未使用になる）。

---

### 4. `frontend/src/locales/en.json`

ja.json と同一キー・同一順序で追加する（ADR-027 必須）:

```json
// lvStep2Download の直後に追加（lvStep2Download は削除する）
"lvStep2DownloadPdf": "Download PDF",
"lvStep2DownloadPng": "Download PNG",
"lvStep2DownloadZpl": "Download ZPL",
```

既存 `lvStep2Desc` の値を更新:
```json
"lvStep2Desc": "Issue test labels for 4 services in Sandbox. Each service generates 3 formats: PDF, PNG, and ZPL."
```

---

### 5. `backend/tests/test_fedex_ship.py`

既存の `TestCreateShipment` クラスに以下を追加:

```python
def test_label_image_type_is_passed_to_request(self):
    """label_image_type が labelSpecification.imageType に渡されること。"""
    with patch("httpx.post", side_effect=[
        _mock_token_resp(),
        _mock_ship_resp(),
    ]) as mock_post:
        create_shipment(
            tenant_id=1,
            environment="sandbox",
            client_id="cid",
            client_secret="csec",
            account_number="123456789",
            shipper=_sample_shipper(),
            recipient=_sample_recipient(),
            service_type="INTERNATIONAL_PRIORITY",
            weight_kg=Decimal("1.0"),
            label_image_type="PNG",
        )

    ship_call = mock_post.call_args_list[1]
    body = ship_call.kwargs.get("json") or ship_call.args[1]
    label_spec = body["requestedShipment"]["labelSpecification"]
    assert label_spec["imageType"] == "PNG"
```

同様に `label_image_type="ZPLII"` のケースも追加する。

---

## テストコマンド

```bash
# バックエンド単体テスト
cd backend && python -m pytest tests/test_fedex_ship.py -v

# バックエンド全テスト
cd backend && python -m pytest tests/ -v

# フロントエンド lint / typecheck
cd frontend && npm run type-check
cd frontend && npm run lint

# フロントエンドビルド確認
cd frontend && npm run build
```

---

## やってはいけないこと

| 禁止事項 | 理由 |
|---|---|
| `backend/app/services/fedex_ship.py` を大きく変更する | `label_image_type` はすでに対応済み。ルーター側のワイヤリングのみ |
| ETD（etdDetail）を実装する | APAC Q1〜Q6 回答待ち |
| Commercial Invoice（FedEx CI フォーム）を実装する | APAC Q6 回答待ち |
| migration を作成する | スキーマ変更なし |
| deploy.yml を変更する | デプロイ変更なし |
| scripts/ を変更する | 本番スクリプト変更なし |
| secrets を変更する | 不要 |
| 本番 DB を操作する | 不要 |
| FedEx 外部設定を変更する | 不要（Sandbox 実機テストは credentials 使用のみ） |
| PayPal / Discord / analytics / QA Smoke / SA-02 / mobile-shell を変更する | スコープ外 |
| `#2250 / #2257 / #2261 / #2262 / #2263 / #2264` を reopen する | スコープ外 |
| `pdf_base64` フィールドを削除・改名する | 後方互換破壊 |
| `handleDownloadLabel` を残したまま重複させる | TypeScript 型エラーの原因になる可能性 |
| i18n キーを ja.json のみ追加して en.json を忘れる | ADR-027 違反・CI 失敗 |

---

## PR 作成時の注意

- ブランチ: `feature/morimoto/fedex-png-zpl-labels`（develop ベース）
- base: `develop`
- PR 本文に `### 標準ワークフロー確認` セクション必須（CLAUDE.md §標準開発フロー）
  - 対象ADR: ADR-123 / ADR-129
  - recon: `docs/handoff/fedex-png-zpl-labels/recon.md`
  - 設計: `docs/handoff/fedex-png-zpl-labels/design.md`
- migration なし・deploy.yml なし・危険変更なしを PR 本文に明記
- docs/handoff/fedex-png-zpl-labels/ の 3 ファイルを `git add` に含める

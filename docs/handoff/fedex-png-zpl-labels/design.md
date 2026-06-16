# design: FedEx PNG/ZPL ラベル発行ワイヤリング

**仕事名**: fedex-png-zpl-labels  
**作成日**: 2026-06-16  
**recon**: docs/handoff/fedex-png-zpl-labels/recon.md  
**対象ADR**: ADR-123 / ADR-125 / ADR-129  
**ステータス**: Generator 着手待ち（Shingo GO 不要 — migration なし / 危険変更なし）

---

## 外部・過去事例の参照と我々への応用

小規模なワイヤリング実装（既存 API パラメータを通すだけ）のため、外部ライブラリ調査・設計パターン調査は不要。

FedEx の形式名（PDF / PNG / ZPLII）は既存実装（`backend/app/services/fedex_ship.py:120`）および `docs/handoff/fedex-ship-stage2/recon.md:107` の調査済み仕様に従う。ZPLII の `labelStockType` はSandbox 実機確認後に確定（U1/U2 参照）。

---

## KGI

| KGI | 検証方法 |
|---|---|
| 4サービス分の PDF / PNG / ZPLII ラベルをバックエンドで発行できる | pytest: `test_lv_issue_sample_labels` が PASS |
| フロントエンドから PDF / PNG / ZPL を個別にダウンロードできる | 目視確認（Shingo sandbox 環境）+ Playwright テスト（追加可能な場合） |
| 既存 PDF ダウンロード動作が壊れない | 既存 CI / pytest 全 PASS |

---

## 対象範囲

### 変更対象ファイル

| ファイル | 変更内容 |
|---|---|
| `backend/app/routers/shipping.py` | LVSampleResult にフィールド追加 + lv_issue_sample_labels 拡張 |
| `frontend/src/pages/integrations/FedexLabelValidationTab.tsx` | LVSampleLabel 拡張 + handleDownloadLabel 分割 + Step 2 UI ボタン追加 |
| `frontend/src/locales/ja.json` | PNG/ZPL ダウンロードボタン用キー追加 |
| `frontend/src/locales/en.json` | 同上（ADR-027: ja.json と同一キー必須） |
| `backend/tests/test_fedex_ship.py` | label_image_type テストケース追加（任意だが推奨） |

### 対象外（やってはいけない）

| 対象外 | 理由 |
|---|---|
| `backend/app/services/fedex_ship.py` | `label_image_type` はすでに実装済み。改修不要 |
| ETD / Paperless Trade（etdDetail） | APAC Q1〜Q6 回答待ち |
| Commercial Invoice（FedEx フォーム 057P） | APAC Q6 回答待ち |
| migration | スキーマ変更なし |
| deploy.yml | デプロイ変更なし |
| scripts/ | 本番スクリプト変更なし |
| FedEx 外部設定 | Sandbox 設定変更なし |
| 本番 DB 操作 | なし |

---

## 実装方針

### 1. バックエンド: LVSampleResult 拡張（後方互換優先）

```python
# backend/app/routers/shipping.py:673-679（変更後）
class LVSampleResult(_BaseModel):
    service_abbr: str
    service_name: str
    service_type: str
    tracking_number: str
    pdf_base64: str        # 既存フィールド（必須・そのまま）
    png_base64: str        # 追加（PNG ラベル Base64）
    zpl_base64: str        # 追加（ZPLII ラベル Base64 — ZPL コマンドを Base64 エンコード）
```

**後方互換の考え方**: フロントエンドは同一リポジトリで同時に更新するため、既存 `pdf_base64` を削除・改名しない。追加のみ行う。

### 2. バックエンド: lv_issue_sample_labels() 拡張

#### 2-1. 発行ループの構造

各サービス（IP/IE/IPE/FICP）に対して、PDF / PNG / ZPLII の 3 形式を順に発行し、すべてを 1 つの `LVSampleResult` にまとめて返す。

```python
# 変更後のループ骨格（擬似コード）
for abbr, service_type, service_name in _LV_SERVICES:
    pdf_bytes  = await _issue_one(creds, service_type, "PDF")
    png_bytes  = await _issue_one(creds, service_type, "PNG")
    zpl_bytes  = await _issue_one(creds, service_type, "ZPLII")

    labels.append(LVSampleResult(
        ...,
        pdf_base64=base64.b64encode(pdf_bytes).decode(),
        png_bytes=base64.b64encode(png_bytes).decode(),
        zpl_base64=base64.b64encode(zpl_bytes).decode(),
    ))
```

ヘルパー `_issue_one()` は `asyncio.to_thread(fedex_ship.create_shipment, ..., label_image_type=fmt)` を呼ぶ薄いラッパー。

#### 2-2. エラーメッセージ形式

形式ごとに失敗した場合に「どのサービス・どの形式で失敗したか」が分かるようにする:

```
"IP(FedEx International Priority) PNG ラベル発行失敗: <詳細エラー>"
```

現状の `f"{service_name}({abbr}) ラベル発行失敗: {e}"` からサービス名の後に形式（PDF/PNG/ZPL）を追加する。

#### 2-3. labelStockType の扱い

ZPLII 用の `labelStockType` は Sandbox 実機確認（U1）が必要。実装時は `STOCK_4X6` を試し、FedEx Sandbox から正常レスポンスが返った形式を採用する。  
**実装担当者（Generator）が Sandbox テストで確定してコミットする。**

#### 2-4. API 呼び出し回数

4 サービス × 3 形式 = **12 回**。Sandbox 用途（審査申請のみ）であるため、パフォーマンス影響は許容範囲内。タイムアウトは既存の `_TIMEOUT`（connect=3s, read=15s）をそのまま使用。

### 3. フロントエンド: LVSampleLabel 拡張

```typescript
// 変更後（frontend/src/pages/integrations/FedexLabelValidationTab.tsx:25-31）
interface LVSampleLabel {
  service_abbr: string;
  service_name: string;
  service_type: string;
  tracking_number: string;
  pdf_base64: string;    // 既存フィールド（そのまま）
  png_base64: string;    // 追加
  zpl_base64: string;    // 追加
}
```

### 4. フロントエンド: ダウンロード関数

`handleDownloadLabel` を形式別に分割する（または形式引数を渡す）:

```typescript
// 方針: 形式ごとに関数を分割（明確・型安全）
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
  // ZPL は Base64 → バイナリ → text/plain または application/octet-stream で保存
  const bytes = Uint8Array.from(atob(label.zpl_base64), c => c.charCodeAt(0));
  _triggerDownload(new Blob([bytes], { type: "application/octet-stream" }),
    `fedex_lv_${label.service_abbr}_${label.tracking_number}.zpl`);
};

// 共通ヘルパー（URL生成・クリック・revoke）
const _triggerDownload = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
};
```

**Content-Type まとめ**:

| 形式 | MIME Type | 拡張子 |
|---|---|---|
| PDF | `application/pdf` | `.pdf` |
| PNG | `image/png` | `.png` |
| ZPL (ZPLII) | `application/octet-stream` | `.zpl` |

ZPL は FedEx API が ZPL コマンドテキストを Base64 エンコードして返す（`docs/handoff/fedex-ship-stage2/recon.md:74`）。ブラウザ上でテキストとして開かれるより、バイナリとして保存する `application/octet-stream` が適切（プリンタードライバーが `.zpl` ファイルを直接受け取ることを想定）。

### 5. フロントエンド: Step 2 UI — 3ボタン化

```tsx
// 変更後（各サービスに PDF / PNG / ZPL ボタンを追加）
{labels.map((label) => (
  <div key={label.service_abbr} className="lv-label-item">
    <span className="lv-service-badge">{label.service_abbr}</span>
    <span className="lv-service-name">{label.service_name}</span>
    <span className="lv-tracking-number">{label.tracking_number}</span>
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
  </div>
))}
```

### 6. i18n キー追加（ADR-027: ja.json と en.json を同時更新）

#### ja.json 追加キー

```json
"lvStep2DownloadPdf": "PDF をダウンロード",
"lvStep2DownloadPng": "PNG をダウンロード",
"lvStep2DownloadZpl": "ZPL をダウンロード",
"lvStep2Desc": "4サービス分のテストラベルをSandboxで発行します。各サービス PDF / PNG / ZPL の3形式が生成されます。"
```

（`lvStep2Desc` は既存キーの値を更新）

#### en.json 追加キー

```json
"lvStep2DownloadPdf": "Download PDF",
"lvStep2DownloadPng": "Download PNG",
"lvStep2DownloadZpl": "Download ZPL",
"lvStep2Desc": "Issue test labels for 4 services in Sandbox. Each service generates 3 formats: PDF, PNG, and ZPL."
```

**既存キー `lvStep2Download` の扱い**: `lvStep2DownloadPdf` に移行後、`lvStep2Download` は削除する（未使用になる）。

---

## 受け入れ基準と検証方法

| 基準 | 検証方法 |
|---|---|
| `lv_issue_sample_labels` が 4サービス × PDF/PNG/ZPLII を返す | pytest: `test_lv_issue_sample_labels_returns_three_formats` が PASS |
| `LVSampleResult` に `png_base64` / `zpl_base64` フィールドが含まれる | pytest: レスポンスのキー確認 |
| label_image_type="PNG" 時に imageType="PNG" がリクエストに含まれる | pytest: `test_create_shipment_with_label_image_type` mock 確認 |
| フロント TypeScript が型エラーなくビルドできる | CI: frontend lint & custom checks が PASS |
| 既存 PDF ダウンロードが壊れない | 既存 pytest / CI が全 PASS |
| `lvStep2DownloadPdf` / `lvStep2DownloadPng` / `lvStep2DownloadZpl` キーが ja.json と en.json の両方にある | CI: Frontend lint & i18n チェックが PASS |

---

## リスクと対策

| リスク | 影響 | 対策 |
|---|---|---|
| FedEx Sandbox API 呼び出しが 12 回になる | レイテンシ増加（約 3〜5 秒 × 12 = 最大 60 秒）| Sandbox 限定用途（申請時のみ実行）で許容。タイムアウト設定は既存 `_TIMEOUT`（connect=3s, read=15s）のまま |
| ZPLII の labelStockType が未確定 | Sandbox でエラーになる可能性 | `STOCK_4X6` を試し、エラーなら `PAPER_85X11_TOP_HALF_LABEL` を試す。Generator が Sandbox 実機で確定する |
| ZPLII が Base64 でなくテキスト直返しの場合 | `atob()` が失敗 | 既存 recon（`docs/handoff/fedex-ship-stage2/recon.md:74`）は Base64 と記録。実機で確認し、テキスト返しなら `new TextEncoder().encode(text)` でバイト変換に切り替える |
| 途中失敗（例: PNG OK / ZPL 失敗）で一部のみ発行済みになる | ユーザーが発行数を見誤る | エラーメッセージに「どのサービス・どの形式」かを明示（§2-2）。全形式一括発行なので部分成功データは返さない（HTTPException で失敗） |
| Base64 レスポンスサイズ増加 | レスポンスが 3 倍のサイズになる | Sandbox 専用エンドポイントのため許容。ZIP 圧縮は将来 ADR で検討 |

---

## 実装済み確認（Generator は触らなくてよい）

- `backend/app/services/fedex_ship.py:57-133` — create_shipment() の label_image_type 対応
- `backend/app/services/fedex_rates.py:230` — get_or_refresh_token()
- `backend/app/services/carrier_credentials.py:114` — get_credentials()
- 固定テストデータ: `_LV_SHIPPER` / `_LV_RECIPIENT` / `_LV_CUSTOMS`（`backend/app/routers/shipping.py:643-669`）

---

## 参照元

- recon: docs/handoff/fedex-png-zpl-labels/recon.md
- ADR-123: `docs/adr/ADR-123-carrier-integrator-provider.md`（D4: "ZPL は FedEx 応答をそのまま保存"）
- ADR-129: `docs/adr/ADR-129-fedex-label-validation-wizard.md`（§3.2 / 技術的制約）
- 前提チェックリスト: `docs/handoff/fedex-label-validation-readiness/checklist.md`（A1+A2）

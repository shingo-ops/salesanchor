# 設計 — billing-display-name-fix

**対象ADR**: ADR-127（追補）, ADR-101（スナップショット不変性）  
**recon**: docs/handoff/billing-display-name-fix/recon.md  
**日付**: 2026-06-12  
**担当**: Morimoto

---

## 外部・過去事例の参照と我々への応用

- **ADR-101 スナップショット不変性**: 既存の `bill_to_snapshot` は作成時点の `company_name` を保持。`billing_display_name` キーがないスナップショットで `snap.get("billing_display_name")` は `None` → `company_name` にフォールバック。過去請求書は一切変わらない。
- **CompanyDetailPage.tsx:130** の `isAlreadyRegistered` パターン: `billingAddresses.some((a) => a.is_default)` を条件にして change_billing ボタンを条件表示する実績パターン → InboxKartePanel に同じ条件を適用。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 新規請求書の BILL TO が `billing_display_name` を優先する | Company 52（`billing_display_name='CANARY Billing NEW'`）で請求書作成後、PDFの BILL TO 行が `CANARY Billing NEW` になることを確認 |
| `billing_display_name` が空の会社は `company_name` にフォールバック | 既存請求書を再度PDFダウンロードし、宛名が変わらないことを確認 |
| change_billing 後の新行の `company_addresses.name` が空でない | company 52 の change_billing 実行後に `SELECT name FROM company_addresses WHERE company_id=52 AND is_default=TRUE` → 空でない値 |
| InboxKartePanel の change_billing ボタンが existing_customer 時のみ表示 | status=lead のカルテでは overflow メニューに請求先変更ボタンが存在しないことを確認 |
| type=change_billing の発行を未登録リードに試みると 409 not_registered | `POST /registration-tokens` に `{lead_id: <未登録>, type: "change_billing"}` → 409 |

---

## 修正方針

### Item 1: 請求書宛名（案A — billing_display_name 優先）

**変更箇所**:
- `backend/app/routers/invoices.py:68-71`: SELECT に `c.billing_display_name` 追加
- `backend/app/routers/invoices.py:84-95`: 返却 dict に `"billing_display_name": row["billing_display_name"]` 追加
- `backend/app/services/invoice_renderer.py:425-426`: `snap.get("billing_display_name") or snap.get("company_name")`
- `backend/app/services/invoice_renderer.py:503-504`: 同上（見積書）

**ADR-101 との整合**: 既存スナップショットに `billing_display_name` キーがなくても `None` → `company_name` フォールバックで安全。過去請求書は変わらない。

### Item 2: company_addresses.name フォールバック

**変更箇所**:
- `backend/app/routers/registration_tokens.py:510` (変更前行番号): `"name": addr.name or data.billing_display_name or ""`

`register` / `add_address` エンドポイントはリクエストに `billing_display_name` がないため未修正。change_billing 経路のみ対応。

### Item 3: InboxKartePanel ガード + API ゲート

**変更箇所**:
- `frontend/src/pages/inbox/InboxKartePanel.tsx:300-308`: `{status === "existing_customer" && <button ...>}` でラップ
- `backend/app/routers/registration_tokens.py:82-100` 直後: `type=change_billing` 未登録ゲート追加（`detail="not_registered"` 409）

**なぜ `status === "existing_customer"` か**: ActionBar はすでに `status` を持ち追加 API 呼び出し不要。`existing_customer` は登録済み確認済みの唯一の状態（register 完了が前提のステータス）。CompanyDetailPage の `isAlreadyRegistered` と実質同等の条件。

---

## 弊害・トレードオフ

- **既存請求書の宛名変化なし**: スナップショットに `billing_display_name` がないため `company_name` のまま。**これは意図した挙動**（ADR-101 不変性）。
- **会社名 ≠ billing_display_name の既存会社**: 次回請求書作成から新しい宛名が適用される。影響会社数は事前確認クエリで把握する（下記参照）。

---

## 事前確認クエリ（Item 0）

VPS 到達不可のため実行待ち。デプロイ前に以下を確認すること:

```sql
SELECT name, billing_display_name
FROM tenant_004.companies
WHERE billing_display_name IS NOT NULL
  AND billing_display_name <> ''
  AND billing_display_name <> name;
```

---

## 計画票

| ステップ | 内容 | 状態 |
|---------|------|------|
| 1 | invoices.py に billing_display_name 追加 | ✅ 完了 |
| 2 | invoice_renderer.py の _to_addr を billing_display_name 優先に | ✅ 完了 |
| 3 | change_billing INSERT の name フォールバック | ✅ 完了 |
| 4 | registration_tokens.py に change_billing 未登録ゲート | ✅ 完了 |
| 5 | InboxKartePanel change_billing ボタンを existing_customer 限定に | ✅ 完了 |
| 6 | ADR-134 軽量ADR 作成 | ✅ 完了 |
| 7 | 事前確認クエリ実行（デプロイ前） | ⏳ 要VPS |
| 8 | カナリー検証（company 52 で請求書作成・確認） | ⏳ デプロイ後 |

---

## カナリー検証手順

1. デプロイ後、`curl -X POST .../api/v1/invoices` で company 52 に請求書作成
2. `GET /invoices/{id}/pdf` でPDF取得
3. BILL TO 行が `CANARY Billing NEW` になっていれば ✅
4. 確認後に `PUT /invoices/{id}/void` で void（テスト請求書の削除）

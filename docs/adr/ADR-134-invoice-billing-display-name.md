# ADR-134: 請求書PDFの宛名に billing_display_name を優先使用する

**ステータス**: Accepted  
**日付**: 2026-06-12  
**担当**: Morimoto  
**関連ADR**: ADR-127（SA-03 change_billing）, ADR-101（請求書スナップショット不変性）

---

## 背景

ADR-127 で導入した `companies.billing_display_name`（UI: 「請求書表示名」）は、ダッシュボード・
レポート・ERP では `COALESCE(billing_display_name, name)` として優先使用されていた。
しかし請求書PDF生成経路（`_fetch_address_snapshot` → `invoice_renderer`）だけが
`companies.name` のみを参照し、`billing_display_name` を無視していた。

PO 決定: 請求書 BILL TO は **案A（billing_display_name 優先・company_name フォールバック）** を採用。

---

## 決定

### 請求書・見積書 BILL TO 宛名

```
billing_display_name が NULL でも "" でもなければ使用
そうでなければ company_name にフォールバック
```

実装箇所:
- `_fetch_address_snapshot`: SELECT に `c.billing_display_name` 追加、返却 dict に含める
- `invoice_renderer.py._to_addr`: `snap.get("billing_display_name") or snap.get("company_name")`

### 既存スナップショットの互換性（ADR-101 準拠）

既存の `bill_to_snapshot` JSONB には `billing_display_name` キーが存在しない。
`snap.get("billing_display_name")` は `None` を返し `company_name` にフォールバックするため、
**過去請求書の宛名表示は一切変わらない**。

### change_billing 時の company_addresses.name

`RegisterChangeBillingPage` は `address.name` フォームフィールドを持たないため
`addr.name` が常に `""` になるバグを修正。

```python
"name": addr.name or data.billing_display_name or ""
```

### InboxKartePanel change_billing ボタンガード

- `existing_customer` ステータス時のみ表示（CompanyDetailPage の `isAlreadyRegistered` と同条件）
- API: `type=change_billing` かつ未登録 → 409 `not_registered`

---

## 影響範囲

| 区分 | 変更あり | 変更なし |
|------|---------|---------|
| 新規請求書 BILL TO | `billing_display_name` が設定された会社 | `billing_display_name` が未設定の会社（company_name 継続） |
| 既存請求書 BILL TO | なし（スナップショット不変） | - |
| 見積書 BILL TO | 同上 | - |
| change_billing 新住所行の name | 空文字→ billing_display_name にフォールバック | - |

---

## トレードオフ

- **pros**: billing_display_name 変更が次回請求書から即反映される。レポート・ダッシュボードと挙動が一致。
- **cons**: `billing_display_name ≠ company_name` の会社は次回請求書から宛名が変わる。事前の影響会社数確認が必要。

---

## 参照

- `docs/handoff/billing-display-name-fix/recon.md`
- `docs/handoff/billing-display-name-fix/design.md`

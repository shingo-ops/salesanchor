# design: paid-at-payment-date

## 課題
PayPal 決済で実際の入金日時が記録されず、常に処理時刻（NOW()）が `paid_at` に入っていた。
手動入金時も担当者が日付を指定できなかった。

## 変更方針

### COALESCE パターン
`paid_at = COALESCE(:paid_at, NOW())`

- `:paid_at` に値が入れば使う
- NULL なら NOW() にフォールバック（後方互換）

### PayPal 自動取得
`paypal_payments.get_invoice_status` の戻り値 `payment_date` を使う。
取得失敗（None）の場合は NOW() フォールバック。

### 手動入金 UI
`InvoiceDetailPage` の入金ボタン前に `TextField type=date` を追加（ADR-144）。
選択しなければ `paid_at` は undefined → バックエンドで NOW() フォールバック。

## 基準と検証方法

| 基準 | 検証方法 |
|------|---------|
| PayPal 決済後の paid_at が実際の入金日時 | DB で invoices.paid_at を確認 |
| 手動入金で日付を選ぶと paid_at に反映される | UI で日付選択後に入金ボタンをクリック→DB確認 |
| 日付未選択で入金すると NOW() が入る | 日付未選択で入金→paid_at が現在時刻付近であることを確認 |

## 影響範囲
- backend: 5ファイル（paypal_payments.py, integrations.py, invoices.py, orders.py, schemas/order.py）
- frontend: 1ファイル（InvoiceDetailPage.tsx）

## 戻し方
各ファイルで `COALESCE(:paid_at, NOW())` を `NOW()` に戻し、`paid_at` パラメータバインドを削除する。

## 外部・過去事例の参照と我々への応用

PayPal Invoicing API v2 公式ドキュメント: `payments.transactions[0].payment_date` フィールドで入金日時が ISO8601 形式で取得可能。
我々への応用: API 戻り値の `payment_date` をそのまま PostgreSQL の TIMESTAMPTZ 列 `paid_at` にバインドする。
COALESCE で NULL フォールバックを入れることで、API が payment_date を返さない場合（未確定・エラー）でも現在時刻で安全に記録できる。

## 維持の仕組み

- `paid_at = COALESCE(:paid_at, NOW())` パターンは全 PayPal 関連エンドポイントで統一
- 手動入金は `PayInvoiceRequest.paid_at: datetime | None` で型検証（Pydantic）
- UI は ADR-144 の TextField コンポーネントを使用（生 input は使わない）
- 将来 PayPal 以外の決済手段を追加する際も同パターンを踏襲すること

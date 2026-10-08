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

## 外部事例
PayPal Invoicing API v2 レスポンス: `payments.transactions[0].payment_date` フィールドで入金日時を取得可能。

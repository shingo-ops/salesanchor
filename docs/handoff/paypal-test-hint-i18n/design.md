# design — paypal-test-hint-i18n

**仕事名**: paypal-test-hint-i18n
**日付**: 2026-06-16
**対象ADR**: ADR-101（PayPal Invoicing 方式）
**recon**: docs/handoff/paypal-test-hint-i18n/recon.md

---

## How（実装方針）

UI 文言とバックエンドのアイテム名のみ変更。ロジック・DB スキーマ・API 仕様に変更なし。

1. `ja.json` / `en.json` の `payTestHint` を PR #2293/#2294 で追加した送料 ¥500 を反映した文言に更新
2. `paypal_payments.py` の送料アイテム名を `"送料"` → `"Shipping"` に変更（国際顧客が PayPal 請求書を受け取る際に英語で表示されるよう統一）
3. `integrations.py` の `invoice_items` INSERT の `product_name` を `'PayPal決済テスト'` → `'PayPal Test Invoice'` に変更

## KPI / 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| UI 説明文に「¥600」合計が表示される | ブラウザで PayPal 連携設定画面を確認 |
| PayPal 請求書 PDF の送料行が "Shipping" で表示される | テスト請求書発行後に PDF ダウンロードで確認 |
| invoice_items に英語名で登録される | テスト請求書発行後に DB 確認 |

## 外部・過去事例の参照と我々への応用

- PayPal Invoicing API 公式ドキュメント — `items[].name` は自由文字列。受信者の PayPal アカウントのロケールに関わらず指定した文字列がそのまま表示される。英語で統一することで国際顧客に対応できる。

## 弊害

なし（表示文言の変更のみ）

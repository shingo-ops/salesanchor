# recon — paypal-test-hint-i18n

**仕事名**: paypal-test-hint-i18n
**日付**: 2026-06-16
**対象ADR**: ADR-101
**担当**: Hikky-dev

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/locales/ja.json:342` | payTestHint — 旧文言「テスト用の請求書（¥100）」 |
| `frontend/src/locales/en.json:342` | payTestHint — 旧文言「Create a test invoice (100 JPY)」 |
| `backend/app/services/paypal_payments.py:604` | 送料アイテム名「Shipping」（旧: 送料） |
| `backend/app/routers/integrations.py:708` | invoice_items product_name「PayPal Test Invoice」（旧: PayPal決済テスト） |

---

## 不明点リスト

**未解決ゼロ確認**: 該当なし（UI文言・アイテム名の英語化のみ）

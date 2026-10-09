# 設計 — paid-at-payment-date

**対象ADR**: ADR-072（reset_tenant_context）, ADR-027（i18n）, ADR-144（UIコンポーネント）  
**recon**: docs/handoff/paid-at-payment-date/recon.md  
**日付**: 2026-10-09  
**担当**: Sonnet

---

## 外部・過去事例の参照と我々への応用

- 事例1: PayPal Invoicing API v2 公式ドキュメント → `payments.transactions[0].payment_date` フィールドで入金日時が ISO8601 形式で取得可能。我々への応用: API 戻り値をそのまま PostgreSQL の TIMESTAMPTZ 列 `paid_at` にバインドする
- 事例2: SQL COALESCE パターン → NULL フォールバックで、API が payment_date を返さない場合（未確定・エラー）でも NOW() で安全に記録できる

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| PayPal 決済後の invoices.paid_at に実際の入金日時が記録される | DB で invoices.paid_at を SELECT して確認 |
| 手動入金で日付を選択すると paid_at に反映される | UI で日付選択後に入金ボタン → DB SELECT 確認 |
| 日付未選択で手動入金すると paid_at が現在時刻付近になる | 日付未選択で入金 → paid_at が NOW() 付近であることを確認 |
| orders.paid_at も同じ値で連動更新される | invoices 入金後に紐づく orders.paid_at を SELECT して確認 |

---

## 技術 How・KPI

- KPI: paid_at が NOW() ではなく実際の入金日時になる（PayPal 決済の場合）
- 技術選択: COALESCE(:paid_at, NOW()) パターン（理由: NULL フォールバックで後方互換・安全）
- UI: TextField type=date（ADR-144）で日付選択 → ISO8601 文字列でバックエンドへ送信

---

## 弊害・トレードオフ

- PayPal API が payment_date を返さない場合は NOW() にフォールバックするため、入金日時が不正確になる可能性がある → 対策: COALESCE で安全にフォールバック、API 改善で解消

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | paypal_payments.py に payment_date 抽出を追加 | Generator |
| 2 | integrations.py を COALESCE パターンに変更 | Generator |
| 3 | invoices.py pay_invoice に paid_at ボディ追加 | Generator |
| 4 | invoices.py confirm_paypal_payment を COALESCE に変更 | Generator |
| 5 | orders.py / schemas/order.py に paid_at フィールド追加 | Generator |
| 6 | InvoiceDetailPage.tsx に日付ピッカー追加 | Generator |
| 7 | i18n キー追加（ja/en） | Generator |

---

## 継続

- 完了後の監視: 本番で invoices.paid_at の値を抜き打ち確認
- 次フェーズへの引き継ぎ: 特になし

---

## 維持の仕組み

- 全 PayPal 経路（paypal_return / webhook / confirm_paypal_payment）で COALESCE パターンを統一。新しい PayPal 経路を追加する際も同パターンを踏襲すること
- 手動入金は `PayInvoiceRequest.paid_at: datetime | None` で型検証（Pydantic）
- UI は ADR-144 の TextField コンポーネントを使用（生 input は使わない）
- 守り手: 人手で守る（新しい PayPal エンドポイント追加時にレビューで確認）

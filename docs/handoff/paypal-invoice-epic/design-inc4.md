# design — Inc4: ケース(dispute)管理（PayPal 正規請求書拡張 KGI#4）

参照: recon = `docs/handoff/paypal-invoice-epic/recon.md`（§4-6/7/9）。正本 ADR: **ADR-101 改訂(2)**。SOP: `docs/STANDARD-WORKFLOW.md`。前提: 署名検証つき webhook 基盤は **PR #1980 実装済**（`integrations.py:853 paypal_webhook` / `paypal_payments.py:467 verify_webhook`）。

## 0. KGI（PO 承認 2026-06-12）
ケース（dispute）の発生・更新・解決を webhook で受信し、該当請求書/受注に紐づけて表示する。

## 1. 外部・過去事例の参照と我々への応用
- **公式（recon §7）**: `CUSTOMER.DISPUTE.CREATED/UPDATED/RESOLVED`（出典: developer.paypal.com/docs/disputes/webhooks/）。dispute resource は top-level `dispute_id`、`disputed_transactions[]`（`seller_transaction_id`＝capture id / `invoice_number`＝当社が `detail.invoice_number` に入れた IN-NNNN）、`status`、`reason`、`dispute_amount{value,currency_code}`。
- **過去事例（自社・PR #1980）**: `paypal_webhook` の署名検証→`set_tenant_context`→処理→`reset_tenant_context`（ADR-072）を**流用**。`register_webhook` の購読イベントに dispute 3種を追加。

## 2. 設計上の論点と決定
### 2.1 マルチテナントのルーティング＋署名検証順序（重要）
- 入金 webhook は `detail.reference="tenant:invoice"` で**テナントが即わかる**ので、そのテナントの webhook_id で検証する。
- dispute webhook には当社 reference が無い（PayPal 生成）。よって**テナント特定が先に必要**。**決定: 全テナントの webhook_id を順に試して `verify_webhook` が成功したテナントを特定**（テナント数=5 と少なく、5 リクエストで足りる）。成功テナントの文脈で処理する。
- **冪等**: `dispute_id` を一意キーに upsert（CREATED/UPDATED/RESOLVED で status を更新）。

### 2.2 dispute → 請求書/受注のリンク（防御的・フィールド前提を1つに賭けない）
- `disputed_transactions[].invoice_number` が当社 `invoices.invoice_number` と一致すれば請求書に紐づけ（第一候補）。
- 無ければ `disputed_transactions[].seller_transaction_id` を `invoices.paypal_capture_id` と照合（**Inc3 prep の capture_id 取得が前提**＝別 step）。
- どちらも無ければ**紐づけ無しで保存**（テナント単位の一覧には出す）。受注へは `orders.invoice_id` 経由で辿る。

### 2.3 保存
- 新テーブル（per-tenant schema）`paypal_disputes`: `id, dispute_id(UNIQUE), invoice_id(NULL可), pp_status, reason, amount, currency, raw(JSONB), created_at, updated_at`。

### 2.4 表示
- 請求書詳細（`InvoiceDetailPage`）に、紐づく dispute（status/理由/金額）を表示する小セクション。

## 3. インクリメント内の段階（安全側で分割）
- **Step A（本 PR・安全な基盤）**: ① `register_webhook` の購読に dispute 3種を追加（HTML ③B「保存し直すだけ」を実現）。② `paypal_disputes` テーブル migration（スキーマのみ・自社列＝payload 前提に依存しない）。③ test。
  - これにより、しんごさんが Disputes 有効化＋認証情報を再保存すれば、PayPal から dispute webhook が**当社エンドポイントに届く状態**になる（現状は 200 で無視＝無害）。
- **Step B（follow-up・Disputes 有効化後）**: webhook の `CUSTOMER.DISPUTE.*` ハンドラ実装（§2.1/2.2 のルーティング＋検証＋ upsert）＋ UI 表示。**実 payload を sandbox で確認してから実装**（§2.2 のフィールド存在を実機確認・推測実装しない）。Inc3 prep の `paypal_capture_id` 取得もここで合流可。

## 4. 受け入れ基準（Step A）
| # | 基準 | 検証方法 |
|---|---|---|
| 1 | register_webhook が INVOICING.INVOICE.PAID ＋ dispute 3種を購読 | pytest: body.event_types に4種 |
| 2 | paypal_disputes テーブルが全テナントに冪等作成（既存不変） | migration-test（実DB）＋ to_regclass/IF NOT EXISTS レビュー |
| 3 | 既存 webhook 挙動（INVOICING.INVOICE.PAID）不変 | 既存 test_paypal_webhook 維持 |

## 5. 弊害・トレードオフ / 危ない変更
- Step A の migration（テーブル追加）＝**危ない変更**→ shingo-ops の GitHub 承認が必要。
- マルチテナント検証「全テナント試行」は O(テナント数) の API コール。テナント増加時は webhook_id→tenant の逆引きキャッシュを検討（将来）。
- Step B は **Disputes 有効化（HTML ②③）後**に実 payload を確認して実装＝推測回避（SOP §3）。

## 6. 範囲外
- ケースへの自動応答（証拠提出等）。受信・表示まで（recon §6）。

# recon — PayPal 正規請求書 拡張（写しPDF自動保存＋追跡＋ケース管理）

- 日付: 2026-06-12 / architect recon
- 入力: Planner recon ブリーフ（`message (2).txt`）＋ 引き継ぎ（`message (3).txt`）／ KGI 4点（PO 承認 2026-06-12）
- 正本 ADR: **ADR-101 §6**（発行モード「PayPal (1) API 自動」）／ **ADR-104**（入金・ステータス）。SOP: `docs/STANDARD-WORKFLOW.md`。
- **重要な前提**: Invoicing 方式の Inc1（作成・送信）と Inc2（入金確認 webhook）は **本セッションの PR #1980 で実装済み・main 反映済み**（`docs/handoff/paypal-invoicing/`）。本 recon は **その上に積む差分**（写しPDF / 追跡 / ケース）を中心に file:line で突合する。

実コードは **フルパス:行番号** で引用（推測禁止・短縮禁止）。

---

## §4 ブリーフ9項目への回答（番号対応）

### 1. 認証情報の再利用（Invoicing にそのまま使えるか）
- `backend/app/services/paypal_payments.py:62` `get_credentials`（tenant_paypal_config から復号した client_id/secret/environment を返す）、`:190` `_get_token`（OAuth `/v1/oauth2/token` でアクセストークン取得）。
- **既に Invoicing で流用済み**: `:536` `create_and_send_invoice` / `:618` `get_invoice_status` が同じ `_get_token` を使用（PR #1980）。→ **追加の認証経路は不要**。Add Tracking（`/v1/shipping/trackers-batch`）・Disputes（`/v1/customer/disputes`）も同一 OAuth トークンで叩ける（同一 PayPal REST アプリ）。
- **実機確認事項（Shingo 領域）**: PayPal REST アプリ側で **Invoicing 機能**（送信に必要）と **Disputes 機能オプション**の有効化、および Add Tracking の利用可否。sandbox の dispute 作成は buyer 側設定が要る（ブリーフ §2 出典）。

### 2. invoices テーブルの現状と新列候補
- `backend/app/routers/invoices.py:120` `_INVOICE_COLUMNS` に既存: `pdf_url`(`:125`)、`paypal_order_id` / `paypal_approval_url` / `payment_fee`(`:130` 付近)。
- **現状の流用（PR #1980）**: `paypal_order_id`=PayPal Invoice ID(INV2-)、`paypal_approval_url`=recipient_view_url。
- **新列候補（migration 必要＝危ない変更）**:
  - `paypal_invoicer_view_url`（発行者用原本画面・KGI#2 のワンクリック導線）← 現状 service は取得していない（下記 §-4参照）。
  - `paypal_invoice_status`（DRAFT/SENT/PAID 等を保持。現状は invoices.status に paid を反映するのみ）。
  - `paypal_capture_id`（= transaction_id。Add Tracking に必須・§8参照。現状未取得）。
  - 写しPDF の参照（既存 `pdf_url` を流用 or `paypal_copy_pdf_*` 新設＝§4/§5 の保存方式に依存）。

### 3. 二重請求の排他（Orders リンク vs 正規請求書）
- **現状は排他不要に近い**: `backend/app/routers/invoices.py:604` `issue_paypal_link` は **PR #1980 で Orders→Invoicing に置換済み**（`:643` `create_and_send_invoice` を呼ぶ）。旧 `create_order`/`capture_order`（`paypal_payments.py`）は dormant で**エンドポイント未公開**。
- 発行ガード: `:664` `UPDATE ... WHERE id=:id AND status IN ('issued','overdue')`（TOCTOU 防御）。`paypal_order_id` が既に入っていれば再発行はフロントで抑止（`InvoiceDetailPage` の `!invoice.paypal_approval_url` 条件）。
- **結論**: 「Orders と Invoicing の両方が顧客に届く」経路は現状ない（Invoicing 一本）。Inc では「既に PayPal 請求書を発行済みなら二重発行しない」ガード（`paypal_order_id IS NULL` 条件）を UPDATE に足すと堅い（軽微・migration 不要）。

### 4. 既存 PDF 生成基盤（写しPDF は拡張で済むか）
- `backend/app/services/invoice_renderer.py:398` `render_invoice_pdf(invoice_data, tenant_profile) -> bytes`。**reportlab（純 Python・`:32-36`）**で生成。ADR-101 テンプレ SSOT（自社ブランド・ロゴ・色）に準拠。
- 呼び出し: `backend/app/routers/invoices.py:807` `pdf_bytes = render_invoice_pdf(...)` → `:810` `Response(content=pdf_bytes, media_type="application/pdf")` で**都度ストリーム返却**（ダウンロード）。
- **QR**: 現状 renderer に QR 描画は無い（`grep qr` ヒットなし）。写しPDF には「原本リンク＋QR」を入れる要件 → **QR 描画の追加が必要**（reportlab は drawImage で PNG 埋め込み可。QR は PayPal `generate-qr-code`(Base64 PNG) か自前生成のどちらか＝設計判断）。
- **結論**: 写しPDF は既存 renderer の**拡張**（フッターに原本リンク＋QR＋「PayPal Invoice INV2-… の写し」表記）で実現可能。本体テンプレは流用。

### 5. ファイル保存の現行方式（永続化先）
- **現状、生成 PDF は永続化されていない**: `invoices.py:807-812` は都度生成しストリーム返却のみ。`pdf_url` 列は存在するが**書き込み箇所が無い**（`grep "pdf_url *="` ヒットなし＝常に NULL 運用）。
- オブジェクトストレージ/documents テーブル/bytea 等の**既存永続基盤は無い**（`grep bytea|documents|s3|minio` ヒットなし）。
- VPS 制約（`CLAUDE.md`）: コンテナ `/app` 書込不可・`/tmp` は tmpfs（再起動で消える）。→ **ファイルシステム保存は不可**。
- **写しPDF 自動保存は新規実装**。現実的選択肢（設計/Shingo 判断）:
  - (a) **DB に bytea で保存**（新テーブル `invoice_documents` or invoices に列）。RLS でテナント分離・インフラ変更不要＝Inc1 の最有力。
  - (b) Docker volume / 永続パス＝compose 変更（危ない・インフラ）。
  - (c) 既に入っている Google Drive 連携（`integrations` の Drive OAuth）に保存＝外部依存だが既存資産。
  - → **Inc1 は (a) DB bytea を推奨**（最小・安全・RLS）。原本リンク（invoicer_view_url）で原本は常に開けるので PDF は「写し（記録用）」に徹する。

### 6. webhook 受信基盤と署名検証
- `backend/app/routers/integrations.py:51` `public_router`（Bearer 不要）。`:824` `@public_router.post("/integrations/paypal/webhook")` `paypal_webhook`（`:825`）。
- **署名検証は実装済み（PR #1980）**: `paypal_webhook` は `verify_webhook`（`paypal_payments.py:467`・`/v2/notifications/verify-webhook-signature`）で transmission 署名を検証 → `set_tenant_context` → status 再取得 → 請求書 paid＋受注 sourcing（ADR-072 reset 込み）。`:807` `_parse_invoicing_paid` が `INVOICING.INVOICE.PAID` の `resource.detail.reference`("tenant:invoice") でルーティング。
- **結論**: Inc4（Disputes webhook）は**この基盤をそのまま流用**できる（署名検証・public_router・tenant_context は完成済み）。追加は「`CUSTOMER.DISPUTE.CREATED/UPDATED/RESOLVED` の event_type 分岐＋dispute→invoice/order 紐づけ UPDATE」。webhook 購読イベント（`register_webhook:444` は現状 `INVOICING.INVOICE.PAID` のみ）に dispute イベントを追加する必要あり。

### 7. Invoicing/Disputes webhook イベント名（公式確定）
- 入金: **`INVOICING.INVOICE.PAID`**（実装済・`register_webhook:444` で購読）。他に `INVOICING.INVOICE.CANCELLED` / `REFUNDED` / `UPDATED` あり（出典: developer.paypal.com/docs/api/notifications/webhooks/event-names）。
- ケース: **`CUSTOMER.DISPUTE.CREATED` / `CUSTOMER.DISPUTE.UPDATED` / `CUSTOMER.DISPUTE.RESOLVED`**（出典: developer.paypal.com/docs/disputes/webhooks/、ブリーフ §2）。
- → recon 出典 URL を残す（公式）。Inc4 で `register_webhook` の event_types に dispute 3種を追加。

### 8. 追跡番号の置き場所 ＋ transaction_id（capture ID）
- **追跡番号フィールドは既存**: `backend/app/routers/orders.py:112` `tracking_number`（`shipping_carrier` 等と同列）。ADR-104 でも「発送通知（追跡番号付き）」を規定（`ADR-104:36`）。
- **PayPal への追跡登録（Add Tracking）は未実装**（`grep trackers-batch` ヒットなし＝新規）。
- **transaction_id（capture ID）が未取得**: `paypal_payments.py:642-654` `get_invoice_status` は `payments.transactions[0].paypal_fee` から **fee のみ**抽出し、**transaction id は取っていない**。Add Tracking は transaction_id 必須（ブリーフ §2）→ **Inc3 で get_invoice_status / webhook 時に transaction id を取得・`paypal_capture_id` に保存**する追加が必要。
- FedEx Stage 2（別案件・追跡別系統）との重複: PayPal への追跡“登録”は資金保留解除/セラープロテクション目的で、配送キャリア追跡とは別レイヤ。`tracking_number` は共用、push 先（PayPal/キャリア）が別。

### 9. ケース（dispute）の紐づけ先
- `orders.invoice_id`（`orders.py:110`）で受注↔請求書が連結。dispute は PayPal の invoice/transaction に紐づくため、**`paypal_invoice_id`（=invoices.paypal_order_id）or `paypal_capture_id` 経由で invoice にルーティング → invoice→order を辿れる**。
- **dispute 保存先は新規**（既存 dispute テーブル/列なし）。新テーブル `paypal_disputes`（dispute_id / invoice_id / status / reason / amount / raw / updated_at）を Inc4 で追加し、請求書詳細・受注詳細に表示。
- UI 挿し込み点: `frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx`（PayPal セクション）／受注詳細ページ。

---

## 確認済み事実（recon 根拠つき）
1. 認証（OAuth）は Invoicing/Tracking/Disputes 全てに流用可。追加認証経路は不要（`paypal_payments.py:62,190,536`）。
2. Invoicing 作成・送信・入金 webhook・**署名検証**は実装済み（PR #1980・`integrations.py:824`, `paypal_payments.py:467`）。Inc4 はこの基盤を流用可能。
3. PDF は reportlab で都度生成・**未永続**（`invoices.py:807`）。`pdf_url` 列はあるが未使用。写しPDF 自動保存＝新規（DB bytea 推奨）。QR 描画も新規。
4. `invoicer_view_url` / `paypal_capture_id`(transaction_id) / `paypal_invoice_status` / 写しPDF は**現状未取得・未保持**＝新列 migration が要る。
5. `tracking_number` は orders に既存（`orders.py:112`）。PayPal への Add Tracking push は新規・transaction_id 必須。
6. dispute の保存先・UI は新規。`orders.invoice_id` で受注↔請求書を辿れる。

## Shingo 判断が必要な事項
1. **写しPDF の保存方式**: (a) DB bytea［推奨・最小］/ (b) Docker volume［インフラ変更・危ない］/ (c) Google Drive 連携流用。→ どれで行くか。
2. **インクリメント分割の最終確定**（暫定: Inc1=写しPDF / Inc2=済 / Inc3=追跡 / Inc4=ケース）。Inc2 入金確認は **PR #1980 で実装済み**のため、実質 Inc1=写しPDF から着手で良いか。
3. **migration の本番 GO**（新列 + 写しPDF 保存テーブル）＝危ない変更。設計確定後に明示 GO をいただく。
4. **PayPal アカウント作業（Shingo 領域）**: REST アプリでの Invoicing/Disputes 機能有効化、webhook の dispute イベント本番登録、Add Tracking 利用可否。
5. **写しPDF と ADR-101 テンプレ SSOT の関係**: 自社ブランド PDF に「PayPal 請求書の写し」表記＋原本リンク＋QR を足す整理で良いか（ADR-101 改訂で明文化予定）。

## 出典（公式）
- Invoicing v2 / event-names: developer.paypal.com/docs/api/invoicing/v2/, /docs/api/notifications/webhooks/event-names
- Add Tracking: developer.paypal.com/docs/tracking/tracking-api/（`POST /v1/shipping/trackers-batch`・transaction_id 必須）
- Disputes webhook: developer.paypal.com/docs/disputes/webhooks/（CUSTOMER.DISPUTE.CREATED/UPDATED/RESOLVED）
- OpenAPI 仕様: github.com/paypal/paypal-rest-api-specifications（invoicing_v2.json に PDF DL endpoint 無し＝写しPDF 方式の根拠）

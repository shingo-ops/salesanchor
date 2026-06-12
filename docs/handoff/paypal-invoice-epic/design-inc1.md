# design — Inc1: 写しPDF自動保存＋原本ワンクリック（PayPal 正規請求書拡張）

参照: recon = `docs/handoff/paypal-invoice-epic/recon.md` ／ 正本 ADR: **ADR-101 改訂(2)**（写しPDF方式）。SOP: `docs/STANDARD-WORKFLOW.md`。前提: Invoicing 作成/送信/入金webhook は **PR #1980 実装済み**。

## 0. KGI（PO 承認 2026-06-12「DB保存でInc1からGO」）
KGI#2 を満たす: **PayPal 正規請求書の送信成功時に、原本と同一内容の写しPDFを自動生成・DB保存**し、原本画面（invoicer_view_url）をアプリからワンクリックで開ける。写しPDF には原本リンク＋QR を含める。
- 受け入れ最低ライン: sandbox で「発行→送信成功→写しPDF自動保存→原本リンク到達」が通る。

## 1. 外部・過去事例の参照と我々への応用
- **公式（recon §7）**: PayPal は API で描画PDFを返さない→自社写しPDF方式（PO 確定）。`invoicer_view_url`/`recipient_view_url` は GET `detail.metadata` から取得（既存 `_fetch_recipient_view_url` と同経路）。
- **過去事例（自社・既存PDF基盤）**: `invoice_renderer.render_invoice_pdf`（reportlab・ADR-101テンプレSSOT）を**拡張**して写し注記＋QRを足す（基盤を作り直さない）。QR は reportlab 同梱 `reportlab.graphics.barcode.qr`（**新規依存なし**）。
- **過去事例（既存 paypal 列 migration）**: `20260611_020000_add_invoice_paypal_columns.sql` の **pg_namespace ループ＋ADD COLUMN IF NOT EXISTS** を踏襲（最小・冪等・安全）。新テーブルを作らず invoices に列追加＝テナンシ判断を増やさない。

## 2. 技術 How
### 2.1 migration（危ない変更・3点セット）
- `migrations/20260612_HHMMSS_add_invoice_copypdf.sql`: 全 `tenant_%` スキーマの `invoices` に
  `paypal_invoicer_view_url TEXT` / `paypal_copy_pdf BYTEA` / `paypal_copy_pdf_at TIMESTAMPTZ` を `ADD COLUMN IF NOT EXISTS`（nullable・既存不変）。`to_regclass` 相当は ALTER 対象が必ず存在する invoices なので不要だが、ループ内で存在チェックはガードとして入れる。
- `scripts/run_all_migrations.sh` に `run_sql migrations/20260612_..._add_invoice_copypdf.sql` を追記（deploy.yml は run_all_migrations を呼ぶため別途編集不要）。
- **bytea を `_INVOICE_COLUMNS` には載せない**（通常クエリで重い blob を取得しない）。取得は専用 endpoint で個別 SELECT。

### 2.2 service `paypal_payments.py`
- `_fetch_recipient_view_url` を `_fetch_view_urls` に拡張し `{recipient_view_url, invoicer_view_url}` を返す（GET `detail.metadata.{recipient_view_url,invoicer_view_url}`）。`create_and_send_invoice` の戻りに `invoicer_view_url` を追加（既存キーは不変＝後方互換）。

### 2.3 renderer `invoice_renderer.py`
- `render_invoice_pdf(..., paypal_copy: dict | None = None)` を追加。`paypal_copy={pp_invoice_number, original_url}` が来たらフッターに帯「PayPal 請求書の写し（原本: INV2-…）」＋原本URL文字列＋**QR（original_url を encode）**を描画。QR は `reportlab.graphics.barcode.qr.QrCodeWidget`＋`Drawing` を `renderPDF.draw`。`paypal_copy=None` は従来通り（既存呼び出し不変）。

### 2.4 router `invoices.py`
- `issue_paypal_link` 成功時（create_and_send_invoice ok）に:
  1. `paypal_invoicer_view_url`=invoicer_view_url を UPDATE（既存 UPDATE に列追加）。
  2. 写しPDF生成: 既存 PDF endpoint と同じく invoice_data＋tenant_profile を構築 → `render_invoice_pdf(..., paypal_copy={pp_invoice_number=paypal_invoice_id, original_url=recipient_view_url})` → bytes。
  3. `UPDATE invoices SET paypal_copy_pdf=:bytes, paypal_copy_pdf_at=NOW()`。
  4. 生成失敗は**致命にしない**（リンク発行は成功扱い・写しは後で再生成可能）。ログ＋warning。
- 新 endpoint `GET /invoices/{id}/paypal-copy-pdf`（`invoices.update` or `invoices.view` 権限）: `SELECT paypal_copy_pdf` → 無ければ 404、あれば `Response(media_type="application/pdf")` で返却。
- `InvoiceResponse` に `paypal_invoicer_view_url` を追加（`_INVOICE_COLUMNS` に列追加・フロントの原本ワンクリック用）。bytea 列は含めない。

### 2.5 frontend `InvoiceDetailPage.tsx` ＋ i18n
- PayPal セクションに、`paypal_copy_pdf_at`相当が在る（=発行済）とき:「**原本を開く**」（`paypal_invoicer_view_url` を新規タブ）＋「**写しPDFをダウンロード**」（copy-pdf endpoint）ボタン。i18n `invoices.paypal.openOriginal` / `downloadCopyPdf`（ja/en 同期）。

## 3. 受け入れ基準（各基準に検証方法）
| # | 基準 | 検証方法 |
|---|---|---|
| 1 | 送信成功時に写しPDFが生成され invoices.paypal_copy_pdf に保存される | pytest(router): create_and_send_invoice をmock成功→issue_paypal_link→DBに blob 有り |
| 2 | 写しPDF に原本URL＋QR＋「写し」表記が入る | pytest(renderer): paypal_copy 指定で bytes 生成・%PDF ヘッダ／QR描画例外なし。目視1回 |
| 3 | invoicer_view_url を取得し InvoiceResponse に出る | pytest: get/ send mock の metadata.invoicer_view_url → 列保存→Response |
| 4 | GET /paypal-copy-pdf が保存blobを返す／無いと404 | pytest: 保存後200+application/pdf、未保存404 |
| 5 | 写し生成失敗でもリンク発行は成功（致命化しない） | pytest: render を例外させても issue_paypal_link は200 |
| 6 | migration が全テナント invoices に3列を冪等追加（既存不変） | migration-test CI（実DB）＋ to_regclass/IF NOT EXISTS レビュー |
| 7 | ADR-072: 書込後 reset_tenant_context | コードレビュー＋lint |
| 8 | i18n ja/en 同一キー・ハードコードなし | check:all/parity |
| 9 | bytea を通常クエリで取得しない（性能） | コードレビュー（_INVOICE_COLUMNS に blob 無し） |

## 4. 弊害・トレードオフ
- bytea を invoices に持つ＝行が太る。緩和: `_INVOICE_COLUMNS` から除外し通常クエリで取らない。将来 blob が増えるなら別テーブル/オブジェクトストレージへ移行（Inc 後続で再検討）。
- 写しPDF は「送信時点」のスナップショット。請求書を後から変更しても写しは再生成しない限り旧版（記録としては妥当）。再生成は再発行 or 専用操作（範囲外）。
- QR/原本リンクは `recipient_view_url`（公開・検証可能な原本ページ）を encode。アプリのワンクリックは `invoicer_view_url`（発行者ビュー）。
- **危ない変更**（migration＋run_all_migrations.sh）→ process-artifacts gate が **shingo-ops の GitHub 承認**を要求（本番投入の PO ゲート）。develop merge も同承認が前提。

## 5. 計画・継続
- Inc3（追跡・transaction_id 取得）／Inc4（dispute）は本 Inc 完了後。`paypal_capture_id` 等は Inc3 で追加。
- blob 肥大が見えたら `invoice_documents` テーブル＋ストレージ移行を再設計（本 Inc は最小・列方式）。

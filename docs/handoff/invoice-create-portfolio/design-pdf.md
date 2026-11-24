# design-pdf — 請求書・見積もりの詳細画面の PDF を保存できるようにする

状態: 設計案作成済み・設計審査済み（Opus の自己審査。独立した第二者の審査ではない）・実装未着手。
recon: `docs/handoff/invoice-create-portfolio/recon-pdf.md`

## 0. PO の決定
- 2026-11-24 PO「1」: 請求書の詳細画面で PDF が開かない件を調べて直す。
- 実装は PO の常時委任（ADR-1003・`docs/handoff/go-record-transcription/opus-delegation.md`）に基づく。画面の動きは今あるボタン名「PDF ダウンロード」どおりで、新しい方針の決定は無い。

## 1. 目的と、利用者に見える変化
| | 今 | 直したあと |
|---|---|---|
| 請求書の詳細「PDF ダウンロード」 | 新しいタブに `{"detail":"Not Found"}` | `{請求書番号}.pdf` が保存される |
| 請求書の詳細「写しPDFをダウンロード」 | 同じく Not Found | `{請求書番号}-paypal-copy.pdf` が保存される |
| 見積もりの詳細「PDF ダウンロード」 | 同じく Not Found | `{見積番号}.pdf` が保存される |
| 読めなかったとき | — | 画面上の既存の赤い知らせに「ダウンロードに失敗しました」 |

## 2. 対象と対象外
- 対象（3か所だけ）: `frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:155-161`、`frontend/src/pages/quote-detail/QuoteDetailPage.tsx:96-98`。
- 対象外: サーバー（道・権限・保存名はそのまま正しい・recon §2-3）。`lib/api.ts`・`lib/saveBlob.ts` は変えない。PDF を画面に埋め込む見せ方（nginx の守りの設定で止まる・recon §2-4）。

## 3. 変え方
今ある金型 `InvoiceCreatedModal.tsx:38-51` と同じ書き方にそろえる（同じ道具を使い、新しい道具を作らない）。
1. `api.getBlob("/invoices/${id}/pdf")` で札つきで読む（道の土台 `/api/v1` は api.ts が足す）。
2. `saveBlob(blob, 名前)` で保存する。
3. 失敗したら `setError(t("common.downloadFailed"))`。表示は今ある `error-message`（新しい部品・色・文言キーなし）。
4. 読んでいる間はボタンを `loading`・`disabled` にする（Button 金型の今ある props）。2度押しで2回読むのを防ぐ。
5. 保存名はサーバーの保存名の正本（`invoices.invoice_number`・`quotes.quote_code`）を画面が既に持っている値で作る。番号が空のときはボタンを出さない（R6 の金型 InvoiceCreatedModal.tsx:36 と同じ）。本番で番号が空の請求書・見積もりは0件（recon §2-6）。

### 代わりの案と選ばなかった理由
- 道の名前だけ `/api/v1/...` に直す: 札を送らないため 401 のまま（recon §2-2）。不採用。
- 新しいタブで blob を開く: 本番の守りの設定で埋め込みが止まる前例がある（recon §2-4）。ボタン名も「ダウンロード」。不採用。
- サーバーの返す保存名（Content-Disposition）を読む道具を api.ts に足す: 共通の道具を変える範囲が広がる。今は画面が同じ正本の値を持っている。不採用（番号が空の請求書が出る道ができたら再検討）。

## 4. 影響範囲
- 呼び出し元: 2つの関数はそれぞれのページの中だけで使う（`git grep -n "handleDownloadPdf\|handleDownloadCopyPdf" -- frontend/src` で対象の2ファイルのほかに `frontend/src/pages/integrations/FedexLabelValidationTab.tsx` が出るが、そのファイルの中だけの別の関数で `window.open('/api` を使っていない。触らない）。
- 権限: サーバーは今と同じ invoices.view で確かめる。画面のボタンの出し方は変えない（番号が空のときだけ隠す）。

## 5. リスクと対処
| リスク | 対処 |
|---|---|
| 写しPDFがまだ無い（404）| 失敗の知らせを出す。ボタンは今どおり `paypal_copy_pdf_at` があるときだけ出る |
| 大きな PDF で時間がかかる | api.getBlob の今ある待ち時間と繰り返しに任せる。読んでいる間はボタンを止める |

## 6. 受入条件
| 基準 | 検証方法 |
|---|---|
| K1 請求書「PDF ダウンロード」が `api.getBlob('/invoices/9/pdf')` を呼び、`saveBlob(blob, 'IN-0009-01.pdf')` で保存する | vitest（新規 InvoiceDetailPage.test.tsx） |
| K2 「写しPDFをダウンロード」が `'/invoices/9/paypal-copy-pdf'` を呼び `'IN-0009-01-paypal-copy.pdf'` で保存する | vitest |
| K3 見積もり「PDF ダウンロード」が `'/quotes/5/pdf'` を呼び `'QT-0005.pdf'` で保存する | vitest（新規 QuoteDetailPage.test.tsx） |
| K4 読めなかったとき `common.downloadFailed` の文（en: Download failed）が画面に出る（請求書・見積もり両方） | vitest |
| K5 番号が空ならボタンが出ない（請求書・見積もり両方） | vitest |
| K6 `window.open(\`/api` が frontend/src に0件 | `git grep -nE "window\.open\(\s*[\`'\"]/api" -- frontend/src` が0行 |
| K7 本番テナント001の見積もり1件で「PDF ダウンロード」を押すと `GET /api/v1/quotes/{id}/pdf` が 200・`application/pdf` で、ファイルが保存される | 反映後に Opus が Chrome で押し、通信の記録を読む（押すのは PO の同意票のあと） |
| K8 npm run check:all が通る | クラウドの実行記録・CI |

- 請求書の本番確認: 本番に請求書が0件のため、K1・K2・K4・K5 の vitest と、同じ道具を使う作成後の枠（R6・本番済）で代える。

## 7. 維持の仕組み
- K6 は検証のコマンドで数え、結果を PR 本文に残す。同じ書き方が新しく入るのを止める見張りは今回は作らない（直したあと本番のコードに0件・必要になれば別テーマ）。
- 担当: 請求書の画面を触る便の設計者（Opus）。

## 8. 外部事例
- 該当なし。理由: 既存の金型（InvoiceCreatedModal）を同じ画面群に広げる直しで、新しいやり方を選ぶ判断が無いため。

## 9. 設計審査（Opus 自己審査・2026-11-24）
- 判定: APPROVE
- 根拠: 原因は本番の返事（404・401）と api.ts:32 で確かめた。直し方は本番で動いている金型と同じ。新しい文言キー・部品・色を足さない。触るファイルは4つ（ページ2・試験2）。
- 未解決: なし。

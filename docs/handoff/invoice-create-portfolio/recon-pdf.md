# recon-pdf — 請求書・見積もりの詳細画面で PDF が開かない件

調べた日: 2026-11-24（origin/main 40e846570）。担当: Opus（設計）。

## 1. PO の言葉と目的
- 2026-11-24 PO「1」（請求書の詳細画面の PDF が開かない件を調べて直す）。
- 目的: 詳細画面の「PDF ダウンロード」「写しPDFをダウンロード」を押すと、PDF ファイルが保存される。

## 2. 観測した事実

### 2-1. ボタンが開く先
- `/Users/tanizawashingo/worktrees/salesanchor/release-invoice-detail-pdf-download/frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:155-161`
  ```tsx
  const handleDownloadPdf = () => {
    window.open(`/api/invoices/${id}/pdf`, "_blank");
  };
  const handleDownloadCopyPdf = () => {
    window.open(`/api/invoices/${id}/paypal-copy-pdf`, "_blank");
  };
  ```
- `/Users/tanizawashingo/worktrees/salesanchor/release-invoice-detail-pdf-download/frontend/src/pages/quote-detail/QuoteDetailPage.tsx:96-98` も同じ書き方（`/api/quotes/${id}/pdf`）。
- `git grep -nE "window\.open\(\s*[\`'\"]/api" -- frontend/src` の結果は、上の3か所だけ。
- この書き方は da004e6e6（2026-06-04・#1613）で入った。

### 2-2. 本番で同じ先を開いたときの返事（2026-11-24・ログインなしの GET）
| 開いた先 | 返事 |
|---|---|
| `https://app.salesanchor.jp/api/invoices/1/pdf`（ボタンが今開く先） | 404 `{"detail":"Not Found"}` |
| `https://app.salesanchor.jp/api/quotes/1/pdf`（見積もりのボタンが今開く先） | 404 |
| `https://app.salesanchor.jp/api/v1/invoices/1/pdf`（正しい道） | 401（ログインの札が無い） |
| `https://app.salesanchor.jp/api/v1/invoices/1/paypal-copy-pdf` | 401 |

原因は2つ重なっている。
1. 道の名前に `/v1` が抜けている。画面の API の土台は `frontend/src/lib/api.ts:32` `const API_BASE = "/api/v1";`。
2. `window.open` は新しいタブを開くだけで、ログインの札（Authorization ヘッダー）を送らない。このアプリはクッキーを使わず札をヘッダーで送るため、道を直しても 401 になる。

### 2-3. サーバーの道（直す必要なし）
- `backend/app/routers/invoices.py:1179` `GET /invoices/{invoice_id}/pdf`（権限 invoices.view）。保存名 `{invoice_code}.pdf`（:1229。invoice_code は invoice_number が空なら IN-{id:04d}-01）。
- `backend/app/routers/invoices.py:1277` `GET /invoices/{invoice_id}/paypal-copy-pdf`（権限 invoices.view）。保存名 `{番号}-paypal-copy.pdf`（:1297）。
- `backend/app/routers/invoices.py:1341` `GET /quotes/{quote_id}/pdf`（権限 invoices.view）。保存名 `{quote_code}.pdf`（:1405）。

### 2-4. 正しく動いている今ある書き方（金型）
- `frontend/src/pages/invoice-create/InvoiceCreatedModal.tsx:38-51`: `api.getBlob(\`/invoices/${invoice.id}/pdf\`)` で札つきで読み、`saveBlob(blob, \`${invoice.invoice_number}.pdf\`)` で保存。失敗は Callout で知らせる。番号が空なら保存のボタンを出さない（:36）。
- `frontend/src/lib/api.ts:200-305` `api.getBlob`（札つき・繰り返しつき）。
- `frontend/src/lib/saveBlob.ts:5` `saveBlob`。冒頭の注記に「同じ書き方の今あるページは R6 では書き換えない」とあり、今回の3か所はその残り。
- PDF を画面やタブに埋め込まない理由: 本番の守りの設定 `nginx/nginx.conf:96` が blob の PDF の埋め込みを止める（InvoiceCreatedModal.tsx:4 の注記）。

### 2-5. 文言（新しいキーは要らない）
- `common.downloadFailed` = 「ダウンロードに失敗しました」（ja.json・en.json に既にある）。
- 両方のページに既に `setError` と `error-message` の表示がある（InvoiceDetailPage.tsx:128-129・:231、QuoteDetailPage.tsx:63・:66・:156）。

### 2-6. 本番のデータ（reader 鍵・2026-11-24）
| テナント | 請求書の件数 | 番号が空 | 見積もりの件数 | 番号が空 |
|---|---|---|---|---|
| 001 | 0 | 0 | 1 | 0 |
| 003〜006 | 0 | 0 | 0 | 0 |

- 本番に請求書は1件も無い。お客様がこの不具合にあたった記録は無い。
- 本番で押して確かめられるのはテナント001の見積もり1件だけ。

### 2-7. 既存の ADR
- ADR-101（請求書）・ADR-027（文言は t() 経由）・ADR-144（UI の金型）。`git grep -il "window.open" docs/adr/` で PDF の開き方を決めた ADR は無い。

## 3. 未確認
- なし（直す道の判断に要るものは上で確かめた）。

# card-pdf: 請求書・見積もりの詳細画面の PDF を札つきで読んで保存する

状態: 発行（Opus 2026-11-24）。
設計: docs/handoff/invoice-create-portfolio/design-pdf.md（Opus 自己審査 APPROVE）・recon-pdf.md。
実装承認: PO「1」（2026-11-24: 請求書の詳細画面で PDF が開かない件を調べて直す）。PR マージ・デプロイまでの完走は ccopusgo の委任の範囲（ADR-1003）。
担当: クラウドの Sonnet（実装）。設計と審査は Opus。
枝: release/invoice-detail-pdf-download（origin に設計の commit が在る。この枝の上に実装を足す）。
基準: origin/main 40e846570。移行（migrations/）なし・deploy.yml なし・scripts/ なし・backend なし。危険便ではない。

## 受領確認（最初の報告の 1 行目に書く）

`RECEIVED invoice-detail-pdf HEAD=` に続けて、手順1 の後の `git rev-parse HEAD` の 40 桁を書く。

## 0. Opus の決めごと（根拠つき）

- D1 PDF は `api.getBlob(道)` で読み、`saveBlob(blob, 名前)` で保存する。作成後の枠 `frontend/src/pages/invoice-create/InvoiceCreatedModal.tsx:38-51` と同じ（design-pdf §3）。`window.open` は使わない。
- D2 道は `/invoices/{id}/pdf`・`/invoices/{id}/paypal-copy-pdf`・`/quotes/{id}/pdf`（`/api/v1` は api.ts:32 が足す）。
- D3 名前は `{invoice_number}.pdf`・`{invoice_number}-paypal-copy.pdf`・`{quote_code}.pdf`（サーバーの保存名と同じ・recon-pdf §2-3）。番号が空ならボタンを出さない。
- D4 失敗は今ある `setError(t("common.downloadFailed"))`。新しい文言キー・部品・色を足さない。
- D5 読んでいる間はボタンを Button の `loading`・`disabled` にする。

## 0-1. カード発行前チェック（docs/ai-agents/design-partner.md §5.5）

| # | 点検 | 結果 |
|---|---|---|
| 1 | 設計の審査は APPROVE か | ○ design-pdf.md §9（Opus 自己審査） |
| 2 | PO の実装承認があるか | ○ PO「1」2026-11-24 |
| 3 | 触るファイルを全部挙げたか | ○ §1 |
| 4 | 触らない範囲を書いたか | ○ §1 末尾 |
| 5 | 変更前の文を実物から写したか | ○ §2（origin/main 40e846570） |
| 6 | 受入条件が○×で判定できるか | ○ design-pdf §6 K1〜K8 |
| 7 | 危険パスの有無 | なし |
| 8 | 新しい部品・色の直書きが無いか | ○ Button の今ある props だけ |
| 9 | i18n の ja/en 同じキー | ○ 新しいキーなし（common.downloadFailed は両方に在る） |
| 10 | 推測の値が無いか | ○ |
| 11 | 想定の分かれ道を書いたか | ○ §4 |
| 12 | 止める条件を書いたか | ○ §0-3・§4 |
| 13 | 報告の形を決めたか | ○ §5 |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・commit は git log で確かめる | ○（§3） |
| guards/03-file.md | 既存ファイルの編集は Edit ツール。新しいファイルは Write ツール。プレースホルダを残さない | ○（§2） |
| guards/04-worktree.md | new-worktree.sh で作る・出力をパイプに通さない・実在は git worktree list で確かめる・push は -u 付き | ○（手順1・手順6） |
| guards/10-executor.md | 散文で頼まない。手順はコマンドで書く | ○（§3） |

## 0-3. 実装前点検（手順2 で流す。外れたら実装せず BLOCKED: で停止）

- P1 指紋（git hash-object の先頭12字）:
  - `bc765289f71f` frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx
  - `e80e1f08bc91` frontend/src/pages/quote-detail/QuoteDetailPage.tsx
- P2 frontend/src/pages/invoice-detail/InvoiceDetailPage.test.tsx と frontend/src/pages/quote-detail/QuoteDetailPage.test.tsx が無い（`ls` の数え 0）。
- P3 `window.open(\`/api` の行が frontend/src に 3 行。

## 1. 触るファイル

- frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx（Edit 5 か所）
- frontend/src/pages/quote-detail/QuoteDetailPage.tsx（Edit 4 か所）
- frontend/src/pages/invoice-detail/InvoiceDetailPage.test.tsx（新規・Write）
- frontend/src/pages/quote-detail/QuoteDetailPage.test.tsx（新規・Write）

触らない: backend すべて・frontend/src/lib/api.ts・frontend/src/lib/saveBlob.ts・locales・components・frontend/src/pages/integrations/FedexLabelValidationTab.tsx（同じ名前の別の関数）。

## 2. 変更

### 2-1. frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx（Edit 5 か所）

(a) 変更前:
```
import { api } from "../../lib/api";
```
変更後:
```
import { api } from "../../lib/api";
import { saveBlob } from "../../lib/saveBlob";
```

(b) 変更前:
```
  const [paymentDate, setPaymentDate] = useState<string>("");
```
変更後:
```
  const [paymentDate, setPaymentDate] = useState<string>("");
  // design-pdf D5: 読んでいる間のボタン（"pdf" | "copy"）。空なら読んでいない
  const [pdfSaving, setPdfSaving] = useState<"" | "pdf" | "copy">("");
```

(c) 変更前:
```
  const handleDownloadPdf = () => {
    window.open(`/api/invoices/${id}/pdf`, "_blank");
  };

  const handleDownloadCopyPdf = () => {
    window.open(`/api/invoices/${id}/paypal-copy-pdf`, "_blank");
  };
```
変更後:
```
  // design-pdf §3: 札つきで blob を読み、サーバーと同じ名前で保存する（金型 InvoiceCreatedModal.tsx と同じ）
  const downloadBlob = async (kind: "pdf" | "copy", path: string, filename: string) => {
    setError("");
    setPdfSaving(kind);
    try {
      const blob = await api.getBlob(path);
      saveBlob(blob, filename);
    } catch {
      setError(t("common.downloadFailed"));
    } finally {
      setPdfSaving("");
    }
  };

  const handleDownloadPdf = () => {
    if (!invoice?.invoice_number) return;
    void downloadBlob("pdf", `/invoices/${id}/pdf`, `${invoice.invoice_number}.pdf`);
  };

  const handleDownloadCopyPdf = () => {
    if (!invoice?.invoice_number) return;
    void downloadBlob("copy", `/invoices/${id}/paypal-copy-pdf`, `${invoice.invoice_number}-paypal-copy.pdf`);
  };
```

(d) 変更前:
```
              <Button variant="secondary" size="sm" layoutClassName="field-h-md" onClick={handleDownloadPdf}>{t("invoices.snapshot.downloadPdf")}</Button>
```
変更後:
```
              {invoice.invoice_number && (
                <Button variant="secondary" size="sm" layoutClassName="field-h-md" onClick={handleDownloadPdf} loading={pdfSaving === "pdf"} disabled={pdfSaving !== ""} data-testid="invoice-detail-download-pdf">{t("invoices.snapshot.downloadPdf")}</Button>
              )}
```

(e) 変更前:
```
            {invoice.paypal_copy_pdf_at && (
              <Button variant="secondary" size="md" onClick={handleDownloadCopyPdf}>{t("invoices.paypal.downloadCopyPdf")}</Button>
            )}
```
変更後:
```
            {invoice.paypal_copy_pdf_at && invoice.invoice_number && (
              <Button variant="secondary" size="md" onClick={handleDownloadCopyPdf} loading={pdfSaving === "copy"} disabled={pdfSaving !== ""} data-testid="invoice-detail-download-copy-pdf">{t("invoices.paypal.downloadCopyPdf")}</Button>
            )}
```

### 2-2. frontend/src/pages/quote-detail/QuoteDetailPage.tsx（Edit 4 か所）

(a) 変更前:
```
import { api, ApiError } from "../../lib/api";
```
変更後:
```
import { api, ApiError } from "../../lib/api";
import { saveBlob } from "../../lib/saveBlob";
```

(b) 変更前:
```
  const [fxLoading, setFxLoading] = useState(false);
```
変更後:
```
  const [fxLoading, setFxLoading] = useState(false);
  const [pdfSaving, setPdfSaving] = useState(false);
```

(c) 変更前:
```
  const handleDownloadPdf = () => {
    window.open(`/api/quotes/${id}/pdf`, "_blank");
  };
```
変更後:
```
  // design-pdf §3: 札つきで blob を読み、サーバーと同じ名前で保存する（金型 InvoiceCreatedModal.tsx と同じ）
  const handleDownloadPdf = async () => {
    if (!quote?.quote_code) return;
    setError("");
    setPdfSaving(true);
    try {
      const blob = await api.getBlob(`/quotes/${id}/pdf`);
      saveBlob(blob, `${quote.quote_code}.pdf`);
    } catch {
      setError(t("common.downloadFailed"));
    } finally {
      setPdfSaving(false);
    }
  };
```

(d) 変更前:
```
            <Button variant="secondary" size="sm" layoutClassName="field-h-md" onClick={handleDownloadPdf}>{t("invoices.snapshot.downloadPdf")}</Button>
```
変更後:
```
            {quote.quote_code && (
              <Button variant="secondary" size="sm" layoutClassName="field-h-md" onClick={() => void handleDownloadPdf()} loading={pdfSaving} disabled={pdfSaving} data-testid="quote-detail-download-pdf">{t("invoices.snapshot.downloadPdf")}</Button>
            )}
```

### 2-3. frontend/src/pages/invoice-detail/InvoiceDetailPage.test.tsx（新規・Write。下の全文）

```tsx
// design-pdf K1・K2・K4・K5: 請求書の詳細画面の PDF は札つきで読み、番号の名前で保存する
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InvoiceDetailPage from './InvoiceDetailPage';
import en from '../../locales/en.json';
import { queryClient } from '../../lib/query/apiQuery';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), getBlob: vi.fn() }));
const saveBlobMock = vi.hoisted(() => vi.fn());
vi.mock('../../lib/saveBlob', () => ({ saveBlob: saveBlobMock }));
vi.mock('../../lib/api', async (importOriginal) => ({ ...(await importOriginal<typeof import('../../lib/api')>()), api: mock }));
let instance = createInstance();
const tr = (key: string) => String(instance.t(key));
const PDF = new Blob(['%PDF'], { type: 'application/pdf' });

function invoice(over: Record<string, unknown> = {}) {
  return {
    id: 9, invoice_number: 'IN-0009-01', quote_id: null, company_id: 4, currency: 'USD',
    subtotal: 100, shipping_fee: 0, tax_amount: 0, total_amount: 100,
    exchange_rate_jpy: null, exchange_rate_usd: null, amount_jpy: null, amount_usd: null,
    payment_fee_charged: null, payment_method: null, status: 'issued', branch_number: null, erp_key: null,
    issued_at: null, due_date: null, paid_at: null, voided_at: null, void_reason: null, notes: null,
    created_at: '2026-11-24T00:00:00Z', items: [], ship_to_snapshot: null, bill_to_snapshot: null,
    duty_amount: null, fx_rate_snapshot: null, paypal_order_id: 'ORDER-1', paypal_approval_url: null,
    payment_fee: null, paypal_invoicer_view_url: null, paypal_copy_pdf_at: '2026-11-24T00:00:00Z',
    ...over,
  };
}

function setup(data: Record<string, unknown>) {
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/me/permissions') return { permissions: ['invoices.view'] };
    if (url === '/invoices/9') return data;
    if (url === '/invoices/9/paypal-disputes') return [];
    throw new Error(`Unexpected GET ${url}`);
  });
  render(
    <I18nextProvider i18n={instance}>
      <MemoryRouter initialEntries={['/invoices/9']}>
        <Routes><Route path="/invoices/:id" element={<InvoiceDetailPage />} /></Routes>
      </MemoryRouter>
    </I18nextProvider>,
  );
}

beforeEach(async () => {
  vi.resetAllMocks(); instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  vi.stubGlobal('open', vi.fn(() => { throw new Error('Unexpected window.open'); }));
  mock.post.mockImplementation(() => { throw new Error('Unexpected post'); });
});
afterEach(() => { cleanup(); queryClient.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('InvoiceDetailPage PDF (design-pdf)', () => {
  it('K1: saves the invoice PDF read with the token under the invoice number', async () => {
    mock.getBlob.mockResolvedValue(PDF);
    setup(invoice());
    fireEvent.click(await screen.findByTestId('invoice-detail-download-pdf'));
    await waitFor(() => expect(saveBlobMock).toHaveBeenCalledTimes(1));
    expect(mock.getBlob).toHaveBeenCalledTimes(1);
    expect(mock.getBlob).toHaveBeenCalledWith('/invoices/9/pdf');
    expect(saveBlobMock).toHaveBeenCalledWith(PDF, 'IN-0009-01.pdf');
  });

  it('K2: saves the PayPal copy PDF under the number with the copy suffix', async () => {
    mock.getBlob.mockResolvedValue(PDF);
    setup(invoice());
    fireEvent.click(await screen.findByTestId('invoice-detail-download-copy-pdf'));
    await waitFor(() => expect(saveBlobMock).toHaveBeenCalledTimes(1));
    expect(mock.getBlob).toHaveBeenCalledWith('/invoices/9/paypal-copy-pdf');
    expect(saveBlobMock).toHaveBeenCalledWith(PDF, 'IN-0009-01-paypal-copy.pdf');
  });

  it('K4: shows the download failure message when the PDF cannot be read', async () => {
    mock.getBlob.mockRejectedValue(new Error('HTTP 404'));
    setup(invoice());
    fireEvent.click(await screen.findByTestId('invoice-detail-download-pdf'));
    expect(await screen.findByText(tr('common.downloadFailed'))).toBeTruthy();
    expect(saveBlobMock).not.toHaveBeenCalled();
  });

  it('K5: hides both PDF buttons when the invoice has no number', async () => {
    setup(invoice({ invoice_number: null }));
    expect(await screen.findByText(tr('invoices.paypal.recordTitle'))).toBeTruthy();
    expect(screen.queryByTestId('invoice-detail-download-pdf')).toBeNull();
    expect(screen.queryByTestId('invoice-detail-download-copy-pdf')).toBeNull();
  });
});
```

### 2-4. frontend/src/pages/quote-detail/QuoteDetailPage.test.tsx（新規・Write。下の全文）

```tsx
// design-pdf K3・K4・K5: 見積もりの詳細画面の PDF は札つきで読み、見積番号の名前で保存する
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import QuoteDetailPage from './QuoteDetailPage';
import en from '../../locales/en.json';
import { queryClient } from '../../lib/query/apiQuery';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), getBlob: vi.fn() }));
const saveBlobMock = vi.hoisted(() => vi.fn());
vi.mock('../../lib/saveBlob', () => ({ saveBlob: saveBlobMock }));
vi.mock('../../lib/api', async (importOriginal) => ({ ...(await importOriginal<typeof import('../../lib/api')>()), api: mock }));
let instance = createInstance();
const tr = (key: string) => String(instance.t(key));
const PDF = new Blob(['%PDF'], { type: 'application/pdf' });

function quote(over: Record<string, unknown> = {}) {
  return {
    id: 5, quote_code: 'QT-0005', company_id: 4, currency: 'JPY',
    subtotal: 100, shipping_fee: 0, tax_amount: 0, total_amount: 100,
    status: 'draft', validity_date: null, notes: null, created_at: '2026-11-24T00:00:00Z', items: [],
    ...over,
  };
}

function setup(data: Record<string, unknown>) {
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/me/permissions') return { permissions: ['invoices.view'] };
    if (url === '/quotes/5') return data;
    throw new Error(`Unexpected GET ${url}`);
  });
  render(
    <I18nextProvider i18n={instance}>
      <MemoryRouter initialEntries={['/quotes/5']}>
        <Routes><Route path="/quotes/:id" element={<QuoteDetailPage />} /></Routes>
      </MemoryRouter>
    </I18nextProvider>,
  );
}

beforeEach(async () => {
  vi.resetAllMocks(); instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  vi.stubGlobal('open', vi.fn(() => { throw new Error('Unexpected window.open'); }));
  mock.post.mockImplementation(() => { throw new Error('Unexpected post'); });
});
afterEach(() => { cleanup(); queryClient.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('QuoteDetailPage PDF (design-pdf)', () => {
  it('K3: saves the quote PDF read with the token under the quote code', async () => {
    mock.getBlob.mockResolvedValue(PDF);
    setup(quote());
    fireEvent.click(await screen.findByTestId('quote-detail-download-pdf'));
    await waitFor(() => expect(saveBlobMock).toHaveBeenCalledTimes(1));
    expect(mock.getBlob).toHaveBeenCalledTimes(1);
    expect(mock.getBlob).toHaveBeenCalledWith('/quotes/5/pdf');
    expect(saveBlobMock).toHaveBeenCalledWith(PDF, 'QT-0005.pdf');
  });

  it('K4: shows the download failure message when the PDF cannot be read', async () => {
    mock.getBlob.mockRejectedValue(new Error('HTTP 500'));
    setup(quote());
    fireEvent.click(await screen.findByTestId('quote-detail-download-pdf'));
    expect(await screen.findByText(tr('common.downloadFailed'))).toBeTruthy();
    expect(saveBlobMock).not.toHaveBeenCalled();
  });

  it('K5: hides the PDF button when the quote has no code', async () => {
    setup(quote({ quote_code: null }));
    expect(await screen.findByText(`${tr('quotes.title')} — #5`)).toBeTruthy();
    expect(screen.queryByTestId('quote-detail-download-pdf')).toBeNull();
  });
});
```

## 3. 手順

手順1 作業場所（枝は origin に在る。new-worktree.sh で作ってから origin の枝を取り込む）
    cd /home/user/salesanchor && git fetch origin main release/invoice-detail-pdf-download
    cd /home/user/salesanchor && git branch --list release/invoice-detail-pdf-download
    cd /home/user/salesanchor && bash scripts/new-worktree.sh release/invoice-detail-pdf-download --claude
    cd /home/user/salesanchor && git worktree list
    cd ~/worktrees/salesanchor/release-invoice-detail-pdf-download && git merge --no-edit origin/release/invoice-detail-pdf-download; echo "rel exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-detail-pdf-download && git merge-base --is-ancestor origin/release/invoice-detail-pdf-download HEAD; echo "is-ancestor exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-detail-pdf-download && git rev-parse HEAD
  new-worktree.sh が「既に在る」で止まったら、作業場所の名前を報告して BLOCKED: で停止する。rel exit か is-ancestor exit が 0 でなければ停止する。

手順2 実装前点検（§0-3）
    cd ~/worktrees/salesanchor/release-invoice-detail-pdf-download && git hash-object frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx frontend/src/pages/quote-detail/QuoteDetailPage.tsx
    cd ~/worktrees/salesanchor/release-invoice-detail-pdf-download && ls frontend/src/pages/invoice-detail/InvoiceDetailPage.test.tsx frontend/src/pages/quote-detail/QuoteDetailPage.test.tsx 2>/dev/null | wc -l
    cd ~/worktrees/salesanchor/release-invoice-detail-pdf-download && git grep -nE "window\.open\(\s*[\`'\"]/api" -- frontend/src | wc -l
  先頭12字が §0-3 と違う・2行目が 0 でない・3行目が 3 でなければ実装せず BLOCKED: で停止する。

手順3 §2 のとおりに編集する（既存ファイルは Edit ツール、新しい試験は Write ツール）。§2 の変更前の文が見つからない・2か所以上ある場合は、推測で選ばず BLOCKED: で停止する。

手順4 画面の検査と試験
    cd ~/worktrees/salesanchor/release-invoice-detail-pdf-download/frontend && npm ci --no-audit --no-fund 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-detail-pdf-download/frontend && npx vitest run src/pages/invoice-detail src/pages/quote-detail src/pages/invoice-create src/lib/saveBlob.test.ts 2>&1 | tail -30
    cd ~/worktrees/salesanchor/release-invoice-detail-pdf-download/frontend && npm run check:all 2>&1 | tail -40
    cd ~/worktrees/salesanchor/release-invoice-detail-pdf-download && git grep -nE "window\.open\(\s*[\`'\"]/api" -- frontend/src | wc -l
  最後の数は 0（K6）。落ちたら §4 を見る。

手順5 差分の確かめ
    cd ~/worktrees/salesanchor/release-invoice-detail-pdf-download && git status --short | head -30
    cd ~/worktrees/salesanchor/release-invoice-detail-pdf-download && git diff --stat | tail -20
  §1 に無いファイルが変わっていたら、何かを報告に書いて BLOCKED: で停止する。

手順6 記録と送る
    cd ~/worktrees/salesanchor/release-invoice-detail-pdf-download && git add frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx frontend/src/pages/quote-detail/QuoteDetailPage.tsx frontend/src/pages/invoice-detail/InvoiceDetailPage.test.tsx frontend/src/pages/quote-detail/QuoteDetailPage.test.tsx
    cd ~/worktrees/salesanchor/release-invoice-detail-pdf-download && git status --short | head -30
    cd ~/worktrees/salesanchor/release-invoice-detail-pdf-download && git -c user.name=shingo-cc -c user.email=shingo-cc@users.noreply.github.com commit -m "fix(invoice): save detail-page PDFs with the auth token (card-pdf)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
    cd ~/worktrees/salesanchor/release-invoice-detail-pdf-download && git log --oneline -3
    cd ~/worktrees/salesanchor/release-invoice-detail-pdf-download && git push -u origin release/invoice-detail-pdf-download
    cd ~/worktrees/salesanchor/release-invoice-detail-pdf-download && git log --oneline origin/release/invoice-detail-pdf-download -1
  commit が見張りに止められたら、言い換えて回避せず、止めた文をそのまま報告して BLOCKED: で停止する。push が拒まれたら force で押さず停止する。

## 4. 想定される分かれ道

- 試験で `Unexpected GET <道>` が出る（ページか部品が他の道を読む）→ その道を setup の mock に最小の値（一覧なら []・物なら {}）で1行足し、足した道を報告する。§2-1・§2-2 の本体は変えない。
- 試験で PageLayout などが別の文脈（Provider）を求めて落ちる → frontend/src/pages/invoice-create/InvoiceCreatePage.test.tsx の包み方（render の形）に合わせて直し、直した点を報告する。
- K5 の見積もりの見出しの文が合わない → 画面に出た見出しの文を報告し、`quotes.title` の en の値と照らして試験の期待だけ直す。
- check:all の i18n・UI の金型の検査で落ちる → 出力の最後 40 行を貼って BLOCKED: で停止（新しいキーも部品も足していないので、落ちる想定は無い）。
- 上のどれにも当たらない失敗 → 推測で直さず、出力の最後 40 行を貼って BLOCKED: で停止。

## 5. 報告の形

1 行目: `RECEIVED invoice-detail-pdf HEAD=` に手順1 の rev-parse の40桁を続ける
続けて手順ごとに: 実行したコマンドと出力の最後の行（試験は passed/failed の数の行）。手順2 の指紋は全部貼る。手順6 の git log の2つの出力を貼る。
最後の行: `DONE` か `BLOCKED:`（後ろに理由）か `NEEDS_DECISION:`（後ろに聞きたいこと） のどれか1つ。

## 6. 委任の定型

- この指示書に無いことはしない。PR は作らない（Opus が作る）。マージしない。本番に触らない。
- 消す命令・force push・枝の削除はしない。
- 見張り（hook）に止められたら言い換えて回避しない。止めた文をそのまま報告して停止する。
- 迷ったら推測で進めず停止して NEEDS_DECISION: で聞く。

END OF CARD

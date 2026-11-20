# card-R6: 請求書を作ったあとに小さな枠を出す（invoice-create-portfolio 便 R6）

作成: Opus（Planner）2026-11-20。設計: docs/handoff/invoice-create-portfolio/design-v2.md 第9版 §3-6・§4 R6・K15・§11（第9版の足し分はこのカードと一緒に審査する）。
実装承認: PO は 2026-11-17 に p1〜p8 を「見本どおり」と決め、PR マージ・デプロイまでの完走を委ねた（ccopusgo の委任の範囲）。2026-11-20 回答「1」でボタン名は今の「請求書を作成」のまま、2026-11-20 回答「1」で作成のあとは PDF を埋め込まず小さな枠に「PDF を保存」「詳細へ」「閉じる」を出すと決めた。
枝: release/invoice-portfolio-r6-modal（origin/main から）。移行（migrations/）なし・deploy.yml なし・scripts/ なし・backend なし。
基準: origin/main d4bea69c185acd74fcbb2e8eda57ada9183718be（置き換える2ファイルの指紋は P1 で照合する）。

## 受領確認（最初の報告の 1 行目に書く）

`RECEIVED invoice-portfolio-R6 HEAD=` に続けて、手順1 の後の `git rev-parse HEAD` の 40 桁を書く。

## 0. Opus の決めごと（根拠つき）

- D1 作成が成功したら詳細画面へ移らない。今の `navigate(`/invoices/${inv.id}`)`（origin/main の frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:184）を、作った請求書を覚える `setCreated(...)` に替え、小さな枠 InvoiceCreatedModal を出す（design-v2 §3-6・K15）。
- D2 PDF は枠に埋め込まない。印刷のボタンも作らない。本番の守りの設定 nginx/nginx.conf:96（`default-src 'self'`・frame-src／object-src なし）が blob の PDF の iframe・object・embed を止める（Opus が 2026-11-20 に手元で確かめた）。守りの設定は変えない（PO 2026-11-20「1」）。
- D3 「PDF を保存」は今の道 GET /invoices/{id}/pdf（backend/app/routers/invoices.py:1133・権限 invoices.view）を今の `api.getBlob`（frontend/src/lib/api.ts:305）で読み、新しい小さな関数 `saveBlob` で `a[download]` を押して保存する。ファイル名は POST の返事の `invoice_number` に `.pdf`（道が付ける名前と同じ。invoices.py:1156・:1183）。番号が空なら「PDF を保存」を出さない（`IN-…` の形を画面で作り直さない）。
- D4 権限は今の `usePermissions()`（frontend/src/hooks/usePermissions.ts）で読む。`invoices.view` が無ければ「PDF を保存」を出さず、案内の知らせを出す。枠は作成のあとにだけ置くので、作成の画面を描く今の試験の権限の答えは変わらない。
- D5 金型は Modal・Button・Callout・ReadOnlyField・Stack だけ（ADR-144）。枠の下段のボタンは DutyRuleFormModal.tsx:166 と同じ `footer` の書き方。背景を押しても閉じない（`dismissOnOverlay={false}`）。Esc と右上の×は「閉じる」と同じ。
- D6 「閉じる」は今の「クリア」と同じ `clearAll()` で空の請求書に戻す。「詳細へ」は `/invoices/{id}` へ移る。
- D7 文言は ja.json・en.json の invoiceForm に 7 キーを足す（両方同じキー。ADR-027）。「閉じる」は今の `common.close`。失敗と権限の文は「次にすること」を含める（check-error-text-next-action.js の決まり）。
- D8 今ある18ファイルの同じ保存の書き方（ConditionsPage.tsx など）は書き換えない（別の作業）。詳細画面の PDF のボタンが本番で 404 になる件（InvoiceDetailPage.tsx:154-156・QuoteDetailPage.tsx:97）も触らない（別テーマ）。

## 0-1. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・commit は git log で確かめる | ○（§3） |
| guards/03-file.md | 編集は Edit ツール。新しいファイルは Write ツール。プレースホルダを残さない | ○（§2） |
| guards/04-worktree.md | new-worktree.sh で作る・出力をパイプに通さない・実在は git worktree list で確かめる・push は -u 付き | ○（手順1・手順8） |
| guards/10-executor.md | 散文で頼まない。手順はコマンドで書く | ○（§3） |

## 0-2. 実装前点検（手順2 で流す。外れたら実装せず停止して BLOCKED: で報告）

- P1 Edit する2ファイルの指紋（git hash-object）が次と同じ（この順）:
  - `6ff5ad7a852d51f3647bb33f26838d527bbe7dff` frontend/src/pages/invoice-create/InvoiceCreatePage.tsx
  - `c86d92ea00bdad9443323335a0b64186548b9e8f` frontend/src/pages/invoice-create/InvoiceCreatePage.test.tsx
- P2 frontend/src/lib/saveBlob.ts・frontend/src/lib/saveBlob.test.ts・frontend/src/pages/invoice-create/InvoiceCreatedModal.tsx が無い（`ls` の数え 0）。
- P3 `"createdTitle"` が ja.json・en.json に無い（python の出力 `False False`）。
- P4 Modal.tsx・Callout.tsx・ReadOnlyField.tsx・Button.tsx・Stack.tsx が frontend/src/components/ にあり、frontend/src/hooks/usePermissions.ts がある（6）。

## 1. 触るファイル

- frontend/src/lib/saveBlob.ts（新規）
- frontend/src/lib/saveBlob.test.ts（新規）
- frontend/src/pages/invoice-create/InvoiceCreatedModal.tsx（新規）
- frontend/src/pages/invoice-create/InvoiceCreatePage.tsx（Edit）
- frontend/src/pages/invoice-create/InvoiceCreatePage.test.tsx（Edit）
- frontend/src/locales/ja.json（Edit）
- frontend/src/locales/en.json（Edit）

## 2. 変更

### 2-1. frontend/src/lib/saveBlob.ts（新規・Write）

```ts
/**
 * Blob に名前を付けて保存する（同じ出所の blob の URL を a[download] で押す）。
 * invoice-create-portfolio design-v2 §3-6（R6）。同じ書き方の今あるページは R6 では書き換えない。
 */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  try {
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
  } finally {
    anchor.remove();
    URL.revokeObjectURL(url);
  }
}
```

### 2-2. frontend/src/lib/saveBlob.test.ts（新規・Write）

```ts
// invoice-create-portfolio R6: saveBlob（design-v2 §3-6・K15）
import { afterEach, describe, expect, it, vi } from 'vitest';
import { saveBlob } from './saveBlob';

const originalURL = URL;
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('saveBlob', () => {
  it('clicks one attached download link with the file name, then removes it and revokes the URL', () => {
    const create = vi.fn().mockReturnValue('blob:fixture');
    const revoke = vi.fn();
    class MockURL extends originalURL { static createObjectURL = create; static revokeObjectURL = revoke; }
    vi.stubGlobal('URL', MockURL);
    const clicks: { href: string; download: string; attached: boolean }[] = [];
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
      clicks.push({ href: this.getAttribute('href') ?? '', download: this.download, attached: document.body.contains(this) });
    });
    const blob = new Blob(['%PDF'], { type: 'application/pdf' });
    saveBlob(blob, 'IN-0011-01.pdf');
    expect(create).toHaveBeenCalledExactlyOnceWith(blob);
    expect(clicks).toEqual([{ href: 'blob:fixture', download: 'IN-0011-01.pdf', attached: true }]);
    expect(document.querySelectorAll('a[download]').length).toBe(0);
    expect(revoke).toHaveBeenCalledExactlyOnceWith('blob:fixture');
  });
});
```

### 2-3. frontend/src/pages/invoice-create/InvoiceCreatedModal.tsx（新規・Write）

```tsx
/**
 * 請求書を作ったあとに出す小さな枠（invoice-create-portfolio design-v2 §3-6・K15。便 R6）。
 *
 * PDF は画面に埋め込まない（本番の守りの設定 nginx/nginx.conf:96 が blob の PDF の埋め込みを止めるため）。
 * 「PDF を保存」は GET /invoices/{id}/pdf（権限 invoices.view）を blob で読み、{請求書番号}.pdf で保存する。
 * 番号の正本はサーバー（POST /invoices の返事の invoice_number）。番号が空なら保存のボタンを出さない。
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { saveBlob } from "../../lib/saveBlob";
import { usePermissions } from "../../hooks/usePermissions";
import { Button } from "../../components/Button";
import { Callout } from "../../components/Callout";
import { Modal } from "../../components/Modal";
import { ReadOnlyField } from "../../components/ReadOnlyField";
import { Stack } from "../../components/Stack";

/** POST /invoices の返事のうち、枠が使う 2 つ（backend/app/schemas/invoice.py InvoiceResponse） */
export interface CreatedInvoice {
  id: number;
  invoice_number: string | null;
}

interface InvoiceCreatedModalProps {
  invoice: CreatedInvoice;
  onClose: () => void;
  onOpenDetail: () => void;
}

export function InvoiceCreatedModal({ invoice, onClose, onOpenDetail }: InvoiceCreatedModalProps) {
  const { t } = useTranslation();
  const { hasPermission, loading } = usePermissions();
  const [pdfSaving, setPdfSaving] = useState(false);
  const [pdfError, setPdfError] = useState(false);
  const canView = !loading && hasPermission("invoices.view");
  const canSavePdf = canView && invoice.invoice_number !== null && invoice.invoice_number !== "";

  const savePdf = async () => {
    if (!canSavePdf) return;
    setPdfError(false);
    setPdfSaving(true);
    try {
      const blob = await api.getBlob(`/invoices/${invoice.id}/pdf`);
      saveBlob(blob, `${invoice.invoice_number}.pdf`);
    } catch {
      setPdfError(true);
    } finally {
      setPdfSaving(false);
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={t("invoiceForm.createdTitle")}
      size="sm"
      dismissOnOverlay={false}
      footer={
        <>
          <Button type="button" variant="secondary" size="md" onClick={onClose} disabled={pdfSaving} data-testid="invoice-created-close">
            {t("common.close")}
          </Button>
          <Button type="button" variant="secondary" size="md" onClick={onOpenDetail} disabled={pdfSaving} data-testid="invoice-created-detail">
            {t("invoiceForm.createdOpenDetail")}
          </Button>
          {canSavePdf && (
            <Button
              type="button"
              variant="primary"
              size="md"
              loading={pdfSaving}
              disabled={pdfSaving}
              onClick={() => void savePdf()}
              data-testid="invoice-created-save-pdf"
            >
              {t("invoiceForm.createdSavePdf")}
            </Button>
          )}
        </>
      }
    >
      <Stack gap="4">
        <div data-testid="invoice-created-number">
          <ReadOnlyField label={t("invoiceForm.createdNumber")} value={invoice.invoice_number} />
        </div>
        <Callout variant="info" title={t("invoiceForm.createdDraftNote")} />
        {!loading && !canView && (
          <div data-testid="invoice-created-pdf-no-permission">
            <Callout variant="info" title={t("invoiceForm.createdPdfNoPermission")} />
          </div>
        )}
        {pdfError && (
          <div data-testid="invoice-created-pdf-error">
            <Callout variant="warning" title={t("invoiceForm.createdPdfError")} />
          </div>
        )}
      </Stack>
    </Modal>
  );
}
```

### 2-4. frontend/src/pages/invoice-create/InvoiceCreatePage.tsx（Edit 5 か所）

(a) 変更前:
```
 * 「在庫表から／見積から」の切り替えは無い（p8）。見積から作るのは見積の詳細画面の道。
```
変更後:
```
 * 作成のあとは詳細画面へ移らず、小さな枠（InvoiceCreatedModal。design-v2 §3-6・R6）で「PDF を保存」「詳細へ」「閉じる」を出す。
 * 「在庫表から／見積から」の切り替えは無い（p8）。見積から作るのは見積の詳細画面の道。
```

(b) 変更前:
```
import { InvoiceShipToSection } from "./InvoiceShipToSection";
```
変更後:
```
import { InvoiceShipToSection } from "./InvoiceShipToSection";
import { InvoiceCreatedModal, type CreatedInvoice } from "./InvoiceCreatedModal";
```

(c) 変更前:
```
  const [saving, setSaving] = useState(false);
```
変更後:
```
  const [saving, setSaving] = useState(false);
  // 作った請求書（作成のあとの枠を出す間だけ。§3-6・K15）
  const [created, setCreated] = useState<CreatedInvoice | null>(null);
```

(d) 変更前:
```
      const inv = await api.post<{ id: number }>("/invoices", {
```
変更後:
```
      const inv = await api.post<CreatedInvoice>("/invoices", {
```

(e) 変更前:
```
      navigate(`/invoices/${inv.id}`);
    } catch (e) {
```
変更後:
```
      setCreated({ id: inv.id, invoice_number: inv.invoice_number });
    } catch (e) {
```

(f) 変更前:
```
        onCancel={() => setClearOpen(false)}
      />
```
変更後:
```
        onCancel={() => setClearOpen(false)}
      />

      {created !== null && (
        <InvoiceCreatedModal
          invoice={created}
          onClose={() => {
            setCreated(null);
            clearAll();
          }}
          onOpenDetail={() => navigate(`/invoices/${created.id}`)}
        />
      )}
```

### 2-5. frontend/src/pages/invoice-create/InvoiceCreatePage.test.tsx（Edit 8 か所）

(a) 変更前:
```
// invoice-create-portfolio R5: 請求書作成ページを見本の見た目と操作に作り直した（design-v2 §3-1〜§3-6・§6 K1〜K3・K5〜K14・K19〜K21）
```
変更後:
```
// invoice-create-portfolio R5: 請求書作成ページを見本の見た目と操作に作り直した（design-v2 §3-1〜§3-6・§6 K1〜K3・K5〜K14・K19〜K21）
// invoice-create-portfolio R6: 作成のあとの小さな枠（design-v2 §3-6・K15）
```

(b) 変更前:
```
const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
```
変更後:
```
const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), getBlob: vi.fn() }));
const saveBlobMock = vi.hoisted(() => vi.fn());
vi.mock('../../lib/saveBlob', () => ({ saveBlob: saveBlobMock }));
```

(c) 変更前:
```
let shippingAnswer: Record<string, unknown>;
```
変更後:
```
let shippingAnswer: Record<string, unknown>;
let permissions: string[];
```

(d) 変更前:
```
const submit = () => screen.getByTestId('invoice-create-submit') as HTMLButtonElement;
```
変更後:
```
const submit = () => screen.getByTestId('invoice-create-submit') as HTMLButtonElement;
/** 送料「無し」と支払方法を選んで作成し、作成のあとの枠を返す（K15） */
async function createAndOpenDialog() {
  await openWithProduct();
  await waitFor(() => expect(optionValues('invoice-payment-select')).toContain('bank:3'));
  fireEvent.change(screen.getByTestId('invoice-payment-select'), { target: { value: 'bank:3' } });
  fireEvent.click(screen.getByTestId('invoice-shipping-none'));
  await waitFor(() => expect(screen.getByTestId('invoice-total-amount').textContent).not.toBe(tr('invoiceForm.notComputed')), SLOW);
  fireEvent.click(submit());
  return screen.findByRole('dialog');
}
```

(e) 変更前:
```
  shippingAnswer = { results: [liveRate, staticRate], live_error: null };
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/me/permissions') return { permissions: ['invoices.create'] };
```
変更後:
```
  shippingAnswer = { results: [liveRate, staticRate], live_error: null };
  permissions = ['invoices.create'];
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/me/permissions') return { permissions };
```

(f) 変更前:
```
    if (url === '/invoices') return { id: 11 };
```
変更後:
```
    if (url === '/invoices') return { id: 11, invoice_number: 'IN-0011-01' };
```

(g) 変更前:
```
  mock.delete.mockImplementation(() => { throw new Error('Unexpected delete'); });
```
変更後:
```
  mock.delete.mockImplementation(() => { throw new Error('Unexpected delete'); });
  mock.getBlob.mockImplementation(async (url: string) => {
    if (url === '/invoices/11/pdf') return new Blob(['%PDF'], { type: 'application/pdf' });
    throw new Error(`Unexpected getBlob ${url}`);
  });
```

(h) 変更前:
```
  it('create: "no shipping" + payment sends the exact body once and opens the detail page', async () => {
```
変更後:
```
  it('K15: create sends the exact body once, stays on the page and shows the created dialog', async () => {
```

(i) 変更前:
```
    await waitFor(() => expect(screen.getByTestId('location').textContent).toBe('/invoices/11'));
```
変更後:
```
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByTestId('invoice-created-number').textContent).toContain('IN-0011-01');
    expect(screen.getByTestId('location').textContent).toBe('/invoices/new');
```

(j) 変更前:
```
  it('create is refused with a reason while shipping is not chosen', async () => {
```
変更後:
```
  it('K15: "Save PDF" reads the PDF once and saves it as the invoice number', async () => {
    permissions = ['invoices.create', 'invoices.view'];
    const dialog = await createAndOpenDialog();
    fireEvent.click(await within(dialog).findByTestId('invoice-created-save-pdf'));
    await waitFor(() => expect(saveBlobMock).toHaveBeenCalledTimes(1));
    expect(mock.getBlob.mock.calls).toEqual([['/invoices/11/pdf']]);
    expect(saveBlobMock.mock.calls[0][0]).toBeInstanceOf(Blob);
    expect(saveBlobMock.mock.calls[0][1]).toBe('IN-0011-01.pdf');
    expect(posts('/invoices').length).toBe(1);
    expect(screen.getByRole('dialog')).toBeTruthy();
  });

  it('K15: a PDF failure shows a notice and keeps the dialog open', async () => {
    permissions = ['invoices.create', 'invoices.view'];
    mock.getBlob.mockImplementation(async () => { throw new Error('PDF failed'); });
    const dialog = await createAndOpenDialog();
    fireEvent.click(await within(dialog).findByTestId('invoice-created-save-pdf'));
    expect((await screen.findByTestId('invoice-created-pdf-error')).textContent).toContain(tr('invoiceForm.createdPdfError'));
    expect(saveBlobMock).not.toHaveBeenCalled();
    expect(screen.getByRole('dialog')).toBeTruthy();
  });

  it('K15: "Open details" moves to the detail page', async () => {
    const dialog = await createAndOpenDialog();
    fireEvent.click(within(dialog).getByTestId('invoice-created-detail'));
    await waitFor(() => expect(screen.getByTestId('location').textContent).toBe('/invoices/11'));
  });

  it('K15: "Close" empties the form and closes the dialog', async () => {
    const dialog = await createAndOpenDialog();
    fireEvent.click(within(dialog).getByTestId('invoice-created-close'));
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    expect(rows().length).toBe(12);
    expect((screen.getByTestId('invoice-item-state-0') as HTMLSelectElement).value).toBe('');
    expect(screen.getByTestId('location').textContent).toBe('/invoices/new');
  });

  it('K15: without invoices.view the save button is not shown and the reason is', async () => {
    const dialog = await createAndOpenDialog();
    expect((await within(dialog).findByTestId('invoice-created-pdf-no-permission')).textContent).toContain(tr('invoiceForm.createdPdfNoPermission'));
    expect(within(dialog).queryByTestId('invoice-created-save-pdf')).toBeNull();
    expect(mock.getBlob).not.toHaveBeenCalled();
  });

  it('create is refused with a reason while shipping is not chosen', async () => {
```

### 2-6. frontend/src/locales/ja.json（Edit）

変更前:
```
    "createNotReady": "送料・支払方法・合計がそろうまで作れません。上の欄を確かめてください",
```
変更後:
```
    "createNotReady": "送料・支払方法・合計がそろうまで作れません。上の欄を確かめてください",
    "createdTitle": "請求書を作成しました",
    "createdNumber": "請求書番号",
    "createdDraftNote": "下書きで保存しました。送付と確定は詳細画面で行います",
    "createdSavePdf": "PDF を保存",
    "createdOpenDetail": "詳細へ",
    "createdPdfNoPermission": "PDF の保存には請求書を見る権限が要ります。必要なら会社の管理者に連絡してください",
    "createdPdfError": "PDF を保存できませんでした。少し待ってもう一度お試しください",
```

### 2-7. frontend/src/locales/en.json（Edit）

変更前:
```
    "createNotReady": "The invoice cannot be created until shipping, payment and totals are ready. Please check the fields above",
```
変更後:
```
    "createNotReady": "The invoice cannot be created until shipping, payment and totals are ready. Please check the fields above",
    "createdTitle": "Invoice created",
    "createdNumber": "Invoice number",
    "createdDraftNote": "Saved as a draft. Send and confirm it on the detail page",
    "createdSavePdf": "Save PDF",
    "createdOpenDetail": "Open details",
    "createdPdfNoPermission": "Saving the PDF needs permission to view invoices. Contact your company administrator if you need it",
    "createdPdfError": "Could not save the PDF. Please wait a moment and try again",
```

## 3. 手順（1つずつ流し、出力を報告に書く）

手順1 作業場所
    cd /home/user/salesanchor && git fetch origin main
    cd /home/user/salesanchor && git branch --list release/invoice-portfolio-r6-modal
    cd /home/user/salesanchor && bash scripts/new-worktree.sh release/invoice-portfolio-r6-modal
    cd /home/user/salesanchor && git worktree list
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal && git merge-base --is-ancestor origin/main HEAD; echo "main exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal && git rev-parse HEAD
  期待: 2行目の出力が空（空でなければ `BLOCKED: 手順1 枝が既にある`）。4行目に `worktrees/salesanchor/release-invoice-portfolio-r6-modal` が出る。5行目 `main exit=0`。

手順2 実装前点検 P1〜P4
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal && git hash-object frontend/src/pages/invoice-create/InvoiceCreatePage.tsx frontend/src/pages/invoice-create/InvoiceCreatePage.test.tsx
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal && ls frontend/src/lib/saveBlob.ts frontend/src/lib/saveBlob.test.ts frontend/src/pages/invoice-create/InvoiceCreatedModal.tsx 2>/dev/null | grep -c .
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal && python3 -c "import json; print('createdTitle' in json.load(open('frontend/src/locales/ja.json'))['invoiceForm'], 'createdTitle' in json.load(open('frontend/src/locales/en.json'))['invoiceForm'])"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal && ls frontend/src/components/Modal.tsx frontend/src/components/Callout.tsx frontend/src/components/ReadOnlyField.tsx frontend/src/components/Button.tsx frontend/src/components/Stack.tsx frontend/src/hooks/usePermissions.ts | grep -c .
  期待（命令の順）: 1行目は P1 の2つの指紋がその順に出る。続いて 0、`False False`、6。

手順3 §2 の変更をする（2-1〜2-3 は Write ツール、2-4〜2-7 は Edit ツール。§2 のコードの囲み（```）の中身だけを書く）

手順4 道具を入れる
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal/frontend && npm ci --no-audit --no-fund 2>&1 | tail -3
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal/frontend && set -o pipefail && npm run generate:api-types 2>&1 | tail -3; echo "gen exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal/frontend && ls src/api/generated/schema.d.ts
  期待: 2行目 `gen exit=0`。3行目に `src/api/generated/schema.d.ts` が出る（生成物は .gitignore で記録の対象外）。外れたら `BLOCKED: 手順4 型の生成`。

手順5 形と試験（どれも作業場所の frontend で流す）
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/lib/saveBlob.test.ts src/pages/invoice-create/InvoiceCreatePage.test.tsx src/components/BillToCountryGuidance.test.tsx src/components/CommerceNavigationButtonMigration.test.tsx src/components/CommerceSubmitButtonMigration.test.tsx src/components/AllLegacyButtonDynamicMigration.test.tsx src/lib/query/batch3cPages.test.tsx 2>&1 | tail -15
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal/frontend && set -o pipefail && npx tsc -p tsconfig.json 2>&1 | tail -15; echo "tsc exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal/frontend && set -o pipefail && npx eslint --max-warnings=0 src/lib/saveBlob.ts src/lib/saveBlob.test.ts src/pages/invoice-create/InvoiceCreatedModal.tsx src/pages/invoice-create/InvoiceCreatePage.tsx src/pages/invoice-create/InvoiceCreatePage.test.tsx 2>&1 | tail -15; echo "eslint exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal/frontend && npm run check:i18n-missing-keys 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal/frontend && npm run check:error-text-next-action 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal/frontend && npm run check:page-size 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal/frontend && npm run check:page-layout 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal/frontend && npm run check:page-folder 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal/frontend && npm run check:loading-clear 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal/frontend && npm run check:status-direct-writes 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal/frontend && npm run check:jsx-emoji 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal/frontend && set -o pipefail && node scripts/check-css-var-fallbacks.js 2>&1 | tail -5; echo "css-var exit=$?"
  期待: 1行目は failed 0（7ファイルの試験がすべて passed。本数はそのまま書く）。2行目 `tsc exit=0`。3行目 `eslint exit=0` で、誤りも警告も 0。最後の行は `css-var exit=0`。4行目以降はどれも誤りなしで終わる（✅ や 0 件の表示。❌・終了の失敗が出ない）。

手順6 変えたファイル
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal && git status --short | tail -15
  期待: §1 の 7 ファイルだけ（` M` が Edit の 4、`??` が新規の 3）。.claude-pipeline/active-work.d/ の未追跡は除く。ほかが出たら `BLOCKED: 範囲外のファイル`。

手順7 記録
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal && git add frontend/src/lib/saveBlob.ts frontend/src/lib/saveBlob.test.ts frontend/src/pages/invoice-create/InvoiceCreatedModal.tsx frontend/src/pages/invoice-create/InvoiceCreatePage.tsx frontend/src/pages/invoice-create/InvoiceCreatePage.test.tsx frontend/src/locales/ja.json frontend/src/locales/en.json && git status --short | tail -15
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal && git config user.name "shingo-cc" && git config user.email "shingo-cc@users.noreply.github.com" && git commit -q -m "feat(invoice): show a small dialog after creating an invoice (invoice-portfolio R6)" && git log --oneline -1 | tail -1

手順8 UI の決まりの検査（commit の後。origin/main と比べる）と送り出し
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal && set -o pipefail && BASE_SHA=origin/main HEAD_SHA=HEAD node scripts/check-ui-governance.js 2>&1 | tail -15; echo "ui-gov exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal && git push -u origin release/invoice-portfolio-r6-modal 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r6-modal && git rev-parse HEAD
  期待: 1行目 `ui-gov exit=0`（新規 ui-allow 0件）。外れたら push せず `BLOCKED: UI の決まりの検査`。push は --no-verify・force を付けない。push が止められたら言い換えず `BLOCKED: push`。

## 4. 想定される分かれ道

- 停止する（その場で停止し、それまでの出力と §5 の報告を返して終わる。別のやり方を試さない）:
  - P1〜P4 のどれかが外れた → `BLOCKED: P番号`（P1 は違った指紋のファイル名を書く）。
  - §2 の Edit の変更前の文が見つからない・2 か所以上当たる → `BLOCKED: ファイル名 変更前の文`。
  - 手順4 の npm ci・型の生成が失敗した → 最後の 3 行を貼って `BLOCKED: 手順4`。
  - 手順5 で試験・型・eslint・検査のどれかが落ちた → 試験や検査やコードを直さず、落ちた試験の名前と最後の出力（30 行まで）を貼って `BLOCKED: 手順5 何行目`。カードからの書き写し間違い（字・字下げ）が出力から分かるときだけ直してよい。直したら何をどう直したかを書く。
  - 手順8 の UI の決まりの検査が 0 以外 → `BLOCKED: UI の決まりの検査`。
  - 手順7 の commit が記録の前の自動点検に止められた → 止めた理由の原文を貼って `BLOCKED: 手順7`（--no-verify を付けない・試験を書き換えない）。
- 警告も止める理由になる: eslint の警告（warning）が 1 件でも出たら手順5 の失敗として扱う。

## 5. 報告の形

- 宛先: クラウドの実行の最後の返事。ファイルに書かない。
- 1 行目: 受領確認の行。2 行目: 「本報告はカード 便R6 請求書を作ったあとに小さな枠を出す の実行結果である」。
- 手順1・2・5・6・7・8 の出力をそのまま貼る（要約しない）。全体で 2000 字を超えるときは、手順5・手順8 を優先して貼り、ほかは期待と合ったかを ○× で書く。
- 停止したときは「停止した手順番号／最後に実行したコマンド／停止した理由」の 3 点。
- 秘密の値・鍵・パスワードは貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`。

## 6. 委任の定型

- sleep しない。CI の結果は Opus が見る。PR は作らない（Opus が作る）。
- ファイルの編集は Edit ツール、新しいファイルは Write ツール。ヒアドキュメントで書かない。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。

## 7. 触らない範囲

§1 以外のファイル。frontend/src/components/ の金型の中身、tokens.css・index.css、frontend/src/lib/api.ts、frontend/src/hooks/usePermissions.ts、InvoiceDetailPage.tsx・QuoteDetailPage.tsx（詳細画面の PDF のボタンは別テーマ）、ConditionsPage.tsx ほか今ある保存の書き方、nginx/nginx.conf（守りの設定）、backend/、migrations/・deploy.yml・scripts/。

END OF CARD

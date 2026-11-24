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

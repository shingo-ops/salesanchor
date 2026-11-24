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

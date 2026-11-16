// invoice-create-portfolio 便D K23: 下書きの請求書で支払方法を選び直す
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { InvoicePaymentPicker } from './InvoicePaymentPicker';
import en from '../../locales/en.json';
import { queryClient } from '../../lib/query/apiQuery';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../../lib/api', async (importOriginal) => ({ ...(await importOriginal<typeof import('../../lib/api')>()), api: mock }));
let instance = createInstance();

const CTX = {
  company_id: 4, ship_to: null, bill_to: null, contact_name: null, contact_email: null,
  issuer_region: 'JP', origin_country_code: 'JP', destination_country_code: 'US', destination_postal_code: null,
  currencies: ['USD'], fx_rates: [], default_currency: 'USD', currency: 'JPY',
  payment_methods: [
    { id: 3, method_type: 'bank', display_name: 'Main bank', wise_currency: null },
    { id: 4, method_type: 'wise', display_name: 'Wise USD', wise_currency: 'USD' },
  ],
  tax_rate_percent: null, incoterms: 'DAP',
};

beforeEach(async () => {
  vi.resetAllMocks(); instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/invoices/draft-context?invoice_id=9') return CTX;
    throw new Error(`Unexpected GET ${url}`);
  });
  mock.post.mockImplementation(() => { throw new Error('Unexpected post'); });
  mock.patch.mockResolvedValue({});
  mock.delete.mockImplementation(() => { throw new Error('Unexpected delete'); });
});
afterEach(() => { cleanup(); queryClient.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

function view(onSaved = vi.fn(), currency = 'JPY') {
  render(<I18nextProvider i18n={instance}><InvoicePaymentPicker invoiceId="9" currency={currency} onSaved={onSaved} /></I18nextProvider>);
  return onSaved;
}

describe('InvoicePaymentPicker (K23)', () => {
  it('offers only the rows that fit the invoice currency and saves the reference only', async () => {
    const onSaved = view();
    const select = (await screen.findByTestId('invoice-detail-payment-select')) as HTMLSelectElement;
    await waitFor(() => expect(Array.from(select.options).map((o) => o.value)).toEqual(['', 'bank:3']));
    expect((screen.getByTestId('invoice-detail-payment-save') as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(select, { target: { value: 'bank:3' } });
    fireEvent.click(screen.getByTestId('invoice-detail-payment-save'));
    await waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
    expect(mock.patch).toHaveBeenCalledTimes(1);
    expect(mock.patch).toHaveBeenCalledWith('/invoices/9', { payment_method_ref: { method_type: 'bank', id: 3 } });
  });

  it('shows the Wise row when its currency matches', async () => {
    view(vi.fn(), 'USD');
    const select = (await screen.findByTestId('invoice-detail-payment-select')) as HTMLSelectElement;
    await waitFor(() => expect(Array.from(select.options).map((o) => o.value)).toEqual(['', 'bank:3', 'wise:4']));
  });

  it('says there is nothing to choose when no row fits', async () => {
    mock.get.mockImplementation(async () => ({ ...CTX, payment_methods: [] }));
    view();
    expect(await screen.findByTestId('invoice-detail-payment-none')).toBeTruthy();
    expect(screen.queryByTestId('invoice-detail-payment-select')).toBeNull();
  });

  it('shows the save error and does not call onSaved', async () => {
    mock.patch.mockRejectedValue(new Error('Save failed'));
    const onSaved = view();
    const select = (await screen.findByTestId('invoice-detail-payment-select')) as HTMLSelectElement;
    await waitFor(() => expect(select.options.length).toBe(2));
    fireEvent.change(select, { target: { value: 'bank:3' } });
    fireEvent.click(screen.getByTestId('invoice-detail-payment-save'));
    expect(await screen.findByText('Save failed')).toBeTruthy();
    expect(onSaved).not.toHaveBeenCalled();
  });
});

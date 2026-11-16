// invoice-create-portfolio 便D: 請求書作成ページは選ぶだけで作れる（design.md §3-2・§8 K1〜K5・K8・K10・K12）
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InvoiceCreatePage from './InvoiceCreatePage';
import en from '../../locales/en.json';
import { queryClient } from '../../lib/query/apiQuery';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../../lib/api', async (importOriginal) => ({ ...(await importOriginal<typeof import('../../lib/api')>()), api: mock }));
let instance = createInstance();
const tr = (key: string, opts?: Record<string, unknown>) => String(instance.t(key, opts));
function Location() { const value = useLocation(); return <output data-testid="location">{value.pathname}</output>; }
function view() {
  render(<I18nextProvider i18n={instance}><MemoryRouter initialEntries={['/invoices/new']}><InvoiceCreatePage /><Location /></MemoryRouter></I18nextProvider>);
}

const CTX_PATH = '/invoices/draft-context?company_id=4&contact_id=5';
const summary = { id: 7, quote_code: 'Q-7', company_id: 4, currency: 'USD', total_amount: 20, status: 'approved', created_at: '' };
const detail = { id: 7, quote_code: 'Q-7', company_id: 4, contact_id: 5, currency: 'USD', items: [{ product_id: 2, product_name: 'Card', quantity: 2, unit_price: 10, weight: 0.5 }] };
const company = { id: 4, company_code: 'C-4', name: 'Company' };
const contact = { id: 5, company_id: 4, surname: 'Buyer', given_name: 'One', surname_en: null, given_name_en: null, email: 'buyer@example.com', is_primary_contact: true };
const address = { company_name: 'Buyer Inc', billing_display_name: null, label: null, postal_code: '10001', address: '1 Main St', city: 'New York', state: 'NY', country: 'US', phone: null };
let ctx: Record<string, unknown>;
function baseCtx() {
  return {
    company_id: 4, ship_to: address, bill_to: { ...address, address: '2 Bill St' }, contact_name: 'One Buyer', contact_email: 'buyer@example.com',
    issuer_region: 'JP', origin_country_code: 'JP', destination_country_code: 'US', destination_postal_code: '10001',
    currencies: ['JPY', 'USD'], fx_rates: [{ currency: 'USD', rate: 150, fetched_at: '2026-11-15' }], default_currency: 'USD', currency: null,
    payment_methods: [
      { id: 3, method_type: 'bank', display_name: 'Main bank', wise_currency: null },
      { id: 4, method_type: 'wise', display_name: 'Wise USD', wise_currency: 'USD' },
    ],
    tax_rate_percent: null, incoterms: 'DAP',
  };
}
type PreviewBody = { currency: string; items: Array<{ quantity: number; unit_price: number }>; shipping: { mode: string; fee?: number } | null };
function previewFor(body: PreviewBody) {
  const subtotal = body.items.reduce((s, i) => s + i.quantity * i.unit_price, 0);
  if (body.shipping === null) {
    return { currency: body.currency, subtotal: String(subtotal), shipping_fee: null, tax_amount: '0', tax_rate_percent: null, duty_amount: '0', duty_label: null, duty_components: [], total_amount: null, uncomputed: ['shipping_required'], incoterms: 'DAP' };
  }
  const fee = body.shipping.mode === 'calculate' ? body.shipping.fee ?? 0 : 0;
  return { currency: body.currency, subtotal: String(subtotal), shipping_fee: String(fee), tax_amount: '0', tax_rate_percent: null, duty_amount: '0', duty_label: null, duty_components: [], total_amount: String(subtotal + fee), uncomputed: [], incoterms: 'DAP' };
}
const rate = { carrier: 'FedEx', zone: 'A', fee: 33.333, currency: 'USD', source: 'fedex_live', service_type: 'FEDEX_IP', service_name: 'International Priority', transit_days: 3, delivery_timestamp: null };

beforeEach(async () => {
  vi.resetAllMocks(); instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  ctx = baseCtx();
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/me/permissions') return { permissions: ['invoices.create'] };
    if (url === '/quotes?status=approved') return [summary];
    if (url === '/quotes/7') return detail;
    if (url === '/companies?per_page=100') return [company];
    if (url === '/contacts?company_id=4&per_page=100') return [contact];
    if (url === CTX_PATH) return ctx;
    throw new Error(`Unexpected GET ${url}`);
  });
  mock.post.mockImplementation(async (url: string, body: unknown) => {
    if (url === '/invoices/preview') return previewFor(body as PreviewBody);
    if (url === '/invoices') return { id: 11 };
    if (url === '/shipping/calculate') return { results: [rate], cheapest: rate, live_error: null, rate_precision: 'exact' };
    throw new Error(`Unexpected POST ${url}`);
  });
  mock.patch.mockImplementation(() => { throw new Error('Unexpected patch'); });
  mock.delete.mockImplementation(() => { throw new Error('Unexpected delete'); });
});
afterEach(() => { cleanup(); queryClient.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

async function loadQuote() {
  view();
  fireEvent.click(await screen.findByTestId('invoice-edit-from-quote-7'));
  expect(await screen.findByDisplayValue('Card')).toBeTruthy();
  await screen.findByTestId('invoice-ship-to-address');
}
const optionValues = (testId: string) => Array.from((screen.getByTestId(testId) as HTMLSelectElement).options).map((o) => o.value);
const previewCalls = () => mock.post.mock.calls.filter(([url]) => url === '/invoices/preview').map(([, body]) => body as PreviewBody);
const postedInvoice = () => mock.post.mock.calls.filter(([url]) => url === '/invoices').map(([, body]) => body);

describe('InvoiceCreatePage (invoice-create-portfolio bin D)', () => {
  it('K1: ship-to, bill-to and contact are shown read-only', async () => {
    await loadQuote();
    const shipTo = screen.getByTestId('invoice-ship-to');
    expect(shipTo.querySelectorAll('input, textarea').length).toBe(0);
    expect(within(shipTo).getByTestId('invoice-ship-to-address').textContent).toContain('1 Main St');
    expect(within(shipTo).getByTestId('invoice-bill-to-address').textContent).toContain('2 Bill St');
    expect(within(shipTo).getByTestId('invoice-contact-line').textContent).toContain('buyer@example.com');
  });

  it('K2: currency and payment choices come from draft-context', async () => {
    await loadQuote();
    await waitFor(() => expect(optionValues('invoice-currency-select')).toEqual(['', 'JPY', 'USD']));
    expect((screen.getByTestId('invoice-currency-select') as HTMLSelectElement).value).toBe('USD');
    expect(optionValues('invoice-payment-select')).toEqual(['', 'bank:3', 'wise:4']);
    expect(screen.getByTestId('invoice-fx-line').textContent).toContain('150');
  });

  it('K3: switching USD to JPY removes the Wise USD row and clears the choice', async () => {
    await loadQuote();
    await waitFor(() => expect(optionValues('invoice-payment-select')).toContain('wise:4'));
    fireEvent.change(screen.getByTestId('invoice-payment-select'), { target: { value: 'wise:4' } });
    expect((screen.getByTestId('invoice-payment-select') as HTMLSelectElement).value).toBe('wise:4');
    fireEvent.change(screen.getByTestId('invoice-currency-select'), { target: { value: 'JPY' } });
    await waitFor(() => expect(optionValues('invoice-payment-select')).toEqual(['', 'bank:3']));
    expect((screen.getByTestId('invoice-payment-select') as HTMLSelectElement).value).toBe('');
  });

  it('K4/K8: before shipping is chosen the total is not computed and the reason is shown', async () => {
    await loadQuote();
    expect(screen.getByTestId('invoice-total-amount')).toBeTruthy();
    expect(await screen.findByTestId('invoice-uncomputed-shipping_required')).toBeTruthy();
    expect(screen.getByTestId('invoice-total-amount').textContent).toBe(tr('invoiceForm.notComputed'));
    expect(screen.getByTestId('invoice-total-shipping').textContent).toBe(tr('invoiceForm.notComputed'));
    expect((screen.getByTestId('invoice-create-submit') as HTMLButtonElement).disabled).toBe(true);
    expect(screen.queryAllByRole('spinbutton').filter((el) => !(el.getAttribute('data-testid') ?? '').startsWith('invoice-item-row-'))).toEqual([]);
  });

  it('K5: a FedEx quote with locked fields sets carrier, fee and total', async () => {
    await loadQuote();
    await waitFor(() => expect((screen.getByTestId('invoice-shipping-quote') as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(screen.getByTestId('invoice-shipping-quote'));
    const dialog = await screen.findByRole('dialog');
    const field = (id: string) => dialog.querySelector(`#${id}`) as HTMLInputElement;
    expect(field('fedex-origin').value).toBe('JP');
    expect(field('fedex-dest-cc').value).toBe('US');
    expect(field('fedex-dest-postal').value).toBe('10001');
    expect(Number(field('fedex-weight').value)).toBe(1);
    for (const id of ['fedex-origin', 'fedex-dest-cc', 'fedex-dest-postal', 'fedex-weight']) expect(field(id).readOnly).toBe(true);
    fireEvent.click(within(dialog).getByRole('button', { name: tr('fedexRateModal.getQuote') }));
    fireEvent.click(await within(dialog).findByRole('button', { name: tr('fedexRateModal.selectRate') }));
    expect(mock.post).toHaveBeenCalledWith('/shipping/calculate', expect.objectContaining({ country_code: 'US', weight_kg: 1, origin_country_code: 'JP', destination_postal_code: '10001' }));
    await waitFor(() => expect(previewCalls().some((b) => b.shipping?.mode === 'calculate' && b.shipping.fee === 33.33)).toBe(true));
    await waitFor(() => expect(screen.queryByTestId('invoice-uncomputed')).toBeNull());
    expect(screen.getByTestId('invoice-total-amount').textContent).not.toBe(tr('invoiceForm.notComputed'));
    expect((screen.getByTestId('invoice-shipping-select') as HTMLSelectElement).value).toBe('calculate');
  });

  it('K5: changing item weight after choosing a rate asks to choose again', async () => {
    await loadQuote();
    await waitFor(() => expect((screen.getByTestId('invoice-shipping-quote') as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(screen.getByTestId('invoice-shipping-quote'));
    const dialog = await screen.findByRole('dialog');
    fireEvent.click(within(dialog).getByRole('button', { name: tr('fedexRateModal.getQuote') }));
    fireEvent.click(await within(dialog).findByRole('button', { name: tr('fedexRateModal.selectRate') }));
    await waitFor(() => expect((screen.getByTestId('invoice-shipping-select') as HTMLSelectElement).value).toBe('calculate'));
    fireEvent.change(screen.getByTestId('invoice-item-row-0-qty'), { target: { value: '3' } });
    expect(await screen.findByTestId('invoice-shipping-stale')).toBeTruthy();
    expect((screen.getByTestId('invoice-create-submit') as HTMLButtonElement).disabled).toBe(true);
  });

  it('K10: section headings are in the designed order', async () => {
    await loadQuote();
    const headings = Array.from(document.querySelectorAll('form h3')).map((h) => h.textContent);
    expect(headings).toEqual([tr('invoiceForm.sectionShipTo'), tr('invoiceForm.sectionPaymentTotals'), tr('quotes.items'), tr('invoiceForm.sectionActions')]);
  });

  it('K12: "no shipping" + payment creates with the exact body and opens the detail page', async () => {
    await loadQuote();
    await waitFor(() => expect(optionValues('invoice-payment-select')).toContain('bank:3'));
    fireEvent.change(screen.getByTestId('invoice-payment-select'), { target: { value: 'bank:3' } });
    fireEvent.change(screen.getByTestId('invoice-shipping-select'), { target: { value: 'none' } });
    await waitFor(() => expect((screen.getByTestId('invoice-create-submit') as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(screen.getByTestId('invoice-create-submit'));
    await waitFor(() => expect(screen.getByTestId('location').textContent).toBe('/invoices/11'));
    expect(postedInvoice()).toEqual([{
      company_id: 4, contact_id: 5, currency: 'USD', shipping: { mode: 'none' }, payment_method_ref: { method_type: 'bank', id: 3 }, notes: null,
      items: [{ product_id: 2, product_name: 'Card', name_en: null, condition: null, unit: null, quantity: 2, unit_price: 10, weight: 0.5 }],
    }]);
    const sent = postedInvoice()[0] as Record<string, unknown>;
    expect('shipping_fee' in sent).toBe(false);
    expect('tax_amount' in sent).toBe(false);
  });

  it('no payment destinations: create is allowed without one and the profile link is offered', async () => {
    ctx = { ...baseCtx(), payment_methods: [] };
    await loadQuote();
    expect(await screen.findByTestId('invoice-open-tenant-profile')).toBeTruthy();
    fireEvent.change(screen.getByTestId('invoice-shipping-select'), { target: { value: 'none' } });
    await waitFor(() => expect((screen.getByTestId('invoice-create-submit') as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(screen.getByTestId('invoice-create-submit'));
    await waitFor(() => expect(postedInvoice().length).toBe(1));
    expect((postedInvoice()[0] as Record<string, unknown>).payment_method_ref).toBeNull();
  });

  it('issuer region missing: create stays disabled and the company page link is shown', async () => {
    ctx = { ...baseCtx(), issuer_region: null };
    await loadQuote();
    expect(await screen.findByTestId('invoice-open-company-for-bill-to')).toBeTruthy();
    fireEvent.change(screen.getByTestId('invoice-shipping-select'), { target: { value: 'none' } });
    await waitFor(() => expect(previewCalls().some((b) => b.shipping?.mode === 'none')).toBe(true));
    expect((screen.getByTestId('invoice-create-submit') as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByTestId('invoice-open-company-for-bill-to'));
    expect(screen.getByTestId('location').textContent).toBe('/crm/companies/4');
  });

  it('clear resets the form to the starting state', async () => {
    await loadQuote();
    fireEvent.click(screen.getByTestId('invoice-clear'));
    expect(screen.queryByDisplayValue('Card')).toBeNull();
    expect(screen.queryByTestId('invoice-ship-to')).toBeNull();
    expect((screen.getByTestId('invoice-create-submit') as HTMLButtonElement).disabled).toBe(true);
  });
});

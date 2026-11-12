// ADR-1061 便2-2c2a: 請求先の国が無くて請求書を作れなかったとき、取引先の画面へ移るボタンを出す
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InvoiceCreatePage from '../pages/invoice-create/InvoiceCreatePage';
import QuoteDetailPage from '../pages/quote-detail/QuoteDetailPage';
import en from '../locales/en.json';
import { ApiError } from '../lib/api';
import { queryClient } from '../lib/query/apiQuery';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../lib/api', async (importOriginal) => ({ ...(await importOriginal<typeof import('../lib/api')>()), api: mock }));
let instance = createInstance();
const tr = (key: string) => String(instance.t(key));
function Location() { const value = useLocation(); return <output data-testid="location">{value.pathname}</output>; }
function wrap(node: React.ReactNode, entries = ['/start']) { return <I18nextProvider i18n={instance}><MemoryRouter initialEntries={entries}>{node}<Location /></MemoryRouter></I18nextProvider>; }
function routed(node: React.ReactNode, path: string, entries: string[]) { return <I18nextProvider i18n={instance}><MemoryRouter initialEntries={entries}><Routes><Route path={path} element={node} /><Route path="*" element={<Location />} /></Routes></MemoryRouter></I18nextProvider>; }

const summary = { id: 7, quote_code: 'Q-7', company_id: 4, currency: 'USD', total_amount: 10, status: 'approved', created_at: '' };
const detail = { id: 7, quote_code: 'Q-7', company_id: 4, contact_id: 5, currency: 'USD', items: [{ product_id: 2, product_name: 'Card', quantity: 1, unit_price: 10, weight: null }] };
const approvedQuote = { id: 7, quote_code: 'Q-7', company_id: 4, currency: 'USD', subtotal: 10, shipping_fee: null, tax_amount: null, total_amount: 10, status: 'approved', validity_date: null, notes: null, created_at: '', items: [] };
const company = { id: 4, company_code: 'C-4', name: 'Company' };
const contact = { id: 5, company_id: 4, surname: 'Buyer', given_name: 'One', surname_en: null, given_name_en: null, email: 'buyer@example.com', is_primary_contact: true };

beforeEach(async () => {
  vi.resetAllMocks(); instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/me/permissions') return { permissions: ['invoices.create'] };
    if (url === '/quotes?status=approved') return [summary];
    if (url === '/quotes/7') return detail;
    if (url === '/companies?per_page=100') return [company];
    if (url === '/contacts?company_id=4&per_page=100') return [contact];
    throw new Error(`Unexpected GET ${url}`);
  });
  mock.post.mockImplementation(() => { throw new Error('Unexpected post'); });
  mock.patch.mockResolvedValue({});
  mock.delete.mockImplementation(() => { throw new Error('Unexpected delete'); });
});
afterEach(() => { cleanup(); queryClient.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

async function loadQuoteIntoCreatePage() {
  render(wrap(<InvoiceCreatePage />));
  fireEvent.click(await screen.findByTestId('invoice-edit-from-quote-7'));
  expect(await screen.findByDisplayValue('Card')).toBeTruthy();
  expect(await screen.findByRole('option', { name: /Buyer/ })).toBeTruthy();
}

describe('bill-to country guidance (ADR-1061 bin2-2c2a)', () => {
  it('create page: shows the reason and a button that opens the customer page', async () => {
    await loadQuoteIntoCreatePage();
    mock.post.mockRejectedValue(new ApiError(tr('apiError.billToCountry'), 422, 'bill_to_country'));
    fireEvent.click(screen.getByRole('button', { name: tr('invoices.createBtn') }));
    expect(await screen.findByText(tr('apiError.billToCountry'))).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: tr('invoices.openCompanyForBillTo') }));
    expect(screen.getByTestId('location').textContent).toBe('/crm/companies/4');
  });

  it('create page: another error does not show the button', async () => {
    await loadQuoteIntoCreatePage();
    mock.post.mockRejectedValue(new ApiError('Other failure', 400, 'something_else'));
    fireEvent.click(screen.getByRole('button', { name: tr('invoices.createBtn') }));
    expect(await screen.findByText('Other failure')).toBeTruthy();
    expect(screen.queryByRole('button', { name: tr('invoices.openCompanyForBillTo') })).toBeNull();
  });

  it('quote detail: converting shows the reason and a button that opens the customer page', async () => {
    mock.get.mockImplementation(async (url: string) => {
      if (url === '/me/permissions') return { permissions: ['invoices.create'] };
      if (url === '/quotes/7') return approvedQuote;
      throw new Error(`Unexpected GET ${url}`);
    });
    mock.post.mockRejectedValue(new ApiError(tr('apiError.billToCountry'), 422, 'bill_to_country'));
    render(routed(<QuoteDetailPage />, '/quotes/:id', ['/quotes/7']));
    fireEvent.click(await screen.findByRole('button', { name: tr('quotes.convertToInvoice') }));
    expect(await screen.findByText(tr('apiError.billToCountry'))).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: tr('invoices.openCompanyForBillTo') }));
    expect((await screen.findByTestId('location')).textContent).toBe('/crm/companies/4');
  });
});

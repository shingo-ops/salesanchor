import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InventoryPage from '../pages/inventory/InventoryPage';
import InvoiceCreatePage from '../pages/invoice-create/InvoiceCreatePage';
import InvoiceDetailPage from '../pages/invoice-detail/InvoiceDetailPage';
import ProductEditPage from '../pages/products/ProductEditPage';
import ProductsPage from '../pages/products/ProductsPage';
import QuoteCreatePage from '../pages/quote-create/QuoteCreatePage';
import QuotesPage from '../pages/quotes/QuotesPage';
import en from '../locales/en.json';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../lib/api', () => ({ api: mock }));
let instance = createInstance();
const tr = (key: string) => String(instance.t(key));
let permissions: string[] = [];
function Location() { const value = useLocation(); return <output data-testid="location">{value.pathname}</output>; }
function wrap(node: React.ReactNode, entries = ['/start']) { return <I18nextProvider i18n={instance}><MemoryRouter initialEntries={entries}>{node}<Location /></MemoryRouter></I18nextProvider>; }
function routed(node: React.ReactNode, path: string, entries: string[]) { return <I18nextProvider i18n={instance}><MemoryRouter initialEntries={entries}><Routes><Route path={path} element={node} /><Route path="*" element={<Location />} /></Routes></MemoryRouter></I18nextProvider>; }
function deferred() { let resolve!: (v: unknown) => void; let reject!: (e: Error) => void; const promise = new Promise((r, j) => { resolve = r; reject = j; }); return { promise, resolve, reject }; }

beforeEach(async () => {
  vi.resetAllMocks(); permissions = ['products.create', 'quotes.create', 'invoices.void']; instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/me/permissions') return { permissions };
    if (url === '/products/tcg-types') return [];
    if (url === '/products/attribute-options') return {};
    if (url.startsWith('/products?')) return [];
    if (url === '/quotes') return [];
    if (url === '/companies?per_page=100') return [];
    throw new Error(`Unexpected GET ${url}`);
  });
  mock.post.mockImplementation(() => { throw new Error('Unexpected post'); });
  mock.patch.mockResolvedValue({});
  mock.delete.mockImplementation(() => { throw new Error('Unexpected delete'); });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('commerce navigation Button migration contracts', () => {
  it('paginates inventory with exact GETs and disabled pending boundaries', async () => {
    const row = { id: 1, product_id: 2, product_name: 'Card', name_en: null, category: null, mark: null, condition: 'new', unit: null, offer_type: 'in_stock', ship_timing: null, supplier_id: 3, supplier_name: 'Supplier', unit_price: 10, quantity: 1, tcg_type: 'pokemon_booster_box', offered_at: '', release_date: null };
    const page1Url = '/inventory?page=1&per_page=50&sort=release_date&order=desc&tcg_type=pokemon_booster_box';
    const page2Url = '/inventory?page=2&per_page=50&sort=release_date&order=desc&tcg_type=pokemon_booster_box';
    const page2 = deferred();
    mock.get.mockImplementation(async (url: string) => {
      if (url === '/me/permissions') return { permissions };
      if (url === '/products/tcg-types') return [];
      if (url === page1Url) return { items: [row], total: 51, page: 1, per_page: 50 };
      if (url === page2Url) return page2.promise;
      throw new Error(`Unexpected GET ${url}`);
    });
    render(wrap(<InventoryPage />));
    const next = await screen.findByTestId('inventory-next') as HTMLButtonElement;
    const prev = screen.getByTestId('inventory-prev') as HTMLButtonElement;
    expect(prev.disabled).toBe(true); expect(next.disabled).toBe(false);
    fireEvent.click(next);
    await waitFor(() => expect(mock.get).toHaveBeenCalledWith('/inventory?page=2&per_page=50&sort=release_date&order=desc&tcg_type=pokemon_booster_box'));
    expect(next.disabled).toBe(true); expect(prev.disabled).toBe(true);
    await act(async () => page2.resolve({ items: [row], total: 51, page: 2, per_page: 50 }));
    await waitFor(() => expect((screen.getByTestId('inventory-prev') as HTMLButtonElement).disabled).toBe(false));
    expect((screen.getByTestId('inventory-next') as HTMLButtonElement).disabled).toBe(true);
    const page2Reads = mock.get.mock.calls.filter(c => c[0] === page2Url).length;
    fireEvent.click(screen.getByTestId('inventory-next'));
    expect(mock.get.mock.calls.filter(c => c[0] === page2Url)).toHaveLength(page2Reads);
    const page1Reads = mock.get.mock.calls.filter(c => c[0] === page1Url).length;
    fireEvent.click(screen.getByTestId('inventory-prev'));
    await waitFor(() => expect(mock.get.mock.calls.filter(c => c[0] === page1Url)).toHaveLength(page1Reads + 1));
  });

  it('loads an approved quote exactly, blocks a duplicate while pending, and exposes rejection', async () => {
    const summary = { id: 7, quote_code: 'Q-7', company_id: 4, currency: 'USD', total_amount: 10, status: 'approved', created_at: '' };
    const detail = { id: 7, quote_code: 'Q-7', company_id: 4, contact_id: 5, currency: 'USD', items: [{ product_id: 2, product_name: 'Card', quantity: 1, unit_price: 10, weight: null }] };
    const pending = deferred();
    mock.get.mockImplementation(async (url: string) => {
      if (url === '/quotes?status=approved') return [summary];
      if (url === '/quotes/7') return pending.promise;
      if (url === '/companies?per_page=100') return [];
      throw new Error(`Unexpected GET ${url}`);
    });
    render(wrap(<InvoiceCreatePage />));
    const load = await screen.findByTestId('invoice-edit-from-quote-7') as HTMLButtonElement;
    fireEvent.click(load); fireEvent.click(load); expect(mock.get.mock.calls.filter(c => c[0] === '/quotes/7')).toHaveLength(1); expect(load.disabled).toBe(true);
    await act(async () => pending.resolve(detail));
    expect(await screen.findByText(/Q-7/)).toBeTruthy();
    cleanup(); const beforeRetry = mock.get.mock.calls.filter(c => c[0] === '/quotes/7').length; let attempts = 0; mock.get.mockImplementation(async (url: string) => { if (url === '/quotes?status=approved') return [summary]; if (url === '/quotes/7') { attempts += 1; if (attempts === 1) throw new Error('Quote load failed'); return detail; } if (url === '/companies?per_page=100') return []; throw new Error(`Unexpected GET ${url}`); });
    render(wrap(<InvoiceCreatePage />)); let retry = await screen.findByTestId('invoice-edit-from-quote-7'); fireEvent.click(retry); expect(await screen.findByText('Quote load failed')).toBeTruthy();
    retry = screen.getByTestId('invoice-edit-from-quote-7'); fireEvent.click(retry); expect(await screen.findByDisplayValue('Card')).toBeTruthy(); expect((await screen.findByTestId('invoice-source-quote')).textContent).toContain('Q-7'); expect(mock.get.mock.calls.filter(c => c[0] === '/quotes/7')).toHaveLength(beforeRetry + 2);
  });

  it('closes invoice void UI with zero writes', async () => {
    const invoice = { id: 3, invoice_number: 'INV-3', quote_id: null, company_id: 1, currency: 'USD', subtotal: 1, shipping_fee: 0, tax_amount: 0, total_amount: 1, exchange_rate_jpy: null, exchange_rate_usd: null, amount_jpy: null, amount_usd: null, payment_method: null, status: 'draft', branch_number: null, erp_key: null, issued_at: null, due_date: null, paid_at: null, voided_at: null, void_reason: null, notes: null, created_at: '', items: [], ship_to_snapshot: null, bill_to_snapshot: null, duty_amount: null, fx_rate_snapshot: null, paypal_order_id: null, paypal_approval_url: null, payment_fee: null, paypal_invoicer_view_url: null, paypal_copy_pdf_at: null };
    mock.get.mockImplementation(async (url: string) => { if (url === '/me/permissions') return { permissions }; if (url === '/invoices/3') return invoice; if (url === '/invoices/3/paypal-disputes') return []; throw new Error(`Unexpected GET ${url}`); });
    render(routed(<InvoiceDetailPage />, '/invoices/:id', ['/invoices/3']));
    fireEvent.click(await screen.findByRole('button', { name: tr('invoices.voidAction') }));
    expect(screen.getByPlaceholderText(tr('invoices.voidReasonPlaceholder'))).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: tr('common.cancel') }));
    expect(screen.queryByPlaceholderText(tr('invoices.voidReasonPlaceholder'))).toBeNull(); expect(mock.post).not.toHaveBeenCalled();
  });

  it.each([
    ['invoice profile', <InvoiceCreatePage />, '/invoices/new', ['/invoices/new'], 'nav.tenantProfile', '/management-center/tenant-profile'],
    ['product back', <ProductEditPage />, '/admin/products/new', ['/before', '/admin/products/new'], 'common.cancel', '/before'],
    ['new product', <ProductsPage />, '/admin/products', ['/admin/products'], 'products.newProduct', '/admin/products/new'],
    ['quote cancel', <QuoteCreatePage />, '/quotes/new', ['/quotes/new'], 'common.cancel', '/quotes'],
    ['new quote', <QuotesPage />, '/quotes', ['/quotes'], 'quotes.newQuote', '/quotes/new'],
  ] as const)('%s preserves exact navigation', async (_name, Page, path, entries, label, destination) => {
    render(routed(Page, path, [...entries]));
    fireEvent.click(await screen.findByRole('button', { name: tr(label) }));
    expect((await screen.findByTestId('location')).textContent).toBe(destination);
  });

  it('cancels invoice creation to the exact invoices route', async () => {
    mock.get.mockImplementation(async (url: string) => { if (url === '/quotes?status=approved') return []; if (url === '/companies?per_page=100') return []; throw new Error(`Unexpected GET ${url}`); });
    render(routed(<InvoiceCreatePage />, '/invoices/new', ['/invoices/new']));
    fireEvent.click(screen.getByTestId('invoice-mode-inventory'));
    fireEvent.click(await screen.findByRole('button', { name: tr('common.cancel') }));
    expect((await screen.findByTestId('location')).textContent).toBe('/invoices');
  });

  it('blocks ProductEdit cancel navigation while a save is pending', async () => {
    const pending = deferred(); mock.post.mockReturnValue(pending.promise);
    render(routed(<ProductEditPage />, '/admin/products/new', ['/before', '/admin/products/new']));
    await screen.findByTestId('product-edit-save'); fireEvent.change(document.querySelector('input[required]')!, { target: { value: 'Product' } });
    fireEvent.click(screen.getByTestId('product-edit-save'));
    const cancel = screen.getByRole('button', { name: tr('common.cancel') }) as HTMLButtonElement;
    await waitFor(() => expect(cancel.disabled).toBe(true)); fireEvent.click(cancel);
    expect(screen.queryByTestId('location')).toBeNull(); expect(mock.post).toHaveBeenCalledTimes(1);
    await act(async () => pending.reject(new Error('Save failed'))); expect(await screen.findByText('Save failed')).toBeTruthy();
  });

  it('opens and cancels the FedEx dialog without quote or rate writes', async () => {
    render(wrap(<QuoteCreatePage />));
    fireEvent.click(screen.getByTestId('fedex-estimate-btn'));
    const dialog = screen.getByRole('dialog'); expect(within(dialog).getByText(tr('fedexRateModal.title'))).toBeTruthy();
    fireEvent.click(within(dialog).getByRole('button', { name: tr('common.cancel') }));
    expect(screen.queryByRole('dialog')).toBeNull(); expect(mock.post).not.toHaveBeenCalled();
  });
});

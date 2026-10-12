import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InvoiceCreatePage from '../pages/invoice-create/InvoiceCreatePage';
import ProductEditPage from '../pages/products/ProductEditPage';
import QuoteCreatePage from '../pages/quote-create/QuoteCreatePage';
import en from '../locales/en.json';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../lib/api', () => ({ api: mock }));
let instance = createInstance();
function Location() { const location = useLocation(); return <output data-testid="location">{location.pathname}</output>; }
function wrap(node: React.ReactNode, entries = ['/start']) { return <I18nextProvider i18n={instance}><MemoryRouter initialEntries={entries}>{node}</MemoryRouter></I18nextProvider>; }
function routed(node: React.ReactNode, path: string, entries: string[]) { return <I18nextProvider i18n={instance}><MemoryRouter initialEntries={entries}><Routes><Route path={path} element={node} /><Route path="*" element={<Location />} /></Routes></MemoryRouter></I18nextProvider>; }
function deferred() { let resolve!: (value: unknown) => void; let reject!: (error: Error) => void; const promise = new Promise((res, rej) => { resolve = res; reject = rej; }); return { promise, resolve, reject }; }

const company = { id: 4, company_code: 'C-4', name: 'Company' };
const contact = { id: 5, company_id: 4, surname: 'Buyer', given_name: 'One', surname_en: null, given_name_en: null, email: 'buyer@example.com', is_primary_contact: true };
const productPayload = {
  name_ja: 'Product', name_en: null, product_kind: 'TCG', tcg_type: null, set_type: null,
  category: null, mark: null, status: 'active', unit_price: null, quantity: 0, weight: null,
  notes: null, release_date: null, jan_code: null, card_number: null, expansion_code: null,
  rarity: null, language: null, unit_price_usd: null, unit_price_eur: null, image_url: null,
  boxes_per_case: null, packs_per_box: null, box_weight_kg: null, case_weight_kg: null,
  volume_weight: null, moq: null, hs_code: '9504400000', material: 'Paper', item: 'Playing card',
  required_output_value: null, search_keywords: null, exclude_keywords: null, related_series: null,
};
const productOptions = {
  product_kind: [{ code: 'kind', label_ja: 'Kind', label_en: null }],
  set_type: [{ code: 'set', label_ja: 'Set', label_en: null }],
  rarity: [{ code: 'rare', label_ja: 'Rare', label_en: null }],
  language: [{ code: 'en', label_ja: 'English', label_en: null }],
  hs_code: [{ code: 'hs', label_ja: 'HS', label_en: null }],
  item: [{ code: 'item', label_ja: 'Item', label_en: null }],
  material: [{ code: 'material', label_ja: 'Material', label_en: null }],
};
const nonDefaultProductPayload = { ...productPayload, name_ja: 'Product', name_en: 'Product EN', product_kind: 'Kind', tcg_type: 'pokemon', set_type: 'Set', category: 'Category', mark: 'M', status: 'discontinued', unit_price: 12.5, quantity: 7, weight: 0.75, notes: 'memo', release_date: '2026-09-28', jan_code: 'JAN-1', card_number: 'CARD-1', expansion_code: 'EXP-1', rarity: 'Rare', language: 'en', unit_price_usd: 11.5, unit_price_eur: 10.5, image_url: 'https://example.com/p.png', boxes_per_case: 24, packs_per_box: 12, box_weight_kg: 1.5, case_weight_kg: 3.5, volume_weight: 4.5, moq: 6, hs_code: 'HS', material: 'Material', item: 'Item', required_output_value: 'Required', search_keywords: 'search', exclude_keywords: 'exclude', related_series: 'Series' };
const visibleProductValues = ['Product', 'Product EN', 'Kind', 'pokemon', 'M', 'Set', '2026-09-28', 'CARD-1', 'EXP-1', 'Rare', 'en', '12.5', 'https://example.com/p.png', 'discontinued', 'memo', '24', '12', '3.5', '1.5', '4.5', '6', 'HS', 'Item', 'Material'];
function fillVisibleProductForm() {
  const form = screen.getByTestId('product-edit-form');
  const controls = Array.from(form.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>('input, select, textarea'));
  expect(controls).toHaveLength(24); controls.forEach((control, index) => fireEvent.change(control, { target: { value: visibleProductValues[index] } }));
}

beforeEach(async () => {
  vi.resetAllMocks(); instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/quotes?status=approved') return [];
    if (url === '/companies?per_page=100') return [company];
    if (url === '/contacts?company_id=4&per_page=100') return [contact];
    if (url === '/products/tcg-types') return [{ code: 'pokemon', name_ja: 'Pokemon' }];
    if (url === '/products/attribute-options') return productOptions;
    throw new Error(`Unexpected GET ${url}`);
  });
  mock.post.mockImplementation(() => { throw new Error('Unexpected POST'); });
  mock.patch.mockImplementation(() => { throw new Error('Unexpected PATCH'); });
  mock.delete.mockImplementation(() => { throw new Error('Unexpected DELETE'); });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('commerce submit Button migration contracts', () => {
  it.each([
    ['invoice', <InvoiceCreatePage />, 'invoice-add-blank', 'invoice-item-row-'],
    ['quote', <QuoteCreatePage />, 'quote-add-blank', 'quote-item-row-'],
  ] as const)('%s addItem appends one blank row per click with zero writes', async (_name, page, buttonId, rowPrefix) => {
    render(wrap(page));
    if (buttonId === 'invoice-add-blank') fireEvent.click(await screen.findByTestId('invoice-mode-inventory'));
    const button = await screen.findByTestId(buttonId) as HTMLButtonElement;
    const count = () => document.querySelectorAll(`tr[data-testid^="${rowPrefix}"]`).length;
    const before = count();
    fireEvent.click(button); expect(count()).toBe(before + 1);
    const row = screen.getByTestId(`${rowPrefix}${before}`); const inputs = within(row).getAllByRole('textbox'); const numbers = within(row).getAllByRole('spinbutton');
    expect(inputs.map(input => (input as HTMLInputElement).value)).toEqual(['', '', '', '']); expect(numbers.map(input => (input as HTMLInputElement).value)).toEqual(['1', '0', '']);
    fireEvent.click(button); expect(count()).toBe(before + 2);
    expect(button.disabled).toBe(false); expect(button.getAttribute('aria-busy')).toBeNull();
    expect(mock.post).not.toHaveBeenCalled(); expect(mock.patch).not.toHaveBeenCalled(); expect(mock.delete).not.toHaveBeenCalled();
  });

  it('Quote submit enforces contact and item guards without writing', async () => {
    render(wrap(<QuoteCreatePage />));
    const submit = await screen.findByRole('button', { name: String(instance.t('quotes.saveDraft')) });
    fireEvent.submit(submit.closest('form')!);
    expect(await screen.findByText(String(instance.t('companyContactSelector.contactRequired')))).toBeTruthy();
    expect(mock.post).not.toHaveBeenCalled();
    const selects = screen.getAllByRole('combobox');
    fireEvent.change(selects[0], { target: { value: '4' } });
    await screen.findByRole('option', { name: /Buyer/ }); fireEvent.change(selects[1], { target: { value: '5' } });
    fireEvent.submit(submit.closest('form')!);
    expect(await screen.findByText(String(instance.t('quotes.itemsRequired')))).toBeTruthy();
    expect(mock.post).not.toHaveBeenCalled();
  });

  it.each([
    ['empty name', 'name', ''], ['zero price', 'price', '0'], ['zero quantity', 'quantity', '0'],
  ] as const)('Quote item handler rejects %s with zero POST', async (_label, field, value) => {
    render(wrap(<QuoteCreatePage />)); const selects = await screen.findAllByRole('combobox'); fireEvent.change(selects[0], { target: { value: '4' } }); await screen.findByRole('option', { name: /Buyer/ }); fireEvent.change(selects[1], { target: { value: '5' } });
    const row = screen.getByTestId('quote-item-row-0'); const name = within(row).getByTestId('quote-item-row-0-name'); const numbers = within(row).getAllByRole('spinbutton'); fireEvent.change(name, { target: { value: field === 'name' ? value : 'Card' } }); fireEvent.change(numbers[0], { target: { value: field === 'quantity' ? value : '1' } }); fireEvent.change(numbers[1], { target: { value: field === 'price' ? value : '10' } });
    if (field === 'quantity') { fireEvent.click(screen.getByRole('button', { name: String(instance.t('quotes.saveDraft')) })); expect(mock.post).not.toHaveBeenCalled(); }
    fireEvent.submit(screen.getByRole('button', { name: String(instance.t('quotes.saveDraft')) }).closest('form')!); expect(await screen.findByText(String(instance.t('quotes.itemsRequired')))).toBeTruthy(); expect(mock.post).not.toHaveBeenCalled();
  });

  it('Quote submit preserves the exact payload, pending lock, failure state, retry, and success route', async () => {
    const first = deferred(); mock.post.mockReturnValueOnce(first.promise).mockResolvedValueOnce({});
    render(routed(<QuoteCreatePage />, '/quotes/new', ['/quotes/new']));
    const selects = await screen.findAllByRole('combobox'); fireEvent.change(selects[0], { target: { value: '4' } });
    await screen.findByRole('option', { name: /Buyer/ }); fireEvent.change(selects[1], { target: { value: '5' } }); fireEvent.change(selects[2], { target: { value: 'EUR' } });
    const row = screen.getByTestId('quote-item-row-0'); fireEvent.change(within(row).getByTestId('quote-item-row-0-name'), { target: { value: 'Card' } });
    const numbers = within(row).getAllByRole('spinbutton'); fireEvent.change(numbers[1], { target: { value: '12.5' } }); fireEvent.change(numbers[2], { target: { value: '0.25' } });
    fireEvent.change(screen.getByTestId('shipping-fee-input'), { target: { value: '3' } });
    fireEvent.change(screen.getByText(String(instance.t('quotes.tax'))).parentElement!.querySelector('input')!, { target: { value: '7' } }); fireEvent.change(screen.getByText(String(instance.t('common.notes'))).parentElement!.querySelector('input')!, { target: { value: 'memo' } });
    const submit = screen.getByRole('button', { name: String(instance.t('quotes.saveDraft')) }) as HTMLButtonElement;
    fireEvent.click(submit);
    const expected = { company_id: 4, contact_id: 5, currency: 'EUR', shipping_fee: 3, tax_amount: 7, notes: 'memo', items: [{ product_id: null, product_name: 'Card', name_en: null, condition: null, unit: null, quantity: 1, unit_price: 12.5, weight: 0.25 }] };
    expect(mock.post).toHaveBeenCalledExactlyOnceWith('/quotes', expected); expect(submit.disabled).toBe(true); fireEvent.click(submit); expect(mock.post).toHaveBeenCalledTimes(1);
    await act(async () => first.reject(new Error('Quote save failed'))); expect(await screen.findByText('Quote save failed')).toBeTruthy();
    expect((screen.getByTestId('quote-item-row-0-name') as HTMLInputElement).value).toBe('Card'); expect(submit.disabled).toBe(false);
    fireEvent.click(submit); await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(2)); expect(mock.post.mock.calls[1]).toEqual(['/quotes', expected]);
    expect((await screen.findByTestId('location')).textContent).toBe('/quotes');
  });

  it('Quote submit maps empty fee, tax, and notes to null', async () => {
    mock.post.mockResolvedValue({}); render(routed(<QuoteCreatePage />, '/quotes/new', ['/quotes/new'])); const selects = await screen.findAllByRole('combobox'); fireEvent.change(selects[0], { target: { value: '4' } }); await screen.findByRole('option', { name: /Buyer/ }); fireEvent.change(selects[1], { target: { value: '5' } }); const row = screen.getByTestId('quote-item-row-0'); fireEvent.change(within(row).getByTestId('quote-item-row-0-name'), { target: { value: 'Card' } }); fireEvent.change(within(row).getAllByRole('spinbutton')[1], { target: { value: '10' } }); fireEvent.click(screen.getByRole('button', { name: String(instance.t('quotes.saveDraft')) })); await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(1)); expect(mock.post).toHaveBeenCalledExactlyOnceWith('/quotes', { company_id: 4, contact_id: 5, currency: 'USD', shipping_fee: null, tax_amount: null, notes: null, items: [{ product_id: null, product_name: 'Card', name_en: null, condition: null, unit: null, quantity: 1, unit_price: 10, weight: null }] }); expect((await screen.findByTestId('location')).textContent).toBe('/quotes');
  });

  it('Product create sends all 34 payload keys, blocks duplicate pending writes, preserves failure state, and retries', async () => {
    expect(Object.keys(productPayload)).toHaveLength(34); const first = deferred(); mock.post.mockReturnValueOnce(first.promise).mockResolvedValueOnce({});
    render(routed(<ProductEditPage />, '/admin/products/new', ['/before', '/admin/products/new']));
    const save = await screen.findByTestId('product-edit-save') as HTMLButtonElement; fillVisibleProductForm(); const expected = { ...nonDefaultProductPayload, category: null, quantity: 0, weight: null, jan_code: null, unit_price_usd: null, unit_price_eur: null, required_output_value: null, search_keywords: null, exclude_keywords: null, related_series: null }; expect(Object.keys(expected)).toHaveLength(34); fireEvent.click(save);
    expect(mock.post).toHaveBeenCalledExactlyOnceWith('/products', expected); await waitFor(() => expect(save.disabled).toBe(true)); const cancel = screen.getByRole('button', { name: String(instance.t('common.cancel')) }) as HTMLButtonElement; expect(cancel.disabled).toBe(true); fireEvent.click(save); expect(mock.post).toHaveBeenCalledTimes(1);
    await act(async () => first.reject(new Error('Product save failed'))); expect(await screen.findByText('Product save failed')).toBeTruthy(); expect((screen.getByTestId('product-edit-name-ja') as HTMLInputElement).value).toBe('Product'); expect(save.disabled).toBe(false);
    expect(cancel.disabled).toBe(false); fireEvent.click(save); await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(2)); expect(mock.post.mock.calls[1]).toEqual(['/products', expected]); expect((await screen.findByTestId('location')).textContent).toBe('/before');
  });

  it('Product required and edit-loading guards write zero', async () => {
    render(routed(<ProductEditPage />, '/admin/products/new', ['/before', '/admin/products/new'])); const save = await screen.findByTestId('product-edit-save'); fireEvent.click(save); expect(mock.post).not.toHaveBeenCalled(); cleanup();
    const load = deferred(); mock.get.mockImplementation(async (url: string) => { if (url === '/products/tcg-types') return []; if (url === '/products/attribute-options') return {}; if (url === '/products/9') return load.promise; throw new Error(`Unexpected GET ${url}`); });
    render(routed(<ProductEditPage />, '/admin/products/:id/edit', ['/before', '/admin/products/9/edit'])); const editSave = await screen.findByTestId('product-edit-save') as HTMLButtonElement; expect(editSave.disabled).toBe(true); fireEvent.click(editSave); expect(mock.patch).not.toHaveBeenCalled(); await act(async () => load.reject(new Error('load failed'))); expect(await screen.findByText('load failed')).toBeTruthy();
  });

  it('Product edit PATCHes the exact 34-key payload, locks pending, preserves failure state, and retries', async () => {
    const fixture = { id: 9, product_code: null, ...nonDefaultProductPayload, name_ja: 'Existing', created_at: '', updated_at: '', is_archived: false, archived_at: null, supplier_default_id: null, display_order: null };
    const first = deferred(); mock.get.mockImplementation(async (url: string) => { if (url === '/products/tcg-types') return []; if (url === '/products/attribute-options') return {}; if (url === '/products/9') return fixture; throw new Error(`Unexpected GET ${url}`); }); mock.patch.mockReturnValueOnce(first.promise).mockResolvedValueOnce({});
    render(routed(<ProductEditPage />, '/admin/products/:id/edit', ['/before', '/admin/products/9/edit'])); await waitFor(() => expect((screen.getByTestId('product-edit-name-ja') as HTMLInputElement).value).toBe('Existing'));
    const form = screen.getByTestId('product-edit-form'); const controls = Array.from(form.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>('input, select, textarea')); fireEvent.change(controls[0], { target: { value: 'Edited' } }); fireEvent.change(controls[11], { target: { value: '99.25' } });
    const save = screen.getByTestId('product-edit-save') as HTMLButtonElement; fireEvent.click(save); const expected = { ...nonDefaultProductPayload, name_ja: 'Edited', unit_price: 99.25 }; expect(Object.keys(expected)).toHaveLength(34); await waitFor(() => expect(mock.patch).toHaveBeenCalledExactlyOnceWith('/products/9', expected)); expect(save.disabled).toBe(true); const cancel = screen.getByRole('button', { name: String(instance.t('common.cancel')) }) as HTMLButtonElement; expect(cancel.disabled).toBe(true); fireEvent.click(save); expect(mock.patch).toHaveBeenCalledTimes(1);
    await act(async () => first.reject(new Error('Edit save failed'))); expect(await screen.findByText('Edit save failed')).toBeTruthy(); expect((screen.getByTestId('product-edit-name-ja') as HTMLInputElement).value).toBe('Edited'); expect(save.disabled).toBe(false); expect(cancel.disabled).toBe(false);
    fireEvent.click(save); await waitFor(() => expect(mock.patch).toHaveBeenCalledTimes(2)); expect(mock.patch.mock.calls[1]).toEqual(['/products/9', expected]); expect((await screen.findByTestId('location')).textContent).toBe('/before');
  });
});

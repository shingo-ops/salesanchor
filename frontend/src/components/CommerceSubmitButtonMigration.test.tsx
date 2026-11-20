import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InvoiceCreatePage from '../pages/invoice-create/InvoiceCreatePage';
import ProductEditPage from '../pages/products/ProductEditPage';
import QuoteCreatePage from '../pages/quote-create/QuoteCreatePage';
import en from '../locales/en.json';
import { queryClient } from '../lib/query/apiQuery';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../lib/api', async (importOriginal) => ({ ...(await importOriginal<typeof import('../lib/api')>()), api: mock }));
let instance = createInstance();
function Location() { const location = useLocation(); return <output data-testid="location">{location.pathname}</output>; }
type Entries = React.ComponentProps<typeof MemoryRouter>['initialEntries'];
function wrap(node: React.ReactNode, entries: Entries = ['/start']) { return <I18nextProvider i18n={instance}><MemoryRouter initialEntries={entries}>{node}</MemoryRouter></I18nextProvider>; }
function routed(node: React.ReactNode, path: string, entries: Entries) { return <I18nextProvider i18n={instance}><MemoryRouter initialEntries={entries}><Routes><Route path={path} element={node} /><Route path="*" element={<Location />} /></Routes></MemoryRouter></I18nextProvider>; }
function deferred() { let resolve!: (value: unknown) => void; let reject!: (error: Error) => void; const promise = new Promise((res, rej) => { resolve = res; reject = rej; }); return { promise, resolve, reject }; }

const company = { id: 4, company_code: 'C-4', name: 'Company' };
const contact = { id: 5, company_id: 4, surname: 'Buyer', given_name: 'One', surname_en: null, given_name_en: null, email: 'buyer@example.com', is_primary_contact: true };
const productPayload = {
  name_ja: 'Product', name_en: null, product_kind: 'TCG', set_type: null,
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
const nonDefaultProductPayload = { ...productPayload, name_ja: 'Product', name_en: 'Product EN', product_kind: 'Kind', set_type: 'Set', category: 'Category', mark: 'M', status: 'discontinued', unit_price: 12.5, quantity: 7, weight: 0.75, notes: 'memo', release_date: '2026-09-28', jan_code: 'JAN-1', card_number: 'CARD-1', expansion_code: 'EXP-1', rarity: 'Rare', language: 'en', unit_price_usd: 11.5, unit_price_eur: 10.5, image_url: 'https://example.com/p.png', boxes_per_case: 24, packs_per_box: 12, box_weight_kg: 1.5, case_weight_kg: 3.5, volume_weight: 4.5, moq: 6, hs_code: 'HS', material: 'Material', item: 'Item', required_output_value: 'Required', search_keywords: 'search', exclude_keywords: 'exclude', related_series: 'Series' };
const visibleProductValues = ['Product', 'Product EN', 'Kind', 'M', 'Set', '2026-09-28', 'CARD-1', 'EXP-1', 'Rare', 'en', '12.5', 'https://example.com/p.png', 'discontinued', 'memo', '24', '12', '3.5', '1.5', '4.5', '6', 'HS', 'Item', 'Material'];
function fillVisibleProductForm() {
  const form = screen.getByTestId('product-edit-form');
  const controls = Array.from(form.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>('input, select, textarea'));
  expect(controls).toHaveLength(23); controls.forEach((control, index) => fireEvent.change(control, { target: { value: visibleProductValues[index] } }));
}
// invoice-create-portfolio 便R7: 見積の作成画面は請求書と同じ商品行（在庫の道・為替の道を読む。design-v2 §3-8-1・K16）
const inventory = {
  categories: [{ code: 'OP', name_ja: 'One Piece' }],
  items: [
    { product_id: 7, name: 'Booster Box A', name_en: 'Booster Box A EN', mark: 'OP-01', work_code: 'OP', box_weight_kg: 0.5, case_weight_kg: 6,
      cells: { Case: { price: 170000, quantity: 1 }, 'Sealed box': { price: 15000, quantity: 3 } } },
  ],
};
const fxUsd = { currency: 'USD', rate_jpy: 150, fetched_at: '2026-11-19T21:00:00+00:00', updated_at: '2026-11-19T21:00:00+00:00' };
const quoteHandoff = { selectedProducts: [{ product_id: 7, product_name: 'Booster Box A', unit_price: null }] };
const stockRow = { product_id: 7, product_name: 'Booster Box A', name_en: 'Booster Box A EN', condition: 'Sealed box', unit: 'box', quantity: 1, unit_price: 100, weight: 0.5 };
const optionValues = (testId: string) => Array.from((screen.getByTestId(testId) as HTMLSelectElement).options).map((o) => o.value);
const priceValue = () => (screen.getByTestId('invoice-item-price-0') as HTMLInputElement).value;
/** 在庫表の画面から商品 7 を持ってきた形で見積の画面を開き、取引先と担当者を選ぶ。state が空でなければ状態も選ぶ */
async function openQuoteWithProduct(state: string) {
  render(routed(<QuoteCreatePage />, '/quotes/new', [{ pathname: '/quotes/new', state: quoteHandoff }]));
  await waitFor(() => expect(optionValues('invoice-item-state-0')).toContain('Sealed box'), { timeout: 4000 });
  const selects = screen.getAllByRole('combobox'); fireEvent.change(selects[0], { target: { value: '4' } });
  await screen.findByRole('option', { name: /Buyer/ }); fireEvent.change(selects[1], { target: { value: '5' } });
  if (state !== '') fireEvent.change(screen.getByTestId('invoice-item-state-0'), { target: { value: state } });
}

beforeEach(async () => {
  vi.resetAllMocks(); instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/companies?per_page=100') return [company];
    // invoice-create-portfolio 便R5・R7: 請求書と見積の作成画面は在庫の道を 1 回読む。見積は為替の道も読む（USD）
    if (url === '/invoices/draft-inventory') return inventory;
    if (url === '/fx-rates/USD') return fxUsd;
    if (url === '/contacts?company_id=4&per_page=100') return [contact];
    if (url === '/products/tcg-types') return [{ code: 'pokemon', name_ja: 'Pokemon' }];
    if (url === '/products/attribute-options') return productOptions;
    throw new Error(`Unexpected GET ${url}`);
  });
  mock.post.mockImplementation(() => { throw new Error('Unexpected POST'); });
  mock.patch.mockImplementation(() => { throw new Error('Unexpected PATCH'); });
  mock.delete.mockImplementation(() => { throw new Error('Unexpected DELETE'); });
});
afterEach(() => { cleanup(); queryClient.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('commerce submit Button migration contracts', () => {
  it.each([
    // invoice-create-portfolio 便R5: 請求書の行は選ぶ欄（カテゴリ・商品・状態）と数の欄 2 つ（数量・単価）。空の行は数の欄も空
    ['invoice', <InvoiceCreatePage />, 'invoice-add-row', 'invoice-item-row-', [], ['', '']],
    // invoice-create-portfolio 便R7: 見積も同じ商品行の表（K16 (a)）
    ['quote', <QuoteCreatePage />, 'invoice-add-row', 'invoice-item-row-', [], ['', '']],
  ] as const)('%s addItem appends one blank row per click with zero writes', async (_name, page, buttonId, rowPrefix, textValues, numberValues) => {
    render(wrap(page));
    const button = await screen.findByTestId(buttonId) as HTMLButtonElement;
    // 見積の画面は表を form の中に置くので、押しても保存が走らない種類のボタン（design-v2 §3-8-1）
    expect(button.getAttribute('type')).toBe('button');
    const count = () => document.querySelectorAll(`tr[data-testid^="${rowPrefix}"]`).length;
    const before = count();
    fireEvent.click(button); expect(count()).toBe(before + 1);
    const row = screen.getByTestId(`${rowPrefix}${before}`); const inputs = within(row).queryAllByRole('textbox'); const numbers = within(row).getAllByRole('spinbutton');
    expect(inputs.map(input => (input as HTMLInputElement).value)).toEqual([...textValues]); expect(numbers.map(input => (input as HTMLInputElement).value)).toEqual([...numberValues]);
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
    // K16 (g): 自由記入の欄と検索で足す欄は画面に無い
    expect(document.querySelectorAll('[data-testid^="quote-add-search"], [data-testid^="quote-item-row-"]').length).toBe(0);
    expect(mock.post).not.toHaveBeenCalled();
  });

  it.each([
    ['no state', 'state'], ['zero price', 'price'], ['zero quantity', 'quantity'],
  ] as const)('Quote item guard rejects a stock row with %s with zero POST (K16 (c))', async (_label, field) => {
    await openQuoteWithProduct(field === 'state' ? '' : 'Sealed box');
    if (field !== 'state') await waitFor(() => expect(priceValue()).toBe('100'));
    if (field === 'price') fireEvent.change(screen.getByTestId('invoice-item-price-0'), { target: { value: '0' } });
    if (field === 'quantity') fireEvent.change(screen.getByTestId('invoice-item-quantity-0'), { target: { value: '0' } });
    fireEvent.click(screen.getByRole('button', { name: String(instance.t('quotes.saveDraft')) }));
    expect(await screen.findByText(String(instance.t('quotes.itemsRequired')))).toBeTruthy(); expect(mock.post).not.toHaveBeenCalled();
  });

  it('Quote submit sends the stock row in the same 8-field shape, locks pending, keeps the row on failure, retries, and routes (K16 (b)(d)(e))', async () => {
    const first = deferred(); mock.post.mockReturnValueOnce(first.promise).mockResolvedValueOnce({});
    await openQuoteWithProduct('Sealed box');
    // USD: 在庫表の円の値段 15000 ÷ 為替 150 = 100。Sealed box の重さは箱の重さ 0.5
    await waitFor(() => expect(priceValue()).toBe('100'));
    expect(screen.getByTestId('invoice-item-weight-0').textContent).toBe(String(instance.t('lineItems.weightKg', { value: 0.5 })));
    fireEvent.change(screen.getByTestId('shipping-fee-input'), { target: { value: '3' } });
    fireEvent.change(screen.getByText(String(instance.t('quotes.tax'))).parentElement!.querySelector('input')!, { target: { value: '7' } }); fireEvent.change(screen.getByText(String(instance.t('common.notes'))).parentElement!.querySelector('input')!, { target: { value: 'memo' } });
    const submit = screen.getByRole('button', { name: String(instance.t('quotes.saveDraft')) }) as HTMLButtonElement;
    fireEvent.click(submit);
    // 空の行（11行）は送らない（K16 (d)）
    const expected = { company_id: 4, contact_id: 5, currency: 'USD', shipping_fee: 3, tax_amount: 7, notes: 'memo', items: [stockRow] };
    expect(mock.post).toHaveBeenCalledExactlyOnceWith('/quotes', expected); expect(submit.disabled).toBe(true); fireEvent.click(submit); expect(mock.post).toHaveBeenCalledTimes(1);
    await act(async () => first.reject(new Error('Quote save failed'))); expect(await screen.findByText('Quote save failed')).toBeTruthy();
    expect((screen.getByTestId('invoice-item-state-0') as HTMLSelectElement).value).toBe('Sealed box'); expect(submit.disabled).toBe(false);
    fireEvent.click(submit); await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(2)); expect(mock.post.mock.calls[1]).toEqual(['/quotes', expected]);
    expect((await screen.findByTestId('location')).textContent).toBe('/quotes');
  });

  it('Quote submit maps empty fee, tax, and notes to null (K16 (f))', async () => {
    mock.post.mockResolvedValue({}); await openQuoteWithProduct('Sealed box'); await waitFor(() => expect(priceValue()).toBe('100'));
    fireEvent.click(screen.getByRole('button', { name: String(instance.t('quotes.saveDraft')) })); await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(1));
    expect(mock.post).toHaveBeenCalledExactlyOnceWith('/quotes', { company_id: 4, contact_id: 5, currency: 'USD', shipping_fee: null, tax_amount: null, notes: null, items: [stockRow] }); expect((await screen.findByTestId('location')).textContent).toBe('/quotes');
  });

  it('Product create sends all 33 payload keys, blocks duplicate pending writes, preserves failure state, and retries', async () => {
    expect(Object.keys(productPayload)).toHaveLength(33); const first = deferred(); mock.post.mockReturnValueOnce(first.promise).mockResolvedValueOnce({});
    render(routed(<ProductEditPage />, '/admin/products/new', ['/before', '/admin/products/new']));
    const save = await screen.findByTestId('product-edit-save') as HTMLButtonElement; fillVisibleProductForm(); const expected = { ...nonDefaultProductPayload, category: null, quantity: 0, weight: null, jan_code: null, unit_price_usd: null, unit_price_eur: null, required_output_value: null, search_keywords: null, exclude_keywords: null, related_series: null }; expect(Object.keys(expected)).toHaveLength(33); fireEvent.click(save);
    expect(mock.post).toHaveBeenCalledExactlyOnceWith('/products', expected); await waitFor(() => expect(save.disabled).toBe(true)); const cancel = screen.getByRole('button', { name: String(instance.t('common.cancel')) }) as HTMLButtonElement; expect(cancel.disabled).toBe(true); fireEvent.click(save); expect(mock.post).toHaveBeenCalledTimes(1);
    await act(async () => first.reject(new Error('Product save failed'))); expect(await screen.findByText('Product save failed')).toBeTruthy(); expect((screen.getByTestId('product-edit-name-ja') as HTMLInputElement).value).toBe('Product'); expect(save.disabled).toBe(false);
    expect(cancel.disabled).toBe(false); fireEvent.click(save); await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(2)); expect(mock.post.mock.calls[1]).toEqual(['/products', expected]); expect((await screen.findByTestId('location')).textContent).toBe('/before');
  });

  it('Product required and edit-loading guards write zero', async () => {
    render(routed(<ProductEditPage />, '/admin/products/new', ['/before', '/admin/products/new'])); const save = await screen.findByTestId('product-edit-save'); fireEvent.click(save); expect(mock.post).not.toHaveBeenCalled(); cleanup();
    const load = deferred(); mock.get.mockImplementation(async (url: string) => { if (url === '/products/tcg-types') return []; if (url === '/products/attribute-options') return {}; if (url === '/products/9') return load.promise; throw new Error(`Unexpected GET ${url}`); });
    render(routed(<ProductEditPage />, '/admin/products/:id/edit', ['/before', '/admin/products/9/edit'])); const editSave = await screen.findByTestId('product-edit-save') as HTMLButtonElement; expect(editSave.disabled).toBe(true); fireEvent.click(editSave); expect(mock.patch).not.toHaveBeenCalled(); await act(async () => load.reject(new Error('load failed'))); expect(await screen.findByText('load failed')).toBeTruthy();
  });

  it('Product edit PATCHes the exact 33-key payload, locks pending, preserves failure state, and retries', async () => {
    const fixture = { id: 9, product_code: null, ...nonDefaultProductPayload, name_ja: 'Existing', created_at: '', updated_at: '', is_archived: false, archived_at: null, supplier_default_id: null, display_order: null };
    const first = deferred(); mock.get.mockImplementation(async (url: string) => { if (url === '/products/tcg-types') return []; if (url === '/products/attribute-options') return {}; if (url === '/products/9') return fixture; throw new Error(`Unexpected GET ${url}`); }); mock.patch.mockReturnValueOnce(first.promise).mockResolvedValueOnce({});
    render(routed(<ProductEditPage />, '/admin/products/:id/edit', ['/before', '/admin/products/9/edit'])); await waitFor(() => expect((screen.getByTestId('product-edit-name-ja') as HTMLInputElement).value).toBe('Existing'));
    const form = screen.getByTestId('product-edit-form'); const controls = Array.from(form.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>('input, select, textarea')); fireEvent.change(controls[0], { target: { value: 'Edited' } }); fireEvent.change(controls[10], { target: { value: '99.25' } });
    const save = screen.getByTestId('product-edit-save') as HTMLButtonElement; fireEvent.click(save); const expected = { ...nonDefaultProductPayload, name_ja: 'Edited', unit_price: 99.25 }; expect(Object.keys(expected)).toHaveLength(33); await waitFor(() => expect(mock.patch).toHaveBeenCalledExactlyOnceWith('/products/9', expected)); expect(save.disabled).toBe(true); const cancel = screen.getByRole('button', { name: String(instance.t('common.cancel')) }) as HTMLButtonElement; expect(cancel.disabled).toBe(true); fireEvent.click(save); expect(mock.patch).toHaveBeenCalledTimes(1);
    await act(async () => first.reject(new Error('Edit save failed'))); expect(await screen.findByText('Edit save failed')).toBeTruthy(); expect((screen.getByTestId('product-edit-name-ja') as HTMLInputElement).value).toBe('Edited'); expect(save.disabled).toBe(false); expect(cancel.disabled).toBe(false);
    fireEvent.click(save); await waitFor(() => expect(mock.patch).toHaveBeenCalledTimes(2)); expect(mock.patch.mock.calls[1]).toEqual(['/products/9', expected]); expect((await screen.findByTestId('location')).textContent).toBe('/before');
  });
});

/* eslint-disable local/no-japanese-literal -- テスト: 在庫の道が返すカテゴリの日本語名を試験データに書く（ADR-027・precedent: DataTable.test.tsx） */
// invoice-create-portfolio R5: 請求書作成ページを見本の見た目と操作に作り直した（design-v2 §3-1〜§3-6・§6 K1〜K3・K5〜K14・K19〜K21）
// invoice-create-portfolio R6: 作成のあとの小さな枠（design-v2 §3-6・K15）
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InvoiceCreatePage from './InvoiceCreatePage';
import en from '../../locales/en.json';
import { queryClient } from '../../lib/query/apiQuery';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), getBlob: vi.fn() }));
const saveBlobMock = vi.hoisted(() => vi.fn());
vi.mock('../../lib/saveBlob', () => ({ saveBlob: saveBlobMock }));
vi.mock('../../lib/api', async (importOriginal) => ({ ...(await importOriginal<typeof import('../../lib/api')>()), api: mock }));
let instance = createInstance();
const tr = (key: string, opts?: Record<string, unknown>) => String(instance.t(key, opts));
function Location() { const value = useLocation(); return <output data-testid="location">{value.pathname}</output>; }

const SLOW = { timeout: 4000 };
const CTX_PATH = '/invoices/draft-context?company_id=4&contact_id=5';
const company = { id: 4, company_code: 'C-4', name: 'Company' };
const contact = { id: 5, company_id: 4, surname: 'Buyer', given_name: 'One', surname_en: null, given_name_en: null, email: 'buyer@example.com', is_primary_contact: true };
const address = {
  company_name: 'Buyer Inc', billing_display_name: null, label: null, postal_code: '10001', address: '1 Main St', city: 'New York', state: 'NY', country: 'US', phone: '+1 555',
  recipient_name: 'Ann Lee', email: 'ann@example.com', tax_id: 'TAX-9', address_line_1: '1 Main St', address_line_2: 'Suite 2', address_line_3: 'Floor 3', country_name: 'United States',
};
let ctx: Record<string, unknown>;
function baseCtx() {
  return {
    company_id: 4, ship_to: address, bill_to: { ...address, address_line_1: '2 Bill St' }, contact_name: 'One Buyer', contact_email: 'buyer@example.com',
    issuer_region: 'JP', origin_country_code: 'JP', destination_country_code: 'US', destination_postal_code: '10001',
    currencies: ['JPY', 'USD'], fx_rates: [{ currency: 'USD', rate: 150, fetched_at: '2026-11-15' }], default_currency: 'USD', currency: null,
    payment_methods: [
      { id: 3, method_type: 'bank', display_name: 'Main bank', wise_currency: null },
      { id: 4, method_type: 'wise', display_name: 'Wise USD', wise_currency: 'USD' },
    ],
    tax_rate_percent: null, incoterms: 'DAP',
  };
}
const inventory = {
  categories: [{ code: 'OP', name_ja: 'ワンピース' }, { code: 'PK', name_ja: 'ポケモン' }],
  items: [
    { product_id: 7, name: 'Booster Box A', name_en: 'Booster Box A EN', mark: 'OP-01', work_code: 'OP', box_weight_kg: 0.5, case_weight_kg: 6,
      cells: { Case: { price: 170000, quantity: 1 }, 'Sealed box': { price: 15000, quantity: 3 } } },
    { product_id: 8, name: 'No Weight Box', name_en: null, mark: 'PK-1', work_code: 'PK', box_weight_kg: null, case_weight_kg: null,
      cells: { 'Sealed box': { price: 3000, quantity: 2 } } },
    { product_id: 9, name: 'Sold Out Box', name_en: null, mark: 'PK-2', work_code: 'PK', box_weight_kg: 0.4, case_weight_kg: null,
      cells: { 'Sealed box': { price: 3000, quantity: 0 } } },
  ],
};
const liveRate = { carrier: 'FedEx', zone: 'A', fee: 33.333, currency: 'USD', source: 'fedex_live', service_type: 'FEDEX_IP', service_name: 'International Priority', transit_days: 3 };
const staticRate = { carrier: 'DHL', zone: '3', fee: 40, currency: 'USD', source: 'static', service_type: null, service_name: null, transit_days: null };
let shippingAnswer: Record<string, unknown>;
let permissions: string[];

type PreviewBody = { currency: string; items: Array<{ quantity: number; unit_price: number }>; shipping: { mode: string; fee?: number } | null };
function previewFor(body: PreviewBody) {
  const subtotal = body.items.reduce((s, i) => s + i.quantity * i.unit_price, 0);
  if (body.shipping === null) {
    return { currency: body.currency, subtotal: String(subtotal), shipping_fee: null, tax_amount: '0', tax_rate_percent: null, duty_amount: '0', duty_label: null, duty_components: [], total_amount: null, uncomputed: ['shipping_required'], incoterms: 'DAP' };
  }
  const fee = body.shipping.mode === 'calculate' ? body.shipping.fee ?? 0 : 0;
  return { currency: body.currency, subtotal: String(subtotal), shipping_fee: String(fee), tax_amount: '0', tax_rate_percent: null, duty_amount: '0', duty_label: null, duty_components: [], total_amount: String(subtotal + fee), uncomputed: [], incoterms: 'DAP' };
}

function view(state: Record<string, unknown> | null = { draft: { companyId: 4, contactId: 5, currency: 'USD', notes: '' } }) {
  render(
    <I18nextProvider i18n={instance}>
      <MemoryRouter initialEntries={[{ pathname: '/invoices/new', state }]}>
        <InvoiceCreatePage />
        <Location />
      </MemoryRouter>
    </I18nextProvider>,
  );
}
/** 在庫表の画面から 1 商品を持ってきた形で開き、状態を選ぶ */
async function openWithProduct(productId = 7, state = 'Sealed box') {
  const product = inventory.items.find((i) => i.product_id === productId)!;
  view({ draft: { companyId: 4, contactId: 5, currency: 'USD', notes: '' }, selectedProducts: [{ product_id: productId, product_name: product.name, unit_price: null }] });
  await screen.findByTestId('invoice-ship-to-address');
  // 在庫の答えが届くと状態の選択肢が出る（どの商品も Sealed box を持つ）
  await waitFor(() => expect(optionValues('invoice-item-state-0')).toContain('Sealed box'));
  if (state !== '') fireEvent.change(screen.getByTestId('invoice-item-state-0'), { target: { value: state } });
}
const optionValues = (testId: string) => Array.from((screen.getByTestId(testId) as HTMLSelectElement).options).map((o) => o.value);
const posts = (path: string) => mock.post.mock.calls.filter(([url]) => url === path).map(([, body]) => body as Record<string, unknown>);
const previewCalls = () => posts('/invoices/preview') as unknown as PreviewBody[];
const rows = () => screen.getAllByTestId(/^invoice-item-row-\d+$/);
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

beforeEach(async () => {
  vi.resetAllMocks(); instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  ctx = baseCtx();
  shippingAnswer = { results: [liveRate, staticRate], live_error: null };
  permissions = ['invoices.create'];
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/me/permissions') return { permissions };
    if (url === '/companies?per_page=100') return [company];
    if (url === '/contacts?company_id=4&per_page=100') return [contact];
    if (url === CTX_PATH) return ctx;
    if (url === '/invoices/draft-inventory') return inventory;
    throw new Error(`Unexpected GET ${url}`);
  });
  mock.post.mockImplementation(async (url: string, body: unknown) => {
    if (url === '/invoices/preview') return previewFor(body as PreviewBody);
    if (url === '/invoices/draft-shipping-quotes') return shippingAnswer;
    if (url === '/invoices') return { id: 11, invoice_number: 'IN-0011-01' };
    throw new Error(`Unexpected POST ${url}`);
  });
  mock.patch.mockImplementation(() => { throw new Error('Unexpected patch'); });
  mock.delete.mockImplementation(() => { throw new Error('Unexpected delete'); });
  mock.getBlob.mockImplementation(async (url: string) => {
    if (url === '/invoices/11/pdf') return new Blob(['%PDF'], { type: 'application/pdf' });
    throw new Error(`Unexpected getBlob ${url}`);
  });
});
afterEach(() => { cleanup(); queryClient.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('InvoiceCreatePage (invoice-create-portfolio R5)', () => {
  it('K1: four cards in the order ship-to, payment and totals, products, actions', async () => {
    view();
    await screen.findByTestId('invoice-ship-to-address');
    const headings = Array.from(document.querySelectorAll('.comp-section-card__title')).map((h) => h.textContent);
    expect(headings).toEqual([tr('invoiceForm.sectionShipTo'), tr('invoiceForm.sectionPaymentTotals'), tr('invoiceForm.sectionItems'), tr('invoiceForm.sectionActions')]);
  });

  it('K2/K3: ship-to shows 12 read-only fields in two columns with the registered values', async () => {
    view();
    const box = await screen.findByTestId('invoice-ship-to-address');
    expect(box.querySelectorAll('input, textarea, select').length).toBe(0);
    const fields = within(box).getAllByTestId(/^invoice-ship-to-field-/);
    expect(fields.length).toBe(12);
    const text = (key: string) => within(box).getByTestId(`invoice-ship-to-field-${key}`).textContent;
    expect(text('customer')).toContain('Buyer Inc');
    expect(text('recipient')).toContain('Ann Lee');
    expect(text('phone')).toContain('+1 555');
    expect(text('email')).toContain('ann@example.com');
    expect(text('tax')).toContain('TAX-9');
    expect(text('country')).toContain('United States');
    expect(text('address1')).toContain('1 Main St');
    expect(text('address2')).toContain('Suite 2');
    expect(text('address3')).toContain('Floor 3');
    expect(text('city')).toContain('New York');
    expect(text('state')).toContain('NY');
    expect(text('zip')).toContain('10001');
  });

  it('K3: empty fields show "unregistered"', async () => {
    ctx = { ...baseCtx(), ship_to: { ...address, tax_id: null, address_line_3: '' } };
    view();
    const box = await screen.findByTestId('invoice-ship-to-address');
    expect(within(box).getByTestId('invoice-ship-to-field-tax').textContent).toContain(tr('common.unregistered'));
    expect(within(box).getByTestId('invoice-ship-to-field-address3').textContent).toContain(tr('common.unregistered'));
  });

  it('K5: payment and totals has three columns with the designed contents', async () => {
    view();
    await screen.findByTestId('invoice-ship-to-address');
    const pay = screen.getByTestId('invoice-col-payment');
    await waitFor(() => expect(within(pay).getByTestId('invoice-currency-select')).toBeTruthy());
    expect(within(pay).getByTestId('invoice-payment-select')).toBeTruthy();
    expect(within(pay).getByTestId('invoice-notes')).toBeTruthy();
    const ship = screen.getByTestId('invoice-col-shipping');
    expect(within(ship).getByTestId('invoice-total-weight')).toBeTruthy();
    expect(within(ship).getByTestId('invoice-shipping-none')).toBeTruthy();
    const totals = screen.getByTestId('invoice-col-totals');
    for (const id of ['invoice-total-subtotal', 'invoice-total-shipping', 'invoice-total-tax', 'invoice-total-amount']) expect(within(totals).getByTestId(id)).toBeTruthy();
  });

  it('K2 (payment): currency and payment choices come from draft-context; JPY drops the Wise USD row', async () => {
    view();
    await waitFor(() => expect(optionValues('invoice-currency-select')).toEqual(['', 'JPY', 'USD']));
    expect((screen.getByTestId('invoice-currency-select') as HTMLSelectElement).value).toBe('USD');
    expect(optionValues('invoice-payment-select')).toEqual(['', 'bank:3', 'wise:4']);
    fireEvent.change(screen.getByTestId('invoice-payment-select'), { target: { value: 'wise:4' } });
    fireEvent.change(screen.getByTestId('invoice-currency-select'), { target: { value: 'JPY' } });
    await waitFor(() => expect(optionValues('invoice-payment-select')).toEqual(['', 'bank:3']));
    expect((screen.getByTestId('invoice-payment-select') as HTMLSelectElement).value).toBe('');
  });

  it('K6: once the weight is known, every rate is listed without any click, each with a live/static badge', async () => {
    await openWithProduct();
    const list = await screen.findByTestId('invoice-shipping-list');
    await waitFor(() => expect(within(list).getByTestId('invoice-shipping-rate-fedex_live|FedEx|FEDEX_IP')).toBeTruthy(), SLOW);
    expect(within(list).getByTestId('invoice-shipping-rate-static|DHL|')).toBeTruthy();
    expect(list.textContent).toContain(tr('invoiceForm.sourceLive'));
    expect(list.textContent).toContain(tr('invoiceForm.sourceStatic'));
    expect(posts('/invoices/draft-shipping-quotes')).toEqual([{ company_id: 4, weight_kg: 0.5 }]);
  });

  it('K6: when live FedEx fails, the reason is shown', async () => {
    shippingAnswer = { results: [staticRate], live_error: 'FedEx is not connected' };
    await openWithProduct();
    expect((await screen.findByTestId('invoice-shipping-live-error', {}, SLOW)).textContent).toContain('FedEx is not connected');
    expect(screen.queryByTestId('invoice-shipping-rate-fedex_live|FedEx|FEDEX_IP')).toBeNull();
  });

  it('K7: the same weight is not asked twice', async () => {
    await openWithProduct();
    await waitFor(() => expect(posts('/invoices/draft-shipping-quotes').length).toBe(1), SLOW);
    fireEvent.change(screen.getByTestId('invoice-item-quantity-0'), { target: { value: '2' } });
    await waitFor(() => expect(posts('/invoices/draft-shipping-quotes').length).toBe(2), SLOW);
    fireEvent.change(screen.getByTestId('invoice-item-quantity-0'), { target: { value: '1' } });
    await waitFor(() => expect(screen.getByTestId('invoice-shipping-rate-static|DHL|')).toBeTruthy(), SLOW);
    expect(posts('/invoices/draft-shipping-quotes').map((b) => b.weight_kg)).toEqual([0.5, 1]);
  });

  it('K5/K8: choosing a rate sends it to the preview and the total is shown', async () => {
    await openWithProduct();
    const pick = await screen.findByTestId('invoice-shipping-rate-fedex_live|FedEx|FEDEX_IP', {}, SLOW);
    expect(screen.getByTestId('invoice-total-amount').textContent).toBe(tr('invoiceForm.notComputed'));
    fireEvent.click(pick);
    await waitFor(() => expect(previewCalls().some((b) => b.shipping?.mode === 'calculate' && b.shipping.fee === 33.33)).toBe(true), SLOW);
    await waitFor(() => expect(screen.getByTestId('invoice-total-amount').textContent).not.toBe(tr('invoiceForm.notComputed')), SLOW);
  });

  it('K9: 12 rows at first, up to 20, the 21st is refused with a notice; one row cannot be removed', async () => {
    view();
    await screen.findByTestId('invoice-ship-to-address');
    expect(rows().length).toBe(12);
    for (let i = 0; i < 8; i += 1) fireEvent.click(screen.getByTestId('invoice-add-row'));
    expect(rows().length).toBe(20);
    expect((screen.getByTestId('invoice-add-row') as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByTestId('invoice-max-rows').textContent).toBe(tr('lineItems.maxRows', { count: 20 }));
    for (let i = 0; i < 19; i += 1) fireEvent.click(screen.getByTestId('invoice-item-remove-0'));
    expect(rows().length).toBe(1);
    expect((screen.getByTestId('invoice-item-remove-0') as HTMLButtonElement).disabled).toBe(true);
  });

  it('K10: after choosing a category, only in-stock products of that category are offered', async () => {
    view();
    await screen.findByTestId('invoice-ship-to-address');
    await waitFor(() => expect(optionValues('invoice-item-category-0')).toEqual(['', 'OP', 'PK']));
    fireEvent.change(screen.getByTestId('invoice-item-category-0'), { target: { value: 'PK' } });
    const input = within(screen.getByTestId('invoice-item-product-0')).getByRole('combobox');
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: 'box' } });
    await screen.findByRole('option', { name: 'No Weight Box (PK-1)' });
    expect(within(screen.getByRole('listbox')).getAllByRole('option').map((o) => o.textContent)).toEqual(['No Weight Box (PK-1)']);
  });

  it('K11/K13: choosing a product offers only in-stock states; the state fills weight, price and stock limit', async () => {
    await openWithProduct(7, '');
    expect(optionValues('invoice-item-state-0')).toEqual(['', 'Case', 'Sealed box']);
    fireEvent.change(screen.getByTestId('invoice-item-state-0'), { target: { value: 'Sealed box' } });
    expect(screen.getByTestId('invoice-item-weight-0').textContent).toBe(tr('lineItems.weightKg', { value: 0.5 }));
    expect(within(screen.getByTestId('invoice-item-row-0')).queryAllByRole('spinbutton').map((el) => el.getAttribute('data-testid'))).toEqual(['invoice-item-quantity-0', 'invoice-item-price-0']);
    expect((screen.getByTestId('invoice-item-price-0') as HTMLInputElement).value).toBe('100');
  });

  it('K12: a quantity above stock goes back to the stock count with a notice', async () => {
    await openWithProduct();
    fireEvent.change(screen.getByTestId('invoice-item-quantity-0'), { target: { value: '9' } });
    expect((screen.getByTestId('invoice-item-quantity-0') as HTMLInputElement).value).toBe('3');
    expect(screen.getByTestId('invoice-item-row-0').textContent).toContain(tr('lineItems.stockLimit', { count: 3 }));
  });

  it('unit price: a currency change reconverts only rows whose price was not typed by hand', async () => {
    await openWithProduct();
    expect((screen.getByTestId('invoice-item-price-0') as HTMLInputElement).value).toBe('100');
    fireEvent.change(screen.getByTestId('invoice-currency-select'), { target: { value: 'JPY' } });
    await waitFor(() => expect((screen.getByTestId('invoice-item-price-0') as HTMLInputElement).value).toBe('15000'));
    fireEvent.change(screen.getByTestId('invoice-item-price-0'), { target: { value: '14000' } });
    fireEvent.change(screen.getByTestId('invoice-currency-select'), { target: { value: 'USD' } });
    await waitFor(() => expect((screen.getByTestId('invoice-currency-select') as HTMLSelectElement).value).toBe('USD'));
    expect((screen.getByTestId('invoice-item-price-0') as HTMLInputElement).value).toBe('14000');
  });

  it('K14: there is no inventory/quote mode switch and no quote list is read', async () => {
    view();
    await screen.findByTestId('invoice-ship-to-address');
    expect(screen.queryByTestId('invoice-mode-inventory')).toBeNull();
    expect(screen.queryByTestId('invoice-mode-quote')).toBeNull();
    expect(mock.get.mock.calls.some(([url]) => String(url).startsWith('/quotes'))).toBe(false);
  });

  it('K19: clear asks first; "no" changes nothing, "yes" empties rows, ship-to, shipping and memo', async () => {
    await openWithProduct();
    fireEvent.change(screen.getByTestId('invoice-notes'), { target: { value: 'Fragile' } });
    fireEvent.click(screen.getByTestId('invoice-clear'));
    let dialog = await screen.findByRole('dialog');
    fireEvent.click(within(dialog).getByRole('button', { name: tr('common.cancel') }));
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    expect((screen.getByTestId('invoice-notes') as HTMLInputElement).value).toBe('Fragile');
    expect((screen.getByTestId('invoice-item-state-0') as HTMLSelectElement).value).toBe('Sealed box');
    fireEvent.click(screen.getByTestId('invoice-clear'));
    dialog = await screen.findByRole('dialog');
    fireEvent.click(within(dialog).getByRole('button', { name: tr('invoiceForm.clearConfirmYes') }));
    await waitFor(() => expect(screen.queryByTestId('invoice-ship-to')).toBeNull());
    expect((screen.getByTestId('invoice-notes') as HTMLInputElement).value).toBe('');
    expect(rows().length).toBe(12);
    expect((screen.getByTestId('invoice-item-state-0') as HTMLSelectElement).value).toBe('');
    expect((screen.getByTestId('invoice-shipping-none') as HTMLInputElement).checked).toBe(false);
  });

  it('K20: a row without a state stops creation and marks the state field', async () => {
    await openWithProduct(7, '');
    fireEvent.click(submit());
    expect(await screen.findByText(tr('lineItems.stateMissing'))).toBeTruthy();
    expect(screen.getByTestId('invoice-error').textContent).toBe(tr('invoiceForm.rowsNotReady'));
    expect(posts('/invoices')).toEqual([]);
  });

  it('K21: a product without a registered weight shows "unregistered" and is not created', async () => {
    await openWithProduct(8, 'Sealed box');
    expect(within(screen.getByTestId('invoice-item-weight-0')).getByText(tr('common.unregistered'))).toBeTruthy();
    fireEvent.click(submit());
    expect(await screen.findByTestId('invoice-item-weight-missing-0')).toBeTruthy();
    expect(posts('/invoices')).toEqual([]);
  });

  it('K15: create sends the exact body once, stays on the page and shows the created dialog', async () => {
    await openWithProduct();
    await waitFor(() => expect(optionValues('invoice-payment-select')).toContain('bank:3'));
    fireEvent.change(screen.getByTestId('invoice-payment-select'), { target: { value: 'bank:3' } });
    fireEvent.click(screen.getByTestId('invoice-shipping-none'));
    await waitFor(() => expect(previewCalls().some((b) => b.shipping?.mode === 'none' && b.items.length === 1)).toBe(true), SLOW);
    await waitFor(() => expect(screen.getByTestId('invoice-total-amount').textContent).not.toBe(tr('invoiceForm.notComputed')), SLOW);
    fireEvent.click(submit());
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByTestId('invoice-created-number').textContent).toContain('IN-0011-01');
    expect(screen.getByTestId('location').textContent).toBe('/invoices/new');
    expect(posts('/invoices')).toEqual([{
      company_id: 4, contact_id: 5, currency: 'USD', shipping: { mode: 'none' }, payment_method_ref: { method_type: 'bank', id: 3 }, notes: null,
      items: [{ product_id: 7, product_name: 'Booster Box A', name_en: 'Booster Box A EN', condition: 'Sealed box', unit: 'box', quantity: 1, unit_price: 100, weight: 0.5 }],
    }]);
  });

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
    await openWithProduct();
    fireEvent.click(submit());
    expect(screen.getByTestId('invoice-error').textContent).toBe(tr('invoiceForm.createNotReady'));
    expect(posts('/invoices')).toEqual([]);
  });

  it('no payment destinations: create is allowed without one and the profile link is offered', async () => {
    ctx = { ...baseCtx(), payment_methods: [] };
    await openWithProduct();
    expect(await screen.findByTestId('invoice-open-tenant-profile')).toBeTruthy();
    fireEvent.click(screen.getByTestId('invoice-shipping-none'));
    await waitFor(() => expect(screen.getByTestId('invoice-total-amount').textContent).not.toBe(tr('invoiceForm.notComputed')), SLOW);
    fireEvent.click(submit());
    await waitFor(() => expect(posts('/invoices').length).toBe(1));
    expect(posts('/invoices')[0].payment_method_ref).toBeNull();
  });

  it('issuer region missing: create is refused and the company page link is shown', async () => {
    ctx = { ...baseCtx(), issuer_region: null };
    await openWithProduct();
    expect(await screen.findByTestId('invoice-open-company-for-bill-to')).toBeTruthy();
    fireEvent.click(screen.getByTestId('invoice-shipping-none'));
    await waitFor(() => expect(previewCalls().some((b) => b.shipping?.mode === 'none')).toBe(true), SLOW);
    fireEvent.click(submit());
    expect(posts('/invoices')).toEqual([]);
    fireEvent.click(screen.getByTestId('invoice-open-company-for-bill-to'));
    expect(screen.getByTestId('location').textContent).toBe('/crm/companies/4');
  });
});

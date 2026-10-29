import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InventoryPage from './InventoryPage';
import en from '../../locales/en.json';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../../lib/api', () => ({ api: mock }));

const mkRow = (id: string) => ({
  id, product_id: 2, product_name: 'Card', name_en: null, category: null, mark: null,
  condition: 'New', unit: 'BOX', offer_type: null, status: 'sold_out', note_ja: 'memo', ship_ja: 'ship',
  merged_count: 1, posted_at: null, ship_timing: null, supplier_id: 3, supplier_name: 'S',
  unit_price: 10, quantity: null, work_code: 'pokemon_booster_box', offered_at: '', release_date: null,
});
const list = {
  items: [mkRow('r1')], total: 1, page: 1, per_page: 50, window_hours: 18, fresh_window_hours: 24,
  conditions: ['New', 'Used'], units: ['BOX'],
};
const inventoryCalls = () => mock.get.mock.calls.map(([u]) => String(u)).filter((u) => u.startsWith('/inventory?'));
const lastCall = () => { const c = inventoryCalls(); return c[c.length - 1] ?? ''; };

// 偽装した matchMedia（スマホ幅 = true）
const stubMatchMedia = (matches: boolean) => {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: (q: string) => ({
      matches, media: q, onchange: null,
      addEventListener: () => undefined, removeEventListener: () => undefined,
      addListener: () => undefined, removeListener: () => undefined, dispatchEvent: () => false,
    }),
  });
};

let instance = createInstance();
const setup = async (filters: Record<string, unknown> = { enabled: false, merge_same_post: false }) => {
  mock.get.mockImplementation((url: string) => {
    if (url === '/me/permissions') return Promise.resolve({ permissions: [] });
    if (url === '/products/tcg-types') return Promise.resolve([]);
    if (url === '/me/inventory-filters') return Promise.resolve(filters);
    if (url.startsWith('/inventory?')) return Promise.resolve(list);
    return Promise.reject(new Error(`Unexpected GET ${url}`));
  });
  render(<I18nextProvider i18n={instance}><MemoryRouter><InventoryPage /></MemoryRouter></I18nextProvider>);
  await screen.findByTestId('inventory-row-r1');
};
const before = (a: HTMLElement, b: HTMLElement) =>
  Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);

beforeEach(async () => {
  vi.resetAllMocks();
  instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  mock.patch.mockResolvedValue({});
});
afterEach(() => {
  cleanup();
  // jsdom 既定（matchMedia なし = PC 幅）へ戻す
  delete (window as unknown as { matchMedia?: unknown }).matchMedia;
});

describe('InventoryPage toolbar (PC)', () => {
  it('K1: row 1 is search -> price -> quantity', async () => {
    await setup();
    const rows = document.querySelectorAll('.content-toolbar--two-rows > .content-toolbar__row');
    expect(rows).toHaveLength(2);
    const top = rows[0] as HTMLElement;
    const search = screen.getByTestId('inventory-search');
    const price = screen.getByTestId('inventory-price-min');
    const qty = screen.getByTestId('inventory-qty-min');
    expect(top.contains(search) && top.contains(price) && top.contains(qty)).toBe(true);
    expect(before(search, price)).toBe(true);
    expect(before(price, qty)).toBe(true);
  });

  it('K2: row 2 is sort -> condition -> supplier -> detail filter, right side fresh -> reset', async () => {
    await setup();
    const rows = document.querySelectorAll('.content-toolbar--two-rows > .content-toolbar__row');
    const bottom = rows[1] as HTMLElement;
    const sort = screen.getByTestId('inventory-sort-menu');
    const cond = screen.getByTestId('inventory-condition-filter-button');
    const sup = screen.getByTestId('inventory-supplier-filter-button');
    const toggle = screen.getByTestId('inventory-filter-toggle');
    const fresh = screen.getByTestId('inventory-fresh-toggle');
    const reset = screen.getByTestId('inventory-reset-sort');
    for (const el of [sort, cond, sup, toggle, fresh, reset]) expect(bottom.contains(el)).toBe(true);
    expect(before(sort, cond)).toBe(true);
    expect(before(cond, sup)).toBe(true);
    expect(before(sup, toggle)).toBe(true);
    expect(before(toggle, fresh)).toBe(true);
    expect(before(fresh, reset)).toBe(true);
  });

  it('K3: price, quantity and condition reach the API even when the filter switch is OFF', async () => {
    await setup({ enabled: false, merge_same_post: false });
    fireEvent.change(screen.getByTestId('inventory-price-min'), { target: { value: '100' } });
    fireEvent.change(screen.getByTestId('inventory-qty-min'), { target: { value: '3' } });
    fireEvent.click(screen.getByTestId('inventory-condition-filter-button'));
    fireEvent.click(await screen.findByTestId('inventory-condition-filter-option-New'));
    await waitFor(() => {
      const u = lastCall();
      expect(u).toContain('price_min=100');
      expect(u).toContain('qty_min=3');
      expect(u).toContain('condition_in=New');
    });
  });

  it('K4: unit / offer type / hidden categories are NOT sent while the switch is OFF', async () => {
    await setup({
      enabled: false, merge_same_post: false, hidden_categories: ['X'], hidden_columns: [],
      show_units: ['BOX'], show_offer_types: ['in_stock'],
    });
    await new Promise((r) => setTimeout(r, 30));
    const u = lastCall();
    expect(u).not.toContain('unit_in');
    expect(u).not.toContain('offer_type_in');
    expect(u).not.toContain('hide_categories');
  });
});

describe('InventoryPage toolbar (mobile)', () => {
  it('K6: no ContentToolbar on mobile, shows .inventory-toolbar, hides reset/fresh at top, and moves them (plus condition/range) into the detail panel', async () => {
    stubMatchMedia(true);
    await setup();
    expect(document.querySelector('.content-toolbar')).toBeNull();
    expect(document.querySelector('.inventory-toolbar')).not.toBeNull();
    expect(screen.queryByTestId('inventory-reset-sort')).toBeNull();
    expect(screen.queryByTestId('inventory-fresh-toggle')).toBeNull();
    expect(screen.queryByTestId('inventory-price-min')).toBeNull();
    expect(screen.queryByTestId('inventory-condition-filter-button')).toBeNull();
    const order = ['inventory-search', 'inventory-sort-menu', 'inventory-filter-toggle']
      .map((id) => screen.getByTestId(id));
    for (let i = 0; i < order.length - 1; i++) expect(before(order[i], order[i + 1])).toBe(true);
    fireEvent.click(screen.getByTestId('inventory-filter-toggle'));
    const panel = await screen.findByTestId('inventory-filter-panel');
    for (const id of ['inventory-fresh-check', 'inventory-condition-filter-button', 'inventory-price-min', 'inventory-qty-max', 'inventory-reset-in-panel']) {
      expect(panel.contains(screen.getByTestId(id))).toBe(true);
    }
  });
});

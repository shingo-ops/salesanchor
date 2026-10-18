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
const listOf = (id: string) => ({ items: [mkRow(id)], total: 1, page: 1, per_page: 50, window_hours: 18 });

type Deferred<T> = { promise: Promise<T>; resolve: (v: T) => void; reject: (e: unknown) => void };
const defer = <T,>(): Deferred<T> => {
  let resolve!: (v: T) => void;
  let reject!: (e: unknown) => void;
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
};

const lastCall = () => { const c = inventoryCalls(); return c[c.length - 1] ?? ''; };
const inventoryCalls = () => mock.get.mock.calls.map(([u]) => String(u)).filter((u) => u.startsWith('/inventory?'));

let instance = createInstance();
beforeEach(async () => {
  vi.resetAllMocks();
  instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  mock.patch.mockResolvedValue({});
});
afterEach(() => cleanup());

const renderPage = () =>
  render(<I18nextProvider i18n={instance}><MemoryRouter><InventoryPage /></MemoryRouter></I18nextProvider>);

describe('InventoryPage single fetch on open', () => {
  it('does not call /inventory until saved filters resolve, then calls once with the saved filters', async () => {
    const filters = defer<unknown>();
    mock.get.mockImplementation((url: string) => {
      if (url === '/me/permissions') return Promise.resolve({ permissions: [] });
      if (url === '/products/tcg-types') return Promise.resolve([]);
      if (url === '/me/inventory-filters') return filters.promise;
      if (url.startsWith('/inventory?')) return Promise.resolve(listOf('r1'));
      return Promise.reject(new Error(`Unexpected GET ${url}`));
    });
    renderPage();
    await waitFor(() => expect(mock.get.mock.calls.some(([u]) => u === '/me/inventory-filters')).toBe(true));
    await new Promise((r) => setTimeout(r, 30));
    expect(inventoryCalls()).toHaveLength(0);

    filters.resolve({ enabled: true, merge_same_post: false, hidden_supplier_ids: [1], hidden_categories: [], hidden_columns: [] });
    await screen.findByTestId('inventory-row-r1');
    await new Promise((r) => setTimeout(r, 30));
    const calls = inventoryCalls();
    expect(calls).toHaveLength(1);
    expect(calls[0]).toContain('merge_same_post=false');
    expect(calls[0]).not.toContain('hide_supplier_ids');
    expect(calls[0]).not.toContain('supplier_ids');
  });

  it('still calls /inventory once with defaults when saved filters fail', async () => {
    mock.get.mockImplementation((url: string) => {
      if (url === '/me/permissions') return Promise.resolve({ permissions: [] });
      if (url === '/products/tcg-types') return Promise.resolve([]);
      if (url === '/me/inventory-filters') return Promise.reject(new Error('boom'));
      if (url.startsWith('/inventory?')) return Promise.resolve(listOf('r1'));
      return Promise.reject(new Error(`Unexpected GET ${url}`));
    });
    renderPage();
    await screen.findByTestId('inventory-row-r1');
    await new Promise((r) => setTimeout(r, 30));
    const calls = inventoryCalls();
    expect(calls).toHaveLength(1);
    expect(calls[0]).toContain('merge_same_post=false');
  });

  it('ignores a stale response that resolves after a newer one', async () => {
    const first = defer<unknown>();
    const second = defer<unknown>();
    let n = 0;
    mock.get.mockImplementation((url: string) => {
      if (url === '/me/permissions') return Promise.resolve({ permissions: [] });
      if (url === '/products/tcg-types') return Promise.resolve([]);
      if (url === '/me/inventory-filters') return Promise.resolve({ enabled: false, merge_same_post: true });
      if (url.startsWith('/inventory?')) { n += 1; return n === 1 ? first.promise : second.promise; }
      return Promise.reject(new Error(`Unexpected GET ${url}`));
    });
    renderPage();
    await waitFor(() => expect(inventoryCalls()).toHaveLength(1));
    fireEvent.click(screen.getByTestId('inventory-settings-open'));
    fireEvent.click(await screen.findByTestId('inventory-merge-toggle'));
    await waitFor(() => expect(inventoryCalls()).toHaveLength(2));

    second.resolve(listOf('new'));
    await screen.findByTestId('inventory-row-new');
    first.resolve(listOf('old'));
    await new Promise((r) => setTimeout(r, 30));
    expect(screen.queryByTestId('inventory-row-old')).toBeNull();
    expect(screen.getByTestId('inventory-row-new')).toBeTruthy();
  });

  const withSuppliers = () => {
    mock.get.mockImplementation((url: string) => {
      if (url === '/me/permissions') return Promise.resolve({ permissions: [] });
      if (url === '/products/tcg-types') return Promise.resolve([]);
      if (url === '/me/inventory-filters') return Promise.resolve({ enabled: false, merge_same_post: false, hidden_supplier_ids: [], hidden_categories: [], hidden_columns: [] });
      if (url.startsWith('/inventory?')) {
        return Promise.resolve({ ...listOf('r1'), suppliers: [{ id: 3, name: 'S' }, { id: 4, name: 'T' }] });
      }
      return Promise.reject(new Error(`Unexpected GET ${url}`));
    });
  };

  it('sends supplier_ids when suppliers are chosen in the toolbar MultiSelect, and stops sending after clear', async () => {
    withSuppliers();
    renderPage();
    await screen.findByTestId('inventory-row-r1');
    expect(inventoryCalls()[0]).not.toContain('supplier_ids');

    fireEvent.click(await screen.findByTestId('inventory-supplier-filter-button'));
    fireEvent.click(await screen.findByTestId('inventory-supplier-filter-option-3'));
    await waitFor(() => expect(lastCall()).toContain('supplier_ids=3'));
    expect(lastCall()).toContain('page=1');
    fireEvent.click(await screen.findByTestId('inventory-supplier-filter-option-4'));
    await waitFor(() => expect(lastCall()).toContain('supplier_ids=3%2C4'));
    expect(lastCall()).not.toContain('hide_supplier_ids');

    fireEvent.click(await screen.findByTestId('inventory-supplier-filter-clear'));
    await waitFor(() => expect(lastCall()).not.toContain('supplier_ids'));
  });

  it('has no search button, and Enter searches at once', async () => {
    withSuppliers();
    renderPage();
    await screen.findByTestId('inventory-row-r1');
    expect(screen.queryByTestId('inventory-search-btn')).toBeNull();
    const input = screen.getByTestId('inventory-search');
    expect(input.getAttribute('placeholder')).toBe('Search by name or code');
    const before = inventoryCalls().length;
    fireEvent.change(input, { target: { value: String.fromCodePoint(0x307d, 0x3051, 0x3082, 0x3093) } });
    fireEvent.keyDown(input, { key: 'Enter' });
    await waitFor(() => expect(inventoryCalls().length).toBeGreaterThan(before));
    expect(lastCall()).toContain('q=%E3%81%BD%E3%81%91%E3%82%82%E3%82%93');
  });
});

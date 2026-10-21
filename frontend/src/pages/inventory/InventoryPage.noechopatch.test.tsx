import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InventoryPage from './InventoryPage';
import en from '../../locales/en.json';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../../lib/api', () => ({ api: mock }));

const row = {
  id: 'r1', product_id: 2, product_name: 'Card', name_en: null, category: null, mark: null,
  condition: 'New', unit: 'BOX', offer_type: null, status: 'sold_out', note_ja: 'memo', ship_ja: 'ship',
  merged_count: 1, posted_at: null, ship_timing: null, supplier_id: 3, supplier_name: 'S',
  unit_price: 10, quantity: null, work_code: 'pokemon_booster_box', offered_at: '', release_date: null,
};

let instance = createInstance();
beforeEach(async () => {
  vi.resetAllMocks();
  instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  mock.patch.mockResolvedValue({});
});
afterEach(() => cleanup());

const setupGet = (filters: () => Promise<unknown>) => {
  mock.get.mockImplementation((url: string) => {
    if (url === '/me/permissions') return Promise.resolve({ permissions: [] });
    if (url === '/products/tcg-types') return Promise.resolve([]);
    if (url === '/me/inventory-filters') return filters();
    if (url.startsWith('/inventory?')) return Promise.resolve({ items: [row], total: 1, page: 1, per_page: 50, window_hours: 18 });
    return Promise.reject(new Error(`Unexpected GET ${url}`));
  });
};
const renderPage = () =>
  render(<I18nextProvider i18n={instance}><MemoryRouter><InventoryPage /></MemoryRouter></I18nextProvider>);
const settle = () => new Promise((r) => setTimeout(r, 450));
const bodies = () => mock.patch.mock.calls.map(([, b]) => b as { merge_same_post: boolean });

describe('InventoryPage does not echo loaded filters back via PATCH', () => {
  it('loaded filters -> 0 PATCH; change -> 1 PATCH; revert -> 2nd PATCH', async () => {
    setupGet(() => Promise.resolve({
      enabled: true, merge_same_post: true, hidden_supplier_ids: [1, 1], hidden_categories: [], hidden_columns: [],
      qty_min: 5,
    }));
    renderPage();
    await screen.findByTestId('inventory-row-r1');
    await settle();
    expect(mock.patch).toHaveBeenCalledTimes(0);

    fireEvent.click(screen.getByTestId('inventory-settings-open'));
    const toggle = await screen.findByTestId('inventory-merge-toggle');
    fireEvent.click(toggle);
    await waitFor(() => expect(mock.patch).toHaveBeenCalledTimes(1));
    expect(bodies()[0].merge_same_post).toBe(false);

    fireEvent.click(toggle);
    await waitFor(() => expect(mock.patch).toHaveBeenCalledTimes(2));
    expect(bodies()[1].merge_same_post).toBe(true);
    await settle();
    expect(mock.patch).toHaveBeenCalledTimes(2);
  });

  it('filter fetch failure -> defaults saved once (unchanged behaviour)', async () => {
    setupGet(() => Promise.reject(new Error('boom')));
    renderPage();
    await screen.findByTestId('inventory-row-r1');
    await waitFor(() => expect(mock.patch).toHaveBeenCalledTimes(1));
    await settle();
    expect(mock.patch).toHaveBeenCalledTimes(1);
    expect(bodies()[0].merge_same_post).toBe(false);
  });

  it('reverting while the first PATCH is still pending sends the reverted value', async () => {
    setupGet(() => Promise.resolve({ enabled: true, merge_same_post: true, hidden_supplier_ids: [], hidden_categories: [], hidden_columns: [] }));
    let release!: () => void;
    mock.patch.mockImplementationOnce(() => new Promise((res) => { release = () => res({}); }));
    renderPage();
    await screen.findByTestId('inventory-row-r1');
    fireEvent.click(screen.getByTestId('inventory-settings-open'));
    const toggle = await screen.findByTestId('inventory-merge-toggle');
    fireEvent.click(toggle);
    await waitFor(() => expect(mock.patch).toHaveBeenCalledTimes(1));
    expect(bodies()[0].merge_same_post).toBe(false);
    fireEvent.click(toggle);
    await waitFor(() => expect(mock.patch).toHaveBeenCalledTimes(2));
    expect(bodies()[1].merge_same_post).toBe(true);
    release();
  });

  it('keeps the saved hidden_supplier_ids in the PATCH body even though the UI no longer edits them', async () => {
    setupGet(() => Promise.resolve({
      enabled: true, merge_same_post: true, hidden_supplier_ids: [1], hidden_categories: [], hidden_columns: [],
    }));
    renderPage();
    await screen.findByTestId('inventory-row-r1');
    await settle();
    expect(mock.patch).toHaveBeenCalledTimes(0);
    fireEvent.click(screen.getByTestId('inventory-settings-open'));
    fireEvent.click(await screen.findByTestId('inventory-merge-toggle'));
    await waitFor(() => expect(mock.patch).toHaveBeenCalledTimes(1));
    expect((mock.patch.mock.calls[0][1] as { hidden_supplier_ids: number[] }).hidden_supplier_ids).toEqual([1]);
  });
});

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
  id: 'r1', product_id: 2, product_name: 'Card', name_en: null, category: 'cat', mark: null,
  condition: 'Sealed box', unit: 'BOX', offer_type: 'in_stock', status: 'in_stock', note_ja: 'memo', ship_ja: 'ship',
  merged_count: 1, posted_at: null, ship_timing: null, supplier_id: 3, supplier_name: 'S',
  unit_price: 10, quantity: 2, work_code: 'pokemon_booster_box', offered_at: '', release_date: null,
};
const TCG_TYPES = [
  { code: 'pokemon_booster_box', name_ja: 'P' },
  { code: 'one_piece', name_ja: 'O' },
  { code: 'dragon_ball', name_ja: 'D' },
  { code: 'hololive', name_ja: 'H' },
];

let instance = createInstance();
beforeEach(async () => {
  vi.resetAllMocks();
  instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/me/permissions') return { permissions: [] };
    if (url === '/products/tcg-types') return TCG_TYPES;
    if (url === '/me/inventory-filters') return { enabled: false };
    if (url.startsWith('/inventory?')) return { items: [row], total: 1, page: 1, per_page: 50, window_hours: 18, fresh_window_hours: 24 };
    throw new Error(`Unexpected GET ${url}`);
  });
});
afterEach(() => {
  cleanup();
  delete (window as unknown as { matchMedia?: unknown }).matchMedia;
});

const renderPage = () =>
  render(<I18nextProvider i18n={instance}><MemoryRouter><InventoryPage /></MemoryRouter></I18nextProvider>);

const lastInventoryUrl = () => {
  const calls = mock.get.mock.calls.filter(([u]) => String(u).startsWith('/inventory?'));
  return String(calls[calls.length - 1][0]);
};

describe('InventoryPage type tabs (Tabs mold attached to the table)', () => {
  it('K1: PC tab row is a Tabs bar placed right before the table, table has the attached-top class', async () => {
    renderPage();
    await screen.findByTestId('inventory-row-r1');
    await screen.findByLabelText(en.inventory.filter.otherTypes);
    const tablist = screen.getByRole('tablist');
    const bar = tablist.closest('.comp-tabs-bar') as HTMLElement;
    expect(bar).toBeTruthy();
    const attached = document.querySelector('.comp-table--attached-top');
    expect(attached).toBeTruthy();
    expect(bar.nextElementSibling?.contains(attached)).toBe(true);
    expect(bar.contains(screen.getByTestId('inventory-expiry-warning'))).toBe(true);
    expect(screen.getAllByRole('tab')).toHaveLength(4);
  });

  it('K2/K6: other pull-down uses the tab look; picking it sends that work_code and clears every tab selection', async () => {
    renderPage();
    await screen.findByTestId('inventory-row-r1');
    const other = (await screen.findByLabelText(en.inventory.filter.otherTypes)) as HTMLSelectElement;
    expect(other.className).toContain('comp-select--tab');
    expect(other.className).not.toContain('comp-select--tab-active');
    fireEvent.change(other, { target: { value: 'hololive' } });
    await waitFor(() => expect(lastInventoryUrl()).toContain('work_code=hololive'));
    expect((screen.getByLabelText(en.inventory.filter.otherTypes) as HTMLSelectElement).className).toContain('comp-select--tab-active');
    for (const tab of screen.getAllByRole('tab')) expect(tab.getAttribute('aria-selected')).toBe('false');
  });

  it('K6: tab clicks send the same work_code as before', async () => {
    renderPage();
    await screen.findByTestId('inventory-row-r1');
    expect(lastInventoryUrl()).toContain('work_code=pokemon_booster_box');
    fireEvent.click(screen.getAllByRole('tab')[2]);
    await waitFor(() => expect(lastInventoryUrl()).toContain('work_code=one_piece'));
    fireEvent.click(screen.getAllByRole('tab')[0]);
    await waitFor(() => expect(lastInventoryUrl()).not.toContain('work_code='));
  });

  it('K5b (reversed by design.md 4-1): on mobile the tab row is gone (type picked via inventory-tab-select instead) and the card view has no attached-top class', async () => {
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      writable: true,
      value: (q: string) => ({
        matches: true, media: q, onchange: null,
        addEventListener: () => undefined, removeEventListener: () => undefined,
        addListener: () => undefined, removeListener: () => undefined, dispatchEvent: () => false,
      }),
    });
    renderPage();
    await screen.findByTestId('inventory-row-r1');
    expect(screen.queryByRole('tablist')).toBeNull();
    expect(screen.getByTestId('inventory-tab-select')).toBeTruthy();
    expect(document.querySelector('.comp-table--attached-top')).toBeNull();
  });
});

import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
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

let instance = createInstance();
beforeEach(async () => {
  vi.resetAllMocks();
  instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/me/permissions') return { permissions: [] };
    if (url === '/products/tcg-types') return [];
    if (url === '/me/inventory-filters') return { enabled: false };
    if (url.startsWith('/inventory?')) return { items: [row], total: 1, page: 1, per_page: 50, window_hours: 18, fresh_window_hours: 24 };
    throw new Error(`Unexpected GET ${url}`);
  });
  mock.patch.mockResolvedValue({});
});
afterEach(() => cleanup());

const renderPage = () =>
  render(<I18nextProvider i18n={instance}><MemoryRouter><InventoryPage /></MemoryRouter></I18nextProvider>);

describe('InventoryPage table layout (DataTable)', () => {
  it('shows columns in the designed order without a category column, condition as Badge', async () => {
    renderPage();
    const rowEl = await screen.findByTestId('inventory-row-r1');
    const heads = Array.from(document.querySelectorAll('thead th')).map((th) => th.textContent?.trim());
    expect(heads).toEqual(
      ['status', 'mark', 'title', 'condition', 'unitPrice', 'quantity', 'note', 'ship', 'supplier', 'releaseDate']
        .map((k) => (en as unknown as { inventory: { col: Record<string, string> } }).inventory.col[k]),
    );
    expect(heads).not.toContain(en.inventory.col.category);
    expect(within(rowEl).getByText('Sealed box').className).toContain('inventory-cell__condition--info');
  });

  it('sort menu has a heading plus 3 options (no release_date:desc) and shows the heading by default; picking one sets sort and resetAll returns to the heading', async () => {
    renderPage();
    await screen.findByTestId('inventory-row-r1');
    const menu = screen.getByTestId('inventory-sort-menu') as HTMLSelectElement;
    expect(menu.value).toBe('');
    expect(Array.from(menu.options).map((o) => o.value)).toEqual(['', 'unit_price:asc', 'quantity:desc', 'offered_at:desc']);
    expect(Array.from(menu.options).map((o) => o.value)).not.toContain('release_date:desc');
    expect(menu.options[0].textContent).toBe('Sort');
    fireEvent.change(menu, { target: { value: 'unit_price:asc' } });
    await waitFor(() =>
      expect(mock.get.mock.calls.some(([u]) => String(u).includes('sort=unit_price') && String(u).includes('order=asc'))).toBe(true),
    );
    expect((screen.getByTestId('inventory-sort-menu') as HTMLSelectElement).value).toBe('unit_price:asc');
    fireEvent.click(screen.getByTestId('inventory-reset-sort'));
    await waitFor(() => expect((screen.getByTestId('inventory-sort-menu') as HTMLSelectElement).value).toBe(''));
    const invCalls = mock.get.mock.calls.filter(([u]) => String(u).startsWith('/inventory?'));
    const last = String(invCalls[invCalls.length - 1][0]);
    expect(last).toContain('sort=release_date');
    expect(last).toContain('order=desc');
  });

  it('choosing the heading after another sort returns to release_date desc', async () => {
    renderPage();
    await screen.findByTestId('inventory-row-r1');
    fireEvent.change(screen.getByTestId('inventory-sort-menu'), { target: { value: 'unit_price:asc' } });
    await waitFor(() => expect((screen.getByTestId('inventory-sort-menu') as HTMLSelectElement).value).toBe('unit_price:asc'));
    fireEvent.change(screen.getByTestId('inventory-sort-menu'), { target: { value: '' } });
    await waitFor(() => expect((screen.getByTestId('inventory-sort-menu') as HTMLSelectElement).value).toBe(''));
    await waitFor(() => {
      const invCalls = mock.get.mock.calls.filter(([u]) => String(u).startsWith('/inventory?'));
      const last = String(invCalls[invCalls.length - 1][0]);
      expect(last).toContain('sort=release_date');
      expect(last).toContain('order=desc');
    });
  });
});

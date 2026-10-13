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
  merged_count: 3, posted_at: null, ship_timing: null, supplier_id: 3, supplier_name: 'S',
  unit_price: 10, quantity: null, tcg_type: 'pokemon_booster_box', offered_at: '', release_date: null,
};

let instance = createInstance();
beforeEach(async () => {
  vi.resetAllMocks();
  instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/me/permissions') return { permissions: [] };
    if (url === '/products/tcg-types') return [];
    if (url === '/me/inventory-filters') return { enabled: false, merge_same_post: true };
    if (url.startsWith('/inventory?')) return { items: [row], total: 1, page: 1, per_page: 50, window_hours: 18 };
    throw new Error(`Unexpected GET ${url}`);
  });
  mock.patch.mockResolvedValue({});
});
afterEach(() => cleanup());

const renderPage = () =>
  render(<I18nextProvider i18n={instance}><MemoryRouter><InventoryPage /></MemoryRouter></I18nextProvider>);

describe('InventoryPage settings (merge_same_post)', () => {
  it('requests merge_same_post=true by default and renders merged/blank/null-offer rows', async () => {
    renderPage();
    await screen.findByTestId('inventory-row-r1');
    expect(mock.get.mock.calls.some(([u]) => String(u).startsWith('/inventory?') && String(u).includes('merge_same_post=true'))).toBe(true);
    expect(screen.getByTestId('inventory-row-r1-merged').textContent).toBe('3 rows');
    expect(screen.getByText('sold_out')).toBeTruthy();
    expect(screen.getByText('memo')).toBeTruthy();
    expect(screen.getByTestId('inventory-expiry-warning').textContent).toContain('18 hours');
  });

  it('gear opens the drawer; toggling sends PATCH with merge_same_post and refetches with false', async () => {
    renderPage();
    await screen.findByTestId('inventory-row-r1');
    fireEvent.click(screen.getByTestId('inventory-settings-open'));
    const toggle = await screen.findByTestId('inventory-merge-toggle');
    expect(toggle.getAttribute('aria-pressed')).toBe('true');
    fireEvent.click(toggle);
    await waitFor(() => expect(toggle.getAttribute('aria-pressed')).toBe('false'));
    await waitFor(() =>
      expect(mock.patch.mock.calls.some(([u, b]) => u === '/me/inventory-filters' && (b as { merge_same_post: boolean }).merge_same_post === false)).toBe(true),
    );
    await waitFor(() =>
      expect(mock.get.mock.calls.some(([u]) => String(u).startsWith('/inventory?') && String(u).includes('merge_same_post=false'))).toBe(true),
    );
  });
});

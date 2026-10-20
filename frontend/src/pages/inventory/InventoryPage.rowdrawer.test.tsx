import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InventoryPage from './InventoryPage';
import en from '../../locales/en.json';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../../lib/api', () => ({
  api: mock,
  ApiError: class ApiError extends Error {
    status = 0;
  },
}));

vi.mock('../../features/tcg-analysis-review/ConditionReviewPanel', async () => ({
  ...(await vi.importActual<typeof import('../../features/tcg-analysis-review/ConditionReviewPanel')>('../../features/tcg-analysis-review/ConditionReviewPanel')),
  ConditionReviewPanel: (props: { onRefresh: () => Promise<void> }) => (
    <button type="button" data-testid="condition-panel" onClick={() => void props.onRefresh()}>refresh</button>
  ),
}));

const row = {
  id: 'r1', product_id: 2, product_name: 'Card', name_en: null, category: 'cat', mark: null,
  condition: 'sealed', unit: 'BOX', offer_type: 'in_stock', status: 'in_stock', note_ja: 'memo', ship_ja: 'ship',
  merged_count: 1, posted_at: null, ship_timing: null, supplier_id: 3, supplier_name: 'S',
  unit_price: 10, quantity: 2, work_code: 'pokemon_booster_box', offered_at: '', release_date: null,
  extraction_item_ids: ['item-1'],
};

const analysis = {
  items: [{
    extraction_item_id: 'item-1', source_message_id: 'msg-1', provider: 'S', raw_text: 'original line text',
    gemini: { name: 'gemini-name' }, system: { work_name: 'system-title' },
    review_reason_details: [], review_issues: [],
    condition_review: { condition_id: '1', review_version: 'v', needs_review: true, review_reasons: 'condition_unknown', confirmed: false, classification: 'none' },
  }],
};

const analysisCalls = () => mock.get.mock.calls.map(([u]) => String(u)).filter((u) => u.startsWith('/tcg/analysis-results'));

let instance = createInstance();
const setup = async (isSuperAdmin: boolean) => {
  vi.resetAllMocks();
  instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/me/permissions') return { permissions: [], is_super_admin: isSuperAdmin };
    if (url === '/products/tcg-types') return [];
    if (url === '/me/inventory-filters') return { enabled: false };
    if (url.startsWith('/inventory?')) return { items: [row], total: 1, page: 1, per_page: 50, window_hours: 18, fresh_window_hours: 24 };
    if (url.startsWith('/tcg/analysis-results')) return analysis;
    throw new Error(`Unexpected GET ${url}`);
  });
  mock.patch.mockResolvedValue({});
};
afterEach(() => cleanup());

const renderPage = () =>
  render(<I18nextProvider i18n={instance}><MemoryRouter><InventoryPage /></MemoryRouter></I18nextProvider>);

describe('InventoryPage row drawer', () => {
  beforeEach(() => vi.useRealTimers());

  it('F1: super admin click opens the panel with source, Gemini and system results', async () => {
    await setup(true);
    renderPage();
    const rowEl = await screen.findByTestId('inventory-row-r1');
    await waitFor(() => expect(mock.get).toHaveBeenCalledWith('/me/permissions'));
    await new Promise((r) => setTimeout(r, 30));
    fireEvent.click(rowEl);
    expect(await screen.findByText('original line text')).toBeTruthy();
    expect(screen.getAllByText('gemini-name').length).toBeGreaterThan(0);
    expect(screen.getAllByText('system-title').length).toBeGreaterThan(0);
    expect(analysisCalls()).toEqual(['/tcg/analysis-results?extraction_item_ids=item-1']);
  });

  it('F2: a non super admin click on PC opens the original text only and calls no analysis API', async () => {
    await setup(false);
    mock.get.mockImplementation(async (url: string) => {
      if (url === '/me/permissions') return { permissions: [], is_super_admin: false };
      if (url === '/products/tcg-types') return [];
      if (url === '/me/inventory-filters') return { enabled: false };
      if (url.startsWith('/inventory?')) return { items: [row], total: 1, page: 1, per_page: 50, window_hours: 18, fresh_window_hours: 24 };
      if (url.startsWith('/inventory/raw-texts')) return { items: [{ extraction_item_id: 'item-1', raw_text: 'staff raw text', line_start: 1, line_end: 1 }] };
      throw new Error(`Unexpected GET ${url}`);
    });
    renderPage();
    const rowEl = await screen.findByTestId('inventory-row-r1');
    await waitFor(() => expect(mock.get).toHaveBeenCalledWith('/me/permissions'));
    await new Promise((r) => setTimeout(r, 30));
    fireEvent.click(rowEl);
    expect(await screen.findByText('staff raw text')).toBeTruthy();
    expect(mock.get).toHaveBeenCalledWith('/inventory/raw-texts?extraction_item_ids=item-1');
    expect(within(screen.getByText('staff raw text').closest('[role="dialog"]') as HTMLElement).queryByRole('tab')).toBeNull();
    expect(analysisCalls()).toHaveLength(0);
  });

  it('F2b: on mobile the panel does not open for anyone', async () => {
    const original = window.matchMedia;
    window.matchMedia = ((query: string) => ({
      matches: true, media: query, onchange: null,
      addEventListener: () => undefined, removeEventListener: () => undefined,
      addListener: () => undefined, removeListener: () => undefined, dispatchEvent: () => false,
    })) as unknown as typeof window.matchMedia;
    try {
      await setup(false);
      renderPage();
      const rowEl = await screen.findByTestId('inventory-row-r1');
      await new Promise((r) => setTimeout(r, 30));
      fireEvent.click(rowEl);
      await new Promise((r) => setTimeout(r, 30));
      const rawCalls = mock.get.mock.calls.filter(([u]) => String(u).startsWith('/inventory/raw-texts'));
      expect(rawCalls).toHaveLength(0);
      expect(analysisCalls()).toHaveLength(0);
    } finally {
      window.matchMedia = original;
    }
  });

  it('F3: there is no row-select checkbox column', async () => {
    await setup(true);
    renderPage();
    await screen.findByTestId('inventory-row-r1');
    expect(screen.queryAllByRole('checkbox', { name: /select row r1/i })).toHaveLength(0);
    expect(screen.queryAllByRole('checkbox', { name: /select all/i })).toHaveLength(0);
    expect(document.querySelector('.comp-table__th--check')).toBeNull();
  });

  it('E5: a saved fix in the panel reloads /inventory (onChanged)', async () => {
    await setup(true);
    renderPage();
    const rowEl = await screen.findByTestId('inventory-row-r1');
    await waitFor(() => expect(mock.get).toHaveBeenCalledWith('/me/permissions'));
    await new Promise((r) => setTimeout(r, 30));
    fireEvent.click(rowEl);
    await screen.findByText('original line text');
    const inventoryCalls = () => mock.get.mock.calls.filter(([u]) => String(u).startsWith('/inventory?')).length;
    const before = inventoryCalls();
    fireEvent.click(screen.getByRole('row', { name: /^Condition/ }));
    fireEvent.click(screen.getByTestId('condition-panel'));
    await waitFor(() => expect(inventoryCalls()).toBe(before + 1));
  });
});

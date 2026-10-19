import { act, cleanup, render, screen } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InventoryPage from './InventoryPage';
import en from '../../locales/en.json';
import { RealtimeContext, type RealtimeApi, type RealtimeHandler } from '../../lib/realtime/context';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../../lib/api', () => ({ api: mock }));

const row = {
  id: 'r1', product_id: 2, product_name: 'Card', name_en: null, category: null, mark: null,
  condition: 'New', unit: 'BOX', offer_type: null, status: 'sold_out', note_ja: 'memo', ship_ja: 'ship',
  merged_count: 1, posted_at: null, ship_timing: null, supplier_id: 3, supplier_name: 'S',
  unit_price: 10, quantity: null, work_code: 'pokemon_booster_box', offered_at: '', release_date: null,
};

const inventoryCalls = () => mock.get.mock.calls.filter(([url]) => String(url).startsWith('/inventory?')).length;

let handler: RealtimeHandler = () => undefined;
const api: RealtimeApi = {
  clientId: 'me',
  // 実 Provider と同じく、購読した topic の合図だけを渡す（reconnected は常に渡す）
  subscribe: (topics, h) => {
    handler = (ev) => {
      if ('reconnected' in ev || topics.includes(ev.topic)) h(ev);
    };
    return () => undefined;
  },
};

let instance = createInstance();
beforeEach(async () => {
  vi.resetAllMocks();
  instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  mock.patch.mockResolvedValue({});
  vi.spyOn(Math, 'random').mockReturnValue(0);
  mock.get.mockImplementation((url: string) => {
    if (url === '/me/permissions') return Promise.resolve({ permissions: [] });
    if (url === '/products/tcg-types') return Promise.resolve([]);
    if (url === '/me/inventory-filters') {
      return Promise.resolve({ enabled: true, merge_same_post: true, hidden_supplier_ids: [], hidden_categories: [], hidden_columns: [] });
    }
    if (url.startsWith('/inventory?')) return Promise.resolve({ items: [row], total: 1, page: 1, per_page: 50, window_hours: 18 });
    return Promise.reject(new Error(`Unexpected GET ${url}`));
  });
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

async function renderLoaded() {
  render(
    <RealtimeContext.Provider value={api}>
      <I18nextProvider i18n={instance}><MemoryRouter><InventoryPage /></MemoryRouter></I18nextProvider>
    </RealtimeContext.Provider>,
  );
  await screen.findByTestId('inventory-row-r1');
  vi.useFakeTimers();
  return inventoryCalls();
}

describe('InventoryPage auto refresh (ADR-1016 revision 2026-10-18)', () => {
  it('tcg.inventory signal -> one more /inventory fetch after 5 seconds', async () => {
    const before = await renderLoaded();
    act(() => handler({ topic: 'tcg.inventory', origin: null }));
    await act(async () => { await vi.advanceTimersByTimeAsync(4_900); });
    expect(inventoryCalls()).toBe(before);
    await act(async () => { await vi.advanceTimersByTimeAsync(200); });
    expect(inventoryCalls()).toBe(before + 1);
  });

  it('three signals within 5 seconds -> one reload', async () => {
    const before = await renderLoaded();
    act(() => handler({ topic: 'tcg.inventory', origin: null }));
    await act(async () => { await vi.advanceTimersByTimeAsync(2_000); });
    act(() => handler({ topic: 'tcg.inventory', origin: null }));
    await act(async () => { await vi.advanceTimersByTimeAsync(2_000); });
    act(() => handler({ topic: 'tcg.inventory', origin: null }));
    await act(async () => { await vi.advanceTimersByTimeAsync(6_000); });
    expect(inventoryCalls()).toBe(before + 1);
  });

  it('own origin signal -> no reload', async () => {
    const before = await renderLoaded();
    act(() => handler({ topic: 'tcg.inventory', origin: 'me' }));
    await act(async () => { await vi.advanceTimersByTimeAsync(10_000); });
    expect(inventoryCalls()).toBe(before);
  });

  it('tcg.review signal -> no reload', async () => {
    const before = await renderLoaded();
    act(() => handler({ topic: 'tcg.review', origin: null }));
    await act(async () => { await vi.advanceTimersByTimeAsync(10_000); });
    expect(inventoryCalls()).toBe(before);
  });
});

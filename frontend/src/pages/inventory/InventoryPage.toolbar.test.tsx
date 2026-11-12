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
// listExtra: /inventory? 応答に重ねる値（K9・K10 が categories を足すために使う。list 定数自体は
// 他のテストと共有するため変更しない）
const setup = async (
  filters: Record<string, unknown> = { enabled: false, merge_same_post: false },
  listExtra: Record<string, unknown> = {},
) => {
  mock.get.mockImplementation((url: string) => {
    if (url === '/me/permissions') return Promise.resolve({ permissions: [] });
    if (url === '/products/tcg-types') return Promise.resolve([]);
    if (url === '/me/inventory-filters') return Promise.resolve(filters);
    if (url.startsWith('/inventory?')) return Promise.resolve({ ...list, ...listExtra });
    return Promise.reject(new Error(`Unexpected GET ${url}`));
  });
  render(<I18nextProvider i18n={instance}><MemoryRouter><InventoryPage /></MemoryRouter></I18nextProvider>);
  await screen.findByTestId('inventory-row-r1');
};
const before = (a: HTMLElement, b: HTMLElement) =>
  Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
// Drawer は閉じても中身を DOM に残す（frontend/src/components/Drawer.tsx「DOM は常にマウント」）。
// 開閉は --open クラスで見る（先例 frontend/src/pages/viewer/InventoryView.test.tsx）
const openPanel = () => document.querySelector('.comp-drawer-panel--open') as HTMLElement | null;

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
  it('K6: no ContentToolbar on mobile, shows .inventory-toolbar (search -> type -> sort -> detail filter); detail-filter items live only inside the (always-mounted) drawer, not in the top toolbar', async () => {
    stubMatchMedia(true);
    await setup();
    expect(document.querySelector('.content-toolbar')).toBeNull();
    expect(document.querySelector('.inventory-toolbar')).not.toBeNull();
    expect(screen.queryByTestId('inventory-reset-sort')).toBeNull();
    expect(screen.queryByTestId('inventory-fresh-toggle')).toBeNull();
    // design.md 4-3: Drawer は閉じても中身を DOM に残す作りに変わったため、開く前から
    // inventory-price-min 等が DOM 上に存在する。toBeNull では確かめられない（実測:
    // 1 failed/40 passed・このテストの元の135行目 queryByTestId('inventory-price-min').toBeNull() が
    // 落ちた。design.md 4-9 (1) の「K6 は作り替え不要」は誤り）。
    // 「開く前は閉じている」「上の操作台の中には無い」の2つに分けて確かめる
    expect(openPanel()).toBeNull();
    const toolbar = document.querySelector('.inventory-toolbar')!;
    expect(toolbar.contains(screen.getByTestId('inventory-price-min'))).toBe(false);
    expect(toolbar.contains(screen.getByTestId('inventory-fresh-check'))).toBe(false);
    // design.md 4-9 (1): コンディションは MultiSelect layout="row" になり、button は出ない
    // （frontend/src/components/MultiSelect.tsx:21「button は inline/row では出さない」）。
    // 目印は -row（inventory-condition-filter-row）に変わった
    expect(screen.queryByTestId('inventory-condition-filter-button')).toBeNull();
    // design.md 4-2: 4つ（検索・種別・並び替え・詳細フィルタ）。並び替えはボタン（select ではない）
    const order = ['inventory-search', 'inventory-tab-select', 'inventory-sort-menu', 'inventory-filter-toggle']
      .map((id) => screen.getByTestId(id));
    for (let i = 0; i < order.length - 1; i++) expect(before(order[i], order[i + 1])).toBe(true);
    expect(screen.getByTestId('inventory-sort-menu').tagName).not.toBe('SELECT');

    fireEvent.click(screen.getByTestId('inventory-filter-toggle'));
    const panel = openPanel();
    expect(panel).not.toBeNull();
    for (const id of ['inventory-fresh-check', 'inventory-condition-filter-row', 'inventory-price-min', 'inventory-qty-max', 'inventory-reset-in-panel', 'inventory-expiry-warning']) {
      expect(panel!.contains(screen.getByTestId(id))).toBe(true);
    }
  });

  it('K7 (design.md 4-2・K4): tapping inventory-tab-select opens a panel; picking a type applies it and closes; picking the same type again also closes', async () => {
    stubMatchMedia(true);
    await setup();
    expect(openPanel()).toBeNull();
    fireEvent.click(screen.getByTestId('inventory-tab-select'));
    const panel = openPanel();
    expect(panel).not.toBeNull();
    const option = screen.getByTestId('inventory-type-option-one_piece');
    expect(panel?.contains(option)).toBe(true);
    fireEvent.click(option);
    await waitFor(() => expect(lastCall()).toContain('work_code=one_piece'));
    expect(openPanel()).toBeNull();

    // すでに選ばれている行をもう一度押しても閉じる（K4）
    fireEvent.click(screen.getByTestId('inventory-tab-select'));
    expect(openPanel()).not.toBeNull();
    fireEvent.click(screen.getByTestId('inventory-type-option-one_piece'));
    expect(openPanel()).toBeNull();
  });

  it('K8 (design.md 4-2・K6): tapping inventory-sort-menu opens a panel; a non-default pick shows its label, then "default" reverts to the placeholder', async () => {
    stubMatchMedia(true);
    await setup();
    const sortTrigger = screen.getByTestId('inventory-sort-menu');
    fireEvent.click(sortTrigger);
    expect(openPanel()?.contains(screen.getByTestId('inventory-sort-option-unit_price:asc'))).toBe(true);
    fireEvent.click(screen.getByTestId('inventory-sort-option-unit_price:asc'));
    await waitFor(() => expect(lastCall()).toContain('sort=unit_price'));
    expect(openPanel()).toBeNull();
    expect(screen.getByTestId('inventory-sort-menu').textContent).toContain(en.inventory.sortMenu.priceAsc);

    fireEvent.click(screen.getByTestId('inventory-sort-menu'));
    expect(openPanel()).not.toBeNull();
    fireEvent.click(screen.getByTestId('inventory-sort-option-release_date:desc'));
    await waitFor(() => expect(lastCall()).toContain('sort=release_date'));
    expect(openPanel()).toBeNull();
    expect(screen.getByTestId('inventory-sort-menu').textContent).toContain(en.inventory.sortMenu.placeholder);
  });

  it('K9 (design.md 4-5, review H2): selecting a hide-series candidate keeps a saved hidden value that is outside the candidate list', async () => {
    stubMatchMedia(true);
    // eslint-disable-next-line local/no-japanese-literal -- fixture value standing in for a saved category name
    const outsideHidden = 'ZZZ_候補に無い';
    await setup(
      { enabled: false, merge_same_post: false, hidden_categories: [outsideHidden], hidden_columns: [] },
      { categories: ['Card'] },
    );
    fireEvent.click(screen.getByTestId('inventory-filter-toggle'));
    expect(openPanel()).not.toBeNull();
    fireEvent.click(screen.getByTestId('inventory-category-filter-row'));
    fireEvent.click(await screen.findByTestId('inventory-category-filter-option-Card'));

    // 「(いまの集合 − 候補) ∪ next」で計算するため、候補 ['Card'] の外にある outsideHidden は
    // PATCH の hidden_categories から消えない（design.md 4-5・審査 H2 の歯止め）
    await waitFor(() => {
      const calls = mock.patch.mock.calls;
      const payload = calls[calls.length - 1]?.[1] as { hidden_categories?: string[] } | undefined;
      expect(payload?.hidden_categories).toContain(outsideHidden);
      expect(payload?.hidden_categories).toContain('Card');
    });
  });

  it('K10 (design.md 4-5a, PO decision 6): picking a hide-series candidate auto-enables the "enable filter" checkbox', async () => {
    stubMatchMedia(true);
    await setup({ enabled: false, merge_same_post: false }, { categories: ['Card'] });
    fireEvent.click(screen.getByTestId('inventory-filter-toggle'));
    expect(openPanel()).not.toBeNull();
    expect((screen.getByTestId('inventory-filter-enabled') as HTMLInputElement).checked).toBe(false);

    fireEvent.click(screen.getByTestId('inventory-category-filter-row'));
    fireEvent.click(await screen.findByTestId('inventory-category-filter-option-Card'));
    // 「決定する」で root に戻る（root にしか inventory-filter-enabled は無い）
    fireEvent.click(screen.getByTestId('inventory-filter-apply'));

    await waitFor(() => {
      expect((screen.getByTestId('inventory-filter-enabled') as HTMLInputElement).checked).toBe(true);
    });
  });

  it('K11 (design.md 4-5/4-5a, review r2): hiding a column via the drawer actually removes it from the row, enables the filter, and keeps a saved hidden_columns value outside HIDEABLE_COLUMNS', async () => {
    stubMatchMedia(true);
    const outsideHidden = 'ZZZ_candidate_outside';
    await setup({ enabled: false, merge_same_post: false, hidden_columns: [outsideHidden] });

    // mkRow's "condition" is 'New' — the only place that literal text appears inside row r1,
    // so it doubles as a direct signal that the "condition" column has been removed from render
    // (frontend/src/pages/inventory/InventoryPage.tsx:276 confirms colVisible only takes effect
    // once filterEnabled is true; frontend/src/features/inventory/inventoryColumns.tsx:217 drops
    // the whole column — not just its value — from the columns array when hidden).
    expect(screen.getByTestId('inventory-row-r1').textContent).toContain('New');

    fireEvent.click(screen.getByTestId('inventory-filter-toggle'));
    expect(openPanel()).not.toBeNull();
    expect((screen.getByTestId('inventory-filter-enabled') as HTMLInputElement).checked).toBe(false);

    fireEvent.click(screen.getByTestId('inventory-columns-filter-row'));
    fireEvent.click(await screen.findByTestId('inventory-columns-filter-option-condition'));
    fireEvent.click(screen.getByTestId('inventory-filter-apply'));

    // 期待①: 有効化が自動で入る（filterEnabled が切だと colVisible は常に表示扱いなので列は消えない）
    await waitFor(() => {
      expect((screen.getByTestId('inventory-filter-enabled') as HTMLInputElement).checked).toBe(true);
    });

    // 期待②: 一覧の行から該当列（condition="New"）の中身が消える
    await waitFor(() => {
      expect(screen.getByTestId('inventory-row-r1').textContent).not.toContain('New');
    });

    // 期待③: 「(いまの集合 − 候補) ∪ next」のため、HIDEABLE_COLUMNS の外にある保存値は消えない
    // （K9 のシリーズ版と対になる歯止め・審査 H2 相当）
    await waitFor(() => {
      const calls = mock.patch.mock.calls;
      const payload = calls[calls.length - 1]?.[1] as { hidden_columns?: string[] } | undefined;
      expect(payload?.hidden_columns).toContain(outsideHidden);
      expect(payload?.hidden_columns).toContain('condition');
    });
  });
});

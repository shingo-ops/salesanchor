import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import UnitsPage from '../pages/units/UnitsPage';
import ProductCategoriesPage from '../pages/product-categories/ProductCategoriesPage';
import SuppliersPage from '../pages/suppliers/SuppliersPage';
import ConditionsPage from '../pages/conditions/ConditionsPage';
import StatusMasterPage from '../pages/status-master/StatusMasterPage';
import en from '../locales/en.json';

const mock = vi.hoisted(() => ({ get: vi.fn(), getBlob: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../lib/api', () => ({ api: mock }));
let instance = createInstance();
const tr = (key: string) => String(instance.t(key));
const remotes = {
  units: { Page: UnitsPage, input: 'units-search', button: 'units-search-btn', prefix: '/units?' },
  categories: { Page: ProductCategoriesPage, input: 'product-categories-search', button: 'product-categories-search-btn', prefix: '/product-categories?', perPage: 50 },
  suppliers: { Page: SuppliersPage, input: 'suppliers-search', button: 'suppliers-search-btn', prefix: '/suppliers?' },
  conditions: { Page: ConditionsPage, input: 'conditions-search', button: 'conditions-search-btn', prefix: '/conditions?', perPage: 50 },
  statuses: { Page: StatusMasterPage, input: 'status-master-search', button: 'status-master-search-btn', prefix: '/status-master?' },
} as const;
type Remote = keyof typeof remotes;
const remoteCases = (Object.keys(remotes) as Remote[]).flatMap(kind => (['click', 'enter'] as const).map(input => ({ kind, input })));

beforeEach(async () => {
  vi.resetAllMocks(); instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/me/permissions') return { permissions: [] };
    if (url === '/conditions/catalog') return [];
    if (url.startsWith('/units?') || url.startsWith('/product-categories?') || url.startsWith('/suppliers?') || url.startsWith('/conditions?') || url.startsWith('/status-master?')) return [];
    throw new Error('Unexpected GET ' + url);
  });
  for (const method of ['post', 'patch', 'delete'] as const) mock[method].mockImplementation(() => { throw new Error('Unexpected write'); });
});
afterEach(() => { cleanup(); expect(fetch).not.toHaveBeenCalled(); expect(mock.post).not.toHaveBeenCalled(); expect(mock.patch).not.toHaveBeenCalled(); expect(mock.delete).not.toHaveBeenCalled(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('master search Button migration', () => {
  it.each(remoteCases)('$kind keeps exact trimmed encoded GET through $input and clear resets page one', async ({ kind, input }) => {
    const c = remotes[kind], Page = c.Page;
    render(<I18nextProvider i18n={instance}><MemoryRouter><Page /></MemoryRouter></I18nextProvider>);
    await waitFor(() => expect(mock.get.mock.calls.some(call => String(call[0]).startsWith(c.prefix))).toBe(true));
    const field = screen.getByTestId(c.input) as HTMLInputElement;
    fireEvent.change(field, { target: { value: '  A & B  ' } });
    if (input === 'click') fireEvent.click(screen.getByTestId(c.button));
    else { const user = userEvent.setup(); await user.click(field); await user.keyboard('{Enter}'); }
    const perPage = 'perPage' in c ? c.perPage : 100;
    const expected = c.prefix + `page=1&per_page=${perPage}&search=A+%26+B`;
    await waitFor(() => expect(mock.get).toHaveBeenCalledWith(expected));
    const target = screen.getByTestId(c.button) as HTMLButtonElement;
    expect(target.type).toBe('submit'); expect(target.className).toBe('comp-btn comp-btn--secondary');
    fireEvent.click(screen.getByRole('button', { name: tr('common.clear') }));
    await waitFor(() => expect(mock.get).toHaveBeenCalledWith(c.prefix + `page=1&per_page=${perPage}`));
    expect(field.value).toBe('');
  });
});

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MasterListEditor, type MasterDataSource } from './master-list-editor/MasterListEditor';
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

  it.each(['click', 'enter'] as const)('MasterList local search trims/clears without another source call via %s', async input => {
    const source: MasterDataSource = {
      list: vi.fn().mockResolvedValue([{ id: 1, name_ja: 'Alpha target', name_en: null }, { id: 2, name_ja: 'Beta', name_en: null }]),
      create: vi.fn(), update: vi.fn(), remove: vi.fn(), reorder: vi.fn(),
    };
    render(<I18nextProvider i18n={instance}><MasterListEditor source={source} /></I18nextProvider>);
    await screen.findByText('Alpha target');
    const field = screen.getByPlaceholderText(tr('superAdmin.attrMasters.searchPlaceholder')) as HTMLInputElement;
    fireEvent.change(field, { target: { value: '  alpha  ' } });
    if (input === 'click') fireEvent.click(screen.getByRole('button', { name: tr('common.search') }));
    else { const user = userEvent.setup(); await user.click(field); await user.keyboard('{Enter}'); }
    expect(screen.queryByText('Beta')).toBeNull(); expect(screen.getByText('Alpha target')).toBeTruthy();
    expect(source.list).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', { name: tr('common.clear') }));
    expect(screen.getByText('Beta')).toBeTruthy(); expect(field.value).toBe(''); expect(source.list).toHaveBeenCalledTimes(1);
  });

  it('MasterList add/edit/cancel preserves trimmed callbacks, required guard and grid placement', async () => {
    const source: MasterDataSource = {
      list: vi.fn().mockResolvedValue([{ id: 1, name_ja: 'Existing', name_en: 'Old' }]), create: vi.fn().mockResolvedValue(undefined),
      update: vi.fn().mockResolvedValue(undefined), remove: vi.fn(), reorder: vi.fn(),
    };
    render(<I18nextProvider i18n={instance}><MasterListEditor source={source} /></I18nextProvider>); await screen.findByText('Existing');
    const ja = screen.getByLabelText(tr('superAdmin.attrMasters.col.labelJa')) as HTMLInputElement;
    const enField = screen.getByLabelText(tr('superAdmin.attrMasters.col.labelEn')) as HTMLInputElement;
    const add = screen.getByRole('button', { name: tr('superAdmin.attrMasters.addBtn') }) as HTMLButtonElement;
    expect(add.type).toBe('submit'); expect(add.closest('form')?.style.display).toBe('grid');
    fireEvent.change(ja, { target: { value: '  New  ' } }); fireEvent.change(enField, { target: { value: '   ' } }); fireEvent.click(add);
    await waitFor(() => expect(source.create).toHaveBeenCalledExactlyOnceWith('New', null));
    fireEvent.click(screen.getByRole('button', { name: tr('common.edit') }));
    fireEvent.change(ja, { target: { value: '  Edited  ' } }); fireEvent.click(screen.getByRole('button', { name: tr('common.update') }));
    await waitFor(() => expect(source.update).toHaveBeenCalledExactlyOnceWith(1, 'Edited', 'Old'));
    fireEvent.click(screen.getByRole('button', { name: tr('common.edit') })); fireEvent.click(screen.getByRole('button', { name: tr('common.cancel') }));
    expect(ja.value).toBe(''); expect(source.update).toHaveBeenCalledTimes(1);
    expect(ja.required).toBe(true); fireEvent.click(add); expect(source.create).toHaveBeenCalledTimes(1);
  });

  it.each(['create', 'edit'] as const)('MasterList %s retains values on failure and retries', async mode => {
    const send = vi.fn().mockRejectedValueOnce(new Error('Fixture master failure')).mockResolvedValueOnce(undefined);
    const source: MasterDataSource = { list: vi.fn().mockResolvedValue([{ id: 1, name_ja: 'Existing', name_en: 'Old' }]), create: mode === 'create' ? send : vi.fn(), update: mode === 'edit' ? send : vi.fn(), remove: vi.fn(), reorder: vi.fn() };
    render(<I18nextProvider i18n={instance}><MasterListEditor source={source} /></I18nextProvider>); await screen.findByText('Existing');
    if (mode === 'edit') fireEvent.click(screen.getByRole('button', { name: tr('common.edit') }));
    const ja = screen.getByLabelText(tr('superAdmin.attrMasters.col.labelJa')) as HTMLInputElement;
    fireEvent.change(ja, { target: { value: ' Retry value ' } });
    const save = screen.getByRole('button', { name: tr(mode === 'create' ? 'superAdmin.attrMasters.addBtn' : 'common.update') }) as HTMLButtonElement;
    fireEvent.click(save); expect(await screen.findByText('Fixture master failure')).toBeTruthy(); expect(ja.value).toBe(' Retry value ');
    fireEvent.click(save); await waitFor(() => expect(send).toHaveBeenCalledTimes(2)); await waitFor(() => expect(ja.value).toBe(''));
  });

  it.each(['create', 'edit'] as const)('MasterList %s preserves unlocked duplicate pending submissions', async mode => {
    let resolve!: () => void; const pending = new Promise<void>(res => { resolve = res; }); const send = vi.fn().mockReturnValue(pending);
    const source: MasterDataSource = { list: vi.fn().mockResolvedValue([{ id: 1, name_ja: 'Existing', name_en: 'Old' }]), create: mode === 'create' ? send : vi.fn(), update: mode === 'edit' ? send : vi.fn(), remove: vi.fn(), reorder: vi.fn() };
    render(<I18nextProvider i18n={instance}><MasterListEditor source={source} /></I18nextProvider>); await screen.findByText('Existing');
    if (mode === 'edit') fireEvent.click(screen.getByRole('button', { name: tr('common.edit') }));
    const ja = screen.getByLabelText(tr('superAdmin.attrMasters.col.labelJa')) as HTMLInputElement; fireEvent.change(ja, { target: { value: ' Pending ' } });
    const save = screen.getByRole('button', { name: tr(mode === 'create' ? 'superAdmin.attrMasters.addBtn' : 'common.update') }) as HTMLButtonElement;
    fireEvent.click(save); fireEvent.click(save); expect(send).toHaveBeenCalledTimes(2); expect(save.disabled).toBe(false); expect(save.getAttribute('aria-busy')).toBeNull(); expect(ja.value).toBe(' Pending ');
    resolve(); await waitFor(() => expect(ja.value).toBe(''));
  });
});

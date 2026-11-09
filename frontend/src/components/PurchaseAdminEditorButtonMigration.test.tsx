import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { rowMenuLabelKey } from '../constants/menuPermissions';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import RolesPage from '../pages/roles/RolesPage';
import en from '../locales/en.json';
import { queryClient } from '../lib/query/apiQuery';
import { registerTestDevSession } from '../test-utils/devSession';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../lib/api', () => ({ api: mock }));
let instance = createInstance(); const tr = (key: string) => String(instance.t(key));
function wrap(node: React.ReactNode) { return <I18nextProvider i18n={instance}><MemoryRouter>{node}</MemoryRouter></I18nextProvider>; }
const role = { id: 1, name: 'Role fixture', color: null, priority: 500, description: null, is_system: false, user_count: 0 };
const permission = { id: 10, key: 'customers.view', description: 'View customers', category: 'customers' };

beforeEach(async () => {
  vi.resetAllMocks(); instance = createInstance(); await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  registerTestDevSession({ getAccessToken: async () => 'token', hasSession: () => true });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/me/permissions') return { permissions: ['purchase_orders.create', 'roles.update'] };
    if (url.startsWith('/purchase-orders')) return [];
    if (url === '/suppliers/catalog') return [{ id: 7, name: 'Supplier', is_active: true }];
    if (url === '/roles?scope=role_page') return [role]; if (url === '/permissions') return [permission]; if (url === '/roles/1/permissions') return [permission];
    throw new Error('Unexpected GET ' + url);
  });
  for (const method of ['post', 'put', 'patch', 'delete'] as const) mock[method].mockImplementation(() => { throw new Error('Unexpected ' + method); });
});
afterEach(() => { cleanup(); queryClient.clear(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('purchase and admin editor Button migration', () => {
  it('role permission cancel restores the server baseline and writes zero', async () => {
    render(wrap(<RolesPage />)); await screen.findAllByText('Role fixture');
    const group = await screen.findByRole('radiogroup', { name: tr(rowMenuLabelKey('leads')) });
    const viewOnly = within(group).getByRole('radio', { name: tr('roles.stateView') }) as HTMLButtonElement;
    const hidden = within(group).getByRole('radio', { name: tr('roles.stateOff') }) as HTMLButtonElement;
    await waitFor(() => expect(viewOnly.getAttribute('aria-checked')).toBe('true'));
    const cancel = screen.getByRole('button', { name: tr('roles.cancelChanges') }) as HTMLButtonElement; expect(cancel.disabled).toBe(true); fireEvent.click(hidden);
    expect(hidden.getAttribute('aria-checked')).toBe('true'); expect(viewOnly.getAttribute('aria-checked')).toBe('false'); expect(cancel.disabled).toBe(false); fireEvent.click(cancel);
    expect(viewOnly.getAttribute('aria-checked')).toBe('true'); expect(cancel.disabled).toBe(true); expect(mock.put).not.toHaveBeenCalled();
  });
});

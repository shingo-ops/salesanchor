import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import RolesPage from '../pages/roles/RolesPage';
import en from '../locales/en.json';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../lib/api', () => ({ api: mock }));
vi.mock('../lib/firebase', () => ({ auth: { currentUser: { getIdToken: vi.fn().mockResolvedValue('token') } } }));
let instance = createInstance(); const tr = (key: string) => String(instance.t(key));
function wrap(node: React.ReactNode) { return <I18nextProvider i18n={instance}><MemoryRouter>{node}</MemoryRouter></I18nextProvider>; }
const role = { id: 1, name: 'Role fixture', color: null, priority: 500, description: null, is_system: false, user_count: 0 };
const permission = { id: 10, key: 'customers.view', description: 'View customers', category: 'customers' };

beforeEach(async () => {
  vi.resetAllMocks(); instance = createInstance(); await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/me/permissions') return { permissions: ['purchase_orders.create', 'roles.update'] };
    if (url.startsWith('/purchase-orders')) return [];
    if (url === '/suppliers/catalog') return [{ id: 7, name: 'Supplier', is_active: true }];
    if (url === '/roles') return [role]; if (url === '/permissions') return [permission]; if (url === '/roles/1/permissions') return [permission];
    throw new Error('Unexpected GET ' + url);
  });
  for (const method of ['post', 'put', 'patch', 'delete'] as const) mock[method].mockImplementation(() => { throw new Error('Unexpected ' + method); });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('purchase and admin editor Button migration', () => {
  it('role permission cancel restores the server baseline and writes zero', async () => {
    render(wrap(<RolesPage />)); await screen.findAllByText('Role fixture'); const checkbox = await screen.findByRole('checkbox', { name: /View customers/ }) as HTMLInputElement; await waitFor(() => expect(checkbox.checked).toBe(true));
    const cancel = screen.getByRole('button', { name: tr('roles.cancelChanges') }) as HTMLButtonElement; expect(cancel.disabled).toBe(true); fireEvent.click(checkbox); expect(checkbox.checked).toBe(false); expect(cancel.disabled).toBe(false); fireEvent.click(cancel);
    expect(checkbox.checked).toBe(true); expect(cancel.disabled).toBe(true); expect(mock.put).not.toHaveBeenCalled();
  });
});

import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import PurchaseOrdersFormModal from '../pages/purchase-orders/PurchaseOrdersFormModal';
import PurchaseOrdersPage from '../pages/purchase-orders/PurchaseOrdersPage';
import RolesPage from '../pages/roles/RolesPage';
import en from '../locales/en.json';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../lib/api', () => ({ api: mock }));
vi.mock('../lib/firebase', () => ({ auth: { currentUser: { getIdToken: vi.fn().mockResolvedValue('token') } } }));
let instance = createInstance(); const tr = (key: string) => String(instance.t(key));
function wrap(node: React.ReactNode) { return <I18nextProvider i18n={instance}><MemoryRouter>{node}</MemoryRouter></I18nextProvider>; }
const role = { id: 1, name: 'Role fixture', color: null, priority: 500, description: null, is_system: false, user_count: 0 };
const permission = { id: 10, key: 'customers.view', description: 'View customers', category: 'customers' };
function deferred() { let resolve!: (v: unknown) => void; let reject!: (e: Error) => void; const promise = new Promise((res, rej) => { resolve = res; reject = rej; }); return { promise, resolve, reject }; }

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
  it('purchase-order form cancel calls onClose with zero writes', async () => {
    const close = vi.fn(); render(wrap(<PurchaseOrdersFormModal open onClose={close} onCreated={vi.fn()} />)); await screen.findByRole('option', { name: 'Supplier' });
    const cancel = screen.getByRole('button', { name: tr('common.cancel') }) as HTMLButtonElement; expect(cancel.type).toBe('button'); expect(cancel.disabled).toBe(false); fireEvent.click(cancel); expect(close).toHaveBeenCalledTimes(1);
    expect(mock.post).not.toHaveBeenCalled(); expect(mock.put).not.toHaveBeenCalled(); expect(mock.patch).not.toHaveBeenCalled();
  });

  it('purchase-order form cancel remains disabled and inert while save is pending, then recovers on failure', async () => {
    const close = vi.fn(), pending = deferred(); mock.post.mockReturnValue(pending.promise);
    render(wrap(<PurchaseOrdersFormModal open onClose={close} onCreated={vi.fn()} initialSupplierId={7} initialItems={[{ product_id: 8, product_name: 'Product', quantity: 1, unit_cost: 100 }]} pickerless />));
    await screen.findByRole('option', { name: 'Supplier' }); const save = screen.getByRole('button', { name: tr('common.save') }); const cancel = screen.getByRole('button', { name: tr('common.cancel') }) as HTMLButtonElement; fireEvent.click(save);
    expect(mock.post).toHaveBeenCalledExactlyOnceWith('/purchase-orders', { supplier_id: 7, notes: null, items: [{ product_id: 8, quantity: 1, unit_cost: 100 }] }); expect(cancel.disabled).toBe(true); fireEvent.click(cancel); expect(close).not.toHaveBeenCalled();
    pending.reject(new Error('save failed')); expect(await screen.findByText('save failed')).toBeTruthy(); expect(cancel.disabled).toBe(false); expect(screen.getByRole('dialog')).toBeTruthy();
  });

  it('purchase-order new opener clears an inventory-prefilled order, loads suppliers and cancels without writes', async () => {
    render(<I18nextProvider i18n={instance}><MemoryRouter initialEntries={[{ pathname: '/purchase-orders', state: { selectedProducts: [{ product_id: 8, product_name: 'Inventory product', unit_price: 100, supplier_id: 7, supplier_name: 'Supplier' }] } }]}><PurchaseOrdersPage /></MemoryRouter></I18nextProvider>);
    let dialog = await screen.findByRole('dialog', { name: tr('purchaseOrders.newPO') }); await screen.findByRole('option', { name: 'Supplier' });
    expect((dialog.querySelector('select') as HTMLSelectElement).value).toBe('7'); expect((within(dialog).getByDisplayValue('Inventory product') as HTMLInputElement).value).toBe('Inventory product');
    fireEvent.click(within(dialog).getByRole('button', { name: tr('common.cancel') })); expect(screen.queryByRole('dialog')).toBeNull();
    const opener = await screen.findByTestId('po-new-btn'); const before = mock.get.mock.calls.filter(c => c[0] === '/suppliers/catalog').length; fireEvent.click(opener);
    dialog = await screen.findByRole('dialog', { name: tr('purchaseOrders.newPO') }); await waitFor(() => expect(mock.get.mock.calls.filter(c => c[0] === '/suppliers/catalog')).toHaveLength(before + 1));
    expect((dialog.querySelector('select') as HTMLSelectElement).value).toBe(''); expect((dialog.querySelector('input[readonly]') as HTMLInputElement).value).toBe(''); fireEvent.click(within(dialog).getByRole('button', { name: tr('common.cancel') })); expect(screen.queryByRole('dialog')).toBeNull(); expect(mock.post).not.toHaveBeenCalled();
  });

  it('role permission cancel restores the server baseline and writes zero', async () => {
    render(wrap(<RolesPage />)); await screen.findAllByText('Role fixture'); const checkbox = await screen.findByRole('checkbox', { name: /View customers/ }) as HTMLInputElement; await waitFor(() => expect(checkbox.checked).toBe(true));
    const cancel = screen.getByRole('button', { name: tr('roles.cancelChanges') }) as HTMLButtonElement; expect(cancel.disabled).toBe(true); fireEvent.click(checkbox); expect(checkbox.checked).toBe(false); expect(cancel.disabled).toBe(false); fireEvent.click(cancel);
    expect(checkbox.checked).toBe(true); expect(cancel.disabled).toBe(true); expect(mock.put).not.toHaveBeenCalled();
  });
});

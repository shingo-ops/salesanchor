import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import PurchaseOrdersFormModal from '../pages/purchase-orders/PurchaseOrdersFormModal';
import en from '../locales/en.json';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn(), delete: vi.fn() }));
vi.mock('../lib/api', () => ({ api: mock }));
let instance = createInstance(); const tr = (key: string) => String(instance.t(key));
function deferred() { let resolve!: (v: unknown) => void; let reject!: (e: Error) => void; const promise = new Promise((r, j) => { resolve = r; reject = j; }); return { promise, resolve, reject }; }
function wrap(node: React.ReactNode) { return <I18nextProvider i18n={instance}><MemoryRouter>{node}</MemoryRouter></I18nextProvider>; }

beforeEach(async () => {
  vi.resetAllMocks(); instance = createInstance(); await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } }); vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  mock.get.mockImplementation(async (url: string) => { if (url === '/suppliers/catalog') return [{ id: 7, name: 'Supplier', is_active: true }]; throw new Error(`Unexpected GET ${url}`); });
  for (const method of ['post', 'patch', 'put', 'delete'] as const) mock[method].mockImplementation(() => { throw new Error(`Unexpected ${method}`); });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('purchase and admin master save Button migration', () => {
  it('PO exact payload blocks pending repeats and calls success callbacks in order', async () => {
    const events: string[] = [], pending = deferred(); mock.post.mockReturnValue(pending.promise); render(wrap(<PurchaseOrdersFormModal open onCreated={() => events.push('created')} onClose={() => events.push('closed')} initialSupplierId={7} initialItems={[{ product_id: 8, product_name: 'Product', quantity: 2, unit_cost: 100 }, { product_id: 9, product_name: 'Second', quantity: 3, unit_cost: 50 }]} pickerless />)); await screen.findByRole('option', { name: 'Supplier' }); const dialog = screen.getByRole('dialog'); fireEvent.change(dialog.querySelector('textarea')!, { target: { value: ' note ' } }); const save = within(dialog).getByRole('button', { name: tr('common.save') }) as HTMLButtonElement; const cancel = within(dialog).getByRole('button', { name: tr('common.cancel') }) as HTMLButtonElement;
    fireEvent.click(save); expect(mock.post).toHaveBeenCalledExactlyOnceWith('/purchase-orders', { supplier_id: 7, notes: ' note ', items: [{ product_id: 8, quantity: 2, unit_cost: 100 }, { product_id: 9, quantity: 3, unit_cost: 50 }] }); expect(save.disabled).toBe(true); expect(cancel.disabled).toBe(true); fireEvent.click(save); fireEvent.click(cancel); expect(mock.post).toHaveBeenCalledTimes(1); expect(events).toEqual([]);
    await act(async () => pending.resolve({})); await waitFor(() => expect(events).toEqual(['created', 'closed']));
  });

  it('PO guards at zero writes and retains values for failure retry', async () => {
    render(wrap(<PurchaseOrdersFormModal open onCreated={vi.fn()} onClose={vi.fn()} />)); await screen.findByRole('option', { name: 'Supplier' }); fireEvent.submit(document.getElementById('po-form')!); expect(mock.post).not.toHaveBeenCalled(); fireEvent.change(screen.getByRole('combobox'), { target: { value: '7' } }); fireEvent.submit(document.getElementById('po-form')!); expect(mock.post).not.toHaveBeenCalled(); expect(await screen.findByText(tr('purchaseOrders.itemsRequired'))).toBeTruthy();
    cleanup(); const events: string[] = []; mock.post.mockRejectedValueOnce(new Error('PO failed')).mockResolvedValueOnce({}); render(wrap(<PurchaseOrdersFormModal open onCreated={() => events.push('created')} onClose={() => events.push('closed')} initialSupplierId={7} initialItems={[{ product_id: 8, product_name: 'Product', quantity: 1, unit_cost: 10 }]} pickerless />)); await screen.findByRole('option', { name: 'Supplier' }); const notes = document.querySelector('textarea')!; fireEvent.change(notes, { target: { value: 'retained note' } }); fireEvent.click(screen.getByRole('button', { name: tr('common.save') })); expect(await screen.findByText('PO failed')).toBeTruthy(); expect((screen.getByRole('combobox') as HTMLSelectElement).value).toBe('7'); expect(notes.value).toBe('retained note'); expect((screen.getByDisplayValue('Product') as HTMLInputElement).value).toBe('Product'); expect(events).toEqual([]); const firstPayload = mock.post.mock.calls[0]; fireEvent.click(screen.getByRole('button', { name: tr('common.save') })); await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(2)); expect(mock.post.mock.calls[1]).toEqual(firstPayload); await waitFor(() => expect(events).toEqual(['created', 'closed']));
  });
});

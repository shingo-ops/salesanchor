import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ConfirmModal from './ConfirmModal';
import CommissionPanel from './CommissionPanel';
import PriorityScoreOverride from './PriorityScoreOverride';
import OrderFinancialPanel from './OrderFinancialPanel';
import PurchaseDetailPanel from './PurchaseDetailPanel';
import ShippingDetailPanel from './ShippingDetailPanel';
import type { CustomerScoreData } from './PriorityScoreBadge';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), permission: vi.fn(), token: vi.fn() }));
vi.mock('../lib/api', () => ({ api: mock, ApiError: class extends Error { constructor(message: string, public status: number, public responseDetail: unknown) { super(message); } } }));
vi.mock('../lib/firebase', () => ({ auth: { currentUser: { getIdToken: mock.token } } }));
vi.mock('../hooks/usePermissions', () => ({ usePermissions: () => ({ hasPermission: mock.permission }) }));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));

const originalURL = URL;
const originalCreateObjectURL = URL.createObjectURL;
const originalRevokeObjectURL = URL.revokeObjectURL;

const roles = ['sales', 'order', 'ship', 'purchase', 'trouble'];
const bundle = { order_id: 7, commissions: Object.fromEntries(roles.map(role => [role, { id: 1, role, staff_id: 2, staff_name: 'Staff', calculated_amount: 100 }])) };
const financialKeys = ['revenue_amount', 'purchase_cost', 'purchase_shipping', 'paypal_fee', 'wise_fee', 'exchange_fee', 'outsource_fee', 'packing_fee', 'ad_cost', 'return_fee', 'refund_amount', 'commission_base_amount', 'tax_refund'];
const financial = { id: 1, ...Object.fromEntries(financialKeys.map(k => [k, 0])), notes: null };
const purchaseText = ['purchase_staff', 'transaction_no', 'supplier_name', 'supplier_url', 'carrier_name', 'waybill_no', 'purchase_date', 'purchase_note', 'purchase_status'];
const purchaseNumbers = ['purchase_amount', 'purchase_quantity', 'purchase_total', 'purchase_shipping'];
const purchase = { id: 1, ...Object.fromEntries([...purchaseText, ...purchaseNumbers].map(k => [k, null])) };
const shippingText = ['recipient_name', 'phone', 'email', 'tax_number', 'address1', 'address2', 'address3', 'city', 'state_code', 'zip_code', 'country_code', 'packing_memo', 'packing_type', 'inspection_status', 'item_description', 'hs_code', 'tax_id', 'fedex_id', 'ship_method', 'tracking_number', 'carrier', 'ship_date', 'ship_memo'];
const shippingNumbers = ['length_cm', 'width_cm', 'height_cm', 'weight_kg', 'volume_g', 'box_count', 'item_price_usd', 'exchange_rate', 'est_shipping_fee'];
const shipping = { id: 1, ...Object.fromEntries([...shippingText, ...shippingNumbers].map(k => [k, null])) };
const currentScore = { score: 0.4, override_score: null } as CustomerScoreData;
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(r => { resolve = r; }); return { promise, resolve }; }
function button(id: string) { return screen.getByTestId(id) as HTMLButtonElement; }

beforeEach(() => {
  vi.clearAllMocks();
  mock.permission.mockReturnValue(true);
  mock.token.mockResolvedValue('fixture-token');
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network request'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/orders/7/commissions') return bundle;
    if (url === '/staff?per_page=100') return [{ id: 2, surname_jp: 'Test', given_name_jp: 'Staff' }];
    if (url === '/orders/7/financial') return financial;
    if (url === '/orders/7/purchase') return purchase;
    if (url === '/orders/7/shipping') return shipping;
    throw new Error(`Unexpected GET ${url}`);
  });
  mock.post.mockImplementation(() => { throw new Error('Unexpected POST'); });
  mock.patch.mockImplementation(() => { throw new Error('Unexpected PATCH'); });
  mock.delete.mockImplementation(() => { throw new Error('Unexpected DELETE'); });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); expect(URL).toBe(originalURL); expect(URL.createObjectURL).toBe(originalCreateObjectURL); expect(URL.revokeObjectURL).toBe(originalRevokeObjectURL); });

describe('shared button migration: real panel operations', () => {
  it.each([false, true])('keeps Confirm callbacks and danger=%s', danger => {
    const confirm = vi.fn(), cancel = vi.fn();
    render(<ConfirmModal open title="Confirm" message="Message" danger={danger} onConfirm={confirm} onCancel={cancel} />);
    const target = screen.getByRole('button', { name: 'confirmModal.defaultConfirm' });
    expect(target.classList.contains(danger ? 'comp-btn--danger' : 'comp-btn--primary')).toBe(true);
    expect(target.getAttribute('type')).toBe('button');
    fireEvent.click(target); expect(confirm).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', { name: 'confirmModal.defaultCancel' })); expect(cancel).toHaveBeenCalledTimes(1);
  });

  it('hides Priority without permission and retains omitted trigger type/cancel', () => {
    const updated = vi.fn(); mock.permission.mockReturnValue(false);
    const { rerender } = render(<PriorityScoreOverride leadId={9} currentScore={currentScore} onUpdated={updated} />);
    expect(screen.queryByRole('button')).toBeNull();
    expect(mock.permission).toHaveBeenCalledWith('analytics.customer_priority.override');
    mock.permission.mockReturnValue(true);
    rerender(<PriorityScoreOverride leadId={9} currentScore={currentScore} onUpdated={updated} />);
    const trigger = screen.getByRole('button', { name: 'priority.overrideTitle' });expect(trigger.hasAttribute('type')).toBe(false);
    fireEvent.click(trigger);fireEvent.click(screen.getByRole('button', { name: 'common.cancel' }));
    expect(screen.queryByRole('dialog')).toBeNull();expect(mock.post).not.toHaveBeenCalled();
  });

  it('submits Priority values once while saving, reports result and closes', async () => {
    const updated = vi.fn(), pending = deferred<CustomerScoreData>();mock.post.mockReturnValue(pending.promise);
    render(<PriorityScoreOverride leadId={9} currentScore={currentScore} onUpdated={updated} />);
    fireEvent.click(screen.getByRole('button', { name: 'priority.overrideTitle' }));
    fireEvent.change(screen.getByRole('slider'), { target: { value: '75' } });
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'manual note' } });
    const save = screen.getByRole('button', { name: 'common.save' }) as HTMLButtonElement;
    expect(save.type).toBe('submit');fireEvent.click(save);
    expect(mock.post).toHaveBeenCalledExactlyOnceWith('/leads/9/priority-score/override', { override_score: 0.75, override_note: 'manual note' });
    expect(save.disabled).toBe(true);expect(save.textContent).toBe('common.saving');fireEvent.click(save);expect(mock.post).toHaveBeenCalledTimes(1);
    await act(async () => { pending.resolve(currentScore); });expect(updated).toHaveBeenCalledExactlyOnceWith(currentScore);expect(screen.queryByRole('dialog')).toBeNull();
  });

  it.each(roles)('unassigns only %s and blocks repeat while that role saves', async role => {
    const saved = vi.fn(), pending = deferred<void>();mock.delete.mockReturnValue(pending.promise);
    render(<CommissionPanel orderId={7} orderNumber="ORD-7" onClose={vi.fn()} onSaved={saved} />);
    const unassign = await screen.findByTestId(`commission-unassign-${role}`) as HTMLButtonElement;
    fireEvent.click(unassign);expect(unassign.disabled).toBe(true);fireEvent.click(unassign);
    expect(mock.delete).toHaveBeenCalledExactlyOnceWith(`/orders/7/commissions/${role}`);
    await act(async () => { pending.resolve(); });expect(saved).toHaveBeenCalledExactlyOnceWith(bundle);expect(mock.get.mock.calls.filter(c => c[0] === '/orders/7/commissions')).toHaveLength(2);
  });

  it('recalculates commissions once and preserves the close action', async () => {
    const saved = vi.fn(), close = vi.fn(), pending = deferred<typeof bundle>();mock.post.mockReturnValue(pending.promise);
    render(<CommissionPanel orderId={7} orderNumber="ORD-7" onClose={close} onSaved={saved} />);
    const recalc = await screen.findByTestId('commission-recalc') as HTMLButtonElement;fireEvent.click(recalc);
    expect(recalc.disabled).toBe(true);expect(recalc.textContent).toBe('commission.recalculating');fireEvent.click(recalc);
    expect(mock.post).toHaveBeenCalledExactlyOnceWith('/orders/7/commissions/recalc', {});
    await act(async () => { pending.resolve(bundle); });expect(saved).toHaveBeenCalledExactlyOnceWith(bundle);
    const closeButtons=screen.getAllByRole('button', { name: 'common.close' });fireEvent.click(closeButtons[closeButtons.length-1]);expect(close).toHaveBeenCalledTimes(1);
  });

  it.each([true,false])('saves financial existing=%s and blocks cancel/save while saving', async existing => {
    const saved = vi.fn(), close = vi.fn(), pending = deferred<typeof financial>();const send=existing?mock.patch:mock.post; send.mockReturnValue(pending.promise);
    if (!existing) { const { ApiError }=await import('../lib/api'); mock.get.mockRejectedValue(new ApiError('not found',404,null)); }
    render(<OrderFinancialPanel orderId={7} orderNumber="ORD-7" onClose={close} onSaved={saved} />);
    await screen.findByTestId('fin-input-revenue_amount');fireEvent.change(button('fin-input-revenue_amount'), { target: { value: '1250' } });
    fireEvent.click(button('fin-save'));
    expect(send).toHaveBeenCalledExactlyOnceWith('/orders/7/financial', { ...Object.fromEntries(financialKeys.map(k => [k, k === 'revenue_amount' ? 1250 : 0])), notes: null });
    expect(button('fin-save').disabled).toBe(true);expect(button('fin-save').textContent).toBe('common.saving');
    const cancel = screen.getByRole('button', { name: 'common.cancel' }) as HTMLButtonElement;expect(cancel.disabled).toBe(true);fireEvent.click(cancel);fireEvent.click(button('fin-save'));expect(close).not.toHaveBeenCalled();expect(send).toHaveBeenCalledTimes(1);
    await act(async () => { pending.resolve(financial); });expect(saved).toHaveBeenCalledExactlyOnceWith(financial);expect(close).toHaveBeenCalledTimes(1);
  });

  it.each([{kind:'purchase',existing:true},{kind:'shipping',existing:true},{kind:'purchase',existing:false},{kind:'shipping',existing:false}] as const)('submits external $kind form existing=$existing once with exact payload', async ({kind,existing}) => {
    const saved = vi.fn(), close = vi.fn(), data = kind === 'purchase' ? purchase : shipping, pending = deferred<typeof data>();const send = existing ? mock.patch : mock.post; send.mockReturnValue(pending.promise);
    if (!existing) { const { ApiError } = await import('../lib/api'); mock.get.mockRejectedValue(new ApiError('not found',404,null)); }
    const Panel = kind === 'purchase' ? PurchaseDetailPanel : ShippingDetailPanel;
    const prefix = kind === 'purchase' ? 'pur' : 'ship';
    render(<Panel orderId={7} orderNumber="ORD-7" onClose={close} onSaved={saved} />);
    await screen.findByTestId(`${prefix}-input-${kind === 'purchase' ? 'purchase_amount' : 'weight_kg'}`);
    fireEvent.change(screen.getByTestId(`${prefix}-input-${kind === 'purchase' ? 'purchase_amount' : 'weight_kg'}`), { target: { value: kind === 'purchase' ? '125.50' : '2.5' } });
    const save = button(`${prefix}-save`);expect(save.form?.id).toBe(`${kind}-detail-form`);expect(save.closest('form')).toBeNull();expect(save.type).toBe('submit');
    fireEvent.click(save);const expected = Object.fromEntries((kind === 'purchase' ? [...purchaseText, ...purchaseNumbers] : [...shippingText, ...shippingNumbers]).map(k => [k, k === 'purchase_amount' ? 125.5 : k === 'weight_kg' ? 2.5 : null]));
    expect(send).toHaveBeenCalledExactlyOnceWith(`/orders/7/${kind}`, expected);expect(save.disabled).toBe(true);expect(save.textContent).toBe('common.saving');fireEvent.click(save);
    const cancel=screen.getByRole('button', { name: 'common.cancel' }) as HTMLButtonElement;expect(cancel.disabled).toBe(true);fireEvent.click(cancel);expect(close).not.toHaveBeenCalled();expect(send).toHaveBeenCalledTimes(1);
    await act(async () => { pending.resolve(data); });expect(saved).toHaveBeenCalledExactlyOnceWith(data);expect(close).toHaveBeenCalledTimes(1);
  });

  it('confirms existing purchase once while confirming and updates displayed status', async () => {
    const saved=vi.fn(), close=vi.fn(), pending=deferred<typeof purchase>();mock.patch.mockReturnValue(pending.promise);
    render(<PurchaseDetailPanel orderId={7} orderNumber="ORD-7" onClose={close} onSaved={saved} />);await screen.findByTestId('pur-input-purchase_amount');
    const confirm=button('pur-confirm');fireEvent.click(confirm);expect(confirm.disabled).toBe(true);expect(confirm.textContent).toBe('purchase.confirming');fireEvent.click(confirm);expect(mock.patch).toHaveBeenCalledExactlyOnceWith('/orders/7/purchase/status', {});
    const result={...purchase,purchase_status:'confirmed'};await act(async () => {pending.resolve(result);});expect(saved).toHaveBeenCalledExactlyOnceWith(result);expect((screen.getByTestId('pur-input-purchase_status') as HTMLSelectElement).value).toBe('confirmed');expect(close).not.toHaveBeenCalled();
  });

  it.each(['purchase','shipping'] as const)('keeps %s existing-only action disabled for a new record', async kind => {
    const { ApiError }=await import('../lib/api');mock.get.mockRejectedValue(new ApiError('not found',404,null));
    const Panel=kind==='purchase'?PurchaseDetailPanel:ShippingDetailPanel;render(<Panel orderId={7} orderNumber="ORD-7" onClose={vi.fn()} />);
    await screen.findByTestId(kind==='purchase'?'pur-input-purchase_amount':'ship-input-weight_kg');const target=button(kind==='purchase'?'pur-confirm':'ship-download-csv');expect(target.disabled).toBe(true);fireEvent.click(target);expect(mock.patch).not.toHaveBeenCalled();expect(fetch).not.toHaveBeenCalled();
  });

  it('downloads CSV via the same authenticated URL and Blob only once while pending', async () => {
    const pending=deferred<Response>(), blob=new Blob(['csv fixture'],{type:'text/csv'}), fetchMock=vi.fn().mockReturnValue(pending.promise);vi.stubGlobal('fetch',fetchMock);
    const create=vi.fn().mockReturnValue('blob:fixture'), revoke=vi.fn();class MockURL extends originalURL { static createObjectURL = create; static revokeObjectURL = revoke; } vi.stubGlobal('URL',MockURL);
    const downloads: {href:string;download:string}[]=[];vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(function(this:HTMLAnchorElement){downloads.push({href:this.href,download:this.download});});
    render(<ShippingDetailPanel orderId={7} orderNumber="ORD-7" onClose={vi.fn()} />);await screen.findByTestId('ship-input-weight_kg');const csv=button('ship-download-csv');fireEvent.click(csv);
    await waitFor(()=>expect(fetchMock).toHaveBeenCalledExactlyOnceWith('/api/v1/orders/7/shipping/elogi-csv',{headers:{Authorization:'Bearer fixture-token'}}));expect(csv.disabled).toBe(true);expect(csv.textContent).toBe('shipping.downloading');fireEvent.click(csv);expect(fetchMock).toHaveBeenCalledTimes(1);
    await act(async()=>{pending.resolve({ok:true,blob:async()=>blob} as Response);});expect(create).toHaveBeenCalledExactlyOnceWith(blob);expect(downloads).toEqual([{href:'blob:fixture',download:'elogi-ORD-7.csv'}]);expect(revoke).toHaveBeenCalledExactlyOnceWith('blob:fixture');expect(csv.disabled).toBe(false);expect(mock.token).toHaveBeenCalledTimes(1);
  });
});

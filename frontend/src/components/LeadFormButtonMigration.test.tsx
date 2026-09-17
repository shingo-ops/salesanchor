import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import LeadsPage from '../pages/leads/LeadsPage';
import LeadEditPage from '../pages/leads/LeadEditPage';
import en from '../locales/en.json';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), user: { uid: 'fixture-user' } }));
vi.mock('../lib/api', () => ({ api: mock }));
vi.mock('../lib/firebase', () => ({ auth: { currentUser: { getIdToken: async () => 'synthetic-token' } } }));
vi.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ user: mock.user, loading: false }) }));
const blank = { customer_name: 'Fixture Lead', email: null, phone: null, status: 'lead', type: null, notes: null, country: null, company_name: null, channel_type: null, initiative: null, temperature: null, estimated_scale: null, customer_type: null, response_speed: null, monthly_forecast: null };
let lead = { ...blank, id: 7, lead_code: 'FIXTURE', created_at: '', updated_at: '', close_reason_memo: 'Existing memo', close_reasons: [{ reason_id: 42, is_primary: true }] };
let stream: ReadableStreamDefaultController<Uint8Array> | null = null;
type Mode = 'create' | 'quick' | 'full';
const modes: Mode[] = ['create', 'quick', 'full'];
let instance = createInstance();
let permissions: string[];
const tr = (key: string) => String(instance.t(key));
const reads = (url: string) => mock.get.mock.calls.filter(c => c[0] === url).length;
function deferred() {
  let resolve!: (value: unknown) => void, reject!: (error: Error) => void;
  const promise = new Promise<unknown>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}
function Probe() { return <output data-testid="location">{useLocation().pathname}</output>; }
function field(scope: HTMLElement, key: string) {
  const text = tr(key);
  const label = within(scope).getAllByText((s, el) => el?.tagName === 'LABEL' && (s === text || s === text + ' *'))[0];
  const input = label.parentElement?.querySelector<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>('input,textarea,select');
  if (!input) throw new Error('Missing field ' + key);
  return input;
}
function save(scope: HTMLElement, mode: Mode) { return within(scope).getByRole('button', { name: tr(mode === 'create' ? 'common.register' : 'common.update') }) as HTMLButtonElement; }
function cancel(scope: HTMLElement) { return within(scope).getByRole('button', { name: tr('common.cancel') }) as HTMLButtonElement; }
function closed(scope: HTMLElement, mode: Mode) {
  if (mode === 'create') expect(document.body.contains(scope)).toBe(false);
  else if (mode === 'quick') expect(scope.classList.contains('comp-drawer-panel--open')).toBe(false);
  else expect(screen.getByTestId('location').textContent).toBe('/crm/leads');
}
const quickPayload = { customer_name: ' Edited Lead ', email: null, phone: null, status: 'lead', type: null, notes: null, country: null };
const payload = (mode: Mode) => mode === 'quick' ? quickPayload : { ...blank, customer_name: ' Edited Lead ' };
const sender = (mode: Mode) => mode === 'create' ? mock.post : mock.patch;
const path = (mode: Mode) => mode === 'create' ? '/leads' : '/leads/7';
async function mount(mode: Mode) {
  render(<I18nextProvider i18n={instance}><MemoryRouter initialEntries={[mode === 'full' ? '/crm/leads/7/edit' : '/crm/leads']}><Probe /><Routes><Route path="/crm/leads" element={mode === 'full' ? <div data-testid="destination" /> : <LeadsPage />} /><Route path="/crm/leads/:id/edit" element={<LeadEditPage />} /></Routes></MemoryRouter></I18nextProvider>);
  if (mode === 'full') await screen.findByDisplayValue('Fixture Lead');
  else { await screen.findByText('Fixture Lead'); await waitFor(() => expect(reads('/me/permissions')).toBe(1)); }
}
async function open(mode: Mode) {
  if (mode === 'create') fireEvent.click(await screen.findByRole('button', { name: tr('leads.newLead') }));
  else if (mode === 'quick') fireEvent.click(await screen.findByText('Fixture Lead'));
  const scope = mode === 'full' ? screen.getByRole('button', { name: tr('common.update') }).closest('form') : screen.getByRole('dialog', { name: tr(mode === 'create' ? 'leads.newLeadTitle' : 'leads.editLead') });
  if (!scope) throw new Error('Missing form');
  return scope;
}
async function mountForm(mode: Mode) {
  await mount(mode); const scope = await open(mode);
  fireEvent.change(field(scope, 'leads.customerName'), { target: { value: ' Edited Lead ' } });
  return scope;
}
beforeEach(async () => {
  stream = null;
  lead = { ...lead, ...blank };
  vi.resetAllMocks(); permissions = ['leads.create', 'leads.update', 'leads.delete'];
  instance = createInstance(); await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(async (endpoint: string) => {
    if (endpoint !== '/api/v1/leads/stream') throw new Error('Unexpected network');
    return { ok: true, body: new ReadableStream<Uint8Array>({ start(controller) { stream = controller; } }) };
  }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/leads') return [lead];
    if (url === '/leads/7') return lead;
    if (url === '/countries') return [{ code: 'ZZ', name: 'Fixture Country', dial_code: '+999', is_active: true }];
    if (url === '/channel-masters') return [{ id: 1, platform: 'fixture', display_name: 'Fixture Channel', connection_type: 'manual', is_active: true }];
    if (url === '/close-reasons?type=lost') return [{ id: 42, label: 'Fixture Reason', type: 'lost', is_active: true }];
    if (url === '/me/permissions') return { permissions };
    throw new Error('Unexpected GET ' + url);
  });
  mock.post.mockImplementation(() => { throw new Error('Unexpected POST'); });
  mock.patch.mockImplementation(() => { throw new Error('Unexpected PATCH'); });
  mock.delete.mockImplementation(() => { throw new Error('Unexpected DELETE'); });
});
afterEach(() => {
  cleanup(); if (stream) stream.close(); stream = null; expect(vi.mocked(fetch).mock.calls.every(c => c[0] === '/api/v1/leads/stream')).toBe(true); expect(mock.delete).not.toHaveBeenCalled();
  expect(mock.post.mock.calls.every(c => c[0] === '/leads')).toBe(true);
  expect(mock.patch.mock.calls.every(c => c[0] === '/leads/7')).toBe(true);
  expect([mock.get, mock.post, mock.patch, mock.delete].flatMap(fn => fn.mock.calls).every(c => !String(c[0]).includes('/members'))).toBe(true);
  expect(reads('/staff/me')).toBe(0); vi.restoreAllMocks(); vi.unstubAllGlobals();
});
const change = (scope: HTMLElement, key: string, value: string) => fireEvent.change(field(scope, key), { target: { value } });
async function submit(scope: HTMLElement, mode: Mode, expected: object) {
  fireEvent.click(save(scope, mode)); await waitFor(() => expect(sender(mode)).toHaveBeenCalledExactlyOnceWith(path(mode), expected));
}
describe('Lead form migration with real input, permission and SSE hooks', () => {
  it.each(modes.flatMap(mode => ['click', 'enter'].map(input => ({ mode, input }))))('$mode sends exact nullable keys with $input and resets', async ({ mode, input }) => {
    sender(mode).mockResolvedValue(lead); const scope = await mountForm(mode), before = reads('/leads');
    expect(save(scope, mode).type).toBe('submit'); expect(cancel(scope).type).toBe('button');
    expect(save(scope, mode).classList.contains('comp-btn--primary')).toBe(true); expect(cancel(scope).classList.contains('comp-btn--secondary')).toBe(true);
    if (input === 'click') fireEvent.click(save(scope, mode));
    else { const user = userEvent.setup(); await user.click(field(scope, 'leads.customerName')); await user.keyboard('{Enter}'); }
    await waitFor(() => expect(sender(mode)).toHaveBeenCalledExactlyOnceWith(path(mode), payload(mode))); await waitFor(() => closed(scope, mode));
    if (mode !== 'full') { await waitFor(() => expect(reads('/leads')).toBe(before + 1)); const fresh = await open(mode); expect(field(fresh, 'leads.customerName').value).toBe(mode === 'create' ? '' : 'Fixture Lead'); }
    else expect(reads('/me/permissions')).toBe(0);
  });
  it.each(modes)('%s preserves optional text and whitespace', async mode => {
    sender(mode).mockResolvedValue(lead); const scope = await mountForm(mode);
    change(scope, 'leads.phone', ' 123 '); change(scope, 'leads.email', 'fixture@example.test'); change(scope, 'leads.notes', ' Notes '); change(scope, 'leads.type', 'Inbound');
    if (mode !== 'quick') { change(scope, 'leads.companyName', ' Company '); change(scope, 'leads.initiative', 'inbound'); change(scope, 'leads.temperature', 'Hot'); change(scope, 'leads.estimatedScale', 'Small'); }
    await submit(scope, mode, { ...payload(mode), phone: ' 123 ', email: 'fixture@example.test', notes: ' Notes ', type: 'Inbound', ...(mode !== 'quick' ? { company_name: ' Company ', initiative: 'inbound', temperature: 'Hot', estimated_scale: 'Small' } : {}) });
  });
  it.each((['create', 'full'] as Mode[]).flatMap(mode => ['', '0', '42'].map(value => ({ mode, value }))))('$mode monthly $value converts exactly', async ({ mode, value }) => {
    sender(mode).mockResolvedValue(lead); const scope = await mountForm(mode); change(scope, 'leads.monthlyForecast', value);
    expect(field(scope, 'leads.monthlyForecast').checkValidity()).toBe(true); await submit(scope, mode, { ...payload(mode), monthly_forecast: value ? Number(value) : null });
  });
  it.each(modes.flatMap(mode => ['name', 'email', ...(mode === 'quick' ? [] : ['negative', 'fraction'])].map(invalid => ({ mode, invalid }))))('$mode rejects $invalid without sending', async ({ mode, invalid }) => {
    const scope = await mountForm(mode), key = invalid === 'name' ? 'leads.customerName' : invalid === 'email' ? 'leads.email' : 'leads.monthlyForecast';
    change(scope, key, invalid === 'name' ? '' : invalid === 'email' ? 'invalid' : invalid === 'negative' ? '-1' : '0.5');
    expect(field(scope, key).checkValidity()).toBe(false); fireEvent.click(save(scope, mode)); expect(mock.post).not.toHaveBeenCalled(); expect(mock.patch).not.toHaveBeenCalled();
  });
  it.each((['quick', 'full'] as Mode[]).flatMap(mode => ['selected', 'empty', 'return', 'unedited'].map(state => ({ mode, state }))))('$mode lost $state retains existing payload contract', async ({ mode, state }) => {
    if (state === 'unedited') lead.status = 'lost'; sender(mode).mockResolvedValue(lead); const scope = await mountForm(mode);
    change(scope, 'leads.status', 'lost'); expect(field(scope, 'leads.lostReasonCode').value).toBe(''); expect(field(scope, 'leads.lostReason').value).toBe('');
    if (state === 'selected' || state === 'return') { change(scope, 'leads.lostReasonCode', '42'); change(scope, 'leads.lostReason', ' Reason '); }
    if (state === 'return') change(scope, 'leads.status', 'lead');
    await submit(scope, mode, { ...payload(mode), status: state === 'return' ? 'lead' : 'lost', ...(state === 'return' ? {} : { close_reason_memo: state === 'selected' ? ' Reason ' : null, close_reasons: state === 'selected' ? [{ reason_id: 42, is_primary: true }] : [] }) });
  });
  it('create lost sends fifteen keys without reason fields', async () => {
    mock.post.mockResolvedValue(lead); const scope = await mountForm('create'); change(scope, 'leads.status', 'lost');
    expect(within(scope).queryByText(tr('leads.lostReasonCode'))).toBeNull(); await submit(scope, 'create', { ...payload('create'), status: 'lost' });
  });
  it.each(modes)('%s cancel writes zero and reopening restores source', async mode => {
    const scope = await mountForm(mode); fireEvent.click(cancel(scope)); closed(scope, mode); expect(mock.post).not.toHaveBeenCalled(); expect(mock.patch).not.toHaveBeenCalled();
    if (mode !== 'full') expect(field(await open(mode), 'leads.customerName').value).toBe(mode === 'create' ? '' : 'Fixture Lead');
  });
  it.each(modes)('%s pending stays enabled and error retains values before retry', async mode => {
    const pending = deferred(); sender(mode).mockReturnValue(pending.promise); const scope = await mountForm(mode); change(scope, 'leads.notes', ' Keep '); fireEvent.click(save(scope, mode));
    for (const b of [save(scope, mode), cancel(scope)]) { expect(b.disabled).toBe(false); expect(b.hasAttribute('aria-busy')).toBe(false); }
    expect(save(scope, mode).textContent).toBe(tr(mode === 'create' ? 'common.register' : 'common.update')); expect(cancel(scope).textContent).toBe(tr('common.cancel'));
    await act(async () => pending.reject(new Error('Fixture failure'))); expect(screen.getByText('Fixture failure')).toBeTruthy(); expect(field(scope, 'leads.notes').value).toBe(' Keep '); expect(field(scope, 'leads.customerName').value).toBe(' Edited Lead ');
    sender(mode).mockResolvedValue(lead); fireEvent.click(save(scope, mode)); await waitFor(() => closed(scope, mode)); expect(sender(mode)).toHaveBeenCalledTimes(2);
  });
  it.each(modes)('%s permits exactly two independent pending sends', async mode => {
    const a = deferred(), b = deferred(); sender(mode).mockReturnValueOnce(a.promise).mockReturnValueOnce(b.promise); const scope = await mountForm(mode), before = reads('/leads');
    fireEvent.click(save(scope, mode)); fireEvent.click(save(scope, mode)); expect(sender(mode).mock.calls).toEqual([[path(mode), payload(mode)], [path(mode), payload(mode)]]);
    await act(async () => { a.resolve(lead); b.resolve(lead); }); await waitFor(() => closed(scope, mode)); if (mode !== 'full') await waitFor(() => expect(reads('/leads')).toBe(before + 2));
  });
  it.each(modes)('%s textarea Enter adds newline only', async mode => {
    const scope = await mountForm(mode), user = userEvent.setup(); await user.click(field(scope, 'leads.notes')); await user.keyboard('One{Enter}Two'); expect(field(scope, 'leads.notes').value).toBe('One\nTwo'); expect(mock.post).not.toHaveBeenCalled(); expect(mock.patch).not.toHaveBeenCalled();
  });
  it.each(modes.flatMap(mode => (mode === 'quick' ? ['country'] : ['country', 'channel']).flatMap(kind => ['select', 'query', 'clear'].map(action => ({ mode, kind, action })))))('$mode $kind $action uses real combobox', async ({ mode, kind, action }) => {
    sender(mode).mockResolvedValue(lead); const scope = await mountForm(mode), input = field(scope, kind === 'country' ? 'leads.country' : 'leads.channelType');
    fireEvent.focus(input); fireEvent.change(input, { target: { value: 'Fixture' } });
    if (action !== 'query') fireEvent.click(await within(scope).findByRole('option', { name: kind === 'country' ? /Fixture Country/ : /Fixture Channel/ }));
    else fireEvent.blur(input);
    if (action === 'clear') { const group = input.closest('.form-group'); if (!group) throw new Error('Missing group'); fireEvent.click(within(group as HTMLElement).getByRole('button', { name: tr('common.clear') })); }
    await submit(scope, mode, { ...payload(mode), [kind === 'country' ? 'country' : 'channel_type']: action === 'select' ? kind === 'country' ? 'ZZ' : 'fixture' : null });
  });
  it.each([{ create: true, update: true }, { create: false, update: false }, { create: true, update: false }, { create: false, update: true }])('real permissions create=$create update=$update', async ({ create, update }) => {
    permissions = [...(create ? ['leads.create'] : []), ...(update ? ['leads.update'] : [])]; await mount('quick'); expect(!!screen.queryByRole('button', { name: tr('leads.newLead') })).toBe(create);
    fireEvent.click(screen.getByText('Fixture Lead')); expect(screen.getByRole('dialog', { name: tr('leads.editLead') }).classList.contains('comp-drawer-panel--open')).toBe(update);
  });
  it('real SSE ignores ping and refreshes once for update without losing input', async () => {
    const scope = await mountForm('quick'), before = reads('/leads'); await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
    await act(async () => { if (!stream) throw new Error('SSE not connected'); stream.enqueue(new TextEncoder().encode(': ping\n\n')); }); expect(reads('/leads')).toBe(before);
    await act(async () => { if (!stream) throw new Error('SSE not connected'); stream.enqueue(new TextEncoder().encode('event: update\ndata: {}\n\n')); }); await waitFor(() => expect(reads('/leads')).toBe(before + 1)); expect(field(scope, 'leads.customerName').value).toBe(' Edited Lead ');
  });
  it('drawer full page link retains id and makes no writes', async () => {
    const scope = await mountForm('quick'); fireEvent.click(within(scope).getByRole('button', { name: tr('suppliers.openFullPage') })); await screen.findByDisplayValue('Fixture Lead'); expect(screen.getByTestId('location').textContent).toBe('/crm/leads/7/edit'); expect(mock.post).not.toHaveBeenCalled(); expect(mock.patch).not.toHaveBeenCalled();
  });
});

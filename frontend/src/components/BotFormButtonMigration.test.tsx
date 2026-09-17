import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import BotsPage from '../pages/bots/BotsPage';
import BotEditPage from '../pages/bots/BotEditPage';
import en from '../locales/en.json';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), user: { uid: 'fixture-user' } }));
vi.mock('../lib/api', () => ({ api: mock }));
vi.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ user: mock.user, loading: false }) }));
const bot = { id: 7, tenant_id: 1, bot_code: 'FIXTURE', display_name: 'Fixture Bot', purpose: 'invoice', status: 'active', discord_user_id: null, sender_email: null, owner_staff_id: 9, owner_staff_name: 'Fixture Staff', last_executed_at: null, execution_count: 0, created_at: '', updated_at: '' };
const staff = [{ id: 9, surname_jp: 'Fixture', given_name_jp: 'Staff' }, { id: 10, surname_jp: 'Other', given_name_jp: 'Staff' }];
const syntheticKey = 'SYNTHETIC-TEST-ONLY-NOT-A-CREDENTIAL';
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
  const text = key === 'discord' ? 'Discord Bot ID' : tr(key);
  const label = within(scope).getAllByText((s, el) => el?.tagName === 'LABEL' && (s === text || s === text + ' *'))[0];
  const input = label.parentElement?.querySelector<HTMLInputElement | HTMLSelectElement>('input,select');
  if (!input) throw new Error('Missing field ' + key);
  return input;
}
function save(scope: HTMLElement, mode: Mode) { return within(scope).getByRole('button', { name: tr(mode === 'create' ? 'bots.registerIssueKey' : 'common.update') }) as HTMLButtonElement; }
function cancel(scope: HTMLElement) { return within(scope).getByRole('button', { name: tr('common.cancel') }) as HTMLButtonElement; }
function closed(scope: HTMLElement, mode: Mode) {
  if (mode === 'create') expect(document.body.contains(scope)).toBe(false);
  else if (mode === 'quick') expect(scope.classList.contains('comp-drawer-panel--open')).toBe(false);
  else expect(screen.getByTestId('location').textContent).toBe('/bots');
}
const payload = { display_name: 'Edited Bot', purpose: 'custom', status: 'maintenance', owner_staff_id: 10, discord_user_id: null, sender_email: null };
async function mount(mode: Mode) {
  render(<I18nextProvider i18n={instance}><MemoryRouter initialEntries={[mode === 'full' ? '/bots/7/edit' : '/bots']}><Probe /><Routes><Route path="/bots" element={mode === 'full' ? <div data-testid="destination" /> : <BotsPage />} /><Route path="/bots/:id/edit" element={<BotEditPage />} /></Routes></MemoryRouter></I18nextProvider>);
  if (mode === 'full') await screen.findByDisplayValue('Fixture Bot');
  else { await screen.findByText('Fixture Bot'); await waitFor(() => expect(reads('/me/permissions')).toBe(1)); }
}
async function open(mode: Mode) {
  if (mode !== 'full') fireEvent.click(await screen.findByRole('button', { name: tr(mode === 'create' ? 'bots.newBot' : 'common.edit') }));
  const scope = mode === 'full' ? screen.getByRole('button', { name: tr('common.update') }).closest('form') : screen.getByRole('dialog', { name: tr(mode === 'create' ? 'bots.newBot' : 'bots.editBot') });
  if (!scope) throw new Error('Missing form');
  return scope;
}
async function mountForm(mode: Mode) {
  await mount(mode); const scope = await open(mode);
  for (const [key, value] of [['bots.displayName', 'Edited Bot'], ['bots.purposeLabel', 'custom'], ['common.status', 'maintenance'], ['bots.ownerStaff', '10']]) fireEvent.change(field(scope, key), { target: { value } });
  return scope;
}
beforeEach(async () => {
  vi.resetAllMocks(); permissions = ['bots.create', 'bots.update', 'bots.delete'];
  instance = createInstance(); await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/bots') return [bot];
    if (url === '/bots/7') return bot;
    if (url === '/staff') return staff;
    if (url === '/me/permissions') return { permissions };
    throw new Error('Unexpected GET ' + url);
  });
  mock.post.mockImplementation(() => { throw new Error('Unexpected POST'); });
  mock.patch.mockImplementation(() => { throw new Error('Unexpected PATCH'); });
  mock.delete.mockImplementation(() => { throw new Error('Unexpected DELETE'); });
});
afterEach(() => {
  cleanup(); expect(fetch).not.toHaveBeenCalled(); expect(mock.delete).not.toHaveBeenCalled();
  expect(mock.post.mock.calls.every(c => c[0] === '/bots')).toBe(true);
  expect(reads('/staff/me')).toBe(0); vi.restoreAllMocks(); vi.unstubAllGlobals();
});
describe('Bot form migration using real pages and permissions', () => {
  it.each(modes.flatMap(mode => (['click', 'enter'] as const).map(input => ({ mode, input }))))('$mode submits exact payload through $input', async ({ mode, input }) => {
    const send = mode === 'create' ? mock.post : mock.patch; send.mockResolvedValue({ ...bot, api_key: syntheticKey });
    const scope = await mountForm(mode), target = save(scope, mode), beforeBots = reads('/bots'), beforeStaff = reads('/staff');
    expect(target.type).toBe('submit'); expect(target.classList.contains('comp-btn--primary')).toBe(true);
    expect(cancel(scope).type).toBe('button'); expect(cancel(scope).classList.contains('comp-btn--secondary')).toBe(true);
    if (input === 'click') fireEvent.click(target);
    else { const user = userEvent.setup(); await user.click(field(scope, 'bots.displayName')); await user.keyboard('{Enter}'); }
    await waitFor(() => expect(send).toHaveBeenCalledExactlyOnceWith(mode === 'create' ? '/bots' : '/bots/7', payload));
    await waitFor(() => closed(scope, mode));
    if (mode !== 'full') { expect(reads('/bots')).toBe(beforeBots + 1); expect(reads('/staff')).toBe(beforeStaff + 1); }
    expect(mode === 'create' ? mock.patch : mock.post).not.toHaveBeenCalled();
    if (mode === 'create') {
      expect(screen.getByText(syntheticKey)).toBeTruthy(); fireEvent.click(screen.getByRole('button', { name: tr('bots.apiKeyConfirm') }));
      expect(screen.queryByText(syntheticKey)).toBeNull(); const fresh = await open('create');
      expect(field(fresh, 'bots.displayName').value).toBe(''); expect(field(fresh, 'bots.botCodeLabel').value).toBe('');
      expect(field(fresh, 'bots.purposeLabel').value).toBe('invoice'); expect(field(fresh, 'common.status').value).toBe('active');
      expect(field(fresh, 'bots.ownerStaff').value).toBe(''); expect(field(fresh, 'discord').value).toBe(''); expect(field(fresh, 'bots.senderEmail').value).toBe('');
    } else expect(screen.queryByText(syntheticKey)).toBeNull();
  });
  it.each(modes)('%s cancels with zero writes', async mode => {
    const scope = await mountForm(mode); fireEvent.click(cancel(scope)); closed(scope, mode);
    expect(mock.post).not.toHaveBeenCalled(); expect(mock.patch).not.toHaveBeenCalled();
    if (mode !== 'full') { const fresh = await open(mode); expect(field(fresh, 'bots.displayName').value).toBe(mode === 'create' ? '' : 'Fixture Bot'); }
  });
  it.each(modes)('%s preserves pending state and failed input', async mode => {
    const pending = deferred(), send = mode === 'create' ? mock.post : mock.patch; send.mockReturnValue(pending.promise);
    const scope = await mountForm(mode), target = save(scope, mode); fireEvent.click(target);
    expect(target.disabled).toBe(mode === 'create'); expect(cancel(scope).disabled).toBe(mode === 'create'); expect(target.hasAttribute('aria-busy')).toBe(false);
    expect(target.textContent).toBe(tr(mode === 'create' ? 'common.submitting' : 'common.update'));
    await act(async () => { pending.reject(new Error('Fixture failure')); });
    expect(screen.getByText('Fixture failure')).toBeTruthy(); expect(field(scope, 'bots.displayName').value).toBe('Edited Bot');
    expect(field(scope, 'bots.ownerStaff').value).toBe('10'); expect(target.disabled).toBe(false); expect(cancel(scope).disabled).toBe(false);
    expect(target.textContent).toBe(tr(mode === 'create' ? 'bots.registerIssueKey' : 'common.update'));
    send.mockResolvedValue({ ...bot, api_key: syntheticKey }); fireEvent.click(target); await waitFor(() => closed(scope, mode)); expect(send).toHaveBeenCalledTimes(2);
  });
  it.each(['   ', '  BOT-NEW  '])('create trims optional code %s', async code => {
    mock.post.mockResolvedValue({ ...bot, api_key: syntheticKey }); const scope = await mountForm('create');
    fireEvent.change(field(scope, 'bots.botCodeLabel'), { target: { value: code } }); fireEvent.click(save(scope, 'create'));
    await waitFor(() => expect(mock.post).toHaveBeenCalledExactlyOnceWith('/bots', { ...payload, ...(code.trim() ? { bot_code: code.trim() } : {}) }));
  });
  it.each(modes)('%s retains nonempty optional values', async mode => {
    const send = mode === 'create' ? mock.post : mock.patch; send.mockResolvedValue({ ...bot, api_key: syntheticKey });
    const scope = await mountForm(mode); fireEvent.change(field(scope, 'discord'), { target: { value: 'fixture-discord' } }); fireEvent.change(field(scope, 'bots.senderEmail'), { target: { value: 'fixture@example.test' } });
    fireEvent.click(save(scope, mode)); await waitFor(() => expect(send).toHaveBeenCalledExactlyOnceWith(mode === 'create' ? '/bots' : '/bots/7', { ...payload, discord_user_id: 'fixture-discord', sender_email: 'fixture@example.test' }));
  });
  it.each(modes.flatMap(mode => ['bots.displayName', 'bots.purposeLabel', 'bots.ownerStaff', 'bots.senderEmail'].map(key => ({ mode, key }))))('$mode rejects invalid $key', async ({ mode, key }) => {
    const scope = await mountForm(mode), input = field(scope, key);
    if (key === 'bots.purposeLabel') {
      expect(input).toBeInstanceOf(HTMLSelectElement);
      const select = input as HTMLSelectElement;
      expect(Array.from(select.options, option => option.value)).toEqual(['invoice', 'shipment', 'notification', 'custom']);
      // Native invalid-state fixture; the normal UI has no empty purpose option.
      select.selectedIndex = -1;
    } else fireEvent.change(input, { target: { value: key === 'bots.senderEmail' ? 'invalid-email' : '' } });
    if (key !== 'bots.senderEmail') expect(input.required).toBe(true);
    expect(input.checkValidity()).toBe(false); fireEvent.click(save(scope, mode)); expect(mock.post).not.toHaveBeenCalled(); expect(mock.patch).not.toHaveBeenCalled();
  });
  it('create blocks repeated submit and cancel until rejection', async () => {
    const pending = deferred(); mock.post.mockReturnValue(pending.promise); const scope = await mountForm('create'), target = save(scope, 'create');
    fireEvent.click(target); fireEvent.click(target); fireEvent.click(cancel(scope));
    if (!target.form) throw new Error('Missing form'); fireEvent.submit(target.form);
    expect(mock.post).toHaveBeenCalledTimes(1); expect(document.body.contains(scope)).toBe(true);
    await act(async () => { pending.reject(new Error('Fixture pending failure')); });
    expect(target.disabled).toBe(false); expect(cancel(scope).disabled).toBe(false);
  });
  it.each([true, false])('real permissions gate create/update/delete allowed=%s', async allowed => {
    permissions = allowed ? ['bots.create', 'bots.update', 'bots.delete'] : [];
    await mount('quick');
    for (const key of ['bots.newBot', 'common.edit', 'bots.rotateKey', 'common.delete']) expect(!!screen.queryByRole('button', { name: tr(key) })).toBe(allowed);
    fireEvent.click(screen.getByText('Fixture Bot'));
    expect(screen.getByRole('dialog', { name: tr('bots.editBot') }).classList.contains('comp-drawer-panel--open')).toBe(allowed);
    expect(mock.post).not.toHaveBeenCalled(); expect(mock.patch).not.toHaveBeenCalled();
  });
});

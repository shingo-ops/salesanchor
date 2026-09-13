import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import StaffPage from '../pages/staff/StaffPage';
import StaffEditPage from '../pages/staff/StaffEditPage';
import { DEFAULT_UI_PREFS, UiPrefsProvider, useUiPrefs } from '../contexts/UiPrefsContext';
import en from '../locales/en.json';

const mock = vi.hoisted(() => ({
  get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), user: { uid: 'fixture-user' },
}));
vi.mock('../lib/api', () => ({ api: mock }));
vi.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ user: mock.user, loading: false }) }));

const originalPrefs = { dark_mode: false, show_chat_menu: true, show_sales_menu: true, show_settings_menu: true, show_admin_menu: false, show_sidebar: true };
const editedPrefs = { dark_mode: true, show_chat_menu: false, show_sales_menu: false, show_settings_menu: false, show_admin_menu: true, show_sidebar: false };
const staff = {
  id: 7, staff_code: 'ST7', surname_jp: 'Fixture', given_name_jp: 'Staff', primary_email: 'fixture@example.test',
  surname_kana: null, given_name_kana: null, surname_en: null, given_name_en: null,
  discord_user_id: null, role_id: 2, role_name: 'Fixture role', status: 'active',
  firebase_uid: null, ui_preferences: originalPrefs, emails: [],
};
const roles = [{ id: 2, name: 'Fixture role' }, { id: 3, name: 'Other fixture role' }];
type Mode = 'create' | 'quick' | 'full';
const modes: Mode[] = ['create', 'quick', 'full'];
let instance = createInstance();
let selfId: number | null = 99;
const tr = (key: string) => String(instance.t(key));
const meCalls = () => mock.get.mock.calls.filter(call => call[0] === '/staff/me').length;
function me(id: number, prefs = originalPrefs) { return { ...staff, id, ui_preferences: prefs }; }
function deferred() {
  let resolve!: (value: unknown) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<unknown>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}
function Probe() {
  const prefs = useUiPrefs(), location = useLocation();
  return <><output data-testid="provider">{JSON.stringify({ self: prefs.selfStaffId, fetched: prefs.prefsFetched, prefs: prefs.prefs })}</output><output data-testid="location">{location.pathname}</output></>;
}
function field(scope: HTMLElement, key: string) {
  const label = within(scope).getAllByText((text, element) => element?.tagName === 'LABEL' && (text === tr(key) || text === tr(key) + ' *'))[0];
  const target = label.parentElement?.querySelector<HTMLInputElement | HTMLSelectElement>('input,select');
  if (!target) throw new Error('Missing field ' + key);
  return target;
}
function save(scope: HTMLElement, mode: Mode) {
  return within(scope).getByRole('button', { name: tr(mode === 'create' ? 'common.register' : 'common.update') }) as HTMLButtonElement;
}
function cancel(scope: HTMLElement) {
  return within(scope).getByRole('button', { name: tr('common.cancel') }) as HTMLButtonElement;
}
function closed(scope: HTMLElement, mode: Mode) {
  if (mode === 'create') expect(document.body.contains(scope)).toBe(false);
  else if (mode === 'quick') expect(scope.classList.contains('comp-drawer-panel--open')).toBe(false);
  else expect(screen.getByTestId('location').textContent).toBe('/staff');
}
function payload(mode: Mode) {
  const common = { surname_jp: 'Edited', given_name_jp: 'Staff', primary_email: 'fixture@example.test', role_id: 3, status: 'active', discord_user_id: null };
  return mode === 'quick' ? common : {
    ...common, surname_kana: null, given_name_kana: null, surname_en: null, given_name_en: null,
    firebase_uid: null, ui_preferences: editedPrefs,
  };
}
async function mountForm(mode: Mode) {
  render(
    <I18nextProvider i18n={instance}>
      <MemoryRouter initialEntries={[mode === 'full' ? '/staff/7/edit' : '/staff']}>
        <UiPrefsProvider>
          <Probe />
          <Routes>
            <Route path="/staff" element={mode === 'full' ? <div data-testid="destination" /> : <StaffPage />} />
            <Route path="/staff/:id/edit" element={<StaffEditPage />} />
          </Routes>
        </UiPrefsProvider>
      </MemoryRouter>
    </I18nextProvider>,
  );
  await waitFor(() => expect(JSON.parse(screen.getByTestId('provider').textContent || '{}').fetched).toBe(true));
  expect(meCalls()).toBe(1);
  expect(JSON.parse(screen.getByTestId('provider').textContent || '{}').self).toBe(selfId);
  let scope: HTMLElement;
  if (mode === 'full') {
    await screen.findByDisplayValue('Fixture');
    const target = screen.getByRole('button', { name: tr('common.update') });
    if (!target.closest('form')) throw new Error('Missing full form');
    scope = target.closest('form') as HTMLFormElement;
  } else {
    await screen.findByText('Fixture Staff', { exact: true });
    fireEvent.click(await screen.findByRole('button', { name: tr(mode === 'create' ? 'staff.newStaff' : 'common.edit') }));
    scope = screen.getByRole('dialog', { name: tr(mode === 'create' ? 'staff.newStaff' : 'staff.editStaff') });
  }
  fireEvent.change(field(scope, 'staff.surnameJp'), { target: { value: 'Edited' } });
  fireEvent.change(field(scope, 'staff.givenNameJp'), { target: { value: 'Staff' } });
  fireEvent.change(field(scope, 'staff.primaryEmail'), { target: { value: 'fixture@example.test' } });
  fireEvent.change(field(scope, 'staff.role'), { target: { value: '3' } });
  if (mode !== 'quick') {
    const labels = ['staff.darkMode', 'staff.showChatMenu', 'staff.showSalesMenu', 'staff.showSettingsMenu', 'staff.showAdminMenu', 'staff.showSidebar'];
    for (const key of labels) fireEvent.click(within(scope).getByRole('checkbox', { name: tr(key) }));
  }
  return scope;
}

beforeEach(async () => {
  vi.resetAllMocks();
  vi.spyOn(console, 'warn').mockImplementation(() => {});
  selfId = 99;
  instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/staff/me') {
      if (selfId === null) throw new Error('Fixture staff unlinked');
      return me(selfId);
    }
    if (url === '/staff') return [staff];
    if (url === '/staff/7') return staff;
    if (url === '/roles') return roles;
    if (url === '/me/permissions') return { permissions: ['staff.create', 'staff.update', 'staff.delete'] };
    throw new Error('Unexpected GET ' + url);
  });
  mock.post.mockImplementation(() => { throw new Error('Unexpected POST'); });
  mock.patch.mockImplementation(() => { throw new Error('Unexpected PATCH'); });
  mock.delete.mockImplementation(() => { throw new Error('Unexpected DELETE'); });
});
afterEach(() => {
  cleanup();
  expect(fetch).not.toHaveBeenCalled();
  expect(mock.delete).not.toHaveBeenCalled();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('staff form Button migration with real UI preferences provider', () => {
  it.each(modes.flatMap(mode => (['click', 'enter'] as const).map(input => ({ mode, input }))))(
    '$mode sends exact method, ID and payload through $input',
    async ({ mode, input }) => {
      const send = mode === 'create' ? mock.post : mock.patch;
      send.mockResolvedValue({});
      const scope = await mountForm(mode), target = save(scope, mode);
      expect(target.type).toBe('submit');
      expect(target.classList.contains('comp-btn--primary')).toBe(true);
      expect(cancel(scope).type).toBe('button');
      expect(cancel(scope).classList.contains('comp-btn--secondary')).toBe(true);
      const reads = mock.get.mock.calls.filter(c => c[0] === '/staff').length;
      if (input === 'click') fireEvent.click(target);
      else { const user = userEvent.setup(); await user.click(field(scope, 'staff.surnameJp')); await user.keyboard('{Enter}'); }
      await waitFor(() => expect(send).toHaveBeenCalledExactlyOnceWith(mode === 'create' ? '/staff' : '/staff/7', payload(mode)));
      await waitFor(() => closed(scope, mode));
      if (mode !== 'full') expect(mock.get.mock.calls.filter(c => c[0] === '/staff')).toHaveLength(reads + 1);
      expect(meCalls()).toBe(1);
      expect(mode === 'create' ? mock.patch : mock.post).not.toHaveBeenCalled();
    },
  );
  it.each(modes)('%s cancels with zero writes', async mode => {
    const scope = await mountForm(mode);
    fireEvent.click(cancel(scope));
    closed(scope, mode);
    expect(mock.post).not.toHaveBeenCalled();
    expect(mock.patch).not.toHaveBeenCalled();
    expect(meCalls()).toBe(1);
  });
  it.each(modes)('%s retains failed input and existing pending state', async mode => {
    const pending = deferred(), send = mode === 'create' ? mock.post : mock.patch;
    send.mockReturnValue(pending.promise);
    const scope = await mountForm(mode), target = save(scope, mode);
    fireEvent.click(target);
    expect(target.disabled).toBe(mode === 'create');
    expect(cancel(scope).disabled).toBe(mode === 'create');
    await act(async () => { pending.reject(new Error('Fixture failure')); });
    expect(screen.getByText('Fixture failure')).toBeTruthy();
    expect(field(scope, 'staff.surnameJp').value).toBe('Edited');
    expect(target.disabled).toBe(false);
    expect(target.textContent).toBe(tr(mode === 'create' ? 'common.register' : 'common.update'));
    expect(meCalls()).toBe(1);
  });
  it.each(['   ', '  ST-NEW  '])('create handles optional staff code %s', async code => {
    mock.post.mockResolvedValue({});
    const scope = await mountForm('create');
    fireEvent.change(field(scope, 'staff.staffCodeLabel'), { target: { value: code } });
    fireEvent.click(save(scope, 'create'));
    await waitFor(() => expect(mock.post).toHaveBeenCalledExactlyOnceWith('/staff', { ...payload('create'), ...(code.trim() ? { staff_code: code.trim() } : {}) }));
  });
  it.each(modes.flatMap(mode => ['staff.surnameJp', 'staff.givenNameJp', 'staff.primaryEmail', 'staff.role'].map(key => ({ mode, key }))))(
    '$mode preserves required $key',
    async ({ mode, key }) => {
      const scope = await mountForm(mode), input = field(scope, key);
      fireEvent.change(input, { target: { value: '' } });
      expect(input.required).toBe(true);
      expect(input.checkValidity()).toBe(false);
      fireEvent.click(save(scope, mode));
      expect(mock.post).not.toHaveBeenCalled();
      expect(mock.patch).not.toHaveBeenCalled();
    },
  );
  it('create blocks repeat submit/cancel and permits retry after failure', async () => {
    const pending = deferred();
    mock.post.mockReturnValue(pending.promise);
    const scope = await mountForm('create'), target = save(scope, 'create'), cancelTarget = cancel(scope);
    fireEvent.click(target);
    expect(target.disabled).toBe(true);
    expect(cancelTarget.disabled).toBe(true);
    expect(target.textContent).toBe(tr('common.submitting'));
    fireEvent.click(target); fireEvent.click(cancelTarget);
    if (!target.form) throw new Error('Missing native form');
    fireEvent.submit(target.form);
    expect(mock.post).toHaveBeenCalledTimes(1);
    expect(document.body.contains(scope)).toBe(true);
    await act(async () => { pending.reject(new Error('Fixture retry')); });
    expect(target.disabled).toBe(false);
    expect(cancelTarget.disabled).toBe(false);
    expect(field(scope, 'staff.surnameJp').value).toBe('Edited');
    mock.post.mockResolvedValue({});
    fireEvent.click(target);
    await waitFor(() => closed(scope, 'create'));
    expect(mock.post.mock.calls).toEqual([['/staff', payload('create')], ['/staff', payload('create')]]);
  });
  it.each([7, 99, null])('full update refreshes actual provider only for self=%s', async identity => {
    selfId = identity;
    const scope = await mountForm('full'), pending = deferred();
    mock.patch.mockResolvedValue({});
    const originalGet = mock.get.getMockImplementation();
    mock.get.mockImplementation((url: string) => url === '/staff/me' ? pending.promise : originalGet?.(url));
    fireEvent.click(save(scope, 'full'));
    await waitFor(() => expect(mock.patch).toHaveBeenCalledExactlyOnceWith('/staff/7', payload('full')));
    if (identity === 7) {
      await waitFor(() => expect(meCalls()).toBe(2));
      expect(screen.getByTestId('location').textContent).toBe('/staff/7/edit');
      await act(async () => { pending.resolve(me(7, editedPrefs)); });
      await waitFor(() => closed(scope, 'full'));
      expect(JSON.parse(screen.getByTestId('provider').textContent || '{}').prefs).toEqual(editedPrefs);
    } else {
      await waitFor(() => closed(scope, 'full'));
      expect(meCalls()).toBe(1);
    }
  });
  it('self refresh HTTP rejection is caught by real provider before navigation', async () => {
    selfId = 7;
    const scope = await mountForm('full'), pending = deferred();
    mock.patch.mockResolvedValue({});
    mock.get.mockImplementation((url: string) => { if (url === '/staff/me') return pending.promise; throw new Error('Unexpected GET ' + url); });
    fireEvent.click(save(scope, 'full'));
    await waitFor(() => expect(meCalls()).toBe(2));
    expect(screen.getByTestId('location').textContent).toBe('/staff/7/edit');
    await act(async () => { pending.reject(new Error('Fixture refresh failure')); });
    await waitFor(() => closed(scope, 'full'));
    expect(JSON.parse(screen.getByTestId('provider').textContent || '{}')).toEqual({ self: null, fetched: true, prefs: DEFAULT_UI_PREFS });
    expect(console.warn).toHaveBeenCalledTimes(1);
  });
  it('quick edit of self does not add a preferences refresh', async () => {
    selfId = 7;
    mock.patch.mockResolvedValue({});
    const scope = await mountForm('quick');
    fireEvent.click(save(scope, 'quick'));
    await waitFor(() => closed(scope, 'quick'));
    expect(mock.patch).toHaveBeenCalledExactlyOnceWith('/staff/7', payload('quick'));
    expect(meCalls()).toBe(1);
  });
});

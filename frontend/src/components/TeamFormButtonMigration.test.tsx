import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import TeamsPage from '../pages/teams/TeamsPage';
import TeamEditPage from '../pages/teams/TeamEditPage';
import en from '../locales/en.json';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), user: { uid: 'fixture-user' } }));
vi.mock('../lib/api', () => ({ api: mock }));
vi.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ user: mock.user, loading: false }) }));
const team = { id: 7, name: 'Fixture Team', leader_id: null, description: null, is_active: true, member_count: 0, created_at: '', updated_at: '' };
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
  const input = label.parentElement?.querySelector<HTMLInputElement | HTMLTextAreaElement>('input,textarea');
  if (!input) throw new Error('Missing field ' + key);
  return input;
}
function save(scope: HTMLElement, mode: Mode) { return within(scope).getByRole('button', { name: tr(mode === 'create' ? 'common.create' : 'common.update') }) as HTMLButtonElement; }
function cancel(scope: HTMLElement) { return within(scope).getByRole('button', { name: tr('common.cancel') }) as HTMLButtonElement; }
function closed(scope: HTMLElement, mode: Mode) {
  if (mode === 'create') expect(document.body.contains(scope)).toBe(false);
  else if (mode === 'quick') expect(scope.classList.contains('comp-drawer-panel--open')).toBe(false);
  else expect(screen.getByTestId('location').textContent).toBe('/teams');
}
const payload = { name: ' Edited Team ', leader_id: null, description: null };
async function mount(mode: Mode) {
  render(<I18nextProvider i18n={instance}><MemoryRouter initialEntries={[mode === 'full' ? '/teams/7/edit' : '/teams']}><Probe /><Routes><Route path="/teams" element={mode === 'full' ? <div data-testid="destination" /> : <TeamsPage />} /><Route path="/teams/:id/edit" element={<TeamEditPage />} /></Routes></MemoryRouter></I18nextProvider>);
  if (mode === 'full') await screen.findByDisplayValue('Fixture Team');
  else { await screen.findByText('Fixture Team'); await waitFor(() => expect(reads('/me/permissions')).toBe(1)); }
}
async function open(mode: Mode) {
  if (mode !== 'full') fireEvent.click(await screen.findByRole('button', { name: tr(mode === 'create' ? 'teams.newTeam' : 'common.edit') }));
  const scope = mode === 'full' ? screen.getByRole('button', { name: tr('common.update') }).closest('form') : screen.getByRole('dialog', { name: tr(mode === 'create' ? 'teams.newTeam' : 'teams.editTeam') });
  if (!scope) throw new Error('Missing form');
  return scope;
}
async function mountForm(mode: Mode) {
  await mount(mode); const scope = await open(mode);
  fireEvent.change(field(scope, 'teams.teamName'), { target: { value: ' Edited Team ' } });
  return scope;
}
beforeEach(async () => {
  vi.resetAllMocks(); permissions = ['teams.create', 'teams.update', 'teams.delete'];
  instance = createInstance(); await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/teams') return [team];
    if (url === '/teams/7') return team;
    if (url === '/me/permissions') return { permissions };
    throw new Error('Unexpected GET ' + url);
  });
  mock.post.mockImplementation(() => { throw new Error('Unexpected POST'); });
  mock.patch.mockImplementation(() => { throw new Error('Unexpected PATCH'); });
  mock.delete.mockImplementation(() => { throw new Error('Unexpected DELETE'); });
});
afterEach(() => {
  cleanup(); expect(fetch).not.toHaveBeenCalled(); expect(mock.delete).not.toHaveBeenCalled();
  expect(mock.post.mock.calls.every(c => c[0] === '/teams')).toBe(true);
  expect(mock.patch.mock.calls.every(c => c[0] === '/teams/7')).toBe(true);
  expect([mock.get, mock.post, mock.patch, mock.delete].flatMap(fn => fn.mock.calls).every(c => !String(c[0]).includes('/members'))).toBe(true);
  expect(reads('/staff/me')).toBe(0); vi.restoreAllMocks(); vi.unstubAllGlobals();
});
describe('Team form migration using real pages and permissions', () => {
  it.each(modes.flatMap(mode => (['click', 'enter'] as const).map(input => ({ mode, input }))))('$mode submits nullable payload through $input', async ({ mode, input }) => {
    const send = mode === 'create' ? mock.post : mock.patch; send.mockResolvedValue(team);
    const scope = await mountForm(mode), target = save(scope, mode), before = reads('/teams');
    expect(target.type).toBe('submit'); expect(target.classList.contains('comp-btn--primary')).toBe(true);
    expect(cancel(scope).type).toBe('button'); expect(cancel(scope).classList.contains('comp-btn--secondary')).toBe(true);
    expect(field(scope, 'teams.leaderUserIdLabel').checkValidity()).toBe(true);
    if (input === 'click') fireEvent.click(target);
    else { const user = userEvent.setup(); await user.click(field(scope, 'teams.teamName')); await user.keyboard('{Enter}'); }
    await waitFor(() => expect(send).toHaveBeenCalledExactlyOnceWith(mode === 'create' ? '/teams' : '/teams/7', payload));
    await waitFor(() => closed(scope, mode));
    if (mode !== 'full') {
      await waitFor(() => expect(reads('/teams')).toBe(before + 1)); const fresh = await open(mode);
      expect(field(fresh, 'teams.teamName').value).toBe(mode === 'create' ? '' : 'Fixture Team');
      expect(field(fresh, 'teams.leaderUserIdLabel').value).toBe(''); expect(field(fresh, 'common.description').value).toBe('');
    } else expect(reads('/me/permissions')).toBe(0);
    expect(mode === 'create' ? mock.patch : mock.post).not.toHaveBeenCalled();
  });
  it.each(modes)('%s preserves Number conversion and whitespace', async mode => {
    const send = mode === 'create' ? mock.post : mock.patch; send.mockResolvedValue(team); const scope = await mountForm(mode);
    fireEvent.change(field(scope, 'teams.leaderUserIdLabel'), { target: { value: '42' } });
    fireEvent.change(field(scope, 'common.description'), { target: { value: ' Description \n ' } }); fireEvent.click(save(scope, mode));
    await waitFor(() => expect(send).toHaveBeenCalledExactlyOnceWith(mode === 'create' ? '/teams' : '/teams/7', { ...payload, leader_id: 42, description: ' Description \n ' }));
  });
  it.each(modes)('%s cancels with zero writes and restores fresh form', async mode => {
    const scope = await mountForm(mode); fireEvent.click(cancel(scope)); closed(scope, mode);
    expect(mock.post).not.toHaveBeenCalled(); expect(mock.patch).not.toHaveBeenCalled();
    if (mode !== 'full') { const fresh = await open(mode); expect(field(fresh, 'teams.teamName').value).toBe(mode === 'create' ? '' : 'Fixture Team'); }
  });
  it.each(modes)('%s retains failure input and enabled pending buttons before retry', async mode => {
    const pending = deferred(), send = mode === 'create' ? mock.post : mock.patch; send.mockReturnValue(pending.promise);
    const scope = await mountForm(mode), target = save(scope, mode);
    fireEvent.change(field(scope, 'teams.leaderUserIdLabel'), { target: { value: '42' } });
    fireEvent.change(field(scope, 'common.description'), { target: { value: ' Retained ' } }); fireEvent.click(target);
    for (const button of [target, cancel(scope)]) { expect(button.disabled).toBe(false); expect(button.hasAttribute('aria-busy')).toBe(false); }
    expect(target.textContent).toBe(tr(mode === 'create' ? 'common.create' : 'common.update')); expect(cancel(scope).textContent).toBe(tr('common.cancel'));
    await act(async () => { pending.reject(new Error('Fixture failure')); });
    expect(screen.getByText('Fixture failure')).toBeTruthy(); expect(document.body.contains(scope)).toBe(true);
    if (mode === 'quick') expect(scope.classList.contains('comp-drawer-panel--open')).toBe(true);
    expect(field(scope, 'teams.teamName').value).toBe(' Edited Team '); expect(field(scope, 'teams.leaderUserIdLabel').value).toBe('42'); expect(field(scope, 'common.description').value).toBe(' Retained ');
    send.mockResolvedValue(team); fireEvent.click(target); await waitFor(() => closed(scope, mode)); expect(send).toHaveBeenCalledTimes(2);
    expect(send.mock.calls[1]).toEqual([mode === 'create' ? '/teams' : '/teams/7', { ...payload, leader_id: 42, description: ' Retained ' }]);
  });
  it.each(modes)('%s retains two independent pending sends without a lock', async mode => {
    const first = deferred(), second = deferred(), send = mode === 'create' ? mock.post : mock.patch;
    send.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const scope = await mountForm(mode), target = save(scope, mode), before = reads('/teams'); fireEvent.click(target); fireEvent.click(target);
    const path = mode === 'create' ? '/teams' : '/teams/7';
    expect(send.mock.calls).toEqual([[path, payload], [path, payload]]); expect(target.disabled).toBe(false); expect(cancel(scope).disabled).toBe(false);
    await act(async () => { first.resolve(team); second.resolve(team); }); await waitFor(() => closed(scope, mode));
    if (mode !== 'full') await waitFor(() => expect(reads('/teams')).toBe(before + 2));
  });
  it.each(modes.flatMap(mode => ['name', 'zero', 'negative'].map(invalid => ({ mode, invalid }))))('$mode rejects $invalid natively with zero writes', async ({ mode, invalid }) => {
    const scope = await mountForm(mode), input = field(scope, invalid === 'name' ? 'teams.teamName' : 'teams.leaderUserIdLabel');
    fireEvent.change(input, { target: { value: invalid === 'name' ? '' : invalid === 'zero' ? '0' : '-1' } });
    if (invalid === 'name') expect(input.required).toBe(true);
    else { expect((input as HTMLInputElement).type).toBe('number'); expect((input as HTMLInputElement).min).toBe('1'); }
    expect(input.checkValidity()).toBe(false); fireEvent.click(save(scope, mode)); expect(mock.post).not.toHaveBeenCalled(); expect(mock.patch).not.toHaveBeenCalled();
  });
  it.each(modes)('%s textarea Enter inserts newline without sending', async mode => {
    const scope = await mountForm(mode), input = field(scope, 'common.description'), user = userEvent.setup();
    expect(input).toBeInstanceOf(HTMLTextAreaElement); await user.click(input); await user.keyboard('Line one{Enter}Line two');
    expect(input.value).toBe('Line one\nLine two'); expect(mock.post).not.toHaveBeenCalled(); expect(mock.patch).not.toHaveBeenCalled();
  });
  it.each([{ create: true, update: true }, { create: false, update: false }, { create: true, update: false }, { create: false, update: true }])('real permissions gate create=$create update=$update and row click', async ({ create, update }) => {
    permissions = [...(create ? ['teams.create'] : []), ...(update ? ['teams.update'] : [])]; await mount('quick');
    expect(!!screen.queryByRole('button', { name: tr('teams.newTeam') })).toBe(create); expect(!!screen.queryByRole('button', { name: tr('common.edit') })).toBe(update);
    fireEvent.click(screen.getByText('Fixture Team')); expect(screen.getByRole('dialog', { name: tr('teams.editTeam') }).classList.contains('comp-drawer-panel--open')).toBe(update);
    expect(mock.post).not.toHaveBeenCalled(); expect(mock.patch).not.toHaveBeenCalled();
  });
});

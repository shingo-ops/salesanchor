import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import NotificationsPage from '../pages/notifications/NotificationsPage';
import BadgesPage from '../pages/badges/BadgesPage';
import ShiftsPage from '../pages/shifts/ShiftsPage';
import BuddyPage from '../pages/buddy/BuddyPage';
import en from '../locales/en.json';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), delete: vi.fn() }));
vi.mock('../lib/api', () => ({ api: mock }));

type Kind = 'notifications' | 'badges' | 'shifts' | 'buddy';
const configs = {
  notifications: { Page: NotificationsPage, permission: 'notifications.manage', opener: 'settings.addChannel', title: 'settings.addDiscordWebhook', reads: ['/notification-channels'], post: '/notification-channels' },
  badges: { Page: BadgesPage, permission: 'badges.manage', opener: 'badges.newBadge', title: 'badges.newBadge', reads: ['/badges', '/badges/leaderboard'], post: '/badges' },
  shifts: { Page: ShiftsPage, permission: 'shifts.manage', opener: 'shifts.newShift', title: 'shifts.newShift', reads: ['/shifts'], post: '/shifts' },
  buddy: { Page: BuddyPage, permission: 'buddy.manage', opener: 'buddy.newPair', title: 'buddy.newPair', reads: ['/buddy/pairs', '/buddy/feedbacks'], post: '/buddy/pairs' },
} as const;
const kinds = Object.keys(configs) as Kind[];
const badgeIcon = String.fromCodePoint(0x1f3c6);
let instance = createInstance();
let granted = true;
const tr = (key: string) => String(instance.t(key));
function deferred() { let resolve!: (v: unknown) => void; let reject!: (e: Error) => void; const promise = new Promise((res, rej) => { resolve = res; reject = rej; }); return { promise, resolve, reject }; }
function payload(kind: Kind) {
  if (kind === 'notifications') return { channel_name: 'Channel fixture', webhook_url: ' https://example.test/hook ' };
  if (kind === 'badges') return { name: 'Badge fixture', description: null, icon: badgeIcon, criteria: '   ', points: 25 };
  if (kind === 'shifts') return { user_id: 7, shift_date: '2026-09-28', start_time: '08:30', end_time: '17:30', shift_type: 'night', notes: null };
  return { coach_user_id: 7, mentee_user_id: 8, notes: ' Buddy note ' };
}
function fill(kind: Kind, dialog: HTMLElement) {
  const inputs = Array.from(dialog.querySelectorAll<HTMLInputElement>('input'));
  const textareas = Array.from(dialog.querySelectorAll<HTMLTextAreaElement>('textarea'));
  const selects = Array.from(dialog.querySelectorAll<HTMLSelectElement>('select'));
  if (kind === 'notifications') {
    fireEvent.change(inputs[0], { target: { value: 'Channel fixture' } });
    fireEvent.change(inputs[1], { target: { value: ' https://example.test/hook ' } });
  } else if (kind === 'badges') {
    fireEvent.change(inputs[0], { target: { value: 'Badge fixture' } });
    fireEvent.change(inputs[1], { target: { value: badgeIcon } });
    fireEvent.change(textareas[0], { target: { value: '' } });
    fireEvent.change(inputs[2], { target: { value: '   ' } });
    fireEvent.change(inputs[3], { target: { value: '25' } });
  } else if (kind === 'shifts') {
    ['7', '2026-09-28', '08:30', '17:30'].forEach((value, i) => fireEvent.change(inputs[i], { target: { value } }));
    fireEvent.change(selects[0], { target: { value: 'night' } });
  } else {
    fireEvent.change(inputs[0], { target: { value: '7' } });
    fireEvent.change(inputs[1], { target: { value: '8' } });
    fireEvent.change(textareas[0], { target: { value: ' Buddy note ' } });
  }
}
function values(dialog: HTMLElement) { return Array.from(dialog.querySelectorAll<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>('input,textarea,select')).map(x => x.value); }
async function mount(kind: Kind) {
  const { Page, opener, title } = configs[kind];
  render(<I18nextProvider i18n={instance}><Page /></I18nextProvider>);
  const trigger = await screen.findByRole('button', { name: tr(opener) });
  trigger.focus();
  fireEvent.click(trigger);
  return { trigger, dialog: screen.getByRole('dialog', { name: tr(title) }) };
}
function reopen(kind: Kind) {
  const trigger = screen.getByRole('button', { name: tr(configs[kind].opener) });
  fireEvent.click(trigger);
  return { trigger, dialog: screen.getByRole('dialog', { name: tr(configs[kind].title) }) };
}
function submit(dialog: HTMLElement) { return within(dialog).getByRole('button', { name: /^(Add|Create|Register)$/ }) as HTMLButtonElement; }
function cancel(dialog: HTMLElement) { return within(dialog).getByRole('button', { name: tr('common.cancel') }) as HTMLButtonElement; }

beforeEach(async () => {
  vi.resetAllMocks(); granted = true;
  instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/me/permissions') return { permissions: granted ? kinds.map(k => configs[k].permission) : [] };
    if (kinds.some(k => configs[k].reads.includes(url as never))) return [];
    throw new Error('Unexpected GET ' + url);
  });
  mock.post.mockImplementation(() => { throw new Error('Unexpected POST'); });
  mock.delete.mockImplementation(() => { throw new Error('Unexpected DELETE'); });
});
afterEach(() => { cleanup(); expect(fetch).not.toHaveBeenCalled(); expect(mock.delete).not.toHaveBeenCalled(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('native form action Button migration', () => {
  it.each(kinds)('%s submits its exact payload, closes, resets as specified and reloads', async kind => {
    mock.post.mockResolvedValue({});
    const { dialog } = await mount(kind); fill(kind, dialog);
    const save = submit(dialog), stop = cancel(dialog);
    expect(save.type).toBe('submit'); expect(save.className).toBe('comp-btn comp-btn--primary');
    expect(stop.type).toBe('button'); expect(stop.className).toBe('comp-btn comp-btn--secondary');
    const before = Object.fromEntries(configs[kind].reads.map(url => [url, mock.get.mock.calls.filter(c => c[0] === url).length]));
    fireEvent.click(save);
    await waitFor(() => expect(mock.post).toHaveBeenCalledExactlyOnceWith(configs[kind].post, payload(kind)));
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    for (const url of configs[kind].reads) await waitFor(() => expect(mock.get.mock.calls.filter(c => c[0] === url)).toHaveLength(before[url] + 1));
    const reopened = reopen(kind);
    const values = Array.from(reopened.dialog.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>('input,textarea')).map(x => x.value);
    if (kind === 'notifications') expect(values.slice(0, 2)).toEqual(['', '']);
    if (kind === 'badges') expect(values).toEqual(['', badgeIcon, '', '', '10']);
    if (kind === 'shifts') expect(values.slice(0, 4)).toEqual(['7', '2026-09-28', '08:30', '17:30']);
    if (kind === 'buddy') expect(values).toEqual(['', '', '']);
  });

  it.each(kinds)('%s preserves cancel, failure/retry and unlocked duplicate pending submissions', async kind => {
    const { dialog } = await mount(kind); fill(kind, dialog);
    const cancelledValues = values(dialog);
    fireEvent.click(cancel(dialog)); expect(mock.post).not.toHaveBeenCalled();
    const reopened = reopen(kind); expect(values(reopened.dialog)).toEqual(cancelledValues);
    mock.post.mockRejectedValueOnce(new Error('Fixture failure')).mockResolvedValueOnce({});
    fireEvent.click(submit(reopened.dialog)); expect(await screen.findByText('Fixture failure')).toBeTruthy();
    fireEvent.click(submit(reopened.dialog)); await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    const again = reopen(kind); fill(kind, again.dialog); const pending = deferred(); mock.post.mockReturnValue(pending.promise);
    const save = submit(again.dialog), stop = cancel(again.dialog), label = save.textContent;
    fireEvent.click(save); fireEvent.click(save);
    expect(mock.post).toHaveBeenCalledTimes(4); expect(save.disabled).toBe(false); expect(stop.disabled).toBe(false);
    expect(save.getAttribute('aria-busy')).toBeNull(); expect(stop.getAttribute('aria-busy')).toBeNull(); expect(save.textContent).toBe(label);
    await act(async () => pending.resolve({}));
  });

  it.each(kinds)('%s retains native required guards and permission-gated opener', async kind => {
    const { dialog } = await mount(kind);
    const required = Array.from(dialog.querySelectorAll<HTMLInputElement>('input[required]'));
    expect(required.length).toBeGreaterThan(0);
    fireEvent.click(submit(dialog)); expect(mock.post).not.toHaveBeenCalled();
    cleanup(); vi.clearAllMocks(); granted = false; const Page = configs[kind].Page;
    render(<I18nextProvider i18n={instance}><Page /></I18nextProvider>);
    await waitFor(() => expect(mock.get).toHaveBeenCalledWith('/me/permissions'));
    await waitFor(() => expect(screen.queryByRole('button', { name: tr(configs[kind].opener) })).toBeNull());
  });

  it.each(kinds.flatMap(kind => ['close', 'escape'].map(method => ({ kind, method }))))('$kind $method closes and restores trigger focus', async ({ kind, method }) => {
    const { trigger, dialog } = await mount(kind);
    expect(document.activeElement).toBe(within(dialog).getByRole('button', { name: tr('common.close') }));
    if (method === 'close') fireEvent.click(within(dialog).getByRole('button', { name: tr('common.close') }));
    else fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('dialog', { name: tr(configs[kind].title) })).toBeNull();
    expect(document.activeElement).toBe(trigger); expect(mock.post).not.toHaveBeenCalled();
  });

  it.each(kinds.flatMap(kind => ['resolve', 'reject'].map(outcome => ({ kind, outcome }))))('$kind pending cancel then $outcome preserves its existing outcome', async ({ kind, outcome }) => {
    const pending = deferred(); mock.post.mockReturnValue(pending.promise);
    const { dialog } = await mount(kind); fill(kind, dialog); const original = values(dialog);
    const before = Object.fromEntries(configs[kind].reads.map(url => [url, mock.get.mock.calls.filter(c => c[0] === url).length]));
    fireEvent.click(submit(dialog)); fireEvent.click(cancel(dialog));
    await act(async () => outcome === 'resolve' ? pending.resolve({}) : pending.reject(new Error('Post-cancel failure')));
    if (outcome === 'resolve') {
      for (const url of configs[kind].reads) await waitFor(() => expect(mock.get.mock.calls.filter(c => c[0] === url)).toHaveLength(before[url] + 1));
      const reopened = reopen(kind); const next = values(reopened.dialog);
      if (kind === 'notifications' || kind === 'buddy') expect(next.every(value => value === '')).toBe(true);
      if (kind === 'badges') expect(next).toEqual(['', badgeIcon, '', '', '10']);
      if (kind === 'shifts') expect(next).toEqual(original);
    } else {
      expect(await screen.findByText('Post-cancel failure')).toBeTruthy();
      const reopened = reopen(kind); expect(values(reopened.dialog)).toEqual(original);
      for (const url of configs[kind].reads) expect(mock.get.mock.calls.filter(c => c[0] === url)).toHaveLength(before[url]);
    }
  });
});

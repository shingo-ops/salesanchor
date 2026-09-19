import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { GoogleCalendarStatusBar } from './GoogleCalendarStatusBar';

const { get } = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock('../lib/api', () => ({ api: { get } }));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));

beforeEach(() => {
  vi.useFakeTimers();
  get.mockReset();
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
});
const settle = () => act(async () => { await Promise.resolve(); });
const connected = { connected: true, configured: true, connected_at: null };
const disconnected = { connected: false, configured: true, connected_at: null };

describe('Google Calendar status notification dependencies', () => {
  it.each([
    [connected, 'connected', true],
    [disconnected, 'disconnected', false],
    [{ connected: false, configured: false, connected_at: null }, 'not_linked', false],
  ] as const)('preserves response %j as status %s and boolean %s', async (response, status, boolean) => {
    get.mockResolvedValue(response);
    const notify = vi.fn();
    const notifyBoolean = vi.fn();
    render(<GoogleCalendarStatusBar onConnect={vi.fn()} onReconnect={vi.fn()} canManage={false}
      onSyncStatusChange={notify} onStatusChange={notifyBoolean} />);
    await settle();
    expect(get).toHaveBeenCalledExactlyOnceWith('/google-calendar/status');
    expect(notify).toHaveBeenCalledExactlyOnceWith(status);
    expect(notifyBoolean).toHaveBeenCalledExactlyOnceWith(boolean);
    expect(screen.queryByRole('status') !== null).toBe(status !== 'not_linked');
  });

  it('supports omitted notification callbacks', async () => {
    get.mockResolvedValue(connected);
    render(<GoogleCalendarStatusBar onConnect={vi.fn()} onReconnect={vi.fn()} canManage={false} />);
    await settle();
    expect(screen.getByRole('status')).not.toBeNull();
    expect(get).toHaveBeenCalledTimes(1);
  });

  it('sends new fetch results only to the replacement callback and keeps one interval', async () => {
    get.mockResolvedValueOnce(connected).mockResolvedValue(disconnected);
    const oldNotify = vi.fn();
    const newNotify = vi.fn();
    const props = { onConnect: vi.fn(), onReconnect: vi.fn(), canManage: false, onStatusChange: vi.fn() };
    const { rerender, unmount } = render(<GoogleCalendarStatusBar {...props} onSyncStatusChange={oldNotify} />);
    await settle();
    expect(oldNotify).toHaveBeenCalledExactlyOnceWith('connected');
    rerender(<GoogleCalendarStatusBar {...props} onSyncStatusChange={newNotify} />);
    await settle();
    expect(newNotify).toHaveBeenCalledExactlyOnceWith('disconnected');
    expect(oldNotify).toHaveBeenCalledTimes(1);
    expect(get).toHaveBeenCalledTimes(2);
    expect(vi.getTimerCount()).toBe(1);
    await act(async () => { await vi.advanceTimersByTimeAsync(30_000); });
    expect(get).toHaveBeenCalledTimes(3);
    expect(newNotify).toHaveBeenCalledTimes(2);
    expect(oldNotify).toHaveBeenCalledTimes(1);
    expect(vi.getTimerCount()).toBe(1);
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });

  it('does not refetch for stable dependencies and clears settled polling on unmount', async () => {
    get.mockResolvedValue(connected);
    const props = { onConnect: vi.fn(), onReconnect: vi.fn(), canManage: false,
      onStatusChange: vi.fn(), onSyncStatusChange: vi.fn() };
    const { rerender, unmount } = render(<GoogleCalendarStatusBar {...props} />);
    await settle();
    rerender(<GoogleCalendarStatusBar {...props} canManage />);
    await settle();
    expect(get).toHaveBeenCalledTimes(1);
    expect(vi.getTimerCount()).toBe(1);
    await act(async () => { await vi.advanceTimersByTimeAsync(29_999); });
    expect(get).toHaveBeenCalledTimes(1);
    await act(async () => { await vi.advanceTimersByTimeAsync(1); });
    expect(get).toHaveBeenCalledTimes(2);
    await act(async () => { await vi.advanceTimersByTimeAsync(30_000); });
    expect(get).toHaveBeenCalledTimes(3);
    unmount();
    expect(vi.getTimerCount()).toBe(0);
    await act(async () => { await vi.advanceTimersByTimeAsync(60_000); });
    expect(get).toHaveBeenCalledTimes(3);
  });

  it('disables reconnect while pending and refetches after completion', async () => {
    get.mockResolvedValue(disconnected);
    let finish!: () => void;
    const reconnect = vi.fn(() => new Promise<void>((resolve) => { finish = resolve; }));
    const notify = vi.fn();
    render(<GoogleCalendarStatusBar onConnect={vi.fn()} onReconnect={reconnect} canManage onSyncStatusChange={notify} />);
    await settle();
    const button = screen.getByRole('button', { name: 'schedule.statusReconnect' }) as HTMLButtonElement;
    fireEvent.click(button);
    expect(reconnect).toHaveBeenCalledTimes(1);
    expect(button.disabled).toBe(true);
    expect(button.textContent).toBe('common.saving');
    expect(get).toHaveBeenCalledTimes(1);
    await act(async () => { finish(); await Promise.resolve(); });
    expect(get).toHaveBeenCalledTimes(2);
    expect(notify).toHaveBeenLastCalledWith('disconnected');
    expect(notify).toHaveBeenCalledTimes(2);
    expect(button.disabled).toBe(false);
    expect(button.textContent).toBe('schedule.statusReconnect');
  });
});

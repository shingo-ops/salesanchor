import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AppUpdateNotice } from './AppUpdateNotice';

const { useAppUpdateCheck } = vi.hoisted(() => ({ useAppUpdateCheck: vi.fn() }));
vi.mock('../hooks/useAppUpdateCheck', () => ({ useAppUpdateCheck }));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));

const reload = vi.fn();

beforeEach(() => {
  reload.mockReset();
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: { ...window.location, reload },
  });
});
afterEach(() => {
  cleanup();
  useAppUpdateCheck.mockReset();
});

describe('AppUpdateNotice', () => {
  it('renders nothing while no new version is available', () => {
    useAppUpdateCheck.mockReturnValue(false);
    render(<AppUpdateNotice />);
    expect(screen.queryByTestId('app-update-notice')).toBeNull();
    expect(reload).not.toHaveBeenCalled();
  });

  it('K5: shows the message and button; reload is called once only after pressing the button', () => {
    useAppUpdateCheck.mockReturnValue(true);
    render(<AppUpdateNotice />);
    expect(screen.getByRole('status').textContent).toContain('appUpdate.message');
    expect(reload).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'appUpdate.reload' }));
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it('has no close button (only the reload button)', () => {
    useAppUpdateCheck.mockReturnValue(true);
    render(<AppUpdateNotice />);
    expect(screen.getAllByRole('button')).toHaveLength(1);
  });
});

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { IconToggleButton } from './IconToggleButton';
import type { Icon } from '../constants/icons';

afterEach(cleanup);

const IconOff = (() => <svg data-testid="icon-off" />) as unknown as Icon;
const IconOn = (() => <svg data-testid="icon-on" />) as unknown as Icon;

const setup = (props: Partial<Parameters<typeof IconToggleButton>[0]> = {}) =>
  render(
    <IconToggleButton
      pressed={false}
      onClick={() => {}}
      iconOff={IconOff}
      iconOn={IconOn}
      aria-label="toggle"
      {...props}
    />,
  );

describe('IconToggleButton', () => {
  it('shows the off icon and aria-pressed=false when not pressed', () => {
    setup();
    expect(screen.getByRole('button', { name: 'toggle' }).getAttribute('aria-pressed')).toBe('false');
    expect(screen.queryByTestId('icon-off')).not.toBeNull();
    expect(screen.queryByTestId('icon-on')).toBeNull();
  });

  it('shows the on icon and aria-pressed=true when pressed', () => {
    setup({ pressed: true });
    expect(screen.getByRole('button', { name: 'toggle' }).getAttribute('aria-pressed')).toBe('true');
    expect(screen.queryByTestId('icon-on')).not.toBeNull();
    expect(screen.queryByTestId('icon-off')).toBeNull();
  });

  it('calls onClick when clicked', () => {
    const onClick = vi.fn();
    setup({ onClick });
    fireEvent.click(screen.getByRole('button', { name: 'toggle' }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('does not call onClick when disabled', () => {
    const onClick = vi.fn();
    setup({ onClick, disabled: true });
    fireEvent.click(screen.getByRole('button', { name: 'toggle' }));
    expect(onClick).not.toHaveBeenCalled();
  });

  it('renders the count only when provided', () => {
    const { rerender } = setup({ count: 3 });
    expect(screen.getByText('3')).not.toBeNull();
    rerender(
      <IconToggleButton pressed={false} onClick={() => {}} iconOff={IconOff} iconOn={IconOn} aria-label="toggle" />,
    );
    expect(screen.queryByText('3')).toBeNull();
  });
});

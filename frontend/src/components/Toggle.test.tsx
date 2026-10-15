import { createRef } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Toggle } from './Toggle';

afterEach(cleanup);

describe('Toggle', () => {
  it('renders a native checkbox with role=switch reflecting checked', () => {
    const { rerender } = render(<Toggle checked={false} onCheckedChange={() => {}} aria-label="Dark" />);
    const sw = screen.getByRole('switch', { name: 'Dark' }) as HTMLInputElement;
    expect(sw.tagName).toBe('INPUT');
    expect(sw.type).toBe('checkbox');
    expect(sw.checked).toBe(false);
    rerender(<Toggle checked onCheckedChange={() => {}} aria-label="Dark" />);
    expect(sw.checked).toBe(true);
  });

  it('calls onCheckedChange with the next value', () => {
    const fn = vi.fn();
    const { rerender } = render(<Toggle checked={false} onCheckedChange={fn} aria-label="x" />);
    fireEvent.click(screen.getByRole('switch'));
    expect(fn).toHaveBeenLastCalledWith(true);
    rerender(<Toggle checked onCheckedChange={fn} aria-label="x" />);
    fireEvent.click(screen.getByRole('switch'));
    expect(fn).toHaveBeenLastCalledWith(false);
    expect(fn).toHaveBeenCalledTimes(2);
  });

  it('does not call onCheckedChange when disabled', async () => {
    const fn = vi.fn();
    render(<Toggle checked={false} onCheckedChange={fn} disabled aria-label="x" />);
    const sw = screen.getByRole('switch') as HTMLInputElement;
    expect(sw.disabled).toBe(true);
    await userEvent.click(sw);
    expect(fn).not.toHaveBeenCalled();
    expect(sw.closest('label')?.className).toContain('comp-toggle--disabled');
  });

  it('passes id, aria-label and aria-labelledby to the input and forwards ref', () => {
    const ref = createRef<HTMLInputElement>();
    render(<><span id="lbl">Label</span><Toggle ref={ref} id="t1" checked={false} onCheckedChange={() => {}} aria-labelledby="lbl" /></>);
    const sw = screen.getByRole('switch', { name: 'Label' });
    expect(sw.id).toBe('t1');
    expect(ref.current).toBe(sw);
    cleanup();
    render(<Toggle checked={false} onCheckedChange={() => {}} aria-label="Named" />);
    expect(screen.getByRole('switch').getAttribute('aria-label')).toBe('Named');
  });

  it('does not accept className or style (type-level and runtime)', () => {
    // @ts-expect-error className is not part of ToggleProps
    render(<Toggle checked={false} onCheckedChange={() => {}} aria-label="x" className="evil" />);
    // @ts-expect-error style is not part of ToggleProps
    render(<Toggle checked={false} onCheckedChange={() => {}} aria-label="y" style={{ display: 'none' }} />);
    const labels = screen.getAllByRole('switch').map((el) => el.closest('label') as HTMLElement);
    for (const l of labels) {
      expect(l.className).toBe('comp-toggle');
      expect(l.getAttribute('style')).toBeNull();
    }
  });
});

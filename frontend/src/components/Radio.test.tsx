import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { Radio } from './Radio';

afterEach(cleanup);

describe('Radio', () => {
  it('connects the label to a native radio input', () => {
    render(<Radio label="Option A" name="g" value="a" checked={false} onChange={() => {}} />);
    const el = screen.getByLabelText('Option A') as HTMLInputElement;
    expect(el.tagName).toBe('INPUT');
    expect(el.type).toBe('radio');
    expect(el.className).toBe('comp-radio__input');
  });

  it('calls onChange when pressed', () => {
    const fn = vi.fn();
    render(<Radio label="Option A" name="g" value="a" checked={false} onChange={fn} />);
    fireEvent.click(screen.getByLabelText('Option A'));
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('points aria-describedby at the description text', () => {
    render(<Radio label="Option A" description="Hint text" checked={false} onChange={() => {}} />);
    const el = screen.getByLabelText(/Option A/) as HTMLInputElement;
    const hint = screen.getByText('Hint text');
    expect(el.getAttribute('aria-describedby')).toBe(hint.id);
    expect(hint.getAttribute('role')).toBeNull();
  });

  it('sets aria-invalid and role alert on error', () => {
    render(<Radio label="Option A" error="Pick one" checked={false} onChange={() => {}} />);
    const el = screen.getByLabelText(/Option A/) as HTMLInputElement;
    expect(el.getAttribute('aria-invalid')).toBe('true');
    const msg = screen.getByRole('alert');
    expect(msg.textContent).toBe('Pick one');
    expect(el.getAttribute('aria-describedby')).toBe(msg.id);
  });

  it('passes disabled to the input', () => {
    render(<Radio label="Option A" disabled checked={false} onChange={() => {}} />);
    expect((screen.getByLabelText('Option A') as HTMLInputElement).disabled).toBe(true);
  });
});

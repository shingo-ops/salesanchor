import { createRef } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { RadioControl } from './RadioControl';

afterEach(cleanup);

describe('RadioControl', () => {
  it('renders a single native radio input with no wrapper', () => {
    const { container } = render(<RadioControl checked={false} onChange={() => {}} aria-label="x" />);
    expect(container.children).toHaveLength(1);
    const el = container.firstChild as HTMLInputElement;
    expect(el.tagName).toBe('INPUT');
    expect(el.type).toBe('radio');
    expect(el.className).toBe('comp-radio-control');
  });

  it('passes checked, onChange, disabled, aria-label, data-testid, name and value to the same input', () => {
    const fn = vi.fn();
    const { rerender } = render(
      <RadioControl checked={false} onChange={fn} aria-label="Pick" data-testid="rc" name="n" value="v" />,
    );
    const el = screen.getByTestId('rc') as HTMLInputElement;
    expect(el.getAttribute('aria-label')).toBe('Pick');
    expect(el.name).toBe('n');
    expect(el.value).toBe('v');
    expect(el.checked).toBe(false);
    fireEvent.click(el);
    expect(fn).toHaveBeenCalledTimes(1);
    rerender(<RadioControl checked onChange={fn} aria-label="Pick" data-testid="rc" disabled />);
    expect(el.checked).toBe(true);
    expect(el.disabled).toBe(true);
  });

  it('passes readOnly to the input', () => {
    render(<RadioControl checked readOnly aria-label="ro" />);
    expect((screen.getByLabelText('ro') as HTMLInputElement).readOnly).toBe(true);
  });

  it('calls onChange of the one that is pressed among two with the same name', () => {
    const a = vi.fn();
    const b = vi.fn();
    render(
      <>
        <RadioControl name="g" value="a" checked onChange={a} aria-label="a" />
        <RadioControl name="g" value="b" checked={false} onChange={b} aria-label="b" />
      </>,
    );
    fireEvent.click(screen.getByLabelText('b'));
    expect(b).toHaveBeenCalledTimes(1);
    expect(a).not.toHaveBeenCalled();
  });

  it('hands the input element itself to both function refs and object refs', () => {
    const objRef = createRef<HTMLInputElement>();
    const fnRef = vi.fn();
    render(
      <>
        <RadioControl ref={objRef} checked={false} onChange={() => {}} aria-label="a" />
        <RadioControl ref={fnRef} checked={false} onChange={() => {}} aria-label="b" />
      </>,
    );
    const [a, b] = screen.getAllByRole('radio');
    expect(objRef.current).toBe(a);
    expect(fnRef).toHaveBeenCalledWith(b);
  });

  it('does not accept className, style or type (type-level)', () => {
    // @ts-expect-error className is not part of RadioControlProps
    render(<RadioControl checked={false} onChange={() => {}} aria-label="x" className="evil" />);
    // @ts-expect-error style is not part of RadioControlProps
    render(<RadioControl checked={false} onChange={() => {}} aria-label="y" style={{ display: 'none' }} />);
    // @ts-expect-error type is not part of RadioControlProps
    render(<RadioControl checked={false} onChange={() => {}} aria-label="z" type="checkbox" />);
    expect(screen.getAllByLabelText(/^[xyz]$/)).toHaveLength(3);
  });
});

import { createRef } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { CheckboxControl } from './CheckboxControl';

afterEach(cleanup);

describe('CheckboxControl', () => {
  it('renders a single native checkbox input with no wrapper', () => {
    const { container } = render(<CheckboxControl checked={false} onChange={() => {}} aria-label="x" />);
    expect(container.children).toHaveLength(1);
    const el = container.firstChild as HTMLInputElement;
    expect(el.tagName).toBe('INPUT');
    expect(el.type).toBe('checkbox');
    expect(el.className).toBe('comp-checkbox');
  });

  it('passes checked, onChange, disabled, aria-label, data-testid, name and value to the same input', () => {
    const fn = vi.fn();
    const { rerender } = render(
      <CheckboxControl checked={false} onChange={fn} aria-label="Pick" data-testid="cb" name="n" value="v" />,
    );
    const el = screen.getByTestId('cb') as HTMLInputElement;
    expect(el.getAttribute('aria-label')).toBe('Pick');
    expect(el.name).toBe('n');
    expect(el.value).toBe('v');
    expect(el.checked).toBe(false);
    fireEvent.click(el);
    expect(fn).toHaveBeenCalledTimes(1);
    rerender(<CheckboxControl checked onChange={fn} aria-label="Pick" data-testid="cb" disabled />);
    expect(el.checked).toBe(true);
    expect(el.disabled).toBe(true);
  });

  it('reflects indeterminate to the DOM property and resets it', () => {
    const { rerender } = render(<CheckboxControl checked={false} indeterminate onChange={() => {}} aria-label="x" />);
    const el = screen.getByRole('checkbox') as HTMLInputElement;
    expect(el.indeterminate).toBe(true);
    rerender(<CheckboxControl checked={false} indeterminate={false} onChange={() => {}} aria-label="x" />);
    expect(el.indeterminate).toBe(false);
  });

  it('hands the input element itself to both function refs and object refs', () => {
    const objRef = createRef<HTMLInputElement>();
    const fnRef = vi.fn();
    render(
      <>
        <CheckboxControl ref={objRef} checked={false} onChange={() => {}} aria-label="a" />
        <CheckboxControl ref={fnRef} checked={false} onChange={() => {}} aria-label="b" />
      </>,
    );
    const [a, b] = screen.getAllByRole('checkbox');
    expect(objRef.current).toBe(a);
    expect(fnRef).toHaveBeenCalledWith(b);
  });

  it('adds comp-checkbox--sm when size is sm', () => {
    render(<CheckboxControl size="sm" checked={false} onChange={() => {}} aria-label="x" />);
    expect(screen.getByRole('checkbox').className).toBe('comp-checkbox comp-checkbox--sm');
  });

  it('does not accept className, style or type (type-level)', () => {
    // @ts-expect-error className is not part of CheckboxControlProps
    render(<CheckboxControl checked={false} onChange={() => {}} aria-label="x" className="evil" />);
    // @ts-expect-error style is not part of CheckboxControlProps
    render(<CheckboxControl checked={false} onChange={() => {}} aria-label="y" style={{ display: 'none' }} />);
    // @ts-expect-error type is not part of CheckboxControlProps
    render(<CheckboxControl checked={false} onChange={() => {}} aria-label="z" type="radio" />);
    expect(screen.getAllByLabelText(/^[xyz]$/)).toHaveLength(3);
  });
});

import { createRef } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { Button, type ButtonVariant } from './Button';

afterEach(cleanup);

describe('Button native contract', () => {
  it('forwards focus to the same native button through prop changes', () => {
    const ref = createRef<HTMLButtonElement>();
    const { rerender, unmount } = render(<Button ref={ref}>Save</Button>);
    const node = screen.getByRole('button');
    expect(ref.current).toBe(node);
    ref.current?.focus();
    expect(document.activeElement).toBe(node);
    rerender(<Button ref={ref} variant="secondary" loading>Save</Button>);
    expect(ref.current).toBe(node);
    expect(node.tagName).toBe('BUTTON');
    unmount();
    expect(ref.current).toBeNull();
  });

  it('preserves omitted type, external form association, name/value and submitter', () => {
    const submitted = vi.fn();
    render(<><form id="external" onSubmit={(event) => {
      event.preventDefault();
      submitted((event.nativeEvent as SubmitEvent).submitter);
    }} /><Button form="external" name="action" value="save">Save</Button></>);
    const button = screen.getByRole('button') as HTMLButtonElement;
    expect(button.hasAttribute('type')).toBe(false);
    expect(button.type).toBe('submit');
    expect(button.form).toBe(document.getElementById('external'));
    expect(button.name).toBe('action');
    expect(button.value).toBe('save');
    fireEvent.click(button);
    expect(submitted).toHaveBeenCalledExactlyOnceWith(button);
  });

  it.each(['button', 'submit'] as const)('preserves explicit type=%s and click/submit behavior', (type) => {
    const click = vi.fn();
    const submit = vi.fn();
    render(<form onSubmit={(event) => { event.preventDefault(); submit(); }}>
      <Button type={type} onClick={click}>Save</Button>
    </form>);
    const button = screen.getByRole('button');
    expect(button.getAttribute('type')).toBe(type);
    fireEvent.click(button);
    expect(click).toHaveBeenCalledTimes(1);
    expect(submit).toHaveBeenCalledTimes(type === 'submit' ? 1 : 0);
  });

  it('preserves native event currentTarget and caller stopPropagation', () => {
    const parent = vi.fn();
    const target = vi.fn();
    render(<div onClick={parent}><Button type="button" onClick={(event) => {
      event.stopPropagation(); target(event.currentTarget);
    }}>Save</Button></div>);
    const button = screen.getByRole('button');
    fireEvent.click(button);
    expect(target).toHaveBeenCalledExactlyOnceWith(button);
    expect(parent).not.toHaveBeenCalled();
  });

  it.each<ButtonVariant>(['primary', 'secondary', 'ghost', 'danger', 'outline', 'tab'])(
    'retains %s classes, native props, and prevents disabled/loading callbacks', (variant) => {
      const click = vi.fn();
      const props = { variant, active: true, size: 'lg' as const, fullWidth: true,
        layoutClassName: 'caller-class', title: 'Help', 'data-testid': 'target', onClick: click };
      const { rerender } = render(<Button {...props}>Save</Button>);
      const button = screen.getByRole('button') as HTMLButtonElement;
      expect(button.classList.contains(`comp-btn--${variant}`)).toBe(true);
      expect(button.classList.contains('comp-btn--full')).toBe(true);
      expect(button.classList.contains('caller-class')).toBe(true);
      expect(button.classList.contains('comp-btn--lg')).toBe(variant !== 'tab');
      expect(button.classList.contains('comp-btn--active')).toBe(variant === 'tab');
      expect(button.getAttribute('aria-pressed')).toBe(variant === 'tab' ? 'true' : null);
      expect(button.title).toBe('Help');
      fireEvent.click(button);
      expect(click).toHaveBeenCalledTimes(1);
      rerender(<Button {...props} disabled>Save</Button>);
      expect(button.disabled).toBe(true);
      fireEvent.click(button);
      rerender(<Button {...props} loading>Save</Button>);
      fireEvent.click(button);
      expect(click).toHaveBeenCalledTimes(1);
      expect(button.disabled).toBe(true);
      expect(button.getAttribute('aria-busy')).toBe('true');
      expect(screen.getByRole('button', { name: 'Save' })).toBe(button);
      const spinner = button.querySelector('.sa-spinner');
      expect(spinner?.classList.contains('sa-spinner--inherit')).toBe(true);
      expect(spinner?.getAttribute('aria-hidden')).toBe('true');
      expect(spinner?.hasAttribute('role')).toBe(false);
      expect(spinner?.hasAttribute('aria-label')).toBe(false);
    },
  );

  it('preserves loadingText, iconOnly name and native aria override order', () => {
    const { rerender } = render(<Button loading loadingText="Saving">Save</Button>);
    expect(screen.getByRole('button', { name: 'Saving' }).textContent).toBe('Saving');
    rerender(<Button loading iconOnly aria-label="Send"><span aria-hidden="true">X</span></Button>);
    const button = screen.getByRole('button', { name: 'Send' });
    expect(button.classList.contains('comp-btn--icon-only')).toBe(true);
    rerender(<Button variant="tab" active aria-pressed={false} aria-busy={false}
      layoutClassName="caller-layout">Save</Button>);
    expect(button.getAttribute('aria-pressed')).toBe('false');
    expect(button.getAttribute('aria-busy')).toBe('false');
    expect(button.classList.contains('caller-layout')).toBe(true);
    expect(button.hasAttribute('style')).toBe(false);
  });
});

// Public appearance overrides are rejected; native layout/events remain supported.
const validLayout = <Button layoutClassName="caller-layout" />;
// @ts-expect-error Button appearance belongs to Button.css.
const rejectedStyle = <Button style={{ marginLeft: 5 }} />;
// @ts-expect-error Use the layout-only entry instead.
const rejectedClassName = <Button className="caller-class" />;
void [validLayout, rejectedStyle, rejectedClassName];

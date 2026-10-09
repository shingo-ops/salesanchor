import { createRef } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TextField, TextFieldControl } from './TextField';

afterEach(cleanup);

const LABEL = '<label for="t" class="comp-field__label">Name</label>';
const INPUT = '<input id="t" class="comp-field__input">';

describe('TextField (labelled) output is pinned', () => {
  it('(a) label only', () => {
    const { container } = render(<TextField id="t" label="Name" />);
    expect(container.innerHTML).toBe(`<div class="comp-field">${LABEL}${INPUT}</div>`);
  });

  it('(b) label and required', () => {
    const { container } = render(<TextField id="t" label="Name" required />);
    expect(container.innerHTML).toBe(
      '<div class="comp-field">' +
        '<label for="t" class="comp-field__label">Name<span class="comp-field__required" aria-hidden="true">*</span></label>' +
        '<input id="t" class="comp-field__input" required=""></div>',
    );
  });

  it('(c) helperText', () => {
    const { container } = render(<TextField id="t" label="Name" helperText="Help" />);
    expect(container.innerHTML).toBe(
      `<div class="comp-field">${LABEL}${INPUT}<p class="comp-field__hint">Help</p></div>`,
    );
  });

  it('(d) error', () => {
    const { container } = render(<TextField id="t" label="Name" error="Bad" />);
    expect(container.innerHTML).toBe(
      `<div class="comp-field comp-field--error">${LABEL}${INPUT}` +
        '<p class="comp-field__hint comp-field__hint--error" role="alert">Bad</p></div>',
    );
  });

  it('(e) size="sm"', () => {
    const { container } = render(<TextField id="t" label="Name" size="sm" />);
    expect(container.innerHTML).toBe(`<div class="comp-field comp-field--sm">${LABEL}${INPUT}</div>`);
  });

  it('(f) size="lg"', () => {
    const { container } = render(<TextField id="t" label="Name" size="lg" />);
    expect(container.innerHTML).toBe(`<div class="comp-field comp-field--lg">${LABEL}${INPUT}</div>`);
  });

  it('(g) fullWidth', () => {
    const { container } = render(<TextField id="t" label="Name" fullWidth />);
    expect(container.innerHTML).toBe(`<div class="comp-field comp-field--full">${LABEL}${INPUT}</div>`);
  });

  it('(h) className', () => {
    const { container } = render(<TextField id="t" label="Name" className="x-layout" />);
    expect(container.innerHTML).toBe(`<div class="comp-field x-layout">${LABEL}${INPUT}</div>`);
  });

  it('(i) email with value, onChange, placeholder, maxLength, disabled, aria-label, data-testid', () => {
    const { container } = render(
      <TextField
        id="t"
        type="email"
        value="v"
        onChange={() => {}}
        placeholder="ph"
        maxLength={10}
        disabled
        aria-label="al"
        data-testid="tid"
      />,
    );
    expect(container.innerHTML).toBe(
      '<div class="comp-field">' +
        '<input id="t" class="comp-field__input" type="email" placeholder="ph" maxlength="10" disabled="" aria-label="al" data-testid="tid" value="v"></div>',
    );
  });

  it('(j) number with min, max, step, readOnly', () => {
    const { container } = render(<TextField id="t" type="number" min={1} max={9} step={2} readOnly />);
    expect(container.innerHTML).toBe(
      '<div class="comp-field">' +
        '<input id="t" class="comp-field__input" type="number" min="1" max="9" step="2" readonly=""></div>',
    );
  });

  it('(k) without label', () => {
    const { container } = render(<TextField id="t" />);
    expect(container.innerHTML).toBe(`<div class="comp-field">${INPUT}</div>`);
  });
});

describe('TextFieldControl', () => {
  it('renders a single input with no wrapper div or label', () => {
    const { container } = render(<TextFieldControl />);
    expect(container.children).toHaveLength(1);
    expect(container.firstElementChild?.tagName).toBe('INPUT');
  });

  it('applies size classes and appends className last', () => {
    const { container, rerender } = render(<TextFieldControl />);
    const cls = () => container.querySelector('input')?.className;
    expect(cls()).toBe('comp-field__input');
    rerender(<TextFieldControl size="sm" />);
    expect(cls()).toBe('comp-field__input comp-field__input--sm');
    rerender(<TextFieldControl size="lg" />);
    expect(cls()).toBe('comp-field__input comp-field__input--lg');
    rerender(<TextFieldControl size="md" className="x" />);
    expect(cls()).toBe('comp-field__input x');
    rerender(<TextFieldControl size="sm" className="x" />);
    expect(cls()).toBe('comp-field__input comp-field__input--sm x');
  });

  it('object ref receives the input element and getBoundingClientRect is callable', () => {
    const ref = createRef<HTMLInputElement>();
    const { container } = render(<TextFieldControl ref={ref} />);
    expect(ref.current).toBeInstanceOf(HTMLInputElement);
    expect(ref.current).toBe(container.querySelector('input'));
    expect(typeof ref.current?.getBoundingClientRect).toBe('function');
    expect(ref.current?.getBoundingClientRect()).toBeTruthy();
  });

  it('function ref receives the input element', () => {
    const ref = vi.fn();
    const { container } = render(<TextFieldControl ref={ref} />);
    expect(ref).toHaveBeenCalledWith(container.querySelector('input'));
  });

  it('passes attributes to the same element', () => {
    const { container } = render(
      <TextFieldControl
        type="number"
        value="5"
        onChange={() => {}}
        placeholder="ph"
        maxLength={9}
        min={1}
        max={9}
        step={2}
        disabled
        readOnly
        required
        aria-label="al"
        data-testid="tid"
        id="i"
        autoComplete="off"
      />,
    );
    const el = container.querySelector('input') as HTMLInputElement;
    expect(el.type).toBe('number');
    expect(el.value).toBe('5');
    expect(el.getAttribute('placeholder')).toBe('ph');
    expect(el.getAttribute('maxlength')).toBe('9');
    expect(el.getAttribute('min')).toBe('1');
    expect(el.getAttribute('max')).toBe('9');
    expect(el.getAttribute('step')).toBe('2');
    expect(el.disabled).toBe(true);
    expect(el.readOnly).toBe(true);
    expect(el.required).toBe(true);
    expect(el.getAttribute('aria-label')).toBe('al');
    expect(el.getAttribute('data-testid')).toBe('tid');
    expect(el.id).toBe('i');
    expect(el.getAttribute('autocomplete')).toBe('off');
  });

  it('calls handlers on input, Enter and blur without preventing Enter default', async () => {
    const onChange = vi.fn();
    const onBlur = vi.fn();
    let prevented: boolean | null = null;
    const onKeyDown = vi.fn((e: React.KeyboardEvent) => {
      prevented = e.defaultPrevented;
    });
    const { container } = render(
      <TextFieldControl onChange={onChange} onBlur={onBlur} onKeyDown={onKeyDown} />,
    );
    const el = container.querySelector('input') as HTMLInputElement;
    const user = userEvent.setup();
    await user.click(el);
    await user.keyboard('a');
    expect(onChange).toHaveBeenCalled();
    await user.keyboard('{Enter}');
    expect(onKeyDown).toHaveBeenCalled();
    expect(prevented).toBe(false);
    expect(fireEvent.keyDown(el, { key: 'Enter' })).toBe(true);
    await user.tab();
    expect(onBlur).toHaveBeenCalledTimes(1);
  });

  it('omits type, placeholder and id attributes when unspecified', () => {
    const { container } = render(<TextFieldControl />);
    const el = container.querySelector('input') as HTMLInputElement;
    expect(el.hasAttribute('type')).toBe(false);
    expect(el.hasAttribute('placeholder')).toBe(false);
    expect(el.hasAttribute('id')).toBe(false);
  });
});

describe('TextFieldControl variants (design.md §AY-2a)', () => {
  const VARIANTS = ['karte', 'search', 'schedule', 'composer'] as const;

  it.each(VARIANTS)('variant "%s" adds its class before className', (variant) => {
    const { container } = render(<TextFieldControl variant={variant} className="x-layout" />);
    expect(container.querySelector('input')?.className).toBe(`comp-field__input comp-input--${variant} x-layout`);
  });

  it('variant "standard" or omitted adds no variant class', () => {
    const { container, rerender } = render(<TextFieldControl variant="standard" size="sm" />);
    const cls = () => container.querySelector('input')?.className;
    expect(cls()).toBe('comp-field__input comp-field__input--sm');
    rerender(<TextFieldControl />);
    expect(cls()).toBe('comp-field__input');
  });

  it('does not forward variant to the DOM as an attribute', () => {
    const { container } = render(<TextFieldControl variant="karte" id="v" />);
    expect(container.innerHTML).toBe('<input id="v" class="comp-field__input comp-input--karte">');
  });

  it('size cannot be combined with a non-standard variant (type error)', () => {
    // @ts-expect-error size is not accepted together with variant="karte"
    const element = <TextFieldControl variant="karte" size="sm" />;
    expect(element).toBeTruthy();
  });

  it.each(VARIANTS)('variant "%s" passes ref and onKeyDown through (Enter default not prevented)', async (variant) => {
    const ref = createRef<HTMLInputElement>();
    let prevented: boolean | null = null;
    const onKeyDown = vi.fn((e: React.KeyboardEvent) => {
      prevented = e.defaultPrevented;
    });
    const { container } = render(<TextFieldControl variant={variant} ref={ref} onKeyDown={onKeyDown} />);
    const el = container.querySelector('input') as HTMLInputElement;
    expect(ref.current).toBe(el);
    const user = userEvent.setup();
    await user.click(el);
    await user.keyboard('{Enter}');
    expect(onKeyDown).toHaveBeenCalled();
    expect(prevented).toBe(false);
  });
});

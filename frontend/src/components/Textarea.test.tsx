import { createRef } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Textarea, TextareaControl } from './Textarea';

afterEach(cleanup);

const LABEL = '<label for="t" class="comp-field__label">Name</label>';
const AREA = '<textarea id="t" class="comp-field__textarea"></textarea>';

describe('Textarea (labelled) output is pinned', () => {
  it('(a) label only', () => {
    const { container } = render(<Textarea id="t" label="Name" />);
    expect(container.innerHTML).toBe(`<div class="comp-field">${LABEL}${AREA}</div>`);
  });

  it('(b) label and required', () => {
    const { container } = render(<Textarea id="t" label="Name" required />);
    expect(container.innerHTML).toBe(
      '<div class="comp-field">' +
        '<label for="t" class="comp-field__label">Name<span class="comp-field__required" aria-hidden="true">*</span></label>' +
        '<textarea id="t" class="comp-field__textarea" required=""></textarea></div>',
    );
  });

  it('(c) helperText', () => {
    const { container } = render(<Textarea id="t" label="Name" helperText="Help" />);
    expect(container.innerHTML).toBe(
      `<div class="comp-field">${LABEL}${AREA}<p class="comp-field__hint">Help</p></div>`,
    );
  });

  it('(d) error', () => {
    const { container } = render(<Textarea id="t" label="Name" error="Bad" />);
    expect(container.innerHTML).toBe(
      `<div class="comp-field comp-field--error">${LABEL}${AREA}` +
        '<p class="comp-field__hint comp-field__hint--error" role="alert">Bad</p></div>',
    );
  });

  it('(e) size="sm"', () => {
    const { container } = render(<Textarea id="t" label="Name" size="sm" />);
    expect(container.innerHTML).toBe(`<div class="comp-field comp-field--sm">${LABEL}${AREA}</div>`);
  });

  it('(f) size="lg"', () => {
    const { container } = render(<Textarea id="t" label="Name" size="lg" />);
    expect(container.innerHTML).toBe(`<div class="comp-field comp-field--lg">${LABEL}${AREA}</div>`);
  });

  it('(g) fullWidth', () => {
    const { container } = render(<Textarea id="t" label="Name" fullWidth />);
    expect(container.innerHTML).toBe(`<div class="comp-field comp-field--full">${LABEL}${AREA}</div>`);
  });

  it('(h) className', () => {
    const { container } = render(<Textarea id="t" label="Name" className="x-layout" />);
    expect(container.innerHTML).toBe(`<div class="comp-field x-layout">${LABEL}${AREA}</div>`);
  });

  it('(i) rows, value, onChange, maxLength, placeholder, disabled, aria-label, data-testid', () => {
    const { container } = render(
      <Textarea
        id="t"
        rows={4}
        value="v"
        onChange={() => {}}
        maxLength={10}
        placeholder="ph"
        disabled
        aria-label="al"
        data-testid="tid"
      />,
    );
    expect(container.innerHTML).toBe(
      '<div class="comp-field">' +
        '<textarea id="t" class="comp-field__textarea" rows="4" maxlength="10" placeholder="ph" disabled="" aria-label="al" data-testid="tid">v</textarea></div>',
    );
  });
});

describe('TextareaControl', () => {
  it('renders a single textarea with no wrapper div or label', () => {
    const { container } = render(<TextareaControl />);
    expect(container.children).toHaveLength(1);
    expect(container.firstElementChild?.tagName).toBe('TEXTAREA');
  });

  it('applies size classes and appends className last', () => {
    const { container, rerender } = render(<TextareaControl />);
    const cls = () => container.querySelector('textarea')?.className;
    expect(cls()).toBe('comp-field__textarea');
    rerender(<TextareaControl size="sm" />);
    expect(cls()).toBe('comp-field__textarea comp-field__textarea--sm');
    rerender(<TextareaControl size="lg" />);
    expect(cls()).toBe('comp-field__textarea comp-field__textarea--lg');
    rerender(<TextareaControl size="md" className="x" />);
    expect(cls()).toBe('comp-field__textarea x');
    rerender(<TextareaControl size="sm" className="x" />);
    expect(cls()).toBe('comp-field__textarea comp-field__textarea--sm x');
  });

  it('object ref receives the textarea element', () => {
    const ref = createRef<HTMLTextAreaElement>();
    const { container } = render(<TextareaControl ref={ref} />);
    expect(ref.current).toBeInstanceOf(HTMLTextAreaElement);
    expect(ref.current).toBe(container.querySelector('textarea'));
  });

  it('function ref receives the textarea element', () => {
    const ref = vi.fn();
    const { container } = render(<TextareaControl ref={ref} />);
    expect(ref).toHaveBeenCalledWith(container.querySelector('textarea'));
  });

  it('passes attributes to the same element', () => {
    const { container } = render(
      <TextareaControl
        value="v"
        onChange={() => {}}
        rows={3}
        maxLength={9}
        disabled
        placeholder="ph"
        aria-label="al"
        data-testid="tid"
        id="i"
        required
      />,
    );
    const el = container.querySelector('textarea') as HTMLTextAreaElement;
    expect(el.value).toBe('v');
    expect(el.getAttribute('rows')).toBe('3');
    expect(el.getAttribute('maxlength')).toBe('9');
    expect(el.disabled).toBe(true);
    expect(el.getAttribute('placeholder')).toBe('ph');
    expect(el.getAttribute('aria-label')).toBe('al');
    expect(el.getAttribute('data-testid')).toBe('tid');
    expect(el.id).toBe('i');
    expect(el.required).toBe(true);
  });

  it('calls handlers on input, Enter and blur without preventing Enter default', async () => {
    const onChange = vi.fn();
    const onBlur = vi.fn();
    let prevented: boolean | null = null;
    const onKeyDown = vi.fn((e: React.KeyboardEvent) => {
      prevented = e.defaultPrevented;
    });
    const { container } = render(
      <TextareaControl onChange={onChange} onBlur={onBlur} onKeyDown={onKeyDown} />,
    );
    const el = container.querySelector('textarea') as HTMLTextAreaElement;
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

  it('omits rows, placeholder, maxLength and id attributes when unspecified', () => {
    const { container } = render(<TextareaControl />);
    const el = container.querySelector('textarea') as HTMLTextAreaElement;
    expect(el.hasAttribute('rows')).toBe(false);
    expect(el.hasAttribute('placeholder')).toBe(false);
    expect(el.hasAttribute('maxlength')).toBe(false);
    expect(el.hasAttribute('id')).toBe(false);
  });

  it('sets id on the same element when given', () => {
    const { container } = render(<TextareaControl id="abc" />);
    expect(container.querySelector('textarea')?.getAttribute('id')).toBe('abc');
  });
});

describe('TextareaControl variants', () => {
  it.each(['karte', 'embedded', 'composer', 'schedule'] as const)(
    'variant %s outputs its class before className',
    (variant) => {
      const { container } = render(<TextareaControl variant={variant} className="x" />);
      expect(container.querySelector('textarea')?.className).toBe(
        `comp-field__textarea comp-textarea--${variant} x`,
      );
    },
  );

  it('variant standard outputs the same class as no variant', () => {
    const { container } = render(<TextareaControl variant="standard" size="sm" />);
    expect(container.querySelector('textarea')?.className).toBe(
      'comp-field__textarea comp-field__textarea--sm',
    );
  });

  it('rejects size together with a non-standard variant at type level', () => {
    // @ts-expect-error variant="karte" cannot be combined with size="sm"
    const el = <TextareaControl variant="karte" size="sm" />;
    expect(el).toBeTruthy();
  });

  it('embedded variant forwards ref and leaves Enter default unprevented', async () => {
    const ref = createRef<HTMLTextAreaElement>();
    let prevented: boolean | null = null;
    const onKeyDown = vi.fn((e: React.KeyboardEvent) => {
      prevented = e.defaultPrevented;
    });
    const { container } = render(
      <TextareaControl variant="embedded" ref={ref} onKeyDown={onKeyDown} />,
    );
    const el = container.querySelector('textarea') as HTMLTextAreaElement;
    expect(ref.current).toBe(el);
    const user = userEvent.setup();
    await user.click(el);
    await user.keyboard('{Enter}');
    expect(onKeyDown).toHaveBeenCalled();
    expect(prevented).toBe(false);
  });
});

describe('TextareaControl textStyle', () => {
  it('textStyle code adds comp-textarea--code after size/variant and before className', () => {
    const { container } = render(<TextareaControl textStyle="code" className="x" />);
    expect(container.querySelector('textarea')?.className).toBe('comp-field__textarea comp-textarea--code x');
    const { container: c2 } = render(<TextareaControl size="sm" textStyle="code" />);
    expect(c2.querySelector('textarea')?.className).toBe('comp-field__textarea comp-field__textarea--sm comp-textarea--code');
  });

  it('adds no class when textStyle is unspecified or normal', () => {
    const { container } = render(<TextareaControl />);
    expect(container.querySelector('textarea')?.className).toBe('comp-field__textarea');
    const { container: c2 } = render(<TextareaControl textStyle="normal" />);
    expect(c2.querySelector('textarea')?.className).toBe('comp-field__textarea');
    expect(c2.querySelector('textarea')?.hasAttribute('textstyle')).toBe(false);
  });
});

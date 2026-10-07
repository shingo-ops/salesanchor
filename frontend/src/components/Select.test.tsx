import { createRef } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { Select, SelectControl, type SelectOption, type SelectSize } from './Select';

afterEach(cleanup);

const OPTIONS: SelectOption[] = [
  { value: 'a', label: 'A' },
  { value: 'b', label: 'B', disabled: true },
  { value: 'c', label: 'C' },
];

const BARE_CLASS: Record<SelectSize, Record<'normal' | 'full', string>> = {
  sm: {
    normal: 'comp-select__control comp-select__control--sm x',
    full: 'comp-select__control comp-select__control--sm comp-select__control--full x',
  },
  md: {
    normal: 'comp-select__control x',
    full: 'comp-select__control comp-select__control--full x',
  },
  lg: {
    normal: 'comp-select__control comp-select__control--lg x',
    full: 'comp-select__control comp-select__control--lg comp-select__control--full x',
  },
};

const WRAPPER_CLASS: Record<SelectSize, Record<'normal' | 'full', string>> = {
  sm: { normal: 'comp-field comp-field--sm', full: 'comp-field comp-field--sm comp-field--full' },
  md: { normal: 'comp-field', full: 'comp-field comp-field--full' },
  lg: { normal: 'comp-field comp-field--lg', full: 'comp-field comp-field--lg comp-field--full' },
};

const SIZES: SelectSize[] = ['sm', 'md', 'lg'];
const PLACEHOLDERS = [undefined, 'Pick'] as const;
const REQUIRED = [false, true] as const;
const FULL = [false, true] as const;

function readOptions(select: HTMLSelectElement) {
  return Array.from(select.options).map((o) => ({ value: o.value, text: o.text, disabled: o.disabled }));
}

function expectedOptions(placeholder: string | undefined, required: boolean) {
  const base = [
    { value: 'a', text: 'A', disabled: false },
    { value: 'b', text: 'B', disabled: true },
    { value: 'c', text: 'C', disabled: false },
  ];
  return placeholder === undefined ? base : [{ value: '', text: placeholder, disabled: required }, ...base];
}

describe('SelectControl options mode output (frozen)', () => {
  for (const size of SIZES) {
    for (const fullWidth of FULL) {
      for (const placeholder of PLACEHOLDERS) {
        for (const required of REQUIRED) {
          const label = `size=${size} full=${fullWidth} placeholder=${placeholder} required=${required}`;

          it(`bare: ${label}`, () => {
            const { container } = render(
              <SelectControl options={OPTIONS} size={size} fullWidth={fullWidth} placeholder={placeholder} required={required} appearance="bare" className="x" />,
            );
            const select = container.querySelector('select') as HTMLSelectElement;
            expect(container.children).toHaveLength(1);
            expect(select.className).toBe(BARE_CLASS[size][fullWidth ? 'full' : 'normal']);
            expect(readOptions(select)).toEqual(expectedOptions(placeholder, required));
            expect(select.required).toBe(required);
          });

          it(`field: ${label}`, () => {
            const { container } = render(
              <SelectControl options={OPTIONS} size={size} fullWidth={fullWidth} placeholder={placeholder} required={required} appearance="field" className="x" />,
            );
            const select = container.querySelector('select') as HTMLSelectElement;
            expect(select.className).toBe('comp-field__select x');
            expect(readOptions(select)).toEqual(expectedOptions(placeholder, required));
          });

          it(`Select: ${label}`, () => {
            const { container } = render(
              <Select id="i" options={OPTIONS} size={size} fullWidth={fullWidth} placeholder={placeholder} required={required} />,
            );
            const wrapper = container.firstElementChild as HTMLElement;
            const select = container.querySelector('select') as HTMLSelectElement;
            expect(wrapper.className).toBe(WRAPPER_CLASS[size][fullWidth ? 'full' : 'normal']);
            expect(select.className).toBe('comp-field__select');
            expect(readOptions(select)).toEqual(expectedOptions(placeholder, required));
          });
        }
      }
    }
  }

  it('defaults to bare md without placeholder and keeps class before native attributes', () => {
    const { container } = render(<SelectControl options={OPTIONS} name="n" />);
    expect(container.innerHTML).toBe(
      '<select class="comp-select__control" name="n"><option value="a">A</option><option value="b" disabled="">B</option><option value="c">C</option></select>',
    );
  });

  it('Select renders label, required mark and error hint as before', () => {
    const { container } = render(<Select id="i" label="L" required error="E" options={OPTIONS} />);
    expect(container.innerHTML).toBe(
      '<div class="comp-field comp-field--error"><label for="i" class="comp-field__label">L<span class="comp-field__required" aria-hidden="true">*</span></label><select class="comp-field__select" id="i" required=""><option value="a">A</option><option value="b" disabled="">B</option><option value="c">C</option></select><p class="comp-field__hint comp-field__hint--error" role="alert">E</p></div>',
    );
  });
});

describe('SelectControl children mode', () => {
  it('keeps fixed options as given', () => {
    const { container } = render(
      <SelectControl>
        <option value="a">A</option>
        <option value="b" disabled>B</option>
      </SelectControl>,
    );
    const select = container.querySelector('select') as HTMLSelectElement;
    expect(container.children).toHaveLength(1);
    expect(readOptions(select)).toEqual([
      { value: 'a', text: 'A', disabled: false },
      { value: 'b', text: 'B', disabled: true },
    ]);
  });

  it('keeps options generated by map in order', () => {
    const { container } = render(
      <SelectControl>
        {OPTIONS.map((o) => (
          <option key={o.value} value={o.value} disabled={o.disabled}>{o.label}</option>
        ))}
      </SelectControl>,
    );
    expect(readOptions(container.querySelector('select') as HTMLSelectElement)).toEqual(expectedOptions(undefined, false));
  });

  it.each([true, false])('keeps option + conditional expression (show=%s)', (show) => {
    const { container } = render(
      <SelectControl>
        <option value="a">A</option>
        {show && <option value="extra">Extra</option>}
      </SelectControl>,
    );
    const expected = [{ value: 'a', text: 'A', disabled: false }];
    if (show) expected.push({ value: 'extra', text: 'Extra', disabled: false });
    expect(readOptions(container.querySelector('select') as HTMLSelectElement)).toEqual(expected);
  });

  it('keeps an empty-value option without adding a placeholder', () => {
    const { container } = render(
      <SelectControl required>
        <option value="">None</option>
        <option value="a">A</option>
      </SelectControl>,
    );
    expect(readOptions(container.querySelector('select') as HTMLSelectElement)).toEqual([
      { value: '', text: 'None', disabled: false },
      { value: 'a', text: 'A', disabled: false },
    ]);
  });

  it('applies the same class assembly as options mode', () => {
    const { container } = render(
      <SelectControl size="sm" fullWidth className="x"><option value="a">A</option></SelectControl>,
    );
    expect((container.querySelector('select') as HTMLSelectElement).className).toBe(BARE_CLASS.sm.full);
  });
});

describe('SelectControl ref', () => {
  it('passes an object ref to the native select', () => {
    const ref = createRef<HTMLSelectElement>();
    render(<SelectControl ref={ref} options={OPTIONS} defaultValue="c" />);
    const node = screen.getByRole('combobox');
    expect(ref.current).toBe(node);
    expect(ref.current).toBeInstanceOf(HTMLSelectElement);
    ref.current?.focus();
    expect(document.activeElement).toBe(node);
    expect(ref.current?.value).toBe('c');
  });

  it('passes a callback ref to the native select in children mode', () => {
    let node: HTMLSelectElement | null = null;
    render(
      <SelectControl ref={(el) => { node = el; }} defaultValue="a">
        <option value="a">A</option>
      </SelectControl>,
    );
    expect(node).toBe(screen.getByRole('combobox'));
    expect(node).toBeInstanceOf(HTMLSelectElement);
    (node as unknown as HTMLSelectElement).focus();
    expect(document.activeElement).toBe(node);
    expect((node as unknown as HTMLSelectElement).value).toBe('a');
  });

  it('has displayName SelectControl', () => {
    expect(SelectControl.displayName).toBe('SelectControl');
  });
});

describe('SelectControl native attribute passthrough', () => {
  it.each(['options', 'children'] as const)('forwards native attributes to the same select (%s mode)', (mode) => {
    const onChange = vi.fn((e: { target: { value: string } }) => e.target.value);
    const onBlur = vi.fn();
    const common = {
      name: 'field',
      id: 'sel',
      disabled: false,
      required: true,
      'aria-label': 'Pick one',
      'data-testid': 'ctl',
      defaultValue: 'a',
      onChange,
      onBlur,
    };
    const { container } = mode === 'options'
      ? render(<SelectControl options={OPTIONS} {...common} />)
      : render(<SelectControl {...common}>{OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</SelectControl>);
    const select = screen.getByTestId('ctl') as HTMLSelectElement;
    expect(container.querySelectorAll('select')).toHaveLength(1);
    expect(select.name).toBe('field');
    expect(select.id).toBe('sel');
    expect(select.required).toBe(true);
    expect(select.disabled).toBe(false);
    expect(select.getAttribute('aria-label')).toBe('Pick one');
    expect(select.value).toBe('a');
    fireEvent.change(select, { target: { value: 'c' } });
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange.mock.results[0].value).toBe('c');
    fireEvent.blur(select);
    expect(onBlur).toHaveBeenCalledTimes(1);
  });

  it('supports controlled value and disabled', () => {
    render(<SelectControl options={OPTIONS} value="c" onChange={() => {}} disabled data-testid="ctl" />);
    const select = screen.getByTestId('ctl') as HTMLSelectElement;
    expect(select.value).toBe('c');
    expect(select.disabled).toBe(true);
  });
});

describe('SelectControl indicator', () => {
  it.each(['bare', 'field'] as const)('adds comp-select--no-indicator for appearance=%s', (appearance) => {
    const { container } = render(<SelectControl options={OPTIONS} appearance={appearance} indicator="none" className="x" />);
    const select = container.querySelector('select') as HTMLSelectElement;
    expect(select.classList.contains('comp-select--no-indicator')).toBe(true);
    expect(select.className.endsWith(' x')).toBe(true);
  });

  it.each(['bare', 'field'] as const)('omits the class when unspecified or default (appearance=%s)', (appearance) => {
    const unspecified = render(<SelectControl options={OPTIONS} appearance={appearance} />);
    expect(unspecified.container.querySelector('.comp-select--no-indicator')).toBeNull();
    cleanup();
    const explicit = render(<SelectControl options={OPTIONS} appearance={appearance} indicator="default" />);
    expect(explicit.container.querySelector('.comp-select--no-indicator')).toBeNull();
  });

  it('adds the class in children mode too', () => {
    const { container } = render(<SelectControl indicator="none"><option value="a">A</option></SelectControl>);
    expect((container.querySelector('select') as HTMLSelectElement).className).toBe('comp-select__control comp-select--no-indicator');
  });
});

describe('SelectControl type exclusivity', () => {
  it('rejects options with children and children with placeholder at compile time', () => {
    const render1 = () => (
      // @ts-expect-error options and children cannot be combined
      <SelectControl options={OPTIONS}><option value="a">A</option></SelectControl>
    );
    const render2 = () => (
      // @ts-expect-error children and placeholder cannot be combined
      <SelectControl placeholder="Pick"><option value="a">A</option></SelectControl>
    );
    expect(typeof render1).toBe('function');
    expect(typeof render2).toBe('function');
  });
});

describe('SelectControl variant', () => {
  const VARIANTS = ['karte', 'header', 'tabbar'] as const;

  it.each(VARIANTS)('adds comp-select--%s after indicator and before className (options mode)', (variant) => {
    const { container } = render(<SelectControl options={OPTIONS} variant={variant} indicator="none" className="x" />);
    expect((container.querySelector('select') as HTMLSelectElement).className).toBe(
      `comp-select__control comp-select--no-indicator comp-select--${variant} x`,
    );
  });

  it.each(VARIANTS)('adds comp-select--%s in children mode', (variant) => {
    const { container } = render(<SelectControl variant={variant} className="x"><option value="a">A</option></SelectControl>);
    expect((container.querySelector('select') as HTMLSelectElement).className).toBe(`comp-select__control comp-select--${variant} x`);
  });

  it.each(['unspecified', 'standard'] as const)('omits any variant class when variant is %s', (mode) => {
    const props = mode === 'standard' ? { variant: 'standard' as const } : {};
    const options = render(<SelectControl options={OPTIONS} {...props} className="x" />);
    expect((options.container.querySelector('select') as HTMLSelectElement).className).toBe('comp-select__control x');
    cleanup();
    const children = render(<SelectControl {...props} className="x"><option value="a">A</option></SelectControl>);
    expect((children.container.querySelector('select') as HTMLSelectElement).className).toBe('comp-select__control x');
  });

  it('does not forward variant to the DOM', () => {
    const { container } = render(<SelectControl options={OPTIONS} variant="karte" />);
    expect((container.querySelector('select') as HTMLSelectElement).hasAttribute('variant')).toBe(false);
  });

  it('accepts standard only for appearance=field and rejects other variants at compile time', () => {
    const ok = () => <SelectControl options={OPTIONS} appearance="field" variant="standard" />;
    const ng = () => (
      // @ts-expect-error appearance=field accepts only the standard variant
      <SelectControl options={OPTIONS} appearance="field" variant="karte" />
    );
    expect(typeof ok).toBe('function');
    expect(typeof ng).toBe('function');
  });
});

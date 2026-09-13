import { createRef } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import { Check, type IconProps } from './icons';

afterEach(cleanup);

describe('Icon public SVG contract', () => {
  it.each([undefined, 14, '1em'] as const)('keeps size %s and the real Heroicons SVG', (size) => {
    const ref = createRef<SVGSVGElement>();
    const { container, rerender, unmount } = render(<Check ref={ref} size={size} weight="bold" className="usage-color" />);
    const svg = container.querySelector('svg')!;
    expect(ref.current).toBe(svg);
    expect(svg.getAttribute('width')).toBe(String(size ?? 24));
    expect(svg.getAttribute('height')).toBe(String(size ?? 24));
    expect(svg.getAttribute('fill')).toBe('currentColor');
    expect(svg.querySelector('path')).not.toBeNull();
    expect(svg.getAttribute('class')).toBe('usage-color');
    expect(svg.hasAttribute('weight')).toBe(false);
    rerender(<Check ref={ref} size={20} />);
    expect(ref.current).toBe(svg);
    expect(svg.getAttribute('width')).toBe('20');
    unmount();
    expect(ref.current).toBeNull();
  });

  it('defaults omitted aria-hidden to true', () => {
    const { container } = render(<Check />);
    expect(container.querySelector('svg')?.getAttribute('aria-hidden')).toBe('true');
  });

  it.each([undefined, true, false, 'false'] as const)('preserves explicit aria-hidden=%s', (hidden) => {
    const { container } = render(<Check aria-hidden={hidden} />);
    expect(container.querySelector('svg')?.getAttribute('aria-hidden')).toBe(String(hidden ?? true));
  });

  it('forwards the six allowed accessibility attributes and removes them on rerender', () => {
    const { container, rerender } = render(<Check aria-hidden={false} aria-label="Done"
      aria-labelledby="caption" aria-describedby="description" role="img" focusable="false" />);
    const svg = container.querySelector('svg')!;
    const expected = { 'aria-hidden': 'false', 'aria-label': 'Done', 'aria-labelledby': 'caption',
      'aria-describedby': 'description', role: 'img', focusable: 'false' };
    for (const [name, value] of Object.entries(expected)) expect(svg.getAttribute(name)).toBe(value);
    rerender(<Check />);
    expect(svg.getAttribute('aria-hidden')).toBe('true');
    for (const name of Object.keys(expected).filter((key) => key !== 'aria-hidden')) expect(svg.hasAttribute(name)).toBe(false);
  });

  it('does not automatically reveal a labelled decorative icon', () => {
    const { container } = render(<Check aria-label="Done" role="img" />);
    expect(container.querySelector('svg')?.getAttribute('aria-hidden')).toBe('true');
  });

  it('typechecks the narrow API and retains numeric/string size and SVG refs', () => {
    const ref = createRef<SVGSVGElement>();
    const valid: IconProps = { size: '1em', weight: 'bold', 'aria-hidden': false, focusable: false };
    const nodes = [<Check {...valid} ref={ref} />, <Check size={14} ref={ref} />,
      // @ts-expect-error Style is owned by named usage CSS, not the Icon API.
      <Check style={{ marginRight: 8 }} />,
      // @ts-expect-error Color is inherited from usage CSS, not the Icon API.
      <Check color="red" />];
    expect(nodes).toHaveLength(4);
  });
});

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import { Stack } from './Stack';
import { TwoColumn } from './TwoColumn';

afterEach(cleanup);

describe('Stack', () => {
  it('defaults to gap 3 and renders children in order', () => {
    const { container } = render(<Stack><span>a</span><span>b</span></Stack>);
    const root = container.firstElementChild as HTMLElement;
    expect(root.className).toBe('comp-stack comp-stack--gap-3');
    expect(Array.from(root.children).map((c) => c.textContent)).toEqual(['a', 'b']);
  });

  it('applies the requested gap step and extra className', () => {
    const { container } = render(<Stack gap="2" className="x">a</Stack>);
    expect((container.firstElementChild as HTMLElement).className).toBe('comp-stack comp-stack--gap-2 x');
  });
});

describe('TwoColumn', () => {
  it('defaults to 1:2, gap 3, align start', () => {
    const { container } = render(<TwoColumn><i>l</i><i>r</i></TwoColumn>);
    const root = container.firstElementChild as HTMLElement;
    expect(root.className).toBe(
      'comp-two-column comp-two-column--ratio-1-2 comp-two-column--gap-3 comp-two-column--align-start',
    );
    expect(root.children).toHaveLength(2);
  });

  it('applies ratio, gap and align props', () => {
    const { container } = render(<TwoColumn ratio="1:1" gap="6" align="center">x</TwoColumn>);
    expect((container.firstElementChild as HTMLElement).className).toBe(
      'comp-two-column comp-two-column--ratio-1-1 comp-two-column--gap-6 comp-two-column--align-center',
    );
  });
});

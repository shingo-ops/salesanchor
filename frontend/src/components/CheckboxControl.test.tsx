import { readdirSync, readFileSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
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
    expect(el.className).toBe('comp-checkbox-control');
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

  it('adds comp-checkbox-control--sm when size is sm', () => {
    render(<CheckboxControl size="sm" checked={false} onChange={() => {}} aria-label="x" />);
    expect(screen.getByRole('checkbox').className).toBe('comp-checkbox-control comp-checkbox-control--sm');
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

  it('applies dataColor as accent-color and adds no style attribute without it', () => {
    render(<CheckboxControl dataColor="rgb(18, 52, 86)" checked onChange={() => {}} aria-label="c" />);
    expect((screen.getByLabelText('c') as HTMLInputElement).style.accentColor).toBe('rgb(18, 52, 86)');
    cleanup();
    render(<CheckboxControl checked onChange={() => {}} aria-label="d" />);
    expect((screen.getByLabelText('d') as HTMLInputElement).hasAttribute('style')).toBe(false);
  });
});

// dataColor の使い手は登録制（design.md:826 データ由来の色だけ。通常 UI の色をこの口で通さない）。
// 新しい使い手は下の登録表を書き換える PR になり、審査で止まる。
// 注: この試験は dataColor という名前の口だけを数える。別の部品が同じ名前の口を持つ場合は登録表を部品ごとに分ける（Badge は dataBackground / dataForeground で色を受けるので対象外、design.md:874）。
describe('CheckboxControl dataColor registry (AY-4c-2b)', () => {
  const srcRoot = resolve(__dirname, '..');
  const walk = (dir: string): string[] =>
    readdirSync(dir, { withFileTypes: true }).flatMap((d) => {
      const full = join(dir, d.name);
      if (d.isDirectory()) return walk(full);
      return /\.tsx?$/.test(d.name) ? [full] : [];
    });
  const files = walk(srcRoot)
    .map((f) => relative(srcRoot, f))
    .filter((rel) => !/\.test\.tsx?$/.test(rel) && !/\.stories\.tsx$/.test(rel) && rel !== 'components/CheckboxControl.tsx');
  const registry: Array<[string, number]> = [['pages/schedule/SchedulePageImpl.tsx', 2]];

  it('dataColor appears only in the registered files with the registered counts', () => {
    const found: Array<[string, number]> = [];
    for (const rel of files) {
      const n = readFileSync(join(srcRoot, rel), 'utf8').match(/\bdataColor\b\s*[=:]/g)?.length ?? 0;
      if (n > 0) found.push([rel, n]);
    }
    expect(found.sort()).toEqual([...registry].sort());
  });

  it.each(registry)('%s passes only dataColor={owner.color}', (rel, count) => {
    const src = readFileSync(join(srcRoot, rel), 'utf8');
    expect(src.match(/\bdataColor\b\s*=\s*\{owner\.color\}/g)?.length).toBe(count);
  });
});

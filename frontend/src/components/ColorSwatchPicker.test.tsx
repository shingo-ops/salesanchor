import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { ColorSwatchPicker, type ColorSwatchOption } from './ColorSwatchPicker';

afterEach(cleanup);

function makeOptions(count: number): ColorSwatchOption[] {
  const options: ColorSwatchOption[] = [{ value: null, label: 'Default', color: 'var(--accent)' }];
  for (let i = 1; i < count; i += 1) {
    options.push({ value: `c${i}`, label: `Color ${i}`, color: `var(--event-color-c${i})` });
  }
  return options;
}

function open() {
  fireEvent.click(screen.getByRole('button', { name: /Event color/ }));
}

describe('ColorSwatchPicker', () => {
  it('opens the radiogroup only after the button is pressed', () => {
    render(<ColorSwatchPicker label="Event color" name="n" options={makeOptions(3)} value={null} onChange={() => {}} />);
    expect(screen.queryByRole('radiogroup')).toBeNull();
    const button = screen.getByRole('button', { name: /Event color/ });
    expect(button.getAttribute('aria-expanded')).toBe('false');
    fireEvent.click(button);
    expect(screen.getByRole('radiogroup')).toBeTruthy();
    expect(button.getAttribute('aria-expanded')).toBe('true');
    fireEvent.click(button);
    expect(screen.queryByRole('radiogroup')).toBeNull();
  });

  it('renders one radio per option (25)', () => {
    render(<ColorSwatchPicker label="Event color" name="n" options={makeOptions(25)} value={null} onChange={() => {}} />);
    open();
    expect(screen.getAllByRole('radio')).toHaveLength(25);
  });

  it('checks only the radio of the current value', () => {
    render(<ColorSwatchPicker label="Event color" name="n" options={makeOptions(5)} value="c2" onChange={() => {}} />);
    open();
    const radios = screen.getAllByRole('radio') as HTMLInputElement[];
    expect(radios.filter((r) => r.checked)).toHaveLength(1);
    expect((screen.getByRole('radio', { name: 'Color 2' }) as HTMLInputElement).checked).toBe(true);
  });

  it('calls onChange with the value (null for default)', () => {
    const fn = vi.fn();
    render(<ColorSwatchPicker label="Event color" name="n" options={makeOptions(5)} value="c2" onChange={fn} />);
    open();
    fireEvent.click(screen.getByRole('radio', { name: 'Color 3' }));
    expect(fn).toHaveBeenLastCalledWith('c3');
    fireEvent.click(screen.getByRole('radio', { name: 'Default' }));
    expect(fn).toHaveBeenLastCalledWith(null);
  });

  it('uses real radios sharing one name (arrow keys come from the native radio group)', () => {
    render(<ColorSwatchPicker label="Event color" name="shared-name" options={makeOptions(5)} value={null} onChange={() => {}} />);
    open();
    const radios = screen.getAllByRole('radio') as HTMLInputElement[];
    for (const radio of radios) {
      expect(radio.type).toBe('radio');
      expect(radio.name).toBe('shared-name');
    }
  });

  it('keeps the given color string as the swatch background', () => {
    render(<ColorSwatchPicker label="Event color" name="n" options={makeOptions(3)} value={null} onChange={() => {}} />);
    open();
    const swatch = screen.getByTitle('Color 1');
    expect(swatch.style.background).toBe('var(--event-color-c1)');
  });

  it('stays open after choosing a swatch', () => {
    render(<ColorSwatchPicker label="Event color" name="n" options={makeOptions(3)} value={null} onChange={() => {}} />);
    open();
    fireEvent.click(screen.getByRole('radio', { name: 'Color 1' }));
    expect(screen.getByRole('radiogroup')).toBeTruthy();
  });
});

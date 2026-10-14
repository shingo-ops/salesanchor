import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChoiceCardGroup, type ChoiceCardOption } from './ChoiceCardGroup';

afterEach(cleanup);

// jsdom には CSS.escape が無く、user-event の矢印キー（radio の移動）が使う
beforeAll(() => {
  const css = (globalThis as { CSS?: { escape?: (value: string) => string } }).CSS ?? {};
  css.escape ??= (value: string) => value.replace(/[^a-zA-Z0-9_-]/g, (char) => `\\${char}`);
  (globalThis as { CSS?: unknown }).CSS = css;
});

const OPTIONS: ChoiceCardOption<'a' | 'b' | 'c'>[] = [
  { value: 'a', label: 'Alpha', description: 'first' },
  { value: 'b', label: 'Beta' },
  { value: 'c', label: 'Gamma', disabled: true },
];

const renderGroup = (value: 'a' | 'b' | 'c' | null, onChange = vi.fn()) => {
  render(<ChoiceCardGroup legend="Pick one" name="t" options={OPTIONS} value={value} onChange={onChange} />);
  return onChange;
};

describe('ChoiceCardGroup', () => {
  it('shows the legend as the group name and every option', () => {
    renderGroup(null);
    expect(screen.getByRole('group', { name: 'Pick one' })).toBeTruthy();
    expect(screen.getAllByRole('radio').length).toBe(3);
    expect(screen.getByText('first')).toBeTruthy();
  });

  it('calls onChange with the value when a card is clicked', async () => {
    const onChange = renderGroup(null);
    await userEvent.click(screen.getByRole('radio', { name: /Beta/ }));
    expect(onChange).toHaveBeenCalledWith('b');
  });

  it('marks the card for value as checked', () => {
    renderGroup('b');
    expect((screen.getByRole('radio', { name: /Beta/ }) as HTMLInputElement).checked).toBe(true);
    expect((screen.getByRole('radio', { name: /Alpha/ }) as HTMLInputElement).checked).toBe(false);
  });

  it('does not call onChange for a disabled card', async () => {
    const onChange = renderGroup(null);
    await userEvent.click(screen.getByRole('radio', { name: /Gamma/ }));
    expect(onChange).not.toHaveBeenCalled();
  });

  it('moves to the next card with the arrow key', async () => {
    const onChange = renderGroup('a');
    screen.getByRole('radio', { name: /Alpha/ }).focus();
    await userEvent.keyboard('{ArrowDown}');
    expect(onChange).toHaveBeenCalledWith('b');
  });
});

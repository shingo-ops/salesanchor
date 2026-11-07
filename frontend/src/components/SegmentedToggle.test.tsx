import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { SegmentedToggle, type SegmentedOption } from './SegmentedToggle';
import type { Icon } from '../constants/icons';

afterEach(cleanup);

const Dummy = (() => <svg />) as unknown as Icon;
type V = 'off' | 'view' | 'edit';

const options = (over: Partial<Record<V, boolean>> = {}): SegmentedOption<V>[] => [
  { value: 'off', icon: Dummy, label: 'off-label', tone: 'danger', disabled: over.off },
  { value: 'view', icon: Dummy, label: 'view-label', tone: 'neutral', disabled: over.view },
  { value: 'edit', icon: Dummy, label: 'edit-label', tone: 'success', disabled: over.edit },
];

describe('SegmentedToggle', () => {
  it('calls onChange with the value of the pressed button', () => {
    const onChange = vi.fn();
    render(<SegmentedToggle options={options()} value="off" onChange={onChange} aria-label="row" />);
    fireEvent.click(screen.getByRole('radio', { name: 'edit-label' }));
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith('edit');
  });

  it('does not call onChange on a disabled option', () => {
    const onChange = vi.fn();
    render(<SegmentedToggle options={options({ view: true })} value="off" onChange={onChange} aria-label="row" />);
    fireEvent.click(screen.getByRole('radio', { name: 'view-label' }));
    expect(onChange).not.toHaveBeenCalled();
  });

  it('does not call onChange when the whole group is disabled', () => {
    const onChange = vi.fn();
    render(<SegmentedToggle options={options()} value="off" onChange={onChange} aria-label="row" disabled />);
    for (const name of ['off-label', 'view-label', 'edit-label']) {
      fireEvent.click(screen.getByRole('radio', { name }));
    }
    expect(onChange).not.toHaveBeenCalled();
  });

  it('sets aria-checked only on the selected option', () => {
    render(<SegmentedToggle options={options()} value="view" onChange={() => {}} aria-label="row" />);
    expect(screen.getByRole('radio', { name: 'off-label' }).getAttribute('aria-checked')).toBe('false');
    expect(screen.getByRole('radio', { name: 'view-label' }).getAttribute('aria-checked')).toBe('true');
    expect(screen.getByRole('radio', { name: 'edit-label' }).getAttribute('aria-checked')).toBe('false');
  });

  it('marks every option unchecked when value is null', () => {
    render(<SegmentedToggle options={options()} value={null} onChange={() => {}} aria-label="row" />);
    for (const r of screen.getAllByRole('radio')) {
      expect(r.getAttribute('aria-checked')).toBe('false');
    }
  });

  it('exposes the row name on the radiogroup', () => {
    render(<SegmentedToggle options={options()} value={null} onChange={() => {}} aria-label="row-name" />);
    expect(screen.getByRole('radiogroup', { name: 'row-name' })).toBeTruthy();
  });
});
